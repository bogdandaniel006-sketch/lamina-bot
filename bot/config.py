import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MEDIA = ROOT / "docs" / "media"
REFS = ROOT / "assets" / "refs"

TZ = "Europe/Madrid"
# Días de publicación (0=lunes ... 6=domingo) y hora a partir de la cual se prepara el borrador
POST_WEEKDAYS = [int(x) for x in os.getenv("POST_WEEKDAYS", "0,2,4").split(",")]
POST_HOUR = int(os.getenv("POST_HOUR", "17"))
POST_MINUTE = int(os.getenv("POST_MINUTE", "30"))
SLIDES = 3

# Modelos: se prueba en orden hasta que uno funcione (los nombres cambian con el tiempo)
TEXT_MODELS = os.getenv("TEXT_MODELS", "gemini-3-flash,gemini-3-flash-preview,gemini-2.5-flash").split(",")
IMAGE_MODELS = os.getenv("IMAGE_MODELS", "gemini-3.1-flash-image,gemini-3.1-flash-image-preview,gemini-2.5-flash-image").split(",")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TOKEN_KEY = os.getenv("TOKEN_KEY", "")  # clave Fernet para cifrar el token de TikTok guardado en el repo

# URL pública donde GitHub Pages sirve /docs (p. ej. https://usuario.github.io/lamina-bot)
PAGES_BASE = os.getenv("PAGES_BASE", "").rstrip("/")
REDIRECT_URI = os.getenv("TIKTOK_REDIRECT_URI", f"{PAGES_BASE}/callback.html")

WEBSITE = "danidemiguel.com"
