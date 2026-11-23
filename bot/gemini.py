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


def _try_models(models, fn):
    last = None
    for m in models:
        m = m.strip()
        for attempt in range(2):
            try:
                return fn(m)
            except Exception as e:  # modelo inexistente, saturado, etc.
                last = e
                msg = str(e).lower()
                if "not found" in msg or "404" in msg or "not supported" in msg:
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

    return _try_models(config.TEXT_MODELS, call)


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

    return _try_models(config.IMAGE_MODELS, call)
