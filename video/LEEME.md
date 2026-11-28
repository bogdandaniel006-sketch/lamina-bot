# Lámina Vídeo

Vídeos animados para el TikTok de @danidemiguel_: datos curiosos, explicaciones de dibujo técnico e historias
con personajes, con voz en off, subtítulos animados y el sello de **danidemiguel.com** al final.

**Gratis del todo:** los dibujos, la animación y la voz los hace el programa en tu ordenador. No usa Gemini
ni ninguna IA de pago. Los guiones (los archivos de `historias/`) te los escribe Claude: pídele
*"hazme un guion de un dato curioso sobre…"* y mete el archivo que te dé en la carpeta `historias/`.

## Instalar (una vez)

1. Instala **Python 3.10 o más nuevo** desde python.org (en Windows, marca *"Add Python to PATH"*).
2. Descomprime esta carpeta donde quieras.
3. **Windows:** doble clic en `instalar.bat`. **Mac/Linux:** `./instalar.sh`.

## Hacer vídeos

**Windows:** doble clic en `hacer_video.bat`. Renderiza todos los guiones de `historias/` que todavía no tengan
vídeo y abre la carpeta `salida/`. Ahí tendrás cada `.mp4` y un `.txt` con el título y la descripción para TikTok.

Desde la terminal (con el entorno activado: `.venv\Scripts\activate` en Windows, `source .venv/bin/activate` en Mac):

| Comando | Qué hace |
|---|---|
| `python video.py todos` | Renderiza los guiones que aún no tienen vídeo |
| `python video.py render historias/dato_panal.json` | Renderiza (o vuelve a renderizar) uno concreto |
| `python video.py ver historias/dato_panal.json 12` | Imagen del segundo 12, para revisar sin renderizar |

Opciones: `--borrador` (mitad de resolución, para revisar rápido), `--sin-voz`, `--cpu` (sin gráfica), `--nucleos 4`.

Ya vienen 4 guiones: `dato_alcantarillas`, `dato_panal`, `explica_tangencias` y `ejemplo_compas_roto`.

El dibujo usa todos los núcleos del procesador y la codificación usa tu gráfica (NVIDIA, AMD, Intel o Mac)
si la hay. Al empezar, el programa dice qué codificador usa.

## Tipos de vídeo

- **Dato curioso** (`"tipo": "dato"`): ¿por qué las alcantarillas son redondas?, las abejas y los hexágonos…
- **Ahora lo pillo** (`"tipo": "explicacion"`): un concepto de dibujo técnico explicado fácil.
- **¿Imaginas que…?**: situaciones hipotéticas.
- **Historia con personajes**: como la del compás roto.

Todos acaban solos con el sello de danidemiguel.com y la frase *"Y si estudias dibujo técnico, practica gratis en
danidemiguel.com"*. Para cambiar la frase de un vídeo, pon `"cierre": "otra frase"` en el guion, o `"cierre": false`
para quitar el cierre.

## Cómo es un guion

Cada escena tiene un fondo, la frase del narrador, y qué aparece y cuándo. Los eventos van **sincronizados con la voz**:
`"palabra": "rompió"` hace que pase justo cuando el narrador dice esa palabra.

```json
{
  "fondo": "plano",
  "narracion": "Porque la diagonal de un cuadrado mide un 41 por ciento más que su lado.",
  "destacar": ["diagonal"],
  "objetos": [{"tipo": "contador", "id": "num", "x": 0.5, "y": 0.5, "hasta": 41, "prefijo": "+", "sufijo": "%"}],
  "eventos": [{"quien": "num", "hace": "contar", "palabra": "mide"}]
}
```

**Vocabulario**
- Fondos: `aula`, `examen`, `habitacion`, `biblioteca`, `pasillo`, `calle`, `salon`, `escenario`, `magia`,
  `bokeh`, `bokeh_azul`, `bokeh_calido`, `plano`, `cuaderno`, `espacio`, `mesa`, `negro`
  (o una imagen tuya en `assets/fondos/`).
- Personajes: color de sudadera, `pelo` (corto, coleta, pincho, largo, melena, rizado, calvo, flequillo, moño, gorra),
  `pelo_color`, `piel` (clara, media, morena, oscura, rosada), `ojos_color`, `gafas`, `bigote`, `altura`.
- Caras: neutral, feliz, muy_feliz, triste, sorpresa, asustado, enfadado, serio, guiño, agotado, dormido, pensativo.
- Acciones de personaje: saltar, sorpresa, temblar, llorar, agobiado, celebrar, reir, pensar, señalar, saludar,
  hablar, enfadarse, dormir, caer, andar, salir, cara, mirar.
- Objetos: compas, escuadra, cartabon, regla, lapiz, goma, lamina, portatil, movil, pizarra, pupitre, examen, reloj,
  libros, bombilla, cartel, calendario, estrella, rayo, bocadillo, trofeo, check, cruz, flecha, alcantarilla, panal,
  `figura` (circulo, triangulo, cuadrado, pentagono, hexagono, reuleaux), `tangencia`, `contador`, `barras`,
  `cuadricula` (repite un objeto muchas veces), `texto`, `persona`.
- Acciones de objeto: aparecer, desaparecer, contar, dibujar, girar, crecer, brillar, temblar, flotar, romper, caer.
- Efectos: confeti, flash, sacudir, texto (`"texto": "¡PUM!"`), humo, destellos.
- Cámara: zoom_in, zoom_out, paneo_izq, paneo_der, enfoque (con `"foco"`), fijo. Transición: corte o flash.
- Subtítulos: `"subtitulos": "karaoke"` (por defecto, como en los vídeos de referencia) o `"palabra"` (una palabra grande).

## Personalizar

- **Música de fondo:** mete `.mp3` sin copyright en `assets/musica/`. Se elige una al azar y baja sola cuando habla
  el narrador. O deja la carpeta vacía y añade un sonido de moda al publicar en TikTok.
- **Voz:** `"voz": "es-ES-AlvaroNeural"` (hombre) o `"es-ES-ElviraNeural"` (mujer); `"velocidad": "+6%"`.
- **Pantalla del portátil:** las capturas de `assets/web/`.

## Si algo falla

- *"No he podido generar la voz"*: la voz es gratis, pero necesita internet. El vídeo sale igual, sin narración.
- Si la gráfica da problemas, añade `--cpu`.

Fuentes: TikTok Sans, Fredoka y Merriweather (licencia SIL Open Font License).
