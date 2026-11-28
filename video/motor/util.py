"""Utilidades comunes: curvas de animación, colores, fuentes y pinceles de Skia."""
from __future__ import annotations

import math
import random
import unicodedata
import zlib
from functools import lru_cache
from pathlib import Path

import skia

RAIZ = Path(__file__).resolve().parent.parent
ASSETS = RAIZ / "assets"

W, H = 1080, 1920          # resolución final (vertical 9:16)
FPS = 30
SUELO = 1530               # altura (px) donde apoyan los pies los personajes
TINTA = 0xFF1E1B2E         # color de los contornos


# ----------------------------------------------------------------- curvas
def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def ease_in_out(t: float) -> float:
    t = clamp01(t)
    return t * t * (3 - 2 * t)


def ease_out(t: float) -> float:
    t = clamp01(t)
    return 1 - (1 - t) ** 3


def ease_in(t: float) -> float:
    t = clamp01(t)
    return t ** 3


def ease_out_back(t: float, s: float = 1.9) -> float:
    t = clamp01(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out_elastic(t: float) -> float:
    t = clamp01(t)
    if t in (0, 1):
        return t
    return 2 ** (-10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1


def ventana(t: float, t0: float, dur: float) -> float | None:
    """Progreso 0..1 de un evento que empieza en t0 y dura dur; None si no está activo."""
    if t < t0 or t > t0 + dur:
        return None
    return (t - t0) / dur if dur > 0 else 1.0


def ruido(seed: int, t: float) -> float:
    """Ruido suave (-1..1) barato y determinista."""
    return (math.sin(t * 1.7 + seed * 12.9898) * 0.6 + math.sin(t * 3.1 + seed * 78.233) * 0.4)


# ----------------------------------------------------------------- colores
def color(c, alpha: float = 1.0) -> int:
    """'#rrggbb' | 0xAARRGGBB -> int ARGB con alpha aplicado."""
    if isinstance(c, str):
        c = c.lstrip("#")
        v = 0xFF000000 | int(c[:6], 16)
    else:
        v = c
    a = int(((v >> 24) & 0xFF) * clamp01(alpha))
    return (a << 24) | (v & 0x00FFFFFF)


def mezcla(c1, c2, t: float) -> int:
    a, b = color(c1), color(c2)
    out = 0
    for sh in (24, 16, 8, 0):
        x = (a >> sh) & 0xFF
        y = (b >> sh) & 0xFF
        out |= int(lerp(x, y, clamp01(t))) << sh
    return out


def oscurece(c, f: float = 0.25) -> int:
    return mezcla(c, 0xFF000000, f)


def aclara(c, f: float = 0.25) -> int:
    return mezcla(c, 0xFFFFFFFF, f)


# ----------------------------------------------------------------- pinceles
def relleno(c, alpha: float = 1.0) -> skia.Paint:
    return skia.Paint(Color=color(c, alpha), AntiAlias=True, Style=skia.Paint.kFill_Style)


def trazo(c, ancho: float, alpha: float = 1.0, redondo: bool = True) -> skia.Paint:
    p = skia.Paint(Color=color(c, alpha), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=ancho)
    if redondo:
        p.setStrokeCap(skia.Paint.kRound_Cap)
        p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def degradado_v(y0: float, y1: float, c0, c1) -> skia.Paint:
    sh = skia.GradientShader.MakeLinear([(0, y0), (0, y1)], [color(c0), color(c1)])
    return skia.Paint(Shader=sh, AntiAlias=True)


def degradado_r(cx: float, cy: float, r: float, c0, c1) -> skia.Paint:
    sh = skia.GradientShader.MakeRadial((cx, cy), r, [color(c0), color(c1)])
    return skia.Paint(Shader=sh, AntiAlias=True)


def forma(cv: skia.Canvas, path: skia.Path, c, borde: float = 7, c_borde=None, alpha: float = 1.0):
    """Relleno con degradado suave (luz arriba) y contorno del mismo tono más oscuro: aspecto ilustrado."""
    b = path.getBounds()
    sh = skia.GradientShader.MakeLinear(
        [(b.left(), b.top()), (b.left() + b.width() * 0.35, b.bottom())],
        [color(aclara(c, 0.2), alpha), color(oscurece(c, 0.12), alpha)])
    cv.drawPath(path, skia.Paint(Shader=sh, AntiAlias=True))
    if borde:
        cv.drawPath(path, trazo(c_borde if c_borde is not None else oscurece(c, 0.45), borde * 0.8, alpha))


def rrect(x, y, w, h, r) -> skia.Path:
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r))
    return p


def circulo(cx, cy, r) -> skia.Path:
    p = skia.Path()
    p.addCircle(cx, cy, r)
    return p


def poligono(puntos) -> skia.Path:
    p = skia.Path()
    p.moveTo(*puntos[0])
    for q in puntos[1:]:
        p.lineTo(*q)
    p.close()
    return p


# ----------------------------------------------------------------- fuentes e imágenes
@lru_cache(maxsize=None)
def tipografia(nombre: str) -> skia.Typeface:
    ruta = ASSETS / "fuentes" / nombre
    tf = skia.Typeface.MakeFromFile(str(ruta)) if ruta.exists() else None
    return tf or skia.Typeface.MakeDefault()


@lru_cache(maxsize=None)
def fuente(nombre: str, tam: float) -> skia.Font:
    f = skia.Font(tipografia(nombre), tam)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setSubpixel(True)
    return f


@lru_cache(maxsize=None)
def imagen(ruta: str) -> skia.Image | None:
    p = Path(ruta)
    if not p.exists():
        return None
    return skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(str(p)))


def texto_centrado(cv, txt, cx, cy, f: skia.Font, paint: skia.Paint):
    ancho = f.measureText(txt)
    m = f.getMetrics()
    cv.drawString(txt, cx - ancho / 2, cy - (m.fAscent + m.fDescent) / 2, f, paint)


def normaliza(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return "".join(ch for ch in s if ch.isalnum() or ch == " ").strip()


def rng(*claves) -> random.Random:
    # crc32 y no hash(): hash() cambia entre procesos y los efectos parpadearían
    return random.Random(zlib.crc32("|".join(str(k) for k in claves).encode()))
