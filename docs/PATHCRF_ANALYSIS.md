# PathCRF: cómo funciona y qué nos sirve para el reto

> Análisis de la librería en `pathcrf/` (escrito el 2026-11-15, a dos días de la entrega del
> 17-nov-2026). Fuente: código del repositorio
> [hyunsungkim-ds/pathcrf](https://github.com/hyunsungkim-ds/pathcrf) y su README.

---

## TL;DR

- PathCRF detecta **quién tiene el balón y cuándo cambia, sin usar el balón**, solo con las
  trayectorias de los jugadores. Es justo nuestro problema en el 41 % de los frames evaluados donde
  el balón no aparece.
- **El modelo tal cual no encaja con nuestros datos**: necesita 22 jugadores con identidad estable
  y sin huecos. Nuestro ATD tiene 46 slots anónimos, con huecos e identity switches.
- **Lo más valioso son el dataset externo y las ideas**:
  1. Sportec Open DFL: datos externos con tracking, eventos y estado del balón (vivo/muerto y
     equipo dueño). Es lo que necesitamos para tunear sin romper las reglas.
  2. Decodificación con **transiciones restringidas** (Viterbi), que elimina el parpadeo.
  3. Un **filtro de duración mínima** de posesión.
- Recomendación para estos dos días: un pipeline ligero en numpy con estas ideas, con los
  parámetros ajustados sobre Sportec. No reentrenar PathCRF.

---

## 1. Qué es

Es el código oficial del paper *PathCRF: Ball-Free Soccer Event Detection via Possession Path
Inference from Player Trajectories* (Hyunsung Kim et al., KDD 2026). Detecta eventos con balón
(pases, controles, salidas del campo) a partir de las posiciones de los jugadores, sin acceso a la
posición del balón.

## 2. Cómo funciona, paso a paso

### 2.1 La idea central: la posesión es "elegir una arista"

Cada instante del partido se representa como un grafo con **26 nodos**:

- 11 jugadores del equipo que ataca hacia la derecha
- 11 jugadores del otro equipo
- 4 nodos "fuera del campo": `out_left`, `out_right`, `out_bottom`, `out_top`

En cada paso de tiempo el modelo elige **exactamente una arista**:

| arista | significado |
|---|---|
| `A → A` (bucle) | el jugador A controla el balón |
| `A → B` | el balón viaja de A a B (pase en vuelo, a un compañero o a un rival) |
| `A → out` | el balón sale del campo |
| `out → out` | el balón sigue fuera |

Con esto, la "posesión" deja de ser una clasificación frame a frame y pasa a ser **un camino por
el grafo a lo largo del tiempo**.

### 2.2 Cómo construyen las etiquetas de entrenamiento

Archivo: `datatools/preprocess.py`. Usan **event data + tracking** del Sportec Open DFL Dataset
(7 partidos de la Bundesliga):

1. **Simplifican la trayectoria del balón** con el algoritmo RDP (Ramer-Douglas-Peucker) y marcan
   como "toque" cada punto donde el balón cambia de dirección 15° o más.
2. **Alinean esos toques con los eventos manuales** mediante Needleman-Wunsch (programación
   dinámica, como al alinear secuencias de ADN), porque los timestamps de los eventos manuales son
   imprecisos.
3. **Asignan cada toque al jugador más cercano**, a menos de 5 m (`POSS_MAX_DIST`).
4. **Rellenan los frames intermedios** (`merge_tracking_poss`): si el poseedor anterior y el
   siguiente son el mismo jugador, ese jugador posee; si no, el frame queda "en tránsito".

### 2.3 El modelo neuronal

Archivo: `models/set_lstm.py`.

- **Set Transformer por equipo**: procesa a los jugadores como un conjunto, así que el orden en que
  se listan no importa. Features por jugador: posición, velocidad, aceleración, equipo y si es
  portero.
- **Atención temporal (SAB)** sobre ventanas de 10 segundos, muestreadas a 5 fps.
- Dos niveles de salida:
  - **macro**: quién fue el poseedor anterior y quién será el siguiente;
  - **micro**: una puntuación (logit) para cada una de las 26×26 aristas posibles.

### 2.4 El CRF: la pieza clave

Archivo: `models/dynamic_sparse_crf.py`. El decodificador (Viterbi) **prohíbe transiciones
imposibles**:

- Desde `A → A` (A controla), lo siguiente tiene que salir de A: A sigue con el balón, pasa, o el
  balón sale.
- Desde `A → B` (balón en vuelo), solo se puede seguir en vuelo o que B lo controle o lo reenvíe.
- Desde `A → out`, solo se puede pasar a `out → out`.

Las puntuaciones de las transiciones permitidas se aprenden. Resultado: la secuencia no puede
"teletransportar" el balón ni parpadear entre equipos frame a frame.

### 2.5 Inferencia y postprocesado

- `inference.py`: ventanas solapadas al 50 % y promedio ponderado de los logits para procesar
  partidos completos. Incluye **Viterbi y greedy con restricciones que no dependen de la red**
  (`_viterbi_constrained_decode`, `_greedy_constrained_decode`): funcionan con cualquier matriz de
  puntuaciones.
- `datatools/postprocess.py`: `_overwrite_short_self_loops(min_dur)` elimina las posesiones
  demasiado cortas, absorbiéndolas en el estado siguiente.

### 2.6 Modelos entrenados incluidos

En `saved/100` … `saved/140` (el 140, con CRF dinámico disperso, es el mejor). Su log de
validación da `edge_acc 0.71`, `src_acc 0.80` y `dst_acc 0.85`. Esa precisión es **a nivel de
jugador**; a nivel de equipo, que es lo que nos piden, debería ser bastante mayor.

---

## 3. Qué nos sirve (de más a menos importante)

### 3.1 Sportec Open DFL como dataset externo, lo más valioso

Las reglas obligan a entrenar y ajustar **solo con datos externos**. Sportec tiene:

- tracking limpio de 7 partidos profesionales, a 25 fps (igual que nosotros);
- event data ya sincronizado (`pathcrf/data/sportec_synced`);
- por cada frame, **`ball_state` (vivo/muerto)** y **`ball_owning_team_id`**.

Ese último punto importa mucho: nuestro ground truth se generó así ("`D` donde el tracking
corregido marca el balón muerto; si no, el equipo dueño"). Con Sportec se pueden fabricar
etiquetas **H/A/D con la misma semántica** y usarlas para tunear y para elegir entre versiones con
`evaluation/possession_metrics.py`.

### 3.2 Estados y transiciones restringidas, adaptados a nivel de equipo

No hace falta copiar las 576 aristas. Basta con un **HMM de equipo** inspirado en las mismas reglas:

```
H-control ──► H-en-vuelo ──► H-control      (pase entre compañeros)
H-control ──► H-en-vuelo ──► A-control      (pérdida → cambio de posesión)
H-control ──► D                             (balón fuera)
D ──► H-control | A-control                 (reanudación)
```

La clave es que **un balón en vuelo sigue contando para el equipo que lo soltó** hasta que el rival
lo controla. Es exactamente la regla del reto: "si el balón está disputado o suelto, la posesión
sigue con el último equipo". El estado en vuelo se convierte a `H` o `A` al escribir el CSV.
`_viterbi_constrained_decode` de `inference.py` sirve como plantilla.

### 3.3 Filtro de duración mínima

`_overwrite_short_self_loops(min_dur)` equivale a la regla de **"control sostenido"** del reto. Es
lo que más ayuda con `spellF1`, que castiga mucho partir una posesión en dos. El valor de `min_dur`
se ajusta con Sportec, nunca con nuestro partido.

### 3.4 Detección de toques con RDP

En los tramos donde **sí** vemos el balón, los cambios bruscos de dirección son candidatos a toque
o pase. Combinados con "qué jugador está más cerca", dan instantes candidatos de cambio de
posesión.

### 3.5 Adaptador de Metrica (`datatools/metrica_data.py`)

`MetricaData.label_possessions` convierte event data de Metrica en posesión por frame. Si usamos los
**partidos de muestra abiertos de Metrica** como segundo dataset externo (mismo proveedor que
nuestro ATD y mismas coordenadas 0–1), la conversión está casi hecha. **Hay que verificar su
licencia.**

### 3.6 Inyección de ruido (`datatools/preprocess_noise.py`)

Degrada tracking limpio fusionando jugadores cercanos (oclusiones), añadiendo sesgo de posición y
outliers. Sirve para que Sportec se parezca a nuestro ATD ruidoso. **Faltaría añadir**:

- quitar el balón en ~41 % de los frames, más en zonas abarrotadas;
- fragmentar tracks y crear identity switches;
- anonimizar a los jugadores (slots sin identidad).

### 3.7 De eventos a posesión por equipo (`applications/team_poss.py`)

`compute_team_poss(..., mode="split")` asigna equipo a cada frame a partir de los eventos. Es útil
para generar etiquetas externas por un segundo camino y contrastarlas con las de `ball_owning_team_id`.

---

## 4. Por qué no usar el modelo tal cual

| problema | detalle |
|---|---|
| **Necesita identidades estables** | 11 contra 11 con el mismo jugador en cada nodo durante toda la ventana, porque la atención temporal se aplica nodo a nodo. Nuestro ATD: 46 slots sin identidad, que aparecen, desaparecen y se intercambian. |
| **No tolera huecos** | El dataset **descarta cualquier episodio con un NaN**. Nosotros tenemos NaN en todas partes. |
| **Solo balón vivo** | Los episodios se cortan donde `ball_state == "alive"`, un dato que nosotros no tenemos. No detecta el balón muerto ni las reanudaciones: la `D` habría que resolverla aparte. |
| **Unidades y frecuencia** | Metros (105×68) y 5 fps. Nuestro ATD: 0–1 y 25 fps. Esto es fácil de convertir. |
| **Dependencias** | `torch`, `torch_geometric` y, en la práctica, una GPU para reentrenar. |
| **Plazo** | Adaptar las identidades (reconstruir tracklets), reentrenar y validar no cabe en dos días. |

---

## 5. Reglas: qué está permitido con PathCRF

| uso | ¿permitido? |
|---|---|
| Ejecutar en local los pesos preentrenados (entrenados solo con Sportec) sobre nuestro partido | **Sí**: es un modelo externo usado como input. |
| Hacer fine-tuning, reentrenar o calibrar con nuestro partido | **No**: solo se entrena y ajusta con datos externos. |
| Entrenar o tunear con Sportec o Metrica | **Sí**, con la licencia verificada y documentada en `docs/EXTERNAL_DATA.md`. Creo que Sportec es CC BY 4.0, pero **hay que confirmarlo**. |
| Usar y modificar el código | **Sí**. Es MPL-2.0: los archivos modificados siguen bajo MPL y hay que citar el paper. |
| `utils.detect_keepers` / `label_phases` sobre nuestro partido (decidir qué equipo ataca hacia dónde con la posición media del periodo) | **Zona gris, NO GO** hasta que respondan los organizadores (inferencias automáticas en ejecución). Mientras tanto, usar una regla documentada. |

---

## 6. Recomendación para los dos días que quedan

Pipeline ligero en numpy que toma las ideas de PathCRF, no el modelo:

1. **Probabilidades por frame de H/A/D**, a partir de reglas:
   - balón visible: jugador más cercano, con velocidad coherente;
   - balón invisible: forma colectiva (centroides, dirección de avance, presión);
   - Smart Tagging: las reanudaciones (`SET PIECES`) como anclas del final del balón muerto.
2. **HMM de equipo con transiciones restringidas** (sección 3.2), decodificado con Viterbi.
3. **Filtro de duración mínima** (sección 3.3).
4. **Todos los parámetros ajustados con Sportec**: tracking degradado con ruido, etiquetas H/A/D
   sacadas de `ball_state` y `ball_owning_team_id`, y evaluación con
   `evaluation/possession_metrics.py` (`spellF1`).
5. Generar el CSV del partido, pasar `validate_submission.py` y comprobar el determinismo.

---

## 7. Aviso antes de hacer commit

`pathcrf/` está **sin trackear dentro de nuestro repo** y pesa unos 185 MB (checkpoints y datos de
Sportec). Hay que añadirlo a `.gitignore` o enlazarlo como submódulo para no subirlo al repo
público.
