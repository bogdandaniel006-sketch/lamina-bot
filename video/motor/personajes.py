"""Personajes 2D con volumen (cabeza grande, estilo 'chibi'), dibujados por código.

Cada personaje se define con unos pocos rasgos (piel, pelo, ropa, gafas...) y se anima con una
'Pose' que calcula escena.py en cada fotograma. Todo lleva degradados suaves y contornos del
mismo tono (no negros) para que parezca ilustrado.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import skia

from .util import aclara, circulo, color, ease_out_back, fuente, mezcla, oscurece, poligono, relleno, texto_centrado, trazo

PIELES = {"clara": "#ffdcc2", "media": "#f1b98c", "morena": "#c98b5b", "oscura": "#8d5a3b", "rosada": "#ffd0b5"}
PELOS = ("corto", "coleta", "pincho", "largo", "rizado", "calvo", "flequillo", "moño", "gorra", "melena")
CARAS = ("neutral", "feliz", "muy_feliz", "triste", "sorpresa", "asustado", "enfadado", "serio",
         "guiño", "agotado", "dormido", "pensativo")
PANTALON = "#34406b"


@dataclass
class Rasgos:
    color: str = "#4dabf7"          # sudadera
    pelo: str = "corto"
    pelo_color: str = "#4a2f20"
    piel: str = "clara"
    ojos_color: str = "#5b3a24"
    gafas: bool = False
    bigote: bool = False
    altura: float = 1.0
    nombre: str = ""

    @classmethod
    def de_dict(cls, d: dict, nombre: str = "") -> "Rasgos":
        r = cls(nombre=nombre)
        for k, v in (d or {}).items():
            if hasattr(r, k):
                setattr(r, k, v)
        if r.pelo not in PELOS:
            r.pelo = "corto"
        return r

    @property
    def tono(self) -> str:
        return PIELES.get(self.piel, self.piel if str(self.piel).startswith("#") else PIELES["clara"])


@dataclass
class Pose:
    cara: str = "neutral"
    mira: int = 1
    dy: float = 0.0
    dx: float = 0.0
    giro: float = 0.0
    aplasta: float = 0.0
    brazos: tuple = ((0.22, 0.2), (0.22, 0.2))     # (brazo trasero, brazo delantero): (ángulo, codo)
    paso: float | None = None
    respira: float = 0.0
    parpadeo: float = 0.0
    habla: float = 0.0
    ojos: float = 1.0
    marcas: dict = field(default_factory=dict)
    alpha: float = 1.0


# medidas base (escala 1, pies en y = 0)
CADERA, HOMBRO = -150, -292
CABEZA_Y, CABEZA_R = -430, 128
BRAZO1, BRAZO2 = 74, 66
HOMBRO_X = 60


# ------------------------------------------------------------------ pinceles con volumen
def vol(cv, path: skia.Path, c, borde: float = 5.0, luz: float = 0.22, sombra: float = 0.14, alpha: float = 1.0):
    """Relleno con degradado (luz arriba-izquierda) y contorno del mismo color más oscuro."""
    b = path.getBounds()
    sh = skia.GradientShader.MakeLinear(
        [(b.left(), b.top()), (b.left() + b.width() * 0.35, b.bottom())],
        [color(aclara(c, luz), alpha), color(oscurece(c, sombra), alpha)])
    cv.drawPath(path, skia.Paint(Shader=sh, AntiAlias=True))
    if borde:
        cv.drawPath(path, trazo(oscurece(c, 0.42), borde, alpha))


def _brillo(cv, x, y, w, h, alpha=0.45):
    cv.drawOval(skia.Rect.MakeXYWH(x, y, w, h), relleno("#ffffff", alpha))


def _miembro(cv, puntos, c, ancho):
    p = skia.Path()
    p.moveTo(*puntos[0])
    for q in puntos[1:]:
        p.lineTo(*q)
    cv.drawPath(p, trazo(oscurece(c, 0.42), ancho + 10))
    cv.drawPath(p, trazo(c, ancho))
    # reflejo sutil a lo largo del miembro
    cv.drawPath(p, trazo(aclara(c, 0.25), ancho * 0.3, 0.6))


def _brazo(cv, lado, a, b, c, piel):
    s = (HOMBRO_X * lado, HOMBRO + 26)
    codo = (s[0] + lado * math.sin(a) * BRAZO1, s[1] + math.cos(a) * BRAZO1)
    a2 = a + b
    mano = (codo[0] + lado * math.sin(a2) * BRAZO2, codo[1] + math.cos(a2) * BRAZO2)
    _miembro(cv, [s, codo, mano], c, 30)
    p = skia.Path()
    p.addCircle(mano[0], mano[1], 21)
    vol(cv, p, piel, 4)
    return mano


# ------------------------------------------------------------------ pelo
def _pelo(cv, r: Rasgos, mira, detras: bool):
    pc = r.pelo_color
    cy, R = CABEZA_Y, CABEZA_R
    p = skia.Path()
    if detras:
        if r.pelo in ("largo", "melena"):
            largo = 1.25 if r.pelo == "largo" else 0.75
            p.moveTo(-R * 1.08, cy - R * 0.1)
            p.cubicTo(-R * 1.2, cy + R * largo, -R * 0.6, cy + R * (largo + 0.15), 0, cy + R * (largo + 0.1))
            p.cubicTo(R * 0.6, cy + R * (largo + 0.15), R * 1.2, cy + R * largo, R * 1.08, cy - R * 0.1)
            p.close()
            vol(cv, p, oscurece(pc, 0.1), 5)
        elif r.pelo == "coleta":
            bx = -mira * R * 0.9
            p.moveTo(bx, cy - R * 0.55)
            p.cubicTo(bx - mira * 110, cy - R * 0.5, bx - mira * 95, cy + R * 0.8, bx - mira * 30, cy + R * 1.0)
            p.cubicTo(bx - mira * 45, cy + R * 0.4, bx - mira * 15, cy - R * 0.05, bx, cy - R * 0.15)
            p.close()
            vol(cv, p, pc, 5)
            cv.drawCircle(bx - mira * 8, cy - R * 0.38, 14, relleno("#ff6b9d"))
        elif r.pelo == "moño":
            p.addCircle(0, cy - R * 1.08, 52)
            vol(cv, p, pc, 5)
        return

    if r.pelo == "calvo":
        # solo un poco de pelo a los lados
        for lado in (-1, 1):
            q = skia.Path()
            q.moveTo(lado * R * 0.99, cy - 52)
            q.quadTo(lado * R * 1.12, cy - 10, lado * R * 0.93, cy + 30)
            q.quadTo(lado * R * 0.86, cy - 10, lado * R * 0.99, cy - 52)
            vol(cv, q, pc, 3)
        return
    if r.pelo == "gorra":
        p.addArc(skia.Rect.MakeLTRB(-R * 1.02, cy - R * 1.06, R * 1.02, cy + R * 0.55), 180, 180)
        p.close()
        vol(cv, p, r.color, 5)
        v = skia.Path()
        v.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(mira * R * 0.35 - 95, cy - R * 0.34, 190, 34), 17, 17))
        vol(cv, v, oscurece(r.color, 0.18), 5)
        cv.drawCircle(0, cy - R * 1.0, 12, relleno(oscurece(r.color, 0.2)))
        return

    # flequillo / casquete común
    p.moveTo(-R * 1.06, cy + R * 0.05)
    p.cubicTo(-R * 1.15, cy - R * 1.25, R * 1.15, cy - R * 1.25, R * 1.06, cy + R * 0.05)
    if r.pelo in ("pincho",):
        n = 9
        p.lineTo(R * 0.95, cy - R * 0.3)
        for i in range(n):
            x0 = R * 0.95 - (i + 1) * (1.9 * R / (n + 1))
            p.lineTo(x0 + R * 0.1, cy - R * 0.6 + (i % 2) * 18)
            p.lineTo(x0, cy - R * 0.3)
    elif r.pelo in ("flequillo", "largo", "melena"):
        p.quadTo(R * 0.85, cy - R * 0.55, R * 0.45, cy - R * 0.38)
        p.quadTo(R * 0.15, cy - R * 0.62, -R * 0.15, cy - R * 0.4)
        p.quadTo(-R * 0.55, cy - R * 0.62, -R * 0.85, cy - R * 0.2)
    elif r.pelo == "rizado":
        p.lineTo(R * 0.9, cy - R * 0.45)
        p.quadTo(0, cy - R * 0.75, -R * 0.9, cy - R * 0.45)
    else:   # corto, coleta, moño
        p.quadTo(R * 0.6, cy - R * 0.75, -mira * R * 0.1, cy - R * 0.58)
        p.quadTo(-R * 0.7, cy - R * 0.5, -R * 1.06, cy + R * 0.05)
    p.close()
    vol(cv, p, pc, 5)
    if r.pelo == "rizado":
        for i in range(11):
            ang = math.pi * 0.92 + i * math.pi * 1.16 / 10
            q = skia.Path()
            q.addCircle(math.cos(ang) * R * 1.0, cy + math.sin(ang) * R * 0.98, 40)
            vol(cv, q, pc, 4)
    # brillo del pelo
    h = skia.Path()
    h.moveTo(-R * 0.55, cy - R * 0.78)
    h.quadTo(-R * 0.1, cy - R * 0.98, R * 0.3, cy - R * 0.85)
    cv.drawPath(h, trazo("#ffffff", 12, 0.28))


# ------------------------------------------------------------------ cara
def _ojo(cv, ex, ey, r: Rasgos, pose: Pose, cerrado: float, cara: str, lado: int):
    tono = r.tono
    grande = cara in ("sorpresa", "asustado") or pose.ojos > 1.25
    if cerrado > 0.6 or cara == "muy_feliz" or (cara == "guiño" and lado == -pose.mira):
        p = skia.Path()
        p.moveTo(ex - 20, ey + 4)
        if cara in ("muy_feliz", "guiño", "feliz"):
            p.quadTo(ex, ey - 20, ex + 20, ey + 4)
        else:
            p.quadTo(ex, ey + 12, ex + 20, ey + 4)
        cv.drawPath(p, trazo("#3b2316", 7))
        return
    k = 1.25 if grande else 1.0
    w, h = 26 * k, 33 * k * (1 - 0.85 * cerrado)
    cv.drawOval(skia.Rect.MakeXYWH(ex - w, ey - h, w * 2, h * 2), relleno("#ffffff"))
    cv.drawOval(skia.Rect.MakeXYWH(ex - w, ey - h, w * 2, h * 2), trazo(oscurece(tono, 0.45), 3.5))
    if h > 8:
        ix = ex + pose.mira * 6
        ir = (13 if grande else 17)
        cv.save()
        cv.clipRect(skia.Rect.MakeXYWH(ex - w, ey - h, w * 2, h * 2), True)
        sh = skia.GradientShader.MakeRadial((ix, ey + 4), ir, [color(aclara(r.ojos_color, 0.25)), color(oscurece(r.ojos_color, 0.3))])
        cv.drawCircle(ix, ey + 4, ir, skia.Paint(Shader=sh, AntiAlias=True))
        cv.drawCircle(ix, ey + 4, ir * 0.5, relleno("#1a1210"))
        cv.drawCircle(ix - ir * 0.35, ey - ir * 0.2, ir * 0.32, relleno("#ffffff"))
        cv.drawCircle(ix + ir * 0.35, ey + ir * 0.45, ir * 0.15, relleno("#ffffff", 0.8))
        cv.restore()
        # pestañas/párpado superior
        p = skia.Path()
        p.addArc(skia.Rect.MakeXYWH(ex - w, ey - h, w * 2, h * 2), 200, 140)
        cv.drawPath(p, trazo("#3b2316", 5))


def _cara(cv, r: Rasgos, pose: Pose, t: float):
    cy = CABEZA_Y + 22
    ox = pose.mira * 16
    cara = pose.cara
    sep = 46
    tono = r.tono
    cerrado = max(pose.parpadeo, 1.0 if cara == "dormido" else 0.0)

    # mejillas
    rub = 0.35 + 0.45 * (pose.marcas.get("rubor", 0) or (1 if cara in ("muy_feliz", "guiño", "feliz") else 0))
    for lado in (-1, 1):
        cx = ox + lado * 70
        sh = skia.GradientShader.MakeRadial((cx, cy + 40), 30, [color("#ff7b8a", rub), color("#ff7b8a", 0)])
        cv.drawCircle(cx, cy + 40, 30, skia.Paint(Shader=sh, AntiAlias=True))

    for lado in (-1, 1):
        _ojo(cv, ox + lado * sep, cy, r, pose, cerrado, cara, lado)

    # cejas
    inclin = {"triste": 0.4, "asustado": 0.35, "enfadado": -0.5, "serio": -0.15, "agotado": 0.3,
              "pensativo": -0.25, "sorpresa": 0.05}.get(cara, 0.0)
    alto = 52 if cara in ("sorpresa", "asustado") else 44
    for lado in (-1, 1):
        ex = ox + lado * sep
        d = inclin * 18
        p = skia.Path()
        p.moveTo(ex - lado * 20, cy - alto - d)
        p.quadTo(ex, cy - alto - 8 - d * 0.2, ex + lado * 22, cy - alto + d)
        cv.drawPath(p, trazo(oscurece(r.pelo_color, 0.1) if r.pelo != "calvo" else "#7a6a5a", 9))

    # nariz
    cv.drawOval(skia.Rect.MakeXYWH(ox + pose.mira * 4 - 9, cy + 24, 18, 13), relleno(oscurece(tono, 0.14)))

    if r.gafas:
        for lado in (-1, 1):
            cv.drawCircle(ox + lado * sep, cy, 38, trazo("#2b2b3a", 6))
            cv.drawCircle(ox + lado * sep, cy, 38, relleno("#bde0ff", 0.12))
        p = skia.Path()
        p.moveTo(ox - sep + 38, cy - 4)
        p.quadTo(ox, cy - 14, ox + sep - 38, cy - 4)
        cv.drawPath(p, trazo("#2b2b3a", 6))

    my = cy + 62
    if r.bigote:
        p = skia.Path()
        p.moveTo(ox, my - 14)
        p.cubicTo(ox + 24, my - 28, ox + 54, my - 16, ox + 52, my)
        p.cubicTo(ox + 34, my - 6, ox + 14, my - 4, ox, my - 2)
        p.cubicTo(ox - 14, my - 4, ox - 34, my - 6, ox - 52, my)
        p.cubicTo(ox - 54, my - 16, ox - 24, my - 28, ox, my - 14)
        vol(cv, p, r.pelo_color if r.pelo_color != "#ffffff" else "#ced4da", 3)
        my += 10

    boca_c = "#7a2230"
    abre = pose.habla
    p = skia.Path()
    if cara == "sorpresa":
        cv.drawOval(skia.Rect.MakeXYWH(ox - 15, my - 8, 30, 36), relleno(boca_c))
    elif cara == "muy_feliz" or (cara in ("feliz", "guiño") and abre > 0.1):
        h = 28 + 14 * abre
        p.moveTo(ox - 36, my - 6)
        p.quadTo(ox, my - 2, ox + 36, my - 6)
        p.quadTo(ox + 30, my + h, ox, my + h)
        p.quadTo(ox - 30, my + h, ox - 36, my - 6)
        p.close()
        cv.drawPath(p, relleno(boca_c))
        cv.save()
        cv.clipPath(p, True)
        cv.drawRect(skia.Rect.MakeXYWH(ox - 36, my - 8, 72, 12), relleno("#ffffff"))
        cv.drawOval(skia.Rect.MakeXYWH(ox - 16, my + h * 0.5, 32, h * 0.7), relleno("#ff8597"))
        cv.restore()
    elif abre > 0.1:
        h = 10 + 24 * abre
        cv.drawOval(skia.Rect.MakeXYWH(ox - 16, my - h / 2 + 6, 32, h), relleno(boca_c))
    else:
        linea = trazo("#7a2230", 7)
        if cara in ("feliz", "guiño", "neutral"):
            ancho = 26 if cara != "neutral" else 16
            p.moveTo(ox - ancho, my)
            p.quadTo(ox, my + (20 if cara != "neutral" else 8), ox + ancho, my)
        elif cara in ("triste", "agotado"):
            p.moveTo(ox - 22, my + 12)
            p.quadTo(ox, my - 8, ox + 22, my + 12)
        elif cara == "asustado":
            p.moveTo(ox - 26, my + 4)
            for i in range(1, 7):
                p.lineTo(ox - 26 + i * 8.6, my + (-5 if i % 2 else 6))
        elif cara == "enfadado":
            p.moveTo(ox - 22, my + 8)
            p.quadTo(ox, my - 4, ox + 22, my + 8)
        elif cara == "pensativo":
            p.moveTo(ox - 10, my + 5)
            p.lineTo(ox + 20, my)
        elif cara == "dormido":
            cv.drawCircle(ox, my + 4, 8, linea)
        else:
            p.moveTo(ox - 18, my + 4)
            p.lineTo(ox + 18, my + 4)
        cv.drawPath(p, linea)


def _marcas(cv, pose: Pose, t: float):
    cy, R = CABEZA_Y, CABEZA_R
    m = pose.marcas
    if m.get("!"):
        k = ease_out_back(min(1, m["!"] * 4))
        cv.save()
        cv.translate(pose.mira * 40, cy - R - 105)
        cv.scale(k, k)
        e = skia.Path()
        for i in range(20):
            a = i * math.pi / 10
            rr = 66 if i % 2 == 0 else 46
            (e.moveTo if i == 0 else e.lineTo)(math.cos(a) * rr, math.sin(a) * rr)
        e.close()
        vol(cv, e, "#ffd43b", 5)
        texto_centrado(cv, "!", 0, 2, fuente("Rotulo.ttf", 82), relleno("#c92a2a"))
        cv.restore()
    if m.get("?"):
        k = ease_out_back(min(1, m["?"] * 4))
        cv.save()
        cv.translate(pose.mira * 120, cy - R - 70 + math.sin(t * 4) * 6)
        cv.scale(k, k)
        b = skia.Path()
        b.addCircle(0, 0, 56)
        vol(cv, b, "#ffffff", 5, luz=0, sombra=0.06)
        cv.drawCircle(-pose.mira * 46, 58, 13, relleno("#ffffff"))
        texto_centrado(cv, "?", 0, 2, fuente("Rotulo.ttf", 78), relleno("#7048e8"))
        cv.restore()
    if m.get("sudor"):
        for i, (sx, sy) in enumerate(((R * 0.88, cy - R * 0.45), (-R * 0.95, cy - R * 0.15))):
            ph = (t * 1.3 + i * 0.5) % 1
            y = sy + ph * 70
            g = skia.Path()
            g.moveTo(sx, y - 26)
            g.cubicTo(sx + 19, y, sx + 14, y + 16, sx, y + 16)
            g.cubicTo(sx - 14, y + 16, sx - 19, y, sx, y - 26)
            vol(cv, g, "#74c0fc", 3, alpha=(1 - ph) * min(1, m["sudor"] * 5))
    if m.get("lagrimas"):
        for lado in (-1, 1):
            ex = pose.mira * 16 + lado * 46
            p = skia.Path()
            p.moveTo(ex, CABEZA_Y + 50)
            p.lineTo(ex + lado * 6, CABEZA_Y + 50 + 90 * min(1, m["lagrimas"] * 3))
            cv.drawPath(p, trazo("#74c0fc", 16, 0.85))
            for k in range(3):
                ph = (t * 1.8 + k / 3) % 1
                cv.drawCircle(ex + lado * ph * 80, CABEZA_Y + 60 + ph * 160 + ph * ph * 60, 12 * (1 - ph * 0.4),
                              relleno("#4dabf7", 0.9 * (1 - ph)))
    if m.get("zzz"):
        f = fuente("Rotulo.ttf", 52)
        for k in range(3):
            ph = (t * 0.6 + k / 3) % 1
            cv.drawString("z", pose.mira * (80 + ph * 90), cy - R - ph * 150, f, relleno("#5c7cfa", 1 - ph))


# ------------------------------------------------------------------ personaje completo
def dibujar(cv: skia.Canvas, r: Rasgos, x: float, y: float, escala: float, pose: Pose, t: float):
    s = escala * r.altura
    piel = r.tono
    cv.save()
    cv.translate(x + pose.dx, y + pose.dy)
    k = max(0.35, 1 + pose.dy / 400)
    cv.save()
    cv.scale(1, 0.18)
    cv.drawCircle(0, -pose.dy / 0.18, 110 * s * k, skia.Paint(Shader=skia.GradientShader.MakeRadial(
        (0, -pose.dy / 0.18), 110 * s * k, [color("#000000", 0.3 * pose.alpha), color("#000000", 0)]), AntiAlias=True))
    cv.restore()
    sq = pose.aplasta
    cv.scale(s * (1 + sq * 0.5), s * (1 - sq))
    cv.rotate(pose.giro)
    if pose.alpha < 1:
        cv.saveLayerAlpha(None, int(255 * pose.alpha))
    cv.translate(0, -abs(pose.respira) * 5)

    # piernas
    for lado in (-1, 1):
        if pose.paso is None:
            fx, fy = lado * 34, 0
        else:
            ph = pose.paso + (0 if lado < 0 else math.pi)
            fx = lado * 26 + math.sin(ph) * 44 * pose.mira
            fy = -max(0, math.cos(ph)) * 30
        _miembro(cv, [(lado * 30, CADERA), (fx, fy - 22)], PANTALON, 36)
        z = skia.Path()
        z.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(fx - 32 + pose.mira * 12, fy - 40, 66, 38), 19, 19))
        vol(cv, z, "#f8f9fa", 5)
        cv.drawRect(skia.Rect.MakeXYWH(fx - 30 + pose.mira * 12, fy - 12, 62, 9), relleno(r.color, 0.9))

    # pelo de detrás de la cabeza
    _pelo(cv, r, pose.mira, detras=True)

    (a1, b1), (a2, b2) = pose.brazos
    trasero = -pose.mira
    ang = {trasero: (a1, b1), -trasero: (a2, b2)}
    _brazo(cv, trasero, *ang[trasero], oscurece(r.color, 0.1), piel)

    # torso (sudadera redondeada)
    tor = skia.Path()
    tor.moveTo(-64, HOMBRO + 6)
    tor.cubicTo(-30, HOMBRO - 16, 30, HOMBRO - 16, 64, HOMBRO + 6)
    tor.cubicTo(88, HOMBRO + 50, 92, CADERA - 20, 80, CADERA + 18)
    tor.quadTo(0, CADERA + 36, -80, CADERA + 18)
    tor.cubicTo(-92, CADERA - 20, -88, HOMBRO + 50, -64, HOMBRO + 6)
    tor.close()
    vol(cv, tor, r.color, 5)
    cv.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-44, CADERA - 40, 88, 30), 12, 12),
                 relleno(oscurece(r.color, 0.12)))
    cv.drawCircle(-18, HOMBRO + 46, 5, relleno(aclara(r.color, 0.5)))
    cv.drawCircle(18, HOMBRO + 46, 5, relleno(aclara(r.color, 0.5)))

    # cuello y orejas, cabeza
    cv.drawRect(skia.Rect.MakeXYWH(-22, HOMBRO - 20, 44, 30), relleno(oscurece(piel, 0.12)))
    for lado in (-1, 1):
        o = skia.Path()
        o.addOval(skia.Rect.MakeXYWH(lado * CABEZA_R * 0.96 - 22, CABEZA_Y - 8, 44, 54))
        vol(cv, o, piel, 4)
    cab = skia.Path()
    cab.addOval(skia.Rect.MakeXYWH(-CABEZA_R, CABEZA_Y - CABEZA_R * 0.98, CABEZA_R * 2, CABEZA_R * 1.96))
    vol(cv, cab, piel, 5, luz=0.12, sombra=0.08)
    _brillo(cv, -CABEZA_R * 0.6, CABEZA_Y - CABEZA_R * 0.72, CABEZA_R * 0.5, CABEZA_R * 0.28, 0.22)
    _pelo(cv, r, pose.mira, detras=False)
    _cara(cv, r, pose, t)

    _brazo(cv, -trasero, *ang[-trasero], r.color, piel)
    _marcas(cv, pose, t)

    if pose.alpha < 1:
        cv.restore()
    cv.restore()
