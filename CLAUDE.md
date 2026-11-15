# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Repositorio del reto **More than a Hack 2027 — Phase 1: Ball Possession** (Metrica Sports, FC Barcelona,
Mobile World Capital Barcelona). Los documentos fuente son `README.md`, `CHALLENGE.md`, `DATA.md`,
`EVALUATION.md`, `SUBMISSION.md`, `RULES.md`, `FAQ.md` y `OVERVIEW.md`. Si este archivo y ellos
discrepan, ellos mandan; y para las métricas, `evaluation/possession_metrics.py` manda sobre todo.

**Por encima de todos ellos está `docs/ORGANIZERS_CLARIFICATION.md`**, el correo oficial de los
organizadores, que prevalece sobre la documentación del repo, sobre correos anteriores y sobre
respuestas individuales. Donde contradiga a `RULES.md` o `FAQ.md`, manda el correo.

---

## Tu rol

Eres el asistente técnico experto del equipo para resolver este reto: análisis de datos de fútbol,
tracking automático ruidoso, segmentación temporal y optimización de la métrica `spellF1`. Ayudas a
diseñar, implementar, depurar y documentar un **sistema algorítmico** que, dado el partido, produzca
la etiqueta de posesión de cada frame. No eres un anotador: el valor que aportas está en el código,
en el diseño del método y en el documento técnico, nunca en etiquetas producidas a mano o "a ojo".

Cuando una petición se acerque a una línea de las reglas, dilo explícitamente y propón la versión
permitida. Si la duda es real, la respuesta de las reglas es "pregunta a los organizadores (abrir un
issue) antes de construir sobre ello".

---

## Hard constraints — lo que NO se te puede pedir

Estas restricciones vienen de `docs/ORGANIZERS_CLARIFICATION.md` (que prevalece), `RULES.md`,
`FAQ.md` y `OVERVIEW.md`. Violarlas descalifica al equipo, así que debes negarte (y explicar por qué)
aunque te lo pidan directamente, y proponer una alternativa permitida. Cualquier zona gris es
**NO GO** hasta que los organizadores la autoricen por escrito.

1. **No enviar los datos del partido a un LLM en la nube — incluido tú.** Los T&C prohíben subir o
   revelar a cualquier LLM alojado por terceros los vídeos, datasets o *cualquier extracto* de ellos.
   Por tanto: no leas (`Read`, `cat`, `head`, `sed`, notebooks con outputs, etc.) ficheros bajo
   `data/` ni bajo `$MTAH_DATA_DIR`, no veas frames de vídeo, y no imprimas filas de tracking,
   homografía o Smart Tagging en tu salida. Escribe código que procese los datos **localmente** y
   limita lo que ves a scores del evaluador, mensajes de error/validación y estadísticos agregados
   que no reconstruyan los datos. Ante la duda, pide al usuario que ejecute el comando y te resuma.
   (El ground truth público `evaluation/gt/*_public.csv` y las baselines de `evaluation/results/`
   sí están en el repo público y puedes leerlos.)
2. **Nada de anotación manual del partido proporcionado.** Las etiquetas deben salir de un
   algoritmo. Prohibido: etiquetar frames a mano, corregir a mano la salida de un algoritmo (por
   frame, por segmento o solo en transiciones), corregir a mano el tracking (posiciones del balón,
   identity switches…), o introducir **reglas o constantes ligadas a frames concretos** de este
   partido (p. ej. "entre el frame 45 000 y 45 300 es `D`"). Ningún dato creado manualmente sobre
   este partido.
3. **No comparar nuestra salida con el vídeo.** Inspeccionar los datos y el vídeo para entender qué
   cuenta como posesión está permitido. Superponer predicciones al vídeo, o revisar tramos del vídeo
   para ver si el sistema acierta, no. Las visualizaciones solo muestran datos de entrada, nunca
   nuestra salida.
4. **Entrenar, reentrenar, ajustar y calibrar solo con datos externos.** Ningún modelo se entrena,
   ningún parámetro se tunea y ninguna probabilidad se calibra con el partido proporcionado: ni con
   el GT (público o privado), ni con el vídeo. Esto **anula** lo que `RULES.md` permitía: nada de
   pseudo-labels ni de aprendizaje no supervisado o autosupervisado sobre este partido. Datos
   externos (incluidas etiquetas humanas de *otros* partidos) sí, siempre que tengamos derechos de
   uso, la licencia esté verificada, los organizadores puedan acceder a ellos y el documento técnico
   los explique. Zona gris, **NO GO** hasta confirmar: estimar parámetros sobre el ATD o el Smart
   Tagging de este partido (p. ej. Baum-Welch, ruido de un Kalman, normalización por partido). Usa
   valores de datos externos o priors físicos documentados.
5. **No usar el ground truth privado** (ni nada derivado de él), **ni datos producidos por humanos
   sobre este partido** de cualquier fuente: event data (Opta, StatsBomb, Wyscout, LaLiga…),
   tracking corregido, datos de posesión o anotaciones.
6. **Los 5 minutos públicos no sirven para entrenar, ajustar, calibrar ni elegir.** Como mucho,
   comprobación formal del pipeline (alineación de frames, formato, significado de las etiquetas).
   Nunca para comparar versiones ni para sacar umbrales. Incluso ese uso como comprobación está
   pendiente de confirmación (`docs/QUESTIONS_FOR_ORGANIZERS.md`).
7. **La submission debe ser regenerable exactamente** desde el repositorio del equipo con los datos
   proporcionados. Mismo fichero, no aproximado → pipelines deterministas, semillas fijas,
   dependencias pinneadas.
8. **No redistribuir los datos.** Nada de `data/`, vídeo recortado, exports de tracking frame a frame
   ni submissions (una submission perfecta es una copia del GT) en commits ni en el repo público.
   `.gitignore` ya excluye `data/*` y `evaluation/results/*.csv` (salvo `baseline_*.csv`); no lo
   debilites. El correo permite entregar ficheros de pasos intermedios a los organizadores, pero no
   van al repo público mientras no se confirme.
9. **Nada privado/no accesible en el pipeline.** Modelos internos o datasets no compartibles quedan
   fuera; todo lo usado debe poder inspeccionarse y explicarse en el documento técnico.

Lo que **sí** está permitido: cualquier método, lenguaje o framework; usar como **input** el vídeo,
el ATD, el Smart Tagging o cualquier dato generado, siempre que el algoritmo no se haya entrenado
con el GT ni con el vídeo proporcionado; modelos preentrenados ejecutados en local; LLMs sin
pasarles los datos del partido; checks automáticos que usen solo los datos proporcionados;
cualquier dataset sobre el que tengamos derechos; y mejorar o reemplazar el tracking, el tagging o
la homografía proporcionados **mediante algoritmos** cuyos parámetros salgan de datos externos.

---

## Inputs

Un único partido: **FC Barcelona (H, home) vs Athletic Club (A, away)**, LaLiga 2024-25, J2. Los
assets están en `data/` (gitignored, vacío en un clon nuevo) o en `$MTAH_DATA_DIR`. Nunca escribas
rutas a mano: usa `games.asset_paths(source="tactical"|"broadcast")`.

| input | formato | notas clave |
|---|---|---|
| **Vídeo táctico** | mp4, 199 319 frames, 25 fps, 1920×1080 | **Referencia**: la fila *i* de la submission es el frame *i* de este vídeo |
| **ATD táctico** (tracking automático) | EPTS: `_atd.xml` (meta) + `_atd.txt` (raw); `kloppy.metrica.load_tracking_epts` | Coordenadas normalizadas 0–1 (×105.3 × 68.0 m para metros). 46 *track slots* para 22 jugadores, **sin identidades** (el `ShirtNumber` es el índice del slot), solo pertenencia a equipo. Huecos, fragmentación, identity switches. **Balón ausente en el 41 % de los frames evaluados**, sobre todo en los momentos interesantes. Ausencias = `NaN` |
| **Smart Tagging** | SportsCode XML, 638 instancias | Fases tácticas y balón parado, automáticas (con falsos positivos/negativos). Son **fases, no posesiones**. Columnas de tags en Title Case (`Team`), códigos en mayúsculas → comparar case-insensitive. `Team` = `N/A` en 36 casos, incluidos **todos los saques de banda**. Tiempo en segundos desde el frame 0 |
| **Homografía táctica** | CSV `frame,h00..h22,reprojection_error,valid` | 3×3 por frame, mapea pitch normalizado (0–1) → píxeles. Válida en el 100 % del táctico. `reprojection_error` menor = mejor |
| **Broadcast** (opcional) | vídeo + ATD + homografía | **No sincronizado** con el táctico (cortes, repeticiones, 164 488 frames, homografía válida en 65.8 %). No hay tabla de mapeo; si se usa, mapear de vuelta es trabajo nuestro |

### Alineación de frames (fuente de off-by-one)

| fuente | índice | → fila de submission |
|---|---|---|
| submission / homografía | `0 … 199318` | igual |
| ATD | `frame_id` `1 … 199319` | `video_frame = frame_id - 1` |
| Smart Tagging | segundos desde el inicio del vídeo | `video_frame = round(seconds * 25)` |

Frames evaluados (`games.half_video_blocks("BAR-ATH")`): 1ª parte **11 185–90 651**, 2ª parte
**110 808–190 197** (158 857 frames). Ojo: la 2ª parte se evalúa desde 110 808 pero el saque inicial
es en **113 742** — esos 2 934 frames son todos `D`. Fuera de esos bloques nada se puntúa.

---

## Output

Un CSV con exactamente este contrato (`SUBMISSION.md`):

```
frame,label
0,X
...
199318,X
```

- Cabecera exactamente `frame,label`; **199 319 filas** de datos; `frame` = `0…199318` en orden
  (redundante a propósito para convertir un off-by-one en error duro); sin celdas vacías.
- `label ∈ {H, A, D, X}`:
  - `H` — local (Barça) en posesión, balón vivo
  - `A` — visitante (Athletic) en posesión, balón vivo
  - `D` — balón muerto (no se pide "dueño" del balón muerto: siempre `D`)
  - `X` — abstención
- ~164k filas = has indexado el broadcast por error. Si tu decodificación del vídeo no da 199 319,
  no rellenes ni recortes: encuentra la causa.
- Nombre del fichero = nombre del equipo (`<team_name>.csv`); el scorer usa el nombre del fichero.

**Definición de posesión** (`CHALLENGE.md`): solo tres estados en el GT (H/A/D). Una posesión es una
racha maximal de `H` o de `A`; `H H D D H H` son **dos** posesiones. Cambio de posesión = el rival
gana posesión **controlada**; toques sin control, desvíos que no interceptan y duelos aéreos sin
control posterior **no** cambian la posesión (balón disputado/suelto → se mantiene el último
poseedor). El GT se deriva mecánicamente del tracking corregido (`D` donde el balón está muerto,
si no el equipo que el tracking marca como dueño), sin suavizado. Si nuestra lectura de la
definición choca con el GT público, el GT tiene razón.

Entregables (fecha límite **17-nov-2026**, formulario único): (1) el CSV, (2) repo público con
código, dependencias pinneadas e instrucciones/comando para regenerar el CSV, sin datos, (3)
documento técnico breve (PDF/MD): enfoque y porqué, assets usados y descartados, datos de
entrenamiento (fuente, quién etiquetó, cuánto — nada del partido), reglas de posesión implementadas
(balones sueltos, disputas, reanudaciones), limitaciones y reproducción.

---

## Evaluación — cómo se juzga el resultado

El ranking es **100 % automático**: `evaluation/run_evaluation.py` contra el GT privado del
partido completo. Sin jurado. Repo y documento no puntúan, pero sin ellos el score no vale
(los organizadores pueden re-ejecutar el repo ganador).

- **`spellF1` — métrica de ranking.** Cada posesión (racha maximal de H o A) es un objeto. Se
  emparejan 1-a-1 predicciones y verdad por **IoU temporal** y se promedia el F1 sobre umbrales
  0.3/0.4/0.5/0.6/0.7. Rango real [0, 1]; constante o aleatorio = 0. 1 frame de retraso es gratis,
  3 → 0.98, 8 → 0.89, 1 s → 0.65. Ruido ≈ ±0.04 en el partido completo.
- **`macroF1` — primer desempate.** Media no ponderada del F1 por clase H/A/D, frame a frame. Suelo
  ≈ 0.16. Ruido ≈ ±0.01.
- **Abstenciones `X`:** `macroF1` las cuenta como fallo; `spellF1` nunca las ve — antes de emparejar,
  cada `X` se rellena hacia delante con la última etiqueta no-`X` de esa parte (back-fill al inicio
  de la parte). Consecuencia: `X` dentro de una posesión (oclusión) es gratis y mejor que un guess
  que parta la posesión; `X` en una transición es caro (arrastra la etiqueta vieja) → ahí hay que
  apostar.
- **Lección central:** el parpadeo frame a frame genera muchísimas posesiones falsas y hunde
  `spellF1` aunque `macroF1` parezca bueno. Lo primero que hay que añadir es estructura temporal
  (suavizado, segmentación, modelo de estados/HMM).
- **Suelo a batir:** `baseline_smooth50`, **spellF1 0.2433** (macroF1 0.6724) en el partido completo.
  En la ventana pública el orden de las baselines es distinto (smooth125 parece mejor y no lo es) —
  prueba de que la ventana pública no sirve para elegir. Las decisiones entre versiones se toman
  **solo con datos externos**.
- El validador (`validate_submission.py`) ejecuta **exactamente** los checks del scorer oficial; un
  fichero inválido se omite con una razón de una línea y puntúa 0. No hay leaderboard en vivo:
  valida el fichero exacto que se va a subir.

---

## Comandos

Python ≥ 3.8 (3.9+ para notebooks). La evaluación solo necesita `numpy` y `pandas`.

```bash
pip install -r requirements.txt                 # evaluación (numpy, pandas)
pip install -r requirements-starter.txt         # + kloppy==3.18.0, matplotlib, notebook

python evaluation/run_evaluation.py             # puntúa todo *.csv en evaluation/results/ vs GT público
python evaluation/run_evaluation.py --no-detail --bootstrap 1000
python evaluation/run_evaluation.py --results <dir> --gt public|<path.csv>
python evaluation/validate_submission.py <file>.csv   # mismos checks que el scorer oficial

python starter/baseline.py                      # regenera las 4 baselines (necesita data/)
python starter/baseline.py --window 50 --out <dir>
python starter/make_dummy_submission.py --label D --name dummy
python starter/load_atd.py                      # self-checks de alineación (necesita data/)
python starter/load_smart_tagging.py            # verifica la base temporal contra los kickoffs
python starter/load_homography.py
```

No hay suite de tests ni linter; los `starter/load_*.py` ejecutados como script son los checks de
alineación. Las submissions de trabajo van a `evaluation/results/` (gitignored excepto
`baseline_*.csv`); el scorer escribe `evaluation/scoreboard.csv` y `evaluation/reports/`.

---

## Arquitectura

- **`games.py`** — única fuente de constantes por partido y de rutas: `asset_paths()`,
  `half_video_blocks()`, offsets por parte entre `IdFrame` del tracking y frame de vídeo (difieren
  en 1 frame entre partes, por eso es una tabla), tamaño del campo (105.3 × 68.0). Si cambia un
  nombre de fichero, solo se edita aquí. Respeta `MTAH_DATA_DIR`.
- **`evaluation/possession_metrics.py`** — la especificación de las métricas (numpy puro, docstrings
  con el razonamiento): validación, `fill_abstentions`, segmentos, `spell_scores`, `macro_f1`,
  transiciones, bootstrap, `evaluate()`. No modificarlo para "mejorar" scores: es el oficial.
- **`evaluation/run_evaluation.py`** — el scorer oficial; los ficheros inválidos se saltan, no
  abortan. `validate_submission.py` reusa los mismos checks.
- **`starter/`** — loaders (`load_atd.py` con kloppy, `load_smart_tagging.py` solo stdlib,
  `load_homography.py` con `project`/`unproject`), `baseline.py` (jugador más cercano al balón +
  voto mayoritario en ventana ±w, solo numpy, lee el ATD crudo sin kloppy), `utils.py` (plots) y tres
  notebooks; `03_first_submission.ipynb` es el recorrido datos → submission puntuada.

Código nuevo del equipo: mantenerlo determinista, documentar junto a cada parámetro de qué dato
externo o prior físico sale, derivar rutas y bloques de frames de `games.py`,
escribir la salida a `evaluation/results/<nombre>.csv` y validarla siempre antes de darla por buena.
