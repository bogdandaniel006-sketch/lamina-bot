# lamina-bot · carruseles automáticos para @danidemiguel_

Lunes, miércoles y viernes a las 17:30 (hora de Madrid) prepara un carrusel de 3 fotos para TikTok
y lo deja como **borrador en tu bandeja de TikTok**. Tú solo abres la notificación y pulsas *Publicar*.

## Cómo funciona
1. **Decide** (`bot/brain.py`): elige formato (problema→solución, antes→después, tips), escenario y tipo de gancho
   según lo que mejor ha funcionado (aprende solo; siempre deja margen para probar cosas nuevas).
2. **Escribe** textos, título y descripción con Gemini, imitando tus carruseles que mejor funcionaron.
3. **Genera** las 3 fotos con Gemini (Nano Banana). En las fotos con portátil usa capturas reales de tu web (`assets/refs/app_*.jpg`).
4. **Monta** los textos con la tipografía de TikTok y tus estilos (`bot/compose.py`).
5. **Sube** el carrusel a tu bandeja de TikTok (las fotos se sirven desde GitHub Pages).
6. **Aprende**: cada mañana lee visualizaciones, likes, comentarios y compartidos. Cada domingo abre un *issue* con el informe semanal (te llega por email).

## Workflows (pestaña *Actions*)
| Workflow | Cuándo | Para qué |
|---|---|---|
| Preparar carrusel | L-X-V 17:30 | Genera y envía el borrador. Botón *Run workflow* + *force* para mandarlo ya. |
| Métricas y aprendizaje | Diario 8:10 | Actualiza estadísticas |
| Informe semanal | Domingo | Resumen por email |
| Vista previa (sin subir) | Manual | Genera un carrusel en `docs/preview/` para verlo sin mandarlo |
| Autorizar TikTok | Manual, una vez | Conecta tu cuenta |

## Cambiar cosas
- Días/hora: variables `POST_WEEKDAYS` (0=lunes) y `POST_HOUR`/`POST_MINUTE` en `bot/config.py`.
- Escenarios, formatos, emojis y tono: `bot/brain.py`.
- Estilos de texto: `bot/compose.py`.
- Fotos de referencia: `assets/refs/app_*.jpg` (capturas de tu web) y `assets/refs/style_*.jpg` (fotos tuyas de ejemplo, opcional).

## Secretos (Settings → Secrets and variables → Actions)
`GEMINI_API_KEY`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TOKEN_KEY`.

Coste: solo la API de Gemini (~2-3 €/mes con tope de gasto). GitHub Actions, Pages y la API de TikTok son gratis.
