"""Fondos ilustrados planos, dibujados por código (1080x1920).

También se puede usar una imagen propia: "fondo": "mi_fondo.jpg" busca en assets/fondos/.
"""
from __future__ import annotations

import math

import skia

from .util import (ASSETS, H, SUELO, TINTA, W, circulo, color, degradado_r, degradado_v, forma, fuente, imagen,
                   oscurece, poligono, relleno, rrect, texto_centrado, trazo)

LINEA_SUELO = 1240   # donde la pared se junta con el suelo


def _suelo_madera(cv, c1="#c08552", c2="#a86b3c"):
    cv.drawRect(skia.Rect.MakeLTRB(0, LINEA_SUELO, W, H), degradado_v(LINEA_SUELO, H, c1, oscurece(c1, 0.25)))
    # tablas en perspectiva
    for i in range(-6, 8):
        p = skia.Path()
        p.moveTo(W / 2 + i * 120, LINEA_SUELO)
        p.lineTo(W / 2 + i * 380, H)
        cv.drawPath(p, trazo(c2, 4, 0.7))
    for k, y in enumerate((1310, 1440, 1620, 1830)):
        cv.drawRect(skia.Rect.MakeLTRB(0, y, W, y + 3), relleno(c2, 0.5))
    cv.drawRect(skia.Rect.MakeLTRB(0, LINEA_SUELO - 22, W, LINEA_SUELO + 4), relleno(oscurece(c1, 0.35)))


def _ventana(cv, x, y, w, h, noche=False, t=0.0):
    forma(cv, rrect(x - 14, y - 14, w + 28, h + 28, 10), "#f1f3f5", 7)
    cielo = degradado_v(y, y + h, "#1b2a4e" if noche else "#74c0fc", "#3b5bdb" if noche else "#d0ebff")
    cv.drawRect(skia.Rect.MakeXYWH(x, y, w, h), cielo)
    if noche:
        cv.drawCircle(x + w * 0.7, y + h * 0.28, 46, relleno("#fff9db"))
        cv.drawCircle(x + w * 0.7 + 22, y + h * 0.28 - 12, 42, relleno("#1f3260"))
        for i in range(9):
            sx = x + (i * 97) % w
            sy = y + (i * 53) % (h * 0.8)
            cv.drawCircle(sx, sy, 3 + (math.sin(t * 3 + i) + 1) * 1.5, relleno("#ffffff", 0.9))
    else:
        for k in range(2):
            nx = x + ((t * 18 + k * 230) % (w + 200)) - 100
            ny = y + 70 + k * 120
            for dx, r in ((0, 34), (36, 44), (78, 32)):
                cv.drawCircle(nx + dx, ny, r, relleno("#ffffff", 0.95))
    cv.drawRect(skia.Rect.MakeXYWH(x + w / 2 - 6, y, 12, h), relleno("#f1f3f5"))
    cv.drawRect(skia.Rect.MakeXYWH(x, y + h / 2 - 6, w, 12), relleno("#f1f3f5"))
    cv.drawRect(skia.Rect.MakeXYWH(x - 14, y - 14, w + 28, h + 28), trazo(TINTA, 7, redondo=False))


def aula(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, LINEA_SUELO), degradado_v(0, LINEA_SUELO, "#f6e7c8", "#ecd3a3"))
    cv.drawRect(skia.Rect.MakeLTRB(0, 860, W, LINEA_SUELO), relleno("#7fb6a4"))
    cv.drawRect(skia.Rect.MakeLTRB(0, 850, W, 872), relleno("#5c9483"))
    _ventana(cv, 60, 330, 300, 380, t=t)
    # pizarra al fondo
    forma(cv, rrect(470, 360, 560, 330, 10), "#8d5524", 7)
    cv.drawRect(skia.Rect.MakeLTRB(492, 382, 1008, 668), relleno("#2f6b4f"))
    cv.drawCircle(640, 520, 70, trazo("#f8f9fa", 4, 0.5))
    p = skia.Path()
    p.moveTo(540, 620)
    p.lineTo(780, 440)
    cv.drawPath(p, trazo("#f8f9fa", 4, 0.5))
    texto_centrado(cv, "Dibujo Técnico", 880, 430, fuente("Rotulo.ttf", 34), relleno("#f8f9fa", 0.6))
    # lámpara
    cv.drawRect(skia.Rect.MakeXYWH(538, 0, 4, 120), relleno(TINTA))
    forma(cv, poligono([(470, 160), (610, 160), (580, 110), (500, 110)]), "#ffd43b", 6)
    cv.drawPath(poligono([(470, 160), (610, 160), (900, 900), (180, 900)]), relleno("#fff9db", 0.12))
    _suelo_madera(cv)


def habitacion(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, LINEA_SUELO), degradado_v(0, LINEA_SUELO, "#2b2f5c", "#3d4380"))
    _ventana(cv, 620, 300, 340, 400, noche=True, t=t)
    # póster
    forma(cv, rrect(110, 330, 260, 340, 8), "#ff8787", 6)
    cv.drawCircle(240, 470, 70, relleno("#ffe066"))
    texto_centrado(cv, "PAU", 240, 600, fuente("Rotulo.ttf", 60), relleno(TINTA))
    # flexo encendido
    cv.drawPath(poligono([(140, 760), (230, 760), (560, 1300), (-120, 1300)]), relleno("#ffe8a3", 0.16))
    cv.drawCircle(185, 800, 420, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
        (185, 800), 420, [color("#ffd43b", 0.25), color("#ffd43b", 0)])))
    _suelo_madera(cv, "#6b4f3a", "#5a3f2c")


def biblioteca(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, LINEA_SUELO), degradado_v(0, LINEA_SUELO, "#5c3d2e", "#7b4f37"))
    cols = ["#c92a2a", "#1864ab", "#2b8a3e", "#e67700", "#862e9c", "#f1f3f5", "#0b7285"]
    for fila, y in enumerate((260, 520, 780)):
        forma(cv, rrect(-20, y + 200, W + 40, 34, 4), "#8b5a3c", 6)
        x = 20
        i = fila * 3
        while x < W - 20:
            w = 34 + (i * 7) % 26
            h = 150 + (i * 13) % 45
            forma(cv, rrect(x, y + 200 - h, w, h, 4), cols[i % len(cols)], 4)
            x += w + 4
            i += 1
    cv.drawCircle(W / 2, 200, 700, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
        (W / 2, 200), 700, [color("#ffd8a8", 0.25), color("#ffd8a8", 0)])))
    _suelo_madera(cv, "#a9744f", "#8b5a3c")


def pasillo(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, LINEA_SUELO), degradado_v(0, LINEA_SUELO, "#e9ecef", "#dee2e6"))
    for i in range(7):
        x = -20 + i * 160
        forma(cv, rrect(x, 420, 150, 760, 6), "#4c6ef5" if i % 3 else "#f03e3e", 6)
        for k in range(3):
            cv.drawRect(skia.Rect.MakeXYWH(x + 30, 470 + k * 22, 90, 8), relleno(TINTA, 0.5))
        cv.drawRect(skia.Rect.MakeXYWH(x + 120, 780, 10, 50), relleno("#ced4da"))
    cv.drawRect(skia.Rect.MakeLTRB(0, LINEA_SUELO, W, H), degradado_v(LINEA_SUELO, H, "#adb5bd", "#868e96"))
    for i in range(-5, 7):
        p = skia.Path()
        p.moveTo(W / 2 + i * 140, LINEA_SUELO)
        p.lineTo(W / 2 + i * 420, H)
        cv.drawPath(p, trazo("#ced4da", 4))


def examen(cv, t):
    aula(cv, t)
    # reloj grande y cartel de silencio
    cv.save()
    cv.translate(780, 220)
    from .objetos import dibujar as obj
    obj(cv, "reloj", t, {"velocidad": 0.4})
    cv.restore()
    forma(cv, rrect(120, 160, 300, 100, 14), "#ffffff", 6)
    texto_centrado(cv, "SILENCIO", 270, 210, fuente("Rotulo.ttf", 52), relleno("#e03131"))


def escenario(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_v(0, H, "#2b1d5c", "#5f3dc4"))
    for i, x in enumerate((180, 540, 900)):
        ang = math.sin(t * 0.8 + i) * 0.15
        p = poligono([(x - 40, 0), (x + 40, 0), (x + 330 + ang * 600, LINEA_SUELO + 200),
                      (x - 330 + ang * 600, LINEA_SUELO + 200)])
        cv.drawPath(p, relleno("#e5dbff", 0.12))
    cv.drawRect(skia.Rect.MakeLTRB(0, LINEA_SUELO, W, H), degradado_v(LINEA_SUELO, H, "#1f6f78", "#14454b"))
    cv.drawOval(skia.Rect.MakeXYWH(90, SUELO - 90, 900, 190), relleno("#0b2e33", 0.7))
    cv.drawOval(skia.Rect.MakeXYWH(90, SUELO - 90, 900, 190), trazo("#38d9a9", 5, 0.5))


def magia(cv, t):
    """Fondo de 'revelación': rayos girando, para el momento de la herramienta mágica."""
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_r(W / 2, 820, 1300, "#fff3bf", "#ff922b"))
    cv.save()
    cv.translate(W / 2, 820)
    cv.rotate(t * 12)
    for i in range(18):
        a = i * 20
        cv.save()
        cv.rotate(a)
        cv.drawPath(poligono([(0, 0), (1600, -140), (1600, 140)]), relleno("#ffffff", 0.22))
        cv.restore()
    cv.restore()
    cv.drawRect(skia.Rect.MakeLTRB(0, LINEA_SUELO + 120, W, H), degradado_v(LINEA_SUELO + 120, H, "#ffa94d", "#f76707"))


def calle(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, LINEA_SUELO), degradado_v(0, LINEA_SUELO, "#74c0fc", "#d0ebff"))
    cv.drawCircle(860, 260, 90, relleno("#ffd43b"))
    for i, (x, w, h, c) in enumerate(((0, 300, 620, "#e8590c"), (290, 260, 780, "#f59f00"), (540, 280, 560, "#d6336c"),
                                     (810, 290, 700, "#7048e8"))):
        forma(cv, rrect(x, LINEA_SUELO - h, w, h + 30, 6), c, 6)
        for fy in range(int(LINEA_SUELO - h + 50), LINEA_SUELO - 120, 120):
            for fx in range(x + 40, x + w - 60, 90):
                forma(cv, rrect(fx, fy, 50, 70, 4), "#fff3bf", 4)
    cv.drawRect(skia.Rect.MakeLTRB(0, LINEA_SUELO, W, H), degradado_v(LINEA_SUELO, H, "#ced4da", "#868e96"))
    for i in range(6):
        cv.drawRect(skia.Rect.MakeXYWH(i * 200 - 40, 1700, 120, 18), relleno("#ffffff", 0.8))


def salon(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, LINEA_SUELO), degradado_v(0, LINEA_SUELO, "#ffe8cc", "#ffd8a8"))
    for i in range(0, W, 90):
        cv.drawRect(skia.Rect.MakeXYWH(i, 0, 40, LINEA_SUELO), relleno("#ffc078", 0.25))
    forma(cv, rrect(80, 380, 260, 200, 8), "#ffffff", 6)
    cv.drawRect(skia.Rect.MakeXYWH(100, 400, 220, 160), degradado_v(400, 560, "#8ce99a", "#2f9e44"))
    forma(cv, rrect(640, 820, 400, 260, 40), "#e64980", 7)       # sofá
    forma(cv, rrect(620, 940, 440, 180, 30), "#c2255c", 7)
    _suelo_madera(cv)


def negro(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_r(W / 2, H / 2, 1200, "#343a40", "#0b0c10"))


FONDOS = {"aula": aula, "habitacion": habitacion, "biblioteca": biblioteca, "pasillo": pasillo, "examen": examen,
          "escenario": escenario, "magia": magia, "calle": calle, "salon": salon, "negro": negro}


def dibujar(cv, nombre: str, t: float):
    fn = FONDOS.get(nombre)
    if fn:
        fn(cv, t)
        return
    img = imagen(str(ASSETS / "fondos" / nombre))
    if img is None:
        aula(cv, t)
        return
    k = max(W / img.width(), H / img.height())
    cv.drawImageRect(img, skia.Rect.MakeXYWH((W - img.width() * k) / 2, (H - img.height() * k) / 2,
                                             img.width() * k, img.height() * k),
                     skia.SamplingOptions(skia.FilterMode.kLinear), None)


# ------------------------------------------------------------------ fondos con profundidad (para datos y explicaciones)
def _bokeh(cv, t, colores, n=26, semilla=3, alpha=0.35):
    import random
    r = random.Random(semilla)
    for i in range(n):
        x0, y0 = r.uniform(-50, W + 50), r.uniform(-50, H + 50)
        rad = r.uniform(40, 150)
        vx, vy = r.uniform(-12, 12), r.uniform(-18, -4)
        x = (x0 + vx * t) % (W + 300) - 150
        y = (y0 + vy * t) % (H + 300) - 150
        c = colores[i % len(colores)]
        a = alpha * (0.6 + 0.4 * math.sin(t * 0.8 + i))
        cv.drawCircle(x, y, rad, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
            (x, y), rad, [color(c, a), color(c, a * 0.7), color(c, 0)], [0, 0.7, 1])))


def bokeh(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_r(W / 2, H * 0.45, H * 0.8, "#4b2a8c", "#120a2e"))
    _bokeh(cv, t, ["#b197fc", "#748ffc", "#f783ac", "#63e6be"])


def bokeh_azul(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_r(W / 2, H * 0.45, H * 0.8, "#1c4f8f", "#06132b"))
    _bokeh(cv, t, ["#74c0fc", "#4dabf7", "#63e6be", "#ffffff"], semilla=7)


def bokeh_calido(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_r(W / 2, H * 0.45, H * 0.8, "#b5541c", "#2b0f05"))
    _bokeh(cv, t, ["#ffd43b", "#ffa94d", "#ff8787", "#fff3bf"], semilla=11)


def plano(cv, t):
    """Papel de plano azul (blueprint), muy de dibujo técnico."""
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_r(W / 2, H * 0.45, H * 0.85, "#2463b8", "#0d2a5c"))
    for i in range(0, W + 1, 36):
        cv.drawRect(skia.Rect.MakeXYWH(i, 0, 2 if i % 180 else 3, H), relleno("#ffffff", 0.08 if i % 180 else 0.16))
    for j in range(0, H + 1, 36):
        cv.drawRect(skia.Rect.MakeXYWH(0, j, W, 2 if j % 180 else 3), relleno("#ffffff", 0.08 if j % 180 else 0.16))
    # cotas decorativas
    cv.drawCircle(W * 0.82, H * 0.88, 120, trazo("#ffffff", 3, 0.25))
    p = skia.Path()
    p.moveTo(W * 0.08, H * 0.93)
    p.lineTo(W * 0.5, H * 0.93)
    cv.drawPath(p, trazo("#ffffff", 3, 0.25))


def cuaderno(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_v(0, H, "#fffaf0", "#f3ead7"))
    for i in range(0, W + 1, 45):
        cv.drawRect(skia.Rect.MakeXYWH(i, 0, 2, H), relleno("#74c0fc", 0.28))
    for j in range(0, H + 1, 45):
        cv.drawRect(skia.Rect.MakeXYWH(0, j, W, 2), relleno("#74c0fc", 0.28))
    cv.drawRect(skia.Rect.MakeXYWH(110, 0, 4, H), relleno("#ff8787", 0.5))


def espacio(cv, t):
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_v(0, H, "#0b1026", "#1a1446"))
    import random
    r = random.Random(5)
    for c, x, y, rad in (("#7048e8", 0.2, 0.3, 520), ("#e64980", 0.85, 0.7, 480), ("#1098ad", 0.5, 0.95, 600)):
        cv.drawCircle(W * x, H * y, rad, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
            (W * x, H * y), rad, [color(c, 0.35), color(c, 0)])))
    for i in range(160):
        x, y = r.uniform(0, W), r.uniform(0, H)
        cv.drawCircle(x, y, r.uniform(1, 3.2), relleno("#ffffff", 0.4 + 0.6 * abs(math.sin(t * 1.5 + i))))


def mesa(cv, t):
    """Mesa de madera vista desde arriba."""
    cv.drawRect(skia.Rect.MakeLTRB(0, 0, W, H), degradado_r(W / 2, H / 2, H * 0.75, "#c8915e", "#7d4f2b"))
    for i in range(0, W, 140):
        p = skia.Path()
        p.moveTo(i, 0)
        p.cubicTo(i + 40, H * 0.3, i - 30, H * 0.6, i + 20, H)
        cv.drawPath(p, trazo("#6b4226", 3, 0.25))


FONDOS.update({"bokeh": bokeh, "bokeh_azul": bokeh_azul, "bokeh_calido": bokeh_calido, "plano": plano,
               "cuaderno": cuaderno, "espacio": espacio, "mesa": mesa})
