"""Objetos (atrezo) dibujados por código. Todos se dibujan centrados en (0, 0).

Cada función recibe (cv, t, o) donde o es el dict del objeto en la historia (puede llevar
'texto', 'nota', 'color'...) más el estado calculado ('roto', 'dibujo', 'brillo'...).
"""
from __future__ import annotations

import math

import skia

from .util import (ASSETS, TINTA, aclara, ease_out_back, circulo, color, forma, fuente, imagen, oscurece, poligono, relleno,
                   rrect, texto_centrado, trazo)


def _compas(cv, t, o):
    roto = o.get("_roto", 0.0)          # 0 entero, 1 partido del todo
    abre = 0.42
    largo = 230

    def pata(sign, punta):
        cv.save()
        cv.rotate(math.degrees(sign * abre))
        pa = rrect(-11, 0, 22, largo, 10)
        forma(cv, pa, "#adb5bd", 6)
        if punta == "aguja":
            cv.drawPath(poligono([(-5, largo - 4), (5, largo - 4), (0, largo + 34)]), relleno("#495057"))
        else:
            forma(cv, poligono([(-11, largo - 6), (11, largo - 6), (0, largo + 34)]), "#343a40", 5)
        cv.restore()

    # mitad izquierda (con el mango)
    cv.save()
    if roto:
        cv.translate(-90 * roto, 40 * roto * roto)
        cv.rotate(-35 * roto)
    pata(1, "aguja")
    forma(cv, rrect(-14, -70, 28, 64, 12), "#495057", 6)
    forma(cv, circulo(0, 0, 26), "#ced4da", 6)
    cv.restore()
    # mitad derecha
    cv.save()
    if roto:
        cv.translate(110 * roto, 60 * roto * roto)
        cv.rotate(50 * roto)
    pata(-1, "mina")
    cv.restore()
    if 0 < roto < 0.6:   # chispas al romperse
        k = roto / 0.6
        for i in range(10):
            ang = i * math.pi / 5 + 0.3
            r0, r1 = 30 + 120 * k, 60 + 170 * k
            p = skia.Path()
            p.moveTo(math.cos(ang) * r0, math.sin(ang) * r0)
            p.lineTo(math.cos(ang) * r1, math.sin(ang) * r1)
            cv.drawPath(p, trazo("#ffd43b", 12 * (1 - k) + 2))


def _escuadra(cv, t, o):
    c = o.get("color", "#40c057")
    ext = poligono([(-170, 120), (170, 120), (-170, -220)])
    cv.drawPath(ext, relleno(c, 0.75))
    cv.drawPath(ext, trazo(oscurece(c, 0.35), 7))
    hueco = poligono([(-120, 75), (40, 75), (-120, -90)])
    cv.drawPath(hueco, relleno("#ffffff", 0.35))
    cv.drawPath(hueco, trazo(oscurece(c, 0.35), 5))
    for i in range(12):
        x = -160 + i * 28
        p = skia.Path()
        p.moveTo(x, 120)
        p.lineTo(x, 120 - (20 if i % 2 else 12))
        cv.drawPath(p, trazo(oscurece(c, 0.45), 3))


def _cartabon(cv, t, o):
    o = dict(o)
    o.setdefault("color", "#2f9e44")
    cv.save()
    cv.scale(1.1, 0.75)
    _escuadra(cv, t, o)
    cv.restore()


def _regla(cv, t, o):
    forma(cv, rrect(-260, -32, 520, 64, 8), "#ffe066", 6)
    for i in range(27):
        x = -245 + i * 19
        p = skia.Path()
        p.moveTo(x, -32)
        p.lineTo(x, -32 + (26 if i % 5 == 0 else 14))
        cv.drawPath(p, trazo(TINTA, 3))


def _lamina(cv, t, o):
    """Lámina A4 con una construcción geométrica; '_dibujo' (0..1) la va trazando."""
    prog = o.get("_dibujo", 1.0)
    mal = o.get("estilo") == "mal"
    cv.save()
    cv.rotate(o.get("inclinada", -4))
    forma(cv, rrect(-150, -210, 300, 420, 6), "#fffdf7", 6)
    cv.drawRect(skia.Rect.MakeLTRB(-128, -188, 128, 188), trazo("#495057", 3, redondo=False))
    cv.drawRect(skia.Rect.MakeLTRB(28, 150, 128, 188), trazo("#495057", 3, redondo=False))
    lineas = trazo("#1c7ed6" if not mal else "#495057", 5)
    # circunferencia + tangentes + hexágono, apareciendo en orden
    def tramo(i, n=3):
        return max(0.0, min(1.0, prog * n - i))
    a = tramo(0)
    if a:
        cv.drawArc(skia.Rect.MakeXYWH(-80, -130, 160, 160), -90, 360 * a, False, lineas)
    b = tramo(1)
    if b:
        pts = [(math.cos(k * math.pi / 3) * 95, -50 + math.sin(k * math.pi / 3) * 95) for k in range(7)]
        p = skia.Path()
        p.moveTo(*pts[0])
        tot = 6 * b
        for k in range(1, 7):
            if k <= tot:
                p.lineTo(*pts[k])
            else:
                f = tot - (k - 1)
                if f > 0:
                    p.lineTo(pts[k - 1][0] + (pts[k][0] - pts[k - 1][0]) * f,
                             pts[k - 1][1] + (pts[k][1] - pts[k - 1][1]) * f)
                break
        cv.drawPath(p, trazo("#e03131" if not mal else "#495057", 4))
    c = tramo(2)
    if c:
        p = skia.Path()
        p.moveTo(-120, 120)
        p.lineTo(-120 + 240 * c, 120 - 160 * c)
        cv.drawPath(p, trazo("#2b8a3e" if not mal else "#495057", 4))
    if mal:   # borrones y tachones
        for i in range(4):
            cv.drawOval(skia.Rect.MakeXYWH(-110 + i * 55, -10 + (i % 2) * 70, 70, 34), relleno("#868e96", 0.25))
        p = skia.Path()
        p.moveTo(-100, 60)
        for i in range(10):
            p.lineTo(-100 + i * 22, 60 + (18 if i % 2 else -18))
        cv.drawPath(p, trazo("#343a40", 4))
    cv.restore()


def _portatil(cv, t, o):
    brillo = o.get("_brillo", 0.0)
    if brillo:
        for i in range(14):   # rayos de 'herramienta mágica'
            ang = i * math.pi / 7 + t * 0.6
            p = skia.Path()
            p.moveTo(0, -40)
            p.lineTo(math.cos(ang - 0.09) * 620, -40 + math.sin(ang - 0.09) * 620)
            p.lineTo(math.cos(ang + 0.09) * 620, -40 + math.sin(ang + 0.09) * 620)
            p.close()
            cv.drawPath(p, relleno("#fff3bf", 0.55 * brillo))
        cv.drawCircle(0, -40, 330, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
            (0, -40), 330, [color("#ffe066", 0.8 * brillo), color("#ffe066", 0)])))
    # pantalla
    forma(cv, rrect(-260, -250, 520, 330, 26), "#343a40", 7)
    pant = skia.Rect.MakeLTRB(-236, -226, 236, 56)
    img = imagen(str(_web(o)))
    if img is not None:
        cv.save()
        cv.clipRRect(skia.RRect.MakeRectXY(pant, 10, 10), True)
        sw, sh = img.width(), img.height()
        k = max(pant.width() / sw, pant.height() / sh)
        dst = skia.Rect.MakeXYWH(pant.centerX() - sw * k / 2, pant.top(), sw * k, sh * k)
        cv.drawImageRect(img, dst, skia.SamplingOptions(skia.FilterMode.kLinear), None)
        cv.restore()
    else:
        cv.drawRRect(skia.RRect.MakeRectXY(pant, 10, 10), relleno("#e7f5ff"))
        texto_centrado(cv, "danidemiguel.com", 0, -85, fuente("Rotulo.ttf", 42), relleno("#1c7ed6"))
    # base
    base = skia.Path()
    base.moveTo(-300, 80)
    base.lineTo(300, 80)
    base.lineTo(330, 118)
    base.quadTo(330, 128, 318, 128)
    base.lineTo(-318, 128)
    base.quadTo(-330, 128, -330, 118)
    base.close()
    forma(cv, base, "#ced4da", 7)
    cv.drawRect(skia.Rect.MakeLTRB(-50, 82, 50, 92), relleno("#adb5bd"))


def _web(o):
    if o.get("imagen"):
        return ASSETS / "web" / o["imagen"]
    web = sorted((ASSETS / "web").glob("*.*"))
    return web[0] if web else ASSETS / "web" / "nada.jpg"


def _movil(cv, t, o):
    forma(cv, rrect(-90, -170, 180, 340, 28), "#212529", 7)
    pant = skia.Rect.MakeLTRB(-76, -150, 76, 150)
    img = imagen(str(_web(o)))
    cv.save()
    cv.clipRRect(skia.RRect.MakeRectXY(pant, 16, 16), True)
    if img is not None:
        k = pant.height() / img.height()
        cv.drawImageRect(img, skia.Rect.MakeXYWH(-img.width() * k / 2, -150, img.width() * k, img.height() * k),
                         skia.SamplingOptions(skia.FilterMode.kLinear), None)
    else:
        cv.drawRect(pant, relleno("#e7f5ff"))
    cv.restore()


def _pizarra(cv, t, o):
    forma(cv, rrect(-330, -190, 660, 380, 10), "#8d5524", 7)
    cv.drawRect(skia.Rect.MakeLTRB(-305, -166, 305, 166), relleno("#2f6b4f"))
    cv.drawRect(skia.Rect.MakeLTRB(-305, -166, 305, 166), relleno("#ffffff", 0.04))
    txt = o.get("texto", "")
    if txt:
        f = fuente("Rotulo.ttf", 64 if len(txt) < 14 else 50)
        lineas = _partir(txt, f, 560)
        y0 = -(len(lineas) - 1) * 36
        for i, ln in enumerate(lineas):
            texto_centrado(cv, ln, 0, y0 + i * 72, f, relleno("#f8f9fa", 0.92))
    else:
        cv.drawCircle(-120, -10, 80, trazo("#f8f9fa", 5, 0.8))
        p = skia.Path()
        p.moveTo(-240, 90)
        p.lineTo(40, -100)
        cv.drawPath(p, trazo("#f8f9fa", 5, 0.8))
    forma(cv, rrect(-200, 166, 400, 18, 4), "#a0522d", 5)


def _partir(txt, f, ancho):
    out, cur = [], ""
    for w in txt.split():
        prueba = (cur + " " + w).strip()
        if f.measureText(prueba) > ancho and cur:
            out.append(cur)
            cur = w
        else:
            cur = prueba
    if cur:
        out.append(cur)
    return out


def _pupitre(cv, t, o):
    forma(cv, rrect(-210, -20, 420, 36, 8), "#d9a066", 7)
    for x in (-180, 165):
        forma(cv, rrect(x, 14, 16, 200, 5), "#868e96", 5)
    forma(cv, rrect(-150, 14, 300, 50, 6), "#adb5bd", 5)


def _examen(cv, t, o):
    nota = str(o.get("nota", "10"))
    cv.save()
    cv.rotate(o.get("inclinada", 6))
    forma(cv, rrect(-140, -190, 280, 380, 6), "#ffffff", 6)
    texto_centrado(cv, o.get("texto", "EXAMEN"), 0, -150, fuente("Rotulo.ttf", 36), relleno(TINTA))
    for i in range(6):
        cv.drawRect(skia.Rect.MakeXYWH(-110, -100 + i * 40, 160 if i % 2 else 210, 8), relleno("#ced4da"))
    buena = nota not in ("0", "1", "2", "3", "4")
    c = "#e03131"
    texto_centrado(cv, nota, 60, 120, fuente("Rotulo.ttf", 120), relleno(c))
    cv.drawOval(skia.Rect.MakeXYWH(-25, 50, 170, 140), trazo(c, 7))
    cv.restore()


def _reloj(cv, t, o):
    v = o.get("velocidad", 1.0)
    forma(cv, circulo(0, 0, 120), "#ffffff", 9)
    for i in range(12):
        a = i * math.pi / 6
        p = skia.Path()
        p.moveTo(math.cos(a) * 92, math.sin(a) * 92)
        p.lineTo(math.cos(a) * 108, math.sin(a) * 108)
        cv.drawPath(p, trazo(TINTA, 6))
    for largo, vel, ancho in ((80, 1.0, 8), (55, 1 / 12, 11)):
        a = t * vel * v * 2 * math.pi - math.pi / 2
        p = skia.Path()
        p.moveTo(0, 0)
        p.lineTo(math.cos(a) * largo, math.sin(a) * largo)
        cv.drawPath(p, trazo("#e03131" if vel == 1.0 else TINTA, ancho))
    cv.drawCircle(0, 0, 10, relleno(TINTA))


def _libros(cv, t, o):
    cols = ["#e8590c", "#1971c2", "#2f9e44", "#ae3ec9", "#f08c00"]
    for i in range(o.get("cantidad", 4)):
        w = 260 - (i % 2) * 30
        forma(cv, rrect(-w / 2 + (i % 2) * 12, -i * 46, w, 42, 6), cols[i % len(cols)], 6)
        cv.drawRect(skia.Rect.MakeXYWH(-w / 2 + 20 + (i % 2) * 12, -i * 46 + 8, w - 40, 6), relleno("#ffffff", 0.6))


def _bombilla(cv, t, o):
    for i in range(8):
        a = i * math.pi / 4 + 0.2
        p = skia.Path()
        p.moveTo(math.cos(a) * 120, -40 + math.sin(a) * 120)
        p.lineTo(math.cos(a) * (165 + 10 * math.sin(t * 8)), -40 + math.sin(a) * (165 + 10 * math.sin(t * 8)))
        cv.drawPath(p, trazo("#fab005", 12))
    forma(cv, circulo(0, -40, 95), "#ffe066", 8)
    forma(cv, rrect(-42, 48, 84, 60, 10), "#adb5bd", 7)


def _cartel(cv, t, o):
    txt = o.get("texto", "¡OJO!")
    f = fuente("Rotulo.ttf", o.get("tam", 72))
    lineas = _partir(txt, f, 700)
    w = max(f.measureText(l) for l in lineas) + 90
    h = len(lineas) * f.getSize() * 1.12 + 60
    c = o.get("color", "#ffd43b")
    forma(cv, rrect(-w / 2, -h / 2, w, h, 28), c, 8)
    y0 = -(len(lineas) - 1) * f.getSize() * 0.56
    for i, l in enumerate(lineas):
        texto_centrado(cv, l, 0, y0 + i * f.getSize() * 1.12, f, relleno(o.get("color_texto", TINTA)))


def _calendario(cv, t, o):
    forma(cv, rrect(-130, -150, 260, 300, 18), "#ffffff", 7)
    forma(cv, rrect(-130, -150, 260, 80, 18), "#e03131", 7)
    texto_centrado(cv, o.get("mes", "MAYO"), 0, -110, fuente("Rotulo.ttf", 44), relleno("#ffffff"))
    txt = str(o.get("texto", "15"))
    texto_centrado(cv, txt, 0, 35, fuente("Rotulo.ttf", 130 if len(txt) <= 2 else 230 / len(txt) * 1.6), relleno(TINTA))


def _lapiz(cv, t, o):
    cv.rotate(o.get("inclinada", 30))
    forma(cv, rrect(-18, -170, 36, 260, 6), "#fab005", 6)
    forma(cv, poligono([(-18, 90), (18, 90), (0, 150)]), "#f8d9a0", 6)
    cv.drawPath(poligono([(-6, 130), (6, 130), (0, 150)]), relleno(TINTA))
    forma(cv, rrect(-18, -200, 36, 34, 6), "#ff8787", 6)


def _goma(cv, t, o):
    forma(cv, rrect(-80, -40, 160, 80, 14), "#ffffff", 6)
    forma(cv, rrect(-80, -40, 70, 80, 14), "#4dabf7", 6)


def _estrella(cv, t, o):
    c = o.get("color", "#ffd43b")
    p = skia.Path()
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = 90 if i % 2 == 0 else 40
        (p.moveTo if i == 0 else p.lineTo)(math.cos(a) * r, math.sin(a) * r)
    p.close()
    forma(cv, p, c, 7)


def _rayo(cv, t, o):
    forma(cv, poligono([(20, -160), (-70, 20), (-5, 20), (-30, 160), (70, -30), (5, -30)]), "#ffd43b", 7)


def _nube_texto(cv, t, o):
    """Bocadillo de diálogo con texto (para que un personaje 'diga' algo)."""
    txt = o.get("texto", "...")
    f = fuente("Rotulo.ttf", o.get("tam", 54))
    lineas = _partir(txt, f, 560)
    w = max(f.measureText(l) for l in lineas) + 70
    h = len(lineas) * f.getSize() * 1.15 + 46
    cola = -1 if o.get("cola", "izquierda") == "izquierda" else 1
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h), 36, 36))
    p2 = poligono([(cola * w * 0.15, h / 2 - 6), (cola * w * 0.32, h / 2 - 6), (cola * w * 0.08, h / 2 + 50)])
    p = skia.Op(p, p2, skia.PathOp.kUnion_PathOp) or p
    forma(cv, p, "#ffffff", 7)
    y0 = -(len(lineas) - 1) * f.getSize() * 0.575
    for i, l in enumerate(lineas):
        texto_centrado(cv, l, 0, y0 + i * f.getSize() * 1.15, f, relleno(TINTA))


OBJETOS = {
    "compas": _compas, "escuadra": _escuadra, "cartabon": _cartabon, "regla": _regla, "lamina": _lamina,
    "portatil": _portatil, "movil": _movil, "pizarra": _pizarra, "pupitre": _pupitre, "examen": _examen,
    "reloj": _reloj, "libros": _libros, "bombilla": _bombilla, "cartel": _cartel, "calendario": _calendario,
    "lapiz": _lapiz, "goma": _goma, "estrella": _estrella, "rayo": _rayo, "bocadillo": _nube_texto,
}


def dibujar(cv, tipo: str, t: float, o: dict):
    fn = OBJETOS.get(tipo)
    if fn:
        fn(cv, t, o)


# ------------------------------------------------------------------ gráficos animados (para datos)
def _numero(v: float, dec: int = 0, miles: bool = True) -> str:
    txt = f"{v:,.{dec}f}" if miles else f"{v:.{dec}f}"
    return txt.replace(",", "X").replace(".", ",").replace("X", ".")


def _texto_grande(cv, txt, y, tam, relleno_c="#ffd43b", borde_c="#1a1a1a"):
    f = fuente("Rotulo.ttf", tam)
    a = f.measureText(txt)
    if a > 1000:
        f = fuente("Rotulo.ttf", tam * 1000 / a)
        a = f.measureText(txt)
    m = f.getMetrics()
    yb = y - (m.fAscent + m.fDescent) / 2
    cv.drawString(txt, -a / 2 + 6, yb + 10, f, skia.Paint(Color=color("#000000", 0.35), AntiAlias=True,
                                                         MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 8)))
    cv.drawString(txt, -a / 2, yb, f, skia.Paint(Color=color(borde_c), AntiAlias=True, Style=skia.Paint.kStroke_Style,
                                                StrokeWidth=tam * 0.16, StrokeJoin=skia.Paint.kRound_Join))
    sh = skia.GradientShader.MakeLinear([(0, yb + m.fAscent), (0, yb)], [color(aclara(relleno_c, 0.35)), color(relleno_c)])
    cv.drawString(txt, -a / 2, yb, f, skia.Paint(Shader=sh, AntiAlias=True))


def _contador(cv, t, o):
    k = o.get("_cuenta", 1.0)
    v = o.get("desde", 0) + (o.get("hasta", 100) - o.get("desde", 0)) * k
    txt = f"{o.get('prefijo', '')}{_numero(v, o.get('decimales', 0), o.get('miles', True))}{o.get('sufijo', '')}"
    _texto_grande(cv, txt, 0, o.get("tam", 190), o.get("color", "#ffd43b"))
    if o.get("etiqueta"):
        f = fuente("Rotulo.ttf", 52)
        a = f.measureText(o["etiqueta"]) + 60
        forma(cv, rrect(-a / 2, 110, a, 84, 42), "#1a1a2e", 0)
        texto_centrado(cv, o["etiqueta"], 0, 152, f, relleno("#ffffff"))


def _texto(cv, t, o):
    lineas = str(o.get("texto", "")).split("\n")
    tam = o.get("tam", 130)
    for i, ln in enumerate(lineas):
        _texto_grande(cv, ln, (i - (len(lineas) - 1) / 2) * tam * 1.1, tam, o.get("color", "#ffffff"))


def _barras(cv, t, o):
    datos = o.get("datos", [{"etiqueta": "A", "valor": 1}, {"etiqueta": "B", "valor": 3}])
    k = o.get("_cuenta", 1.0)
    alto = o.get("alto", 620)
    n = len(datos)
    ancho = min(220, 820 / n)
    hueco = (860 - ancho * n) / max(1, n - 1) if n > 1 else 0
    mx = max(d.get("valor", 1) for d in datos) or 1
    cols = ["#20c997", "#ff6b6b", "#4dabf7", "#fcc419", "#845ef7"]
    x0 = -430
    cv.drawRect(skia.Rect.MakeXYWH(-460, alto / 2, 920, 6), relleno("#ffffff", 0.6))
    for i, d in enumerate(datos):
        kk = max(0.0, min(1.0, k * n - i * 0.6)) if n > 1 else k
        h = max(8, alto * d.get("valor", 0) / mx * kk)
        x = x0 + i * (ancho + hueco)
        forma(cv, rrect(x, alto / 2 - h, ancho, h, 22), d.get("color", cols[i % len(cols)]), 6)
        cv.drawRect(skia.Rect.MakeXYWH(x + 18, alto / 2 - h + 18, 16, max(0, h - 36)), relleno("#ffffff", 0.3))
        f = fuente("Rotulo.ttf", 64)
        val = _numero(d.get("valor", 0) * kk, d.get("decimales", 0)) + d.get("sufijo", "")
        texto_centrado(cv, val, x + ancho / 2, alto / 2 - h - 48, f, relleno("#ffffff"))
        texto_centrado(cv, d.get("etiqueta", ""), x + ancho / 2, alto / 2 + 52, fuente("Rotulo.ttf", 44), relleno("#ffffff"))


def _cuadricula(cv, t, o):
    filas, cols = o.get("filas", 4), o.get("columnas", 5)
    w, h = o.get("ancho", 900), o.get("alto", 900)
    esc = o.get("escala_item", min(w / cols, h / filas) / 420)
    k = o.get("_cuenta", 1.0)
    tipo = o.get("objeto", "estrella")
    total = filas * cols
    dentro = dict(o.get("item", {}))
    for i in range(total):
        aparece = max(0.0, min(1.0, k * total * 1.3 - i * 1.3)) if k < 1 else 1.0
        if aparece <= 0:
            continue
        r, c = divmod(i, cols)
        x = -w / 2 + (c + 0.5) * w / cols
        y = -h / 2 + (r + 0.5) * h / filas
        cv.save()
        cv.translate(x, y)
        s = esc * ease_out_back(aparece)
        cv.scale(s, s)
        if tipo == "persona":
            _persona_icono(cv, i)
        else:
            dibujar(cv, tipo, t, dentro)
        cv.restore()


def _persona_icono(cv, i):
    c = ["#ff6b6b", "#4dabf7", "#51cf66", "#fcc419", "#845ef7", "#ff922b"][i % 6]
    piel = ["#ffdcc2", "#f1b98c", "#c98b5b", "#8d5a3b"][i % 4]
    forma(cv, rrect(-110, 20, 220, 200, 90), c, 8)
    forma(cv, circulo(0, -80, 95), piel, 8)


def _flecha(cv, t, o):
    largo = o.get("largo", 320)
    c = o.get("color", "#ff6b6b")
    p = skia.Path()
    p.moveTo(-largo / 2, 30)
    p.quadTo(0, -70, largo / 2 - 40, 0)
    cv.drawPath(p, trazo(oscurece(c, 0.4), 40))
    cv.drawPath(p, trazo(c, 26))
    forma(cv, poligono([(largo / 2 + 30, 10), (largo / 2 - 70, -50), (largo / 2 - 40, 60)]), c, 7)


def _check(cv, t, o):
    forma(cv, circulo(0, 0, 110), "#40c057", 8)
    p = skia.Path()
    p.moveTo(-52, 4)
    p.lineTo(-14, 44)
    p.lineTo(58, -40)
    cv.drawPath(p, trazo("#ffffff", 30))


def _cruz(cv, t, o):
    forma(cv, circulo(0, 0, 110), "#fa5252", 8)
    for a, b in (((-45, -45), (45, 45)), ((45, -45), (-45, 45))):
        p = skia.Path()
        p.moveTo(*a)
        p.lineTo(*b)
        cv.drawPath(p, trazo("#ffffff", 30))


def _alcantarilla(cv, t, o):
    forma_ = o.get("forma", "circulo")
    if forma_ == "cuadrado":
        base = rrect(-230, -230, 460, 460, 14)
    else:
        base = circulo(0, 0, 240)
    cv.drawPath(base, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
        (-60, -80), 360, [color("#adb5bd"), color("#495057")])))
    cv.drawPath(base, trazo("#212529", 10))
    cv.save()
    cv.clipPath(base, True)
    for i in range(-6, 7):
        cv.drawRect(skia.Rect.MakeXYWH(-260, i * 40 - 8, 520, 14), relleno("#343a40", 0.55))
        cv.drawRect(skia.Rect.MakeXYWH(i * 40 - 8, -260, 14, 520), relleno("#343a40", 0.25))
    cv.restore()
    if forma_ != "cuadrado":
        cv.drawCircle(0, 0, 200, trazo("#212529", 8, 0.6))
    texto_centrado(cv, o.get("texto", "AGUA"), 0, 0, fuente("Rotulo.ttf", 70), relleno("#dee2e6"))


def _hexagono_path(r, cx=0.0, cy=0.0):
    return poligono([(cx + math.cos(k * math.pi / 3 + math.pi / 6) * r, cy + math.sin(k * math.pi / 3 + math.pi / 6) * r)
                     for k in range(6)])


def _panal(cv, t, o):
    r = 62
    k = o.get("_cuenta", 1.0)
    celdas = [(q, s) for s in range(-3, 4) for q in range(-3, 4) if abs(q + s * 0.5) <= 3.3]
    pos = [((q + (s % 2) * 0.5) * r * math.sqrt(3), s * r * 1.5) for q, s in celdas]
    mx = sum(x for x, _ in pos) / len(pos)
    for i, (q, s) in enumerate(celdas):
        a = max(0.0, min(1.0, k * len(celdas) * 1.2 - i)) if k < 1 else 1
        if a <= 0:
            continue
        cx = (q + (s % 2) * 0.5) * r * math.sqrt(3) - mx
        cy = s * r * 1.5
        cv.save()
        cv.translate(cx, cy)
        cv.scale(ease_out_back(a), ease_out_back(a))
        forma(cv, _hexagono_path(r - 3), "#fcc419", 7)
        cv.drawPath(_hexagono_path(r * 0.55), relleno("#ffe066", 0.7))
        cv.restore()


def _figura(cv, t, o):
    """Figura geométrica; con el evento 'dibujar' se traza poco a poco y luego se rellena."""
    tipo = o.get("forma", "circulo")
    c = o.get("color", "#4dabf7")
    r = 200
    if tipo == "circulo":
        p = circulo(0, 0, r)
    elif tipo == "cuadrado":
        p = rrect(-r * 0.85, -r * 0.85, r * 1.7, r * 1.7, 6)
    elif tipo == "triangulo":
        p = poligono([(math.cos(-math.pi / 2 + k * 2 * math.pi / 3) * r, math.sin(-math.pi / 2 + k * 2 * math.pi / 3) * r + 30)
                      for k in range(3)])
    elif tipo == "hexagono":
        p = _hexagono_path(r)
    elif tipo == "pentagono":
        p = poligono([(math.cos(-math.pi / 2 + k * 2 * math.pi / 5) * r, math.sin(-math.pi / 2 + k * 2 * math.pi / 5) * r)
                      for k in range(5)])
    elif tipo == "reuleaux":
        # triángulo de Reuleaux: anchura constante, como el círculo
        v = [(math.cos(-math.pi / 2 + k * 2 * math.pi / 3) * r * 0.9, math.sin(-math.pi / 2 + k * 2 * math.pi / 3) * r * 0.9 + 25)
             for k in range(3)]
        lado = math.dist(v[0], v[1])
        p = skia.Path()
        p.moveTo(*v[0])
        for k in range(3):
            centro = v[(k + 2) % 3]
            a0 = math.degrees(math.atan2(v[k][1] - centro[1], v[k][0] - centro[0]))
            p.arcTo(skia.Rect.MakeLTRB(centro[0] - lado, centro[1] - lado, centro[0] + lado, centro[1] + lado), a0, 60, False)
        p.close()
    else:
        p = circulo(0, 0, r)
    if o.get("_rot"):
        # centrar la figura en su centro geométrico y girarla
        b = p.getBounds()
        m = skia.Matrix()
        m.setRotate(o["_rot"], b.centerX(), b.centerY() if tipo != "reuleaux" else 25)
        p.transform(m)
    prog = o.get("_dibujo", 1.0)
    if prog >= 1:
        forma(cv, p, c, 10)
    else:
        med = skia.PathMeasure(p, False)
        largo = med.getLength()
        seg = skia.Path()
        med.getSegment(0, largo * min(1, prog / 0.8), seg, True)
        cv.drawPath(seg, trazo("#ffffff", 9))
        if prog > 0.8:
            forma(cv, p, c, 10, alpha=(prog - 0.8) / 0.2)
    if o.get("ancho_cte"):
        # dos rectas paralelas que tocan la figura arriba y abajo: su separación no cambia al girar
        b = p.computeTightBounds()
        for y in (b.top() - 6, b.bottom() + 6):
            q = skia.Path()
            q.moveTo(-r * 1.6, y)
            q.lineTo(r * 1.6, y)
            cv.drawPath(q, trazo("#ff6b6b", 8))
        x = r * 1.35
        q = skia.Path()
        q.moveTo(x, b.top() + 14)
        q.lineTo(x, b.bottom() - 14)
        cv.drawPath(q, trazo("#ffffff", 6))
        for yy, sg in ((b.top() + 4, 1), (b.bottom() - 4, -1)):
            cv.drawPath(poligono([(x, yy), (x - 16, yy + sg * 26), (x + 16, yy + sg * 26)]), relleno("#ffffff"))


def _tangencia(cv, t, o):
    """Dos circunferencias y una recta tangente a ambas, trazándose paso a paso."""
    prog = o.get("_dibujo", 1.0)
    c1, r1, c2, r2 = (-180, 40), 130, (220, 70), 90
    tramo = lambda i: max(0.0, min(1.0, prog * 4 - i))
    for i, (c, r, col) in enumerate(((c1, r1, "#4dabf7"), (c2, r2, "#20c997"))):
        a = tramo(i)
        if a:
            cv.drawArc(skia.Rect.MakeXYWH(c[0] - r, c[1] - r, 2 * r, 2 * r), -90, 360 * a, False, trazo(col, 9))
            cv.drawCircle(*c, 9, relleno("#ffffff", a))
    # tangente exterior superior
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]
    d = math.hypot(dx, dy)
    ang = math.atan2(dy, dx) - math.acos((r1 - r2) / d)
    t1 = (c1[0] + r1 * math.cos(ang), c1[1] + r1 * math.sin(ang))
    t2 = (c2[0] + r2 * math.cos(ang), c2[1] + r2 * math.sin(ang))
    a = tramo(2)
    if a:
        ux, uy = t2[0] - t1[0], t2[1] - t1[1]
        p0 = (t1[0] - ux * 0.4, t1[1] - uy * 0.4)
        p1 = (t1[0] + ux * 1.4, t1[1] + uy * 1.4)
        q = skia.Path()
        q.moveTo(*p0)
        q.lineTo(p0[0] + (p1[0] - p0[0]) * a, p0[1] + (p1[1] - p0[1]) * a)
        cv.drawPath(q, trazo("#ff6b6b", 9))
    if o.get("radios"):
        for c, pt in ((c1, t1), (c2, t2)):
            q = skia.Path()
            q.moveTo(*c)
            q.lineTo(*pt)
            cv.drawPath(q, trazo("#ffffff", 6))
            # marca de ángulo recto
            ux, uy = (c[0] - pt[0]), (c[1] - pt[1])
            n = math.hypot(ux, uy)
            ux, uy = ux / n * 30, uy / n * 30
            vx, vy = (t2[0] - t1[0]), (t2[1] - t1[1])
            m = math.hypot(vx, vy)
            vx, vy = vx / m * 30, vy / m * 30
            sq = skia.Path()
            sq.moveTo(pt[0] + ux, pt[1] + uy)
            sq.lineTo(pt[0] + ux + vx, pt[1] + uy + vy)
            sq.lineTo(pt[0] + vx, pt[1] + vy)
            cv.drawPath(sq, trazo("#ffd43b", 5))
    a = tramo(3)
    if a:
        for pt in (t1, t2):
            cv.drawCircle(*pt, 18 * ease_out_back(a), relleno("#ffd43b"))
            cv.drawCircle(*pt, 18 * ease_out_back(a), trazo("#1a1a1a", 5))


def _trofeo(cv, t, o):
    forma(cv, rrect(-90, 150, 180, 50, 10), "#8d5524", 7)
    forma(cv, rrect(-25, 80, 50, 80, 8), "#fab005", 7)
    copa = skia.Path()
    copa.moveTo(-150, -150)
    copa.lineTo(150, -150)
    copa.cubicTo(150, 20, 60, 90, 0, 90)
    copa.cubicTo(-60, 90, -150, 20, -150, -150)
    copa.close()
    for lado in (-1, 1):
        cv.drawArc(skia.Rect.MakeXYWH(lado * 150 - 60, -130, 120, 130), 0, 360, False, trazo("#e67700", 22))
    forma(cv, copa, "#fcc419", 8)
    texto_centrado(cv, o.get("texto", "1"), 0, -50, fuente("Rotulo.ttf", 110), relleno("#e67700"))


OBJETOS.update({"contador": _contador, "texto": _texto, "barras": _barras, "cuadricula": _cuadricula,
                "flecha": _flecha, "check": _check, "cruz": _cruz, "alcantarilla": _alcantarilla, "panal": _panal,
                "figura": _figura, "tangencia": _tangencia, "trofeo": _trofeo, "persona": lambda cv, t, o: _persona_icono(cv, 0)})
