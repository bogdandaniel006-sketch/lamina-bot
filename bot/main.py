"""Punto de entrada. Uso: python -m bot.main <comando>

  prepare [--force]   Si toca publicar hoy: decide, genera imágenes y monta las 3 slides en docs/media/<id>/
  upload              Envía el carrusel preparado a la bandeja de TikTok (cuando las imágenes ya están online)
  upload-video MP4 GUION  Envía un vídeo animado (video/) a la bandeja de TikTok y lo apunta en el historial
  metrics             Actualiza visualizaciones/likes/etc. de los posts y aprende
  report              Escribe el informe semanal en report.md
  preview             Genera un carrusel de prueba en docs/preview/ (no sube nada)
  auth-url            Muestra el enlace para autorizar la cuenta de TikTok
  auth-code CODE      Canjea el código de autorización y guarda el token cifrado
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from PIL import Image

from . import brain, compose, config, gemini, tiktok

HISTORY = config.DATA / "history.json"
PENDING = config.DATA / "pending.json"


def load_history() -> list[dict]:
    return json.loads(HISTORY.read_text()) if HISTORY.exists() else []


def save_history(h):
    HISTORY.write_text(json.dumps(h, ensure_ascii=False, indent=1))


def gh_output(key, value):
    import os
    p = os.getenv("GITHUB_OUTPUT")
    if p:
        with open(p, "a") as f:
            f.write(f"{key}={value}\n")
    print(f"{key}={value}")


def screen_refs() -> list[Image.Image]:
    return [Image.open(p).convert("RGB") for p in sorted(config.REFS.glob("app_*.*"))][:2]


def style_refs() -> list[Image.Image]:
    return [Image.open(p).convert("RGB") for p in sorted(config.REFS.glob("style_*.*"))][:2]


def due_today(history, now_local) -> bool:
    if now_local.weekday() not in config.POST_WEEKDAYS:
        return False
    if (now_local.hour, now_local.minute) < (config.POST_HOUR, config.POST_MINUTE - 10):
        return False
    today = now_local.date().isoformat()
    return not any(p.get("local_date") == today and not p.get("seed") for p in history)


def build_carousel(history, out_dir: Path) -> dict:
    p = brain.plan(history)
    fdef = brain.FORMATS[p["picks"]["format"]]
    texts = list(p["texts"].values())
    ti = 0
    files, all_texts = [], []
    refs_screen, refs_style = screen_refs(), style_refs()
    for i, sdef in enumerate(fdef["slides"]):
        desc = p["image_prompts"][i] if i < len(p["image_prompts"]) else ""
        prompt = brain.image_prompt(f"Escenario: {brain.SCENES[p['picks']['scene']]}. {desc}", sdef)
        refs = (refs_screen if sdef["screen"] else []) + refs_style
        bg = gemini.generate_image(prompt, refs)
        blocks = []
        for b in sdef["blocks"]:
            if b.get("fixed"):
                txt = b["fixed"]
            else:
                txt = texts[ti] if ti < len(texts) else ""
                ti += 1
                all_texts.append(txt)
            blocks.append({"text": txt, "style": b["style"], "position": b["position"]})
        img = compose.render_slide(bg, blocks)
        f = out_dir / f"{i + 1}.jpg"
        compose.save_jpeg(img, f)
        files.append(f.name)
    return {"picks": p["picks"], "texts": all_texts, "title": p.get("title", ""), "caption": p.get("caption", ""), "files": files}


def cmd_prepare(force=False):
    history = load_history()
    now = datetime.now(ZoneInfo(config.TZ))
    if not force and not due_today(history, now):
        gh_output("prepared", "false"); return
    pid = now.strftime("%Y%m%d-%H%M")
    out = config.MEDIA / pid
    c = build_carousel(history, out)
    c.update(id=pid, local_date=now.date().isoformat(), created_at=brain.now_iso())
    PENDING.write_text(json.dumps(c, ensure_ascii=False, indent=1))
    gh_output("prepared", "true")


def _wait_online(urls, timeout_s=600):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            if all(requests.head(u, timeout=15).status_code == 200 for u in urls):
                return True
        except requests.RequestException:
            pass
        time.sleep(15)
    raise RuntimeError("Las imágenes no aparecieron en GitHub Pages a tiempo")


def cmd_upload():
    if not PENDING.exists():
        print("Nada pendiente"); return
    c = json.loads(PENDING.read_text())
    urls = [f"{config.PAGES_BASE}/media/{c['id']}/{f}" for f in c["files"]]
    _wait_online(urls)
    token = tiktok.access_token()
    pub = tiktok.upload_photo_draft(token, urls, c["title"], c["caption"])
    st = tiktok.wait_status(token, pub)
    print("Estado TikTok:", st)
    if st.get("status") == "FAILED":
        raise RuntimeError(f"TikTok rechazó el carrusel: {st}")
    history = load_history()
    history.append({**{k: c[k] for k in ("id", "local_date", "created_at", "texts", "title", "caption")},
                    **c["picks"], "publish_id": pub, "status": st.get("status"), "metrics": None})
    save_history(history)
    PENDING.unlink()


def cmd_upload_video(video: str, guion: str):
    """Sube un vídeo animado (de video/) a la bandeja de TikTok y lo apunta en el historial,
    para que ese día ya no se genere carrusel."""
    g = json.loads(Path(guion).read_text(encoding="utf-8"))
    token = tiktok.access_token()
    pub = tiktok.upload_video_draft(token, Path(video))
    st = tiktok.wait_status(token, pub)
    print("Estado TikTok:", st)
    if st.get("status") == "FAILED":
        raise RuntimeError(f"TikTok rechazó el vídeo: {st}")
    now = datetime.now(ZoneInfo(config.TZ))
    history = load_history()
    history.append({
        "id": now.strftime("%Y%m%d-%H%M") + "-video", "local_date": now.date().isoformat(), "created_at": brain.now_iso(),
        "format": "video", "tipo": g.get("tipo", "historia"), "guion": Path(guion).stem,
        "title": g.get("titulo", ""), "caption": g.get("descripcion_tiktok", ""),
        "texts": [e.get("narracion", "") for e in g.get("escenas", [])][:3],
        "publish_id": pub, "status": st.get("status"), "metrics": None})
    save_history(history)
    gh_output("titulo", g.get("titulo", ""))


def _norm(s):
    return "".join(ch.lower() for ch in (s or "") if ch.isalnum())[:40]


def cmd_metrics():
    token = tiktok.access_token()
    posts = tiktok.list_posts(token)
    history = load_history()
    used = set(p.get("tiktok_id") for p in history if p.get("tiktok_id"))
    for h in history:
        cand = None
        if h.get("tiktok_id"):
            cand = next((v for v in posts if v["id"] == h["tiktok_id"]), None)
        if not cand:
            keys = {_norm(h.get("title")), _norm(h.get("caption"))} - {""}
            cand = next((v for v in posts if v["id"] not in used and
                         ({_norm(v.get("title")), _norm(v.get("video_description"))} & keys)), None)
        if not cand and h.get("created_at") and not h.get("seed"):
            t = datetime.fromisoformat(h["created_at"]).timestamp()
            later = sorted((v for v in posts if v["id"] not in used and t - 3600 < v["create_time"] < t + 4 * 86400),
                           key=lambda v: v["create_time"])
            cand = later[0] if later else None
        if cand:
            used.add(cand["id"])
            h["tiktok_id"] = cand["id"]
            h["url"] = cand.get("share_url")
            h["metrics"] = {"views": cand.get("view_count", 0), "likes": cand.get("like_count", 0),
                            "comments": cand.get("comment_count", 0), "shares": cand.get("share_count", 0),
                            "updated": brain.now_iso()}
    save_history(history)
    print(f"Métricas actualizadas: {sum(1 for h in history if h.get('metrics'))} posts con datos")


def cmd_report():
    history = load_history()
    since = datetime.now(timezone.utc) - timedelta(days=7)
    week = [h for h in history if not h.get("seed") and h.get("created_at")
            and datetime.fromisoformat(h["created_at"]) >= since]
    lines = ["# Informe semanal de TikTok 📊", ""]
    if week:
        lines += ["## Carruseles de esta semana", "", "| Fecha | Formato | Escena | Gancho | Visualizaciones | Likes | Compartidos |", "|---|---|---|---|---|---|---|"]
        for h in week:
            m = h.get("metrics") or {}
            lines.append(f"| {h['local_date']} | {h.get('format')} | {h.get('scene')} | {h.get('hook')} | {m.get('views', '—')} | {m.get('likes', '—')} | {m.get('shares', '—')} |")
        lines.append("")
        missing = [h for h in week if not h.get("metrics")]
        if missing:
            lines.append(f"⚠️ {len(missing)} borrador(es) sin publicar o sin datos todavía.\n")
    else:
        lines.append("Esta semana no se ha publicado ningún carrusel.\n")
    lines += ["## Lo que mejor funciona (todas las semanas)", ""]
    scored = brain._scored(history)
    for dim, opts in (("format", brain.FORMATS), ("scene", brain.SCENES), ("hook", brain.HOOKS)):
        rows = []
        for o in opts:
            vs = [h["metrics"]["views"] for h in scored if h.get(dim) == o]
            if vs:
                rows.append((sum(vs) / len(vs), o, len(vs)))
        rows.sort(reverse=True)
        if rows:
            lines.append(f"**{dim}:** " + " · ".join(f"{o} ({format(int(a), ',').replace(',', '.')} de media, {n} posts)" for a, o, n in rows))
    nxt = brain.choose(history)
    lines += ["", f"**Próxima apuesta probable:** formato `{nxt['format']}`, escena `{nxt['scene']}`, gancho `{nxt['hook']}`."]
    Path("report.md").write_text("\n".join(lines))
    print("\n".join(lines))


def cmd_preview():
    out = config.ROOT / "docs" / "preview"
    shutil.rmtree(out, ignore_errors=True)
    c = build_carousel(load_history(), out)
    (out / "info.json").write_text(json.dumps(c, ensure_ascii=False, indent=1))
    imgs = "".join(f'<img src="{f}" style="width:32%;margin:.5%">' for f in c["files"])
    (out / "index.html").write_text(
        f'<meta charset="utf-8"><body style="font-family:sans-serif;background:#111;color:#eee;padding:16px">'
        f'<h2>Vista previa</h2><p>{c["picks"]}</p><div>{imgs}</div><h3>{c["title"]}</h3><p>{c["caption"]}</p></body>')
    print(json.dumps(c, ensure_ascii=False, indent=1))


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "prepare":
        cmd_prepare(force="--force" in argv)
    elif cmd == "upload":
        cmd_upload()
    elif cmd == "upload-video":
        cmd_upload_video(argv[2], argv[3])
    elif cmd == "metrics":
        cmd_metrics()
    elif cmd == "report":
        cmd_report()
    elif cmd == "preview":
        cmd_preview()
    elif cmd == "auth-url":
        url = tiktok.auth_url()
        # Página que redirige a TikTok (el client key es público en el flujo OAuth; el secret nunca sale)
        (config.ROOT / "docs" / "authorize.html").write_text(
            f'<meta charset="utf-8"><meta http-equiv="refresh" content="0;url={url}"><a href="{url}">Autorizar TikTok</a>')
        print("Abre: " + config.PAGES_BASE + "/authorize.html")
    elif cmd == "auth-code":
        tiktok.exchange_code(argv[2])
        print("Token guardado ✅")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
