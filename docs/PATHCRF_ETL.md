# PathCRF sobre nuestro ATD: validación, huecos y propuesta de ETL

> Escrito el 2026-11-15 (entrega: 17-nov-2026). Contrasta `docs/PATHCRF_ANALYSIS.md` con la salida
> agregada de `analysis/describe_atd.py` y con el código de la librería en
> `/Users/segoto/PersonalProjects/pathcrf` (commit `1b7c6f8`). Las cifras del ATD son estadísticos
> agregados del partido; **ninguna se usa para fijar parámetros** (regla 4 de `CLAUDE.md`).

---

## TL;DR

- El análisis previo es **correcto en lo esencial**, y los datos lo refuerzan: el balón no falta a
  ratos, falta en **bloques largos** (mediana 268 frames ≈ 11 s; el 99.7 % de los frames sin balón
  está en huecos de más de 5 s). Un método que no dependa del balón es necesario, no opcional.
- Hay que **corregir tres puntos** del análisis:
  1. El problema de identidades es **local, no global**: el modelo solo necesita nodos estables
     dentro de una ventana de 10 s, y la mediana de un fragmento de track es 13.6 s.
  2. El código tiene **dos fallos silenciosos** con nuestros datos: trunca a los 11 primeros slots
     por orden alfabético y rellena con ceros sin máscara (la máscara se calcula y se descarta).
  3. `pathcrf/data/sportec_synced` trae **solo eventos** (7 parquet, 404 KB). El tracking de Sportec
     hay que descargarlo aparte.
- Usado tal cual, PathCRF **no produce nada** sobre nuestro ATD: descarta cualquier episodio con un
  NaN, y los episodios se construyen a partir de `ball_state`, que no tenemos.
- Propuesta: un ETL en dos ramas que comparten un **formato canónico**:
  - **Ruta A (recomendada para el plazo):** ETL de Sportec para obtener etiquetas H/A/D externas, y
    un HMM de equipo en numpy con las ideas de PathCRF, ajustado solo con Sportec.
  - **Ruta B (si sobra tiempo):** ETL del ATD hacia el formato de PathCRF para ejecutar el checkpoint
    `saved/140` como una *feature* más del HMM.

---

## 1. Validación punto a punto

| afirmación de `PATHCRF_ANALYSIS.md` | evidencia (`describe_atd.py` / código) | veredicto |
|---|---|---|
| Falta el balón en el ~41 % de los frames evaluados | Balón visible en el 59.3 % de cada parte | ✔ Confirmado |
| PathCRF resuelve "nuestro 41 %" | 150 huecos; p50 = 268 frames, p90 = 845, máx. 5 537 (221 s). Los huecos de ≤5 frames suman ~0 % | ✔ **Reforzado**: interpolar el balón no sirve; hace falta inferir la posesión a partir de los jugadores |
| 46 slots anónimos, con huecos e identity switches | 2 218 fragmentos; longitud p10 = 2.0 s, p50 = 13.6 s, p90 = 200.7 s; 1 slot nunca usado y 2 casi vacíos | ✔ Confirmado |
| "Necesita 22 jugadores con identidad estable" | La atención temporal es **por nodo** (`set_lstm.py:258`, `reshape(T, B*N)`), pero solo dentro de la ventana (`window_seconds=10`, `target_fps=5`). Mediana de fragmento (13.6 s) > ventana (10 s) | ⚠ **Matizar**: basta con identidad estable **dentro de cada ventana de 10 s**, no en todo el partido. Con *stitching* local es alcanzable |
| "No tolera huecos" | `inference_episode` devuelve `None` si **cualquier** columna de entrada tiene un NaN (`inference.py:406`); `dataset.py:144` hace lo mismo en el entrenamiento. Media de jugadores trackeados: 20.1 (1ª) y 20.9 (2ª) | ✔ Confirmado, y es peor de lo que parecía: casi ningún episodio llegaría al modelo |
| (no mencionado) Cómo trata un número de slots distinto de 11 | `_pad_nodes`: si un equipo tiene **más** de 11 slots con datos, se queda con los 11 primeros **en orden alfabético**; si tiene menos, rellena con ceros. `player_mask` se devuelve pero **no se usa** (`inference.py:432`, `_`), y el modelo no recibe máscara | ❌ **Nuevo problema**: en el 10–16 % de los frames un equipo tiene más de 11 tracks (duplicados/fantasmas), y en un episodio de varios segundos se acumulan aún más slots. Truncado arbitrario y nodos-cero fuera de distribución |
| "Solo balón vivo; la D aparte" | `label_frames_and_episodes` corta los episodios por `ball_state == "alive"` (`utils.py:118`) | ✔ Confirmado. Necesitamos **nuestro propio detector de D** antes de PathCRF |
| `label_phases` / `detect_keepers` son zona gris | Además, `label_phases` abre una fase nueva cada vez que un jugador entra o sale (`utils.py:162-166`). Con 2 218 fragmentos salen miles de fases, y las de menos de 100 frames se descartan | ❌ **Inutilizable tal cual** además de zona gris |
| Unidades 0–1 y 25 fps vs metros y 5 fps | `config.PITCH_X, PITCH_Y = 105.0, 68.0`; nuestro campo mide 105.3 × 68.0. Velocidad y aceleración con `savgol_filter` (15/2 y 9/2) en `utils.py:282` | ✔ Fácil. Hay que calcular la cinemática **por fragmento**, no a través de los huecos |
| Sportec trae tracking + eventos sincronizados | `pathcrf/data/sportec_synced` = 7 parquet de **eventos** (404 KB). El tracking hay que bajarlo de figshare (README de PathCRF) y pasarlo por `datatools/preprocess.py` | ⚠ **Corregir**: falta un paso de descarga |
| Viterbi con restricciones reutilizable como plantilla | `_viterbi_constrained_decode` solo aplica **restricciones duras** (sin coste de transición) y es un bucle Python T×K con K = 26² = 676 | ✔ La idea sirve; la implementación no. Un HMM de equipo con 4–6 estados se escribe en numpy en ~40 líneas |
| `_overwrite_short_self_loops(min_dur)` = control sostenido | Sustituye cada auto-bucle de menos de `min_dur` frames por la arista siguiente (`postprocess.py:31`) | ✔ Confirmado |
| `preprocess_noise.py` acerca Sportec a nuestro ATD | Solo hace oclusión por fusión, sesgo y outliers. No anonimiza, no fragmenta y no quita el balón | ✔ Confirmado, con un **aviso de reglas** (§4) |
| Dependencias torch / torch_geometric | `requirements.txt` de PathCRF **no las lista**, aunque `inference.py` las importa | ⚠ Hay que pinnearlas nosotros si usamos la Ruta B |

### Lo que los datos añaden y el análisis no tenía

- **Señales directas de `D`**: el balón está fuera de [0,1] en el 4.19 % de los frames con balón
  visible. Es útil, con un margen físico, porque el balón sobre la línea sigue en juego.
- **El balón también tiene falsos positivos**: aparece "visible" en el 94 % del descanso, y hay 150
  saltos de más de 45 m/s (0.16 %). Un detector de D no puede fiarse de la mera presencia del balón.
- **Teletransportes de jugadores**: hay 1 493 saltos de más de 12.5 m/s (0.046 %), probablemente
  identity switches dentro de un mismo slot. El stitching tiene que **romper** los fragmentos en
  esos saltos, además de unirlos.
- **Porteros**: dos slots (uno por equipo) están activos el ~92 % del tiempo con fragmentos muy
  largos, y casi seguro son los porteros. **No se puede fijar "slot 24 / 46 = portero"** porque
  sería una constante ligada a este partido (regla 2). Si se necesita, debe salir de un algoritmo.
- **Balón cerca de un jugador**: con balón visible, la distancia al jugador más cercano tiene una
  mediana de 1.9 m, y el 81 % de los frames está a ≤5 m (el `POSS_MAX_DIST` de PathCRF es 5 m, un
  valor externo). Sirve como emisión cuando hay balón, pero solo en el ~59 % de los frames.

---

## 2. Qué falta para que PathCRF sirva

| # | hueco | por qué bloquea | quién lo resuelve |
|---|---|---|---|
| G1 | **Etiquetas externas H/A/D** | Sin ellas no hay forma legal de ajustar ni de elegir versiones | ETL Sportec (§3.1) |
| G2 | **Tracking de Sportec descargado** | Solo están los eventos sincronizados | Descarga figshare + `preprocess.py` |
| G3 | **Licencia de Sportec verificada** y documentada | Regla 4: los datos externos requieren derechos de uso y deben ser accesibles a los organizadores | `docs/EXTERNAL_DATA.md` |
| G4 | **Detector de balón muerto (D) y episodios** | PathCRF no predice D y necesita `ball_state` para cortar episodios | Reglas: balón fuera + margen, `SET PIECES` del Smart Tagging, parones; ajustado en Sportec |
| G5 | **Nodos estables ≤11 por equipo y ventana, sin NaN** | Sin esto, el modelo no recibe ningún episodio | Stitching (§3.2, T3–T4) |
| G6 | **Portero y sentido de ataque** | `node_in_dim = 8` incluye el flag de portero, y el orden de nodos es izquierda/derecha | Pendiente de los organizadores (§5) |
| G7 | **Mapeo aristas → H/A/D** | PathCRF devuelve `edge_src/edge_dst` por frame, no la etiqueta del reto | §3.3 |
| G8 | **Degradación de Sportec parecida a un ATD** | Para que lo ajustado en Sportec generalice a datos ruidosos | Extender `preprocess_noise.py` (§3.1, paso 4) |
| G9 | **Viterbi rápido a nivel de equipo** | El de PathCRF es lento y no tiene costes de transición | numpy propio |
| G10 | **Reproducibilidad** | La submission debe regenerarse exactamente | PathCRF como submódulo pinneado a `1b7c6f8`, torch/PyG pinneados, CPU, semillas fijas |

---

## 3. ETL propuesto

Las dos fuentes, Sportec (externa) y nuestro ATD, pasan a **un mismo formato canónico**. Todo lo
que viene después (features, HMM, PathCRF opcional, escritura del CSV) es el mismo código para las
dos. Así, lo que se mide en Sportec es exactamente lo que se ejecuta sobre nuestro partido.

```
            ┌─────────────── EXTERNO (ajustar / elegir) ───────────────┐
 Sportec XML ─► preprocess.py ─► etiquetas H/A/D ─► degradar ─► CANÓNICO ─┐
                                                                          ├─► features ─► HMM equipo ─► H/A/D/X
 ATD tactical ─► parse ─► metros ─► cinemática ─► stitching ─► CANÓNICO ──┘        ▲
            └──────────── NUESTRO PARTIDO (solo inferencia) ───────────┘   PathCRF 140 (Ruta B, opcional)
```

### Formato canónico (un parquet por partido, en `data/derived/`, gitignored)

| columna | tipo | nota |
|---|---|---|
| `frame` | int | índice de vídeo 0-based (ATD: `frame_id - 1`) |
| `period_id` | int | 1 / 2, desde `games.half_video_blocks` |
| `home_<k>_{x,y,vx,vy,speed,accel}` / `away_<k>_…` | float32 | `k` = nodo virtual 0…10 tras el stitching, en metros (campo 105 × 68) |
| `home_<k>_valid` / `away_<k>_valid` | bool | ¿observación real o imputada? |
| `ball_x, ball_y, ball_valid` | float32 / bool | sin interpolar a través de huecos largos |
| `label` | `H/A/D` | **solo en Sportec**; en el ATD no existe |

### 3.1 ETL de Sportec (dato externo: entrenar, ajustar y elegir)

1. **Extract**: descargar el dataset de figshare (enlace en el README de PathCRF). Ponerlo en
   `pathcrf/data/sportec/{metadata,event,tracking}` y ejecutar `python datatools/preprocess.py`.
   Resultado: `tracking_processed` con `ball_state` y `ball_owning_team_id` por frame.
2. **Licencia**: verificarla (se cree CC BY 4.0, falta confirmarlo) y anotarla en
   `docs/EXTERNAL_DATA.md` con la fuente, quién etiquetó y cuántos frames. Lo pide el documento
   técnico.
3. **Etiquetas**: `D` si `ball_state != "alive"`; si no, `H`/`A` según `ball_owning_team_id` (home o
   away de los metadatos). Es la misma semántica que nuestro GT. Opcionalmente, contrastar con
   `applications/team_poss.compute_team_poss` como segunda fuente.
4. **Degradar** (extender `preprocess_noise.py`):
   - anonimizar: renombrar los jugadores a slots y partir sus trayectorias en fragmentos;
   - identity switches: intercambiar slots entre jugadores cercanos del mismo equipo;
   - quitar el balón en **bloques largos**, más probable cuando hay muchos jugadores cerca;
   - tracks fantasma o duplicados (más de 11 por equipo).

   **Los niveles no se calibran con nuestro ATD** (ver §4). Se usa una **rejilla de niveles**
   (bajo/medio/alto) con valores de la literatura o priors razonados, y se eligen los parámetros del
   pipeline que rinden de forma **robusta en toda la rejilla**.
5. **Transform**: los mismos pasos T2–T4 del ATD (§3.2) aplicados al Sportec degradado, para obtener
   el formato canónico.
6. **Evaluar**: generar el CSV por partido de Sportec y puntuarlo con
   `evaluation/possession_metrics.py` (`spellF1`, `macroF1`), con *leave-one-match-out* sobre los
   7 partidos. Aquí, y solo aquí, se comparan versiones y se fijan umbrales.

### 3.2 ETL de nuestro ATD (solo inferencia)

| paso | qué hace | parámetros y de dónde salen |
|---|---|---|
| **E1 parse** | Reutilizar `load_raw` de `analysis/describe_atd.py` (o `starter/baseline.py`); equipo por slot con `team_of_each_track`. Rutas con `games.asset_paths` | — |
| **E2 Smart Tagging** | `starter/load_smart_tagging.py`; `video_frame = round(s * 25)`; comparar los códigos sin distinguir mayúsculas | — |
| **T1 unidades** | `x * 105.3`, `y * 68.0`, después reescalar a 105 × 68 si se usa PathCRF | tamaños de `games.py` y `config.py` |
| **T2 cinemática** | `vx, vy, speed, accel` con `savgol_filter` **por fragmento**, sin cruzar huecos | 15/2 y 9/2, los de PathCRF (externos) |
| **T3 romper** | Partir un fragmento donde la velocidad derivada supera 12.5 m/s (probable identity switch) | prior físico ya documentado en `describe_atd.py` |
| **T4 stitching** | Por equipo, asignar fragmentos a **11 nodos virtuales** con Hungarian. Coste = distancia entre el fin de un fragmento y el inicio del siguiente; límite = velocidad máxima × tiempo de hueco. Los duplicados (dos tracks a menos de ~1 m) se fusionan. Los huecos cortos de un nodo se interpolan; los largos quedan `valid = False` | velocidad máxima 12.5 m/s (prior); distancia de duplicado y hueco máximo **ajustados en el Sportec degradado** |
| **T5 completar** | Si un nodo sigue vacío en una ventana, se **imputa** (p. ej. a la posición media del equipo o a la última conocida) en vez de dejar ceros. El modelo no lee la máscara | la regla se elige en Sportec |
| **T6 episodios** | Detector de D: balón fuera del campo con un margen, reanudaciones del Smart Tagging como anclas y parones (jugadores casi quietos). Se definen episodios = rachas de "vivo" predicho | margen y umbrales ajustados en Sportec |
| **L** | Escribir el parquet canónico en `data/derived/BAR-ATH_canonical.parquet` | — |

### 3.3 De la salida de PathCRF a H/A/D (Ruta B)

| arista decodificada | etiqueta |
|---|---|
| auto-bucle sobre un jugador `home_*` / `away_*` | `H` / `A` |
| `src → dst` (en vuelo) | equipo de `src` (el último poseedor) hasta que `dst` controla. Un pase al rival solo cambia la posesión cuando el rival tiene un auto-bucle |
| `src → out_*` y `out → out` | `D` cuando el detector T6 lo confirma; si no, se mantiene el último equipo |
| fuera de los episodios | `D` (lo decide T6) |

Mejor aún: **no usar la decodificación dura de PathCRF**, sino sumar las probabilidades de arista
por equipo (`P(H) = Σ` de las aristas que salen de jugadores `home`) y pasarlas como emisión al HMM
de equipo. Así PathCRF es una feature más, y el HMM controla el parpadeo y la duración mínima.

### 3.4 HMM de equipo (común a las dos rutas)

- Estados: `H-ctrl`, `H-vuelo`, `A-ctrl`, `A-vuelo`, `D`. `vuelo` se escribe como su equipo.
- Transiciones permitidas, según el §3.2 de `PATHCRF_ANALYSIS.md`: un cambio de equipo solo puede
  pasar por un control del rival; `D` solo vuelve a un `ctrl`.
- Emisiones:
  - balón visible: equipo del jugador más cercano y su distancia;
  - sin balón: PathCRF (Ruta B) o la forma colectiva (centroides, quién presiona a quién);
  - Smart Tagging: fases y balón parado.
- Duración mínima: estados expandidos o el filtro `min_dur` tras Viterbi.
- `X`: solo **dentro** de una posesión estable y con baja confianza, nunca en una transición (las
  `X` se rellenan hacia delante en `spellF1`).
- Todo se ajusta en Sportec (§3.1, paso 6).

---

## 4. Lo que hay que vigilar de las reglas

| tentación | por qué no | alternativa permitida |
|---|---|---|
| Usar las cifras de `describe_atd.py` (41 % sin balón, fragmento de 13.6 s…) como niveles de ruido para degradar Sportec | Es estimar parámetros a partir del ATD de este partido: **zona gris, NO GO** (regla 4) | Rejilla de niveles con priors o literatura y elegir lo robusto. O preguntar a los organizadores si "describir para elegir el rango de la simulación" está permitido |
| Fijar umbrales (distancia de posesión, margen de fuera) mirando las distribuciones de arriba | Igual que el punto anterior | Ajustar en Sportec etiquetado |
| "Slot 24 y 46 son los porteros" escrito en el código | Constante ligada a este partido (regla 2) | Detección algorítmica, pendiente de §5 |
| Comprobar en la ventana pública si la Ruta B mejora a la A | Regla 6 | Comparar solo en Sportec (LOMO-CV) |
| Hacer fine-tuning de `saved/140` con nuestro ATD (también con pseudo-labels) | Regla 4 | Reentrenar, si se hace, solo con Sportec degradado |
| Subir el parquet canónico o los CSV al repo | Regla 8 | `data/derived/` gitignored |

---

## 5. Preguntas para `docs/QUESTIONS_FOR_ORGANIZERS.md`

1. ¿Puede el algoritmo deducir **en ejecución**, a partir del ATD, qué equipo ataca hacia cada lado
   y qué track es el portero (p. ej. el jugador más retrasado de cada equipo en una ventana)? Es
   inferencia sobre el input, no ajuste de parámetros, pero hoy lo tratamos como NO GO.
2. ¿Podemos usar estadísticas **descriptivas** de nuestro ATD (p. ej. el % de frames sin balón) solo
   para elegir el **rango** de una simulación de ruido aplicada a datos externos?

---

## 6. Plan realista hasta el 17-nov

| cuándo | qué | entregable |
|---|---|---|
| Día 1, mañana | G2 + G3: descargar Sportec, `preprocess.py`, licencia en `EXTERNAL_DATA.md` | etiquetas H/A/D de 7 partidos |
| Día 1, tarde | Formato canónico, T1–T4 (stitching), degradación con rejilla | parquet canónico Sportec + ATD |
| Día 2, mañana | Detector de D (T6) + HMM de equipo; ajuste LOMO-CV en Sportec | `spellF1` en Sportec > `baseline_smooth50` aplicado a Sportec |
| Día 2, tarde | CSV de BAR-ATH, `validate_submission.py`, dos ejecuciones con `diff` para comprobar el determinismo, documento técnico | submission + repo + documento |
| Solo si sobra tiempo | Ruta B: PathCRF 140 como emisión, comparada en Sportec | — |

La Ruta B depende de G5 (stitching), G6 (pendiente de los organizadores) y de pinnear torch/PyG.
Con dos días, lo que más rinde es la Ruta A. El stitching de T4 ya acerca el ATD a lo que PathCRF
necesita, así que no es trabajo perdido si después se añade la Ruta B.
