# Aclaración oficial de los organizadores

Correo enviado a todos los participantes, recibido antes del 2026-11-07. **Prevalece sobre
cualquier otra información**: documentación del repositorio (`RULES.md`, `FAQ.md`, …), correos
anteriores y respuestas individuales. Texto literal:

> There has been some confusion about what is and what is not permitted in the Initial Challenge,
> so we are sending this clarification to all of you.
>
> Please note that the rules below take precedence over any other information you may have
> received previously, whether in the documentation, in earlier emails or in answers to individual
> questions.
>
> **What is not allowed**
>
> - Checking your output against the video.
> - Hand labels, human-produced data or any other data created manually on the provided game.
> - Uploading the provided data to AI services.
> - Training, fitting or calibrating your algorithm on the ground-truth possession data or on the
>   provided video.
>
> **What is allowed**
>
> - Running automatic checks using only the provided data.
> - Inspecting the provided data and the video to better understand what counts as possession.
> - Using as input the video, the automatic tracking data, the smart tagging or any other generated
>   data, as long as your algorithm was not trained on the ground truth or on the provided video.
> - Providing files of intermediate steps.
> - Using any dataset you have the rights to use. Please check the license of any dataset before
>   using it.
>
> **Training and tuning**
>
> If you need to train (or retrain), you MUST use only external data. If your algorithm has
> parameters that need to be tuned, you MUST tune them on external data, never on the ground-truth
> possession data or on the provided video.

## Qué cambia respecto a `RULES.md`

- **Ya no** se permiten pseudo-labels algorítmicos ni aprendizaje no supervisado o autosupervisado
  sobre el partido proporcionado: entrenar y tunear se hace **solo con datos externos**.
- **No** se puede comparar nuestra salida con el vídeo. Mirar el vídeo y los datos para entender qué
  cuenta como posesión sí se puede.
- Los ficheros de pasos intermedios se pueden entregar, pero `RULES.md` sigue prohibiendo publicar
  datos derivados que reconstruyan los originales: no van al repo público mientras no se confirme.
