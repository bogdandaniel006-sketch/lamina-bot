"""El 'cerebro': decide qué carrusel hacer según lo que ha funcionado y escribe textos y prompts.

Aprende con un muestreo tipo Thompson sobre tres dimensiones:
  formato (problema_solucion / antes_despues / tips), escenario y tipo de gancho.
Lo que más puntúa sale más a menudo, pero siempre queda margen para probar cosas nuevas.
"""
from __future__ import annotations

import json
import math
import random
from datetime import datetime, timezone

from . import config, gemini

FORMATS = {
    "problema_solucion": {
        "desc": "Slide 1: el agobio del dibujo técnico en papel. Slide 2: Dani usando danidemiguel.com en el ordenador, todo fácil y gratis. Slide 3: cierre con llamada a la acción.",
        "slides": [
            {"role": "problema", "screen": False, "blocks": [{"style": "black", "position": "center"}]},
            {"role": "solucion", "screen": True, "blocks": [{"style": "outline", "position": "lower"}]},
            {"role": "cierre", "screen": True, "blocks": [{"style": "pill", "position": "upper", "fixed": "danidemiguel.com"}, {"style": "outline", "position": "lower"}]},
        ],
    },
    "antes_despues": {
        "desc": "Slide 1: 'Qué pereza…' con la mesa llena de láminas. Slide 2: 'Qué ganas…' con la misma mesa y la web abierta en el portátil. Slide 3: cierre.",
        "slides": [
            {"role": "antes", "screen": False, "blocks": [{"style": "red", "position": "upper"}]},
            {"role": "despues", "screen": True, "blocks": [{"style": "green", "position": "upper"}]},
            {"role": "cierre", "screen": True, "blocks": [{"style": "pill", "position": "upper", "fixed": "danidemiguel.com"}, {"style": "outline", "position": "lower"}]},
        ],
    },
    "tips": {
        "desc": "Slide 1: gancho de resultado ('Así saqué un 10 en la PAU de Dibujo Técnico'). Slide 2: TIP 1, un consejo real de estudio de dibujo técnico. Slide 3: TIP 2, que es practicar en danidemiguel.com.",
        "slides": [
            {"role": "gancho", "screen": False, "blocks": [{"style": "outline", "position": "center"}]},
            {"role": "tip1", "screen": False, "blocks": [{"style": "outline", "position": "center"}]},
            {"role": "tip2_web", "screen": True, "blocks": [{"style": "outline", "position": "lower"}]},
        ],
    },
}

SCENES = {
    "biblioteca": "mesa de madera de una biblioteca pública española, estanterías con libros al fondo, luz cálida de techo, botella de agua",
    "escritorio_noche": "escritorio de una habitación de estudiante por la noche, luz de flexo cálida, monitor y altavoces pequeños al fondo",
    "escritorio_dia": "escritorio blanco junto a una ventana con luz natural de tarde, una planta pequeña, estuche negro",
    "instituto": "pupitre de un aula de instituto español, sillas azules, pizarra desenfocada al fondo",
    "cama": "cama con edredón gris llena de láminas y apuntes, portátil, luz tenue de mesilla",
    "mesa_salon": "mesa de comedor de una casa española, mantel retirado, luz de lámpara de techo, ambiente de domingo por la tarde",
}

HOOKS = {
    "dolor": "frustración: lo difícil, largo o agobiante que es dibujo técnico en papel",
    "humor": "humor de estudiante de 2º de Bachillerato, situaciones reconocibles, ironía",
    "resultado": "resultado concreto y aspiracional: sacar un 10, aprobar la PAU, estudiar un tema en 1 hora",
    "pregunta": "pregunta directa al espectador que le haga pararse ('¿alguien sabe…?', '¿y si pudieras…?')",
}

ALLOWED_EMOJI = "😎 🔥 👀 📐 💻 ✏️ 💀 😭 ✅ 🙌 📚 🎯 🤓 😮‍💨 🤯 🫠 😩 💯 🚀 🧠 📝 👇 👉 🤔 🤷‍♂️ 🌐 💪 🥳"

STYLE_RULES = """Estilo de la cuenta @danidemiguel_ (lo que ha funcionado):
- Español de España, tono de estudiante de 2º Bach que habla a otros estudiantes. Frases cortas, nada de lenguaje de anuncio.
- Ganchos que mejor han funcionado: "Dibujo técnico es muy difícil" (68K visualizaciones, 9.600 guardados),
  "Así he sacado un 10 en la PAU de Dibujo Técnico" + tips (27K), "Qué pereza estudiar dibujo técnico" → "Qué ganas de estudiar dibujo técnico" (19K).
- La solución siempre es danidemiguel.com: hacer láminas y ejercicios de PAU en el ordenador, sin imprimir, sin reglas ni compás, GRATIS.
- Máximo 2 emojis por texto y solo de esta lista: """ + ALLOWED_EMOJI + """
- Textos de slide: máximo 14 palabras (el gancho de la slide 1: máximo 8).
- No inventes cifras de usuarios ni promesas falsas; sí vale hablar en primera persona como estudiante."""


def score(m: dict) -> float:
    v, l, c, s = (m.get(k, 0) or 0 for k in ("views", "likes", "comments", "shares"))
    return math.log1p(v + 2 * l + 5 * c + 10 * s)


MIN_AGE_DAYS = 3  # un post necesita unos días para acumular visitas antes de compararlo


def _mature(p) -> bool:
    if p.get("seed"):
        return True
    try:
        age = datetime.now(timezone.utc) - datetime.fromisoformat(p["created_at"])
        return age.total_seconds() >= MIN_AGE_DAYS * 86400
    except Exception:
        return False


def _scored(history):
    return [p for p in history if p.get("metrics") and p["metrics"].get("views") is not None and _mature(p)]


def choose(history: list[dict], rng: random.Random | None = None) -> dict:
    rng = rng or random.Random()
    scored = _scored(history)
    gmean = sum(score(p["metrics"]) for p in scored) / len(scored) if scored else 8.0
    picks = {}
    for dim, options in (("format", FORMATS), ("scene", SCENES), ("hook", HOOKS)):
        best, best_v = None, -1e9
        for opt in options:
            vals = [score(p["metrics"]) for p in scored if p.get(dim) == opt]
            n = len(vals)
            mean = (gmean + sum(vals)) / (n + 1)  # prior: la media global cuenta como 1 post
            sample = rng.gauss(mean, 1.2 / math.sqrt(n + 1))
            # no repetir escenario del último post
            if dim == "scene" and history and history[-1].get("scene") == opt:
                sample -= 1.0
            if sample > best_v:
                best, best_v = opt, sample
        picks[dim] = best
    return picks


def _examples(history):
    scored = sorted(_scored(history), key=lambda p: score(p["metrics"]), reverse=True)
    fmt = lambda p: f'- [{p["metrics"].get("views", 0)} visualizaciones] formato={p.get("format")} escena={p.get("scene")} textos={p.get("texts")}'
    top = "\n".join(fmt(p) for p in scored[:5]) or "(aún sin datos)"
    low = "\n".join(fmt(p) for p in scored[-3:]) if len(scored) > 5 else "(aún sin datos)"
    recent = "\n".join(f'- {p.get("texts")}' for p in history[-12:]) or "(ninguno)"
    return top, low, recent


def plan(history: list[dict], picks: dict | None = None) -> dict:
    picks = picks or choose(history)
    f = FORMATS[picks["format"]]
    top, low, recent = _examples(history)
    blocks_needed = []
    for i, s in enumerate(f["slides"], 1):
        for j, b in enumerate(s["blocks"]):
            if not b.get("fixed"):
                blocks_needed.append(f'slide{i}_{s["role"]}_texto{j + 1} (estilo {b["style"]})')
    prompt = f"""Eres el community manager de @danidemiguel_, cuenta de TikTok que promociona danidemiguel.com
(herramienta web GRATIS para hacer láminas y ejercicios de Dibujo Técnico de 2º de Bachillerato y PAU en el ordenador).

{STYLE_RULES}

Carrusel de 3 fotos a crear:
- Formato: {picks['format']} → {f['desc']}
- Escenario de las fotos: {SCENES[picks['scene']]}
- Tipo de gancho: {HOOKS[picks['hook']]}

Lo que mejor ha funcionado:
{top}
Lo que peor:
{low}
Textos ya usados recientemente (NO los repitas, varía):
{recent}

Devuelve SOLO este JSON:
{{
  "texts": {{ {", ".join(f'"{b}": "..."' for b in blocks_needed)} }},
  "image_prompts": ["descripción visual slide 1", "slide 2", "slide 3"],
  "title": "título corto del post (máx 70 caracteres, estilo 'La web que me ahorra horas en dibujo técnico 📐💻')",
  "caption": "descripción del post: 1-2 frases + danidemiguel.com + 5 hashtags (#dibujotecnico #2bachillerato #PAU ...)"
}}
Las descripciones visuales: foto vertical realista hecha con el móvil en primera persona, en el escenario indicado,
con láminas A4 de dibujo técnico (circunferencias, tangencias, polígonos), escuadra y cartabón verdes, portaminas, goma.
Sin personas de frente, sin texto escrito en la imagen. En las slides con pantalla, describe un portátil abierto bien visible.
"""
    out = gemini.generate_json(prompt)
    out["picks"] = picks
    out["blocks_needed"] = blocks_needed
    return out


IMAGE_BASE = (
    "Foto vertical 9:16 hiperrealista, hecha con la cámara de un móvil por un estudiante español de 2º de Bachillerato, "
    "encuadre en primera persona desde arriba de la mesa, ligeramente imperfecta y natural (no de estudio), "
    "colores reales, sin ninguna persona de frente (como mucho una mano), SIN texto, letras ni marcas de agua añadidas. "
    "Deja una zona despejada en el {zona} de la imagen para poner texto encima. "
)
SCREEN_RULE = (
    "En la pantalla del portátil debe verse EXACTAMENTE la captura de pantalla adjunta (la web danidemiguel.com), "
    "con perspectiva realista, sin cambiar su contenido ni inventar texto. "
)


def image_prompt(desc: str, slide_def: dict) -> str:
    pos = slide_def["blocks"][-1]["position"]
    zona = {"upper": "tercio superior", "top": "tercio superior", "lower": "tercio inferior", "bottom": "tercio inferior"}.get(pos, "centro")
    p = IMAGE_BASE.format(zona=zona) + desc
    if slide_def["screen"]:
        p = SCREEN_RULE + p
    return p


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
