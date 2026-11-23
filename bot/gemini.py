"""Llamadas a la API de Gemini: texto (JSON) e imágenes (Nano Banana)."""
from __future__ import annotations

import io
import json
import time

from PIL import Image

from . import config

_client = None


def client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _discover(kind: str) -> list[str]:
    """Pregunta a la API qué modelos hay y elige los más nuevos del tipo pedido."""
    import re
    try:
        names = [m.name.split("/")[-1] for m in client().models.list()]
    except Exception:
        return []
    def ver(n):
        m = re.search(r"(\d+(?:\.\d+)?)", n)
        return float(m.group(1)) if m else 0
    bad = ("tts", "live", "audio", "embedding", "thinking", "exp", "native")
    if kind == "image":
        c = [n for n in names if "image" in n and "flash" in n and not any(b in n for b in bad)]
        c.sort(key=lambda n: (ver(n), "lite" not in n, "preview" not in n), reverse=True)
    else:
        c = [n for n in names if n.startswith("gemini") and "flash" in n and "image" not in n and "lite" not in n
             and not any(b in n for b in bad)]
        c.sort(key=lambda n: (ver(n), "preview" not in n), reverse=True)
    print(f"Modelos {kind} disponibles: {c[:5]}")
    return c[:4]


def _try_models(models, fn, kind="text"):
    last = None
    models = list(models) + [m for m in _discover(kind) if m not in models]
    for m in models:
        m = m.strip()
        for attempt in range(2):
            try:
                return fn(m)
            except Exception as e:  # modelo inexistente, saturado, etc.
                last = e
                msg = str(e).lower()
                if "not found" in msg or "404" in msg or "not supported" in msg or "no longer available" in msg:
                    break
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Ningún modelo funcionó: {last}")


def generate_json(prompt: str) -> dict:
    from google.genai import types

    def call(model):
        r = client().models.generate_content(
            model=model, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0),
        )
        return json.loads(r.text)

    return _try_models(config.TEXT_MODELS, call, 'text')


def generate_image(prompt: str, references: list[Image.Image] | None = None) -> Image.Image:
    from google.genai import types

    contents = [prompt] + list(references or [])

    def call(model):
        cfg = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="9:16"),
        )
        r = client().models.generate_content(model=model, contents=contents, config=cfg)
        for cand in r.candidates or []:
            for part in cand.content.parts or []:
                if getattr(part, "inline_data", None) and part.inline_data.data:
                    return Image.open(io.BytesIO(part.inline_data.data))
        raise RuntimeError("La respuesta no traía imagen")

    return _try_models(config.IMAGE_MODELS, call, 'image')
