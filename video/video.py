#!/usr/bin/env python3
"""Lámina Vídeo · vídeos animados 2D para el TikTok de @danidemiguel_, renderizados en tu ordenador.

USO
  python video.py render historias/x.json   renderiza un guion (los guiones te los escribe Claude)
  python video.py todos                     renderiza todos los guiones de historias/ que aún no tengan vídeo
  python video.py ver historias/x.json 12   guarda una imagen del segundo 12 (para revisar sin renderizar)

OPCIONES
  --borrador      la mitad de resolución, para revisar rápido
  --sin-voz       sin narración (los subtítulos siguen saliendo)
  --nucleos N     núcleos del procesador a usar (por defecto, todos menos uno)
  --cpu           codificar con el procesador en vez de con la gráfica
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ))
for _s in (sys.stdout, sys.stderr):   # la consola de Windows no siempre entiende los emojis
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from motor import guionista, render  # noqa: E402

SALIDA = RAIZ / "salida"

CIERRE = {
    "fondo": "bokeh",
    "narracion": "Y si estudias dibujo técnico, practica gratis en danidemiguel.com.",
    "transicion": "flash",
    "camara": "zoom_in",
    "sello": True,
    "eventos": [{"hace": "destellos", "x": 0.5, "y": 0.53, "t": 0.2}],
    "pausa": 1.2,
}


def cargar(ruta: Path) -> dict:
    h = json.loads(Path(ruta).read_text(encoding="utf-8"))
    h = guionista.limpiar(h)
    if h.get("cierre", True):
        c = copy.deepcopy(CIERRE)
        if isinstance(h.get("cierre"), str):
            c["narracion"] = h["cierre"]
        h["escenas"].append(c)
    return h


def hacer(ruta: Path, args) -> Path:
    h = cargar(ruta)
    print(f"\n📖 {h.get('titulo', ruta.stem)}")
    out = SALIDA / (ruta.stem + ("_borrador" if args.borrador else "") + ".mp4")
    render.renderizar(h, out, sin_voz=args.sin_voz, borrador=args.borrador, nucleos=args.nucleos,
                      codificador="libx264" if args.cpu else None)
    if h.get("descripcion_tiktok"):
        out.with_suffix(".txt").write_text(f"{h.get('titulo', '')}\n\n{h['descripcion_tiktok']}\n", encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("orden", nargs="?", default="todos", choices=["render", "todos", "ver"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("arg2", nargs="?")
    ap.add_argument("--borrador", action="store_true")
    ap.add_argument("--sin-voz", action="store_true")
    ap.add_argument("--nucleos", type=int)
    ap.add_argument("--cpu", action="store_true")
    args = ap.parse_args()

    if args.orden == "render":
        if not args.arg:
            ap.error("dime qué historia: python video.py render historias/archivo.json")
        hacer(Path(args.arg), args)
    elif args.orden == "ver":
        h = cargar(Path(args.arg))
        seg = float(args.arg2 or 1)
        out = SALIDA / f"{Path(args.arg).stem}_{seg:.1f}s.png"
        SALIDA.mkdir(exist_ok=True)
        render.fotograma(h, seg, out, sin_voz=args.sin_voz)
        print(f"🖼️  {out}")
    else:
        hechos = 0
        for ruta in sorted((RAIZ / "historias").glob("*.json")):
            if not (SALIDA / (ruta.stem + ".mp4")).exists():
                hacer(ruta, args)
                hechos += 1
        print("No hay guiones nuevos: todos tienen ya su vídeo en salida/." if not hechos else f"\n🎉 {hechos} vídeo(s) nuevos en salida/")

if __name__ == "__main__":
    main()
