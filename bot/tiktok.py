"""API de TikTok: tokens, subir carrusel como borrador (bandeja) y leer métricas."""
from __future__ import annotations

import json
import time
from pathlib import Path

import requests

from . import config

API = "https://open.tiktokapis.com/v2"
TOKEN_FILE = config.DATA / "tiktok_token.enc"
SCOPES = "user.info.basic,video.upload,video.list"


# ---------- token (guardado cifrado en el repo para poder renovarlo en cada ejecución) ----------
def _fernet():
    import base64, hashlib
    from cryptography.fernet import Fernet
    secret = config.TOKEN_KEY or config.TIKTOK_CLIENT_SECRET
    if not secret:
        raise RuntimeError("Falta el secreto TIKTOK_CLIENT_SECRET")
    # La clave de cifrado se deriva del client secret (que solo está en los secretos de GitHub)
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(("lamina:" + secret).encode()).digest()))


def save_token(tok: dict):
    tok["saved_at"] = int(time.time())
    TOKEN_FILE.write_bytes(_fernet().encrypt(json.dumps(tok).encode()))


def load_token() -> dict:
    if not TOKEN_FILE.exists():
        raise RuntimeError("No hay token de TikTok: ejecuta primero el workflow 'Autorizar TikTok'")
    return json.loads(_fernet().decrypt(TOKEN_FILE.read_bytes()))


def auth_url(state: str = "lamina") -> str:
    from urllib.parse import urlencode
    q = dict(client_key=config.TIKTOK_CLIENT_KEY, scope=SCOPES, response_type="code",
             redirect_uri=config.REDIRECT_URI, state=state)
    return "https://www.tiktok.com/v2/auth/authorize/?" + urlencode(q)


def _token_request(data: dict) -> dict:
    r = requests.post(f"{API}/oauth/token/", data={
        "client_key": config.TIKTOK_CLIENT_KEY, "client_secret": config.TIKTOK_CLIENT_SECRET, **data},
        headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    j = r.json()
    if "access_token" not in j:
        raise RuntimeError(f"Error de token TikTok: {j}")
    return j


def exchange_code(code: str) -> dict:
    from urllib.parse import unquote
    tok = _token_request({"code": unquote(code), "grant_type": "authorization_code", "redirect_uri": config.REDIRECT_URI})
    save_token(tok)
    return tok


def access_token() -> str:
    tok = load_token()
    # El access token dura 24 h: lo renovamos en cada ejecución (el refresh token dura 1 año y se rota)
    new = _token_request({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"]})
    save_token(new)
    return new["access_token"]


def _post(path: str, token: str, body: dict, params: dict | None = None) -> dict:
    r = requests.post(f"{API}{path}", params=params, json=body, timeout=60,
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"})
    j = r.json()
    err = j.get("error", {})
    if err.get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok {path}: {err}")
    return j.get("data", {})


# ---------- publicar como borrador ----------
def upload_photo_draft(token: str, image_urls: list[str], title: str, description: str) -> str:
    body = {
        "media_type": "PHOTO",
        "post_mode": "MEDIA_UPLOAD",  # va a la bandeja de TikTok: Dani revisa y publica
        "post_info": {"title": title[:90], "description": description[:4000]},
        "source_info": {"source": "PULL_FROM_URL", "photo_cover_index": 0, "photo_images": image_urls},
    }
    return _post("/post/publish/content/init/", token, body)["publish_id"]


def publish_status(token: str, publish_id: str) -> dict:
    return _post("/post/publish/status/fetch/", token, {"publish_id": publish_id})


def wait_status(token: str, publish_id: str, timeout_s: int = 300) -> dict:
    t0 = time.time()
    st = {}
    while time.time() - t0 < timeout_s:
        st = publish_status(token, publish_id)
        if st.get("status") in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE", "FAILED"):
            return st
        time.sleep(8)
    return st


# ---------- métricas ----------
def list_posts(token: str, max_pages: int = 5) -> list[dict]:
    fields = "id,title,video_description,create_time,view_count,like_count,comment_count,share_count,share_url"
    out, cursor = [], None
    for _ in range(max_pages):
        body = {"max_count": 20}
        if cursor:
            body["cursor"] = cursor
        d = _post("/video/list/", token, body, params={"fields": fields})
        out += d.get("videos", [])
        if not d.get("has_more"):
            break
        cursor = d.get("cursor")
    return out
