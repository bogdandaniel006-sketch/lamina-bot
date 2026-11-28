"""Convierte una historia (JSON) + los tiempos de la voz en fotogramas.

Video.dibujar(cv, t) pinta el fotograma del segundo t: fondo, objetos, personajes, efectos,
cámara y subtítulos.
"""
from __future__ import annotations

import math

import skia

from . import fondos, objetos, personajes
from .personajes import Pose, Rasgos
from .util import (H, SUELO, TINTA, W, circulo, color, ease_in, ease_in_out, ease_out, ease_out_back, forma, fuente,
                   lerp, normaliza, poligono, relleno, rng, ruido, trazo, ventana)

ESCALA_ACTOR = 1.2   # tamaño base de los personajes

# ------------------------------------------------------------------ vocabulario
BRAZOS = {
    "reposo": ((0.18, 0.15), (0.18, 0.15)),
    "arriba": ((2.55, 0.25), (2.55, 0.25)),
    "señalar": ((0.18, 0.15), (1.55, 0.0)),
    "barbilla": ((0.18, 0.15), (-0.9, 4.04)),
    "cabeza": ((2.35, -4.85), (2.35, -4.85)),
    "pecho": ((0.9, -2.2), (0.9, -2.2)),
    "jarras": ((0.75, -1.9), (0.75, -1.9)),
    "saludar": ((0.18, 0.15), (2.4, 0.5)),
    "sujetar": ((0.18, 0.15), (0.8, -1.0)),
}

DURACION = {  # duración por defecto de cada acción (s); "fin" = hasta que acabe la escena
    "saltar": 0.55, "sorpresa": 1.3, "temblar": 1.6, "llorar": 2.2, "celebrar": 2.2, "pensar": 1.8,
    "señalar": 1.6, "hablar": 1.5, "andar": 1.2, "caer": 0.6, "dormir": 3.0, "agobiado": 2.0,
    "saludar": 1.4, "enfadarse": 1.6, "reir": 1.6,
    # objetos
    "romper": 0.7, "aparecer": 0.45, "desaparecer": 0.35, "brillar": 0.6, "flotar": 99, "girar": 0.7,
    "dibujar": 2.0, "crecer": 0.5, "contar": 1.6,
    # efectos globales
    "confeti": 2.5, "flash": 0.35, "sacudir": 0.5, "texto": 1.3, "humo": 0.7, "destellos": 1.0,
}

ACCIONES_PERSONAJE = {"saltar", "sorpresa", "temblar", "llorar", "celebrar", "pensar", "señalar", "hablar", "andar",
                      "caer", "dormir", "agobiado", "saludar", "enfadarse", "reir", "cara", "mirar", "girar",
                      "salir", "entrar"}
ACCIONES_OBJETO = {"contar", "romper", "aparecer", "desaparecer", "brillar", "temblar", "flotar", "girar", "dibujar", "crecer",
                   "caer"}
EFECTOS = {"confeti", "flash", "sacudir", "texto", "humo", "destellos"}


def _bloques(palabras, maximo=5):
    """Agrupa las palabras en frases cortas para los subtítulos (corta en la puntuación)."""
    out, ini = [], 0
    for k, (tok, _, _) in enumerate(palabras):
        n = k - ini + 1
        if n >= maximo or tok[-1:] in ".,!?…:;" or k == len(palabras) - 1:
            out.append((ini, k + 1))
            ini = k + 1
    return out or [(0, 0)]


def _px(v, total):
    """0..1 -> píxeles; números > 1 se toman ya como píxeles."""
    return v * total if isinstance(v, (int, float)) and -1.5 <= v <= 1.5 else float(v)


class Escena:
    def __init__(self, d: dict, inicio: float, dur: float, palabras, anterior: "Escena | None", indice: int):
        self.d = d
        self.i = indice
        self.inicio = inicio
        self.dur = dur
        self.palabras = palabras                    # [(token, ini, fin)] relativos a la escena
        self.fondo = d.get("fondo", "aula")
        self.destacar = {normaliza(w) for frase in d.get("destacar", []) for w in frase.split()}
        self.bloques = _bloques(palabras)
        previos = set(anterior.actores) if anterior else set()
        self.actores = {}
        for k, a in enumerate(d.get("actores", [])):
            aid = a.get("id")
            if not aid:
                continue
            self.actores[aid] = dict(a, _nuevo=aid not in previos, _orden=k)
        self.objetos = []
        for k, o in enumerate(d.get("objetos", [])):
            o = dict(o)
            o.setdefault("id", f"{o.get('tipo')}{k}")
            self.objetos.append(o)
        self.eventos = []
        for ev in d.get("eventos", []):
            ev = dict(ev)
            ev["_t0"] = self._tiempo(ev)
            dur = ev.get("dur", DURACION.get(ev.get("hace"), 1.0))
            ev["_dur"] = max(0.05, self.dur - ev["_t0"]) if dur == "fin" else float(dur)
            self.eventos.append(ev)
        self.eventos.sort(key=lambda e: e["_t0"])

    def _tiempo(self, ev) -> float:
        if "palabra" in ev:
            objetivo = normaliza(str(ev["palabra"])).split()
            if objetivo:
                for k, (tok, ini, _) in enumerate(self.palabras):
                    if normaliza(tok).startswith(objetivo[0]):
                        return ini
        if "momento" in ev:
            return float(ev["momento"]) * self.dur
        if "t" in ev:
            return float(ev["t"])
        return 0.0

    def eventos_de(self, quien):
        return [e for e in self.eventos if e.get("quien") == quien]


class Video:
    def __init__(self, historia: dict, tiempos: list[dict]):
        self.h = historia
        self.reparto = {k: Rasgos.de_dict(v, k) for k, v in historia.get("reparto", {}).items()}
        self.escenas: list[Escena] = []
        t = 0.0
        ant = None
        for i, (d, tm) in enumerate(zip(historia["escenas"], tiempos)):
            e = Escena(d, t, tm["dur"], tm["palabras"], ant, i)
            self.escenas.append(e)
            t += tm["dur"]
            ant = e
        self.duracion = t
        self.estilo_subs = historia.get("subtitulos", "karaoke")

    # ------------------------------------------------------------ utilidades
    def escena_en(self, t: float) -> Escena:
        for e in self.escenas:
            if t < e.inicio + e.dur:
                return e
        return self.escenas[-1]

    def efectos_sonido(self):
        from .audio import SFX_DE_ACCION
        out = []
        for e in self.escenas:
            out.append((e.inicio, "whoosh" if e.d.get("transicion") in ("barrido", "flash") else None))
            for a in e.actores.values():
                if a["_nuevo"] and e.i > 0 and a.get("entra", "pop") == "pop":
                    out.append((e.inicio + 0.05 + a["_orden"] * 0.08, "pop"))
                    break
            for ev in e.eventos:
                s = ev.get("sonido", SFX_DE_ACCION.get(ev.get("hace")))
                if s:
                    out.append((e.inicio + ev["_t0"], s))
        return out

    # ------------------------------------------------------------ fotograma
    def dibujar(self, cv: skia.Canvas, t: float):
        e = self.escena_en(t)
        u = t - e.inicio
        cv.save()
        self._camara(cv, e, u)
        fondos.dibujar(cv, e.fondo, t)
        # objetos de detrás (y los que brillan, para que sus rayos no tapen a nadie), personajes, objetos de delante
        brillan = {ev.get("quien") for ev in e.eventos if ev.get("hace") == "brillar"}
        detras = [o for o in e.objetos if o.get("capa", "delante") == "detras" or o["id"] in brillan]
        for o in detras:
            self._objeto(cv, e, o, u, t)
        orden = sorted(e.actores.items(), key=lambda kv: kv[1].get("y", 0))
        for aid, a in orden:
            self._actor(cv, e, aid, a, u, t)
        for o in e.objetos:
            if o not in detras:
                self._objeto(cv, e, o, u, t)
        self._efectos(cv, e, u, t)
        cv.restore()
        if e.d.get("vineta", True):
            self._vineta(cv)
        if e.d.get("sello"):
            self._sello(cv, u)
        self._onomatopeyas(cv, e, u)
        self._flash(cv, e, u)
        self._subtitulos(cv, e, u)
        if e.d.get("rotulo"):
            self._rotulo(cv, e.d["rotulo"], u)

    def _camara(self, cv, e: Escena, u: float):
        tipo = e.d.get("camara", "zoom_in")
        p = ease_in_out(u / e.dur)
        z, cx, cy = 1.0, W / 2, H * 0.55
        if tipo == "zoom_in":
            z = lerp(1.0, 1.10, p)
        elif tipo == "zoom_out":
            z = lerp(1.16, 1.0, p)
        elif tipo == "paneo_izq":
            z, cx = 1.12, lerp(W * 0.58, W * 0.42, p)
        elif tipo == "paneo_der":
            z, cx = 1.12, lerp(W * 0.42, W * 0.58, p)
        elif tipo == "enfoque":
            foco = e.d.get("foco")
            a = e.actores.get(foco)
            if a:
                cx = lerp(W / 2, _px(a.get("x", 0.5), W), ease_out(u / 0.9))
                cy = lerp(H * 0.55, _px(a.get("y", SUELO / H), H) - 330, ease_out(u / 0.9))
                z = lerp(1.0, 1.45, ease_out(u / 0.9))
        # asentamiento al cambiar de escena (da ritmo a los cortes)
        if e.i > 0:
            z *= 1 + 0.06 * (1 - ease_out(u / 0.35))
        # sacudidas
        dx = dy = 0.0
        for ev in e.eventos:
            if ev.get("hace") in ("sacudir", "romper") or (ev.get("hace") == "caer" and ev.get("quien") in e.actores):
                pr = ventana(u, ev["_t0"], 0.45)
                if pr is not None:
                    amp = 26 * (1 - pr)
                    dx += math.sin(u * 90) * amp
                    dy += math.cos(u * 77) * amp
        cv.translate(W / 2 + dx, H * 0.55 + dy)
        cv.scale(z, z)
        cv.translate(-cx, -cy)

    # ------------------------------------------------------------ personajes
    def _actor(self, cv, e: Escena, aid: str, a: dict, u: float, t: float):
        r = self.reparto.get(aid) or Rasgos.de_dict({}, aid)
        x = _px(a.get("x", 0.5), W)
        y = _px(a.get("y", SUELO / H), H)
        esc = a.get("escala", 1.0) * ESCALA_ACTOR
        mira = a.get("mira", 1 if x < W / 2 else -1)
        if isinstance(mira, str):
            mira = -1 if mira.startswith("izq") else 1
        cara = a.get("cara", "neutral")
        brazos = BRAZOS.get(a.get("brazos", "reposo"), BRAZOS["reposo"])
        pose = Pose(cara=cara, mira=mira, brazos=brazos)
        sem = sum(map(ord, aid))
        pose.respira = math.sin(t * 2.4 + sem) * 0.5 + 0.5
        # parpadeo cada ~3 s
        ciclo = (t + sem * 0.37) % 3.1
        pose.parpadeo = 1.0 if ciclo < 0.11 else 0.0
        pose.giro = math.sin(t * 1.3 + sem) * 1.8          # balanceo suave para que nunca estén congelados

        alpha = 1.0
        # entrada
        if a["_nuevo"]:
            entra = a.get("entra", "pop" if e.i > 0 or u < 0.5 else "pop")
            d0 = a["_orden"] * 0.08
            if entra == "pop":
                k = ease_out_back(min(1, max(0, (u - d0) / 0.38)))
                esc *= max(0.001, k)
            elif entra in ("izquierda", "derecha"):
                k = ease_out(min(1, max(0, (u - d0) / 0.7)))
                origen = -250 if entra == "izquierda" else W + 250
                x = lerp(origen, x, k)
                if k < 1:
                    pose.paso = u * 14
                    pose.mira = 1 if entra == "izquierda" else -1

        for ev in e.eventos_de(aid):
            hace = ev.get("hace")
            t0, dur = ev["_t0"], ev["_dur"]
            if u < t0:
                continue
            pr = (u - t0) / dur
            activo = pr <= 1
            # cambios que se quedan
            if hace == "cara":
                cara = ev.get("cara", cara)
                pose.cara = cara
                continue
            if hace in ("mirar", "girar"):
                m = ev.get("a", "otro")
                pose.mira = -pose.mira if m == "otro" else (-1 if str(m).startswith("izq") else 1)
                mira = pose.mira
                continue
            if hace in ("andar", "salir", "entrar"):
                destino = ev.get("a", 1.3 if hace == "salir" and mira > 0 else -0.3 if hace == "salir" else 0.5)
                xd = _px(destino, W)
                k = ease_in_out(min(1, pr))
                if activo:
                    pose.paso = (u - t0) * 13
                    pose.mira = 1 if xd > x else -1
                    pose.respira = abs(math.sin((u - t0) * 13)) * 1.4
                x = lerp(x, xd, k)
                continue
            if not activo:
                if hace == "caer":           # se queda en el suelo
                    pose.giro = -pose.mira * 82
                    pose.dy = 0
                    pose.cara = "agotado"
                continue
            # acciones temporales
            if hace == "saltar":
                pose.dy = -math.sin(math.pi * pr) * 170
                pose.aplasta = 0.12 if pr > 0.9 or pr < 0.08 else -0.06
            elif hace == "sorpresa":
                pose.cara = "sorpresa"
                pose.ojos = 1.4
                pose.marcas["!"] = pr * dur
                if pr < 0.25:
                    pose.dy = -math.sin(math.pi * pr / 0.25) * 60
                pose.brazos = BRAZOS["pecho"] if pr < 0.7 else pose.brazos
            elif hace == "temblar":
                pose.cara = "asustado"
                pose.dx = math.sin(u * 70) * 9
                pose.marcas["sudor"] = pr * dur
                pose.brazos = BRAZOS["pecho"]
            elif hace == "llorar":
                pose.cara = "triste"
                pose.marcas["lagrimas"] = pr * dur
                pose.dy = -abs(math.sin(u * 9)) * 6
            elif hace == "agobiado":
                pose.cara = "agotado"
                pose.marcas["sudor"] = pr * dur
                pose.brazos = BRAZOS["cabeza"]
                pose.dx = math.sin(u * 30) * 4
            elif hace == "celebrar":
                pose.cara = "muy_feliz"
                sw = math.sin(u * 10) * 0.25
                pose.brazos = ((2.55 + sw, 0.25), (2.55 - sw, 0.25))
                pose.dy = -abs(math.sin(u * 7.5)) * 90
            elif hace == "reir":
                pose.cara = "muy_feliz"
                pose.habla = abs(math.sin(u * 16))
                pose.giro = math.sin(u * 8) * 4
            elif hace == "pensar":
                pose.cara = "pensativo"
                pose.marcas["?"] = pr * dur
                pose.brazos = BRAZOS["barbilla"]
            elif hace == "señalar":
                pose.brazos = BRAZOS["señalar"]
                if ev.get("a") in ("izquierda", "derecha"):
                    pose.mira = -1 if ev["a"] == "izquierda" else 1
            elif hace == "saludar":
                pose.cara = "feliz"
                pose.brazos = ((0.18, 0.15), (2.4 + math.sin(u * 14) * 0.35, 0.5))
            elif hace == "hablar":
                pose.habla = abs(math.sin(u * 17)) * (0.5 + 0.5 * abs(math.sin(u * 5)))
            elif hace == "enfadarse":
                pose.cara = "enfadado"
                pose.brazos = BRAZOS["jarras"]
                pose.dx = math.sin(u * 50) * 3
            elif hace == "dormir":
                pose.cara = "dormido"
                pose.marcas["zzz"] = pr * dur
                pose.giro = mira * 6
            elif hace == "caer":
                pose.giro = -pose.mira * 82 * ease_in(pr)
                pose.cara = "asustado"
        pose.alpha = alpha
        if esc > 0.002:
            personajes.dibujar(cv, r, x, y, esc, pose, t)

    # ------------------------------------------------------------ objetos
    def _objeto(self, cv, e: Escena, o: dict, u: float, t: float):
        tipo = o.get("tipo")
        x = _px(o.get("x", 0.5), W)
        y = _px(o.get("y", 0.55), H)
        esc = o.get("escala", 1.0)
        rot = o.get("rot", 0.0)
        alpha = 1.0
        estado = dict(o)
        evs = e.eventos_de(o["id"])
        tiene_aparecer = any(ev.get("hace") == "aparecer" for ev in evs)
        if tiene_aparecer:
            esc_vis = 0.0
        else:
            esc_vis = 1.0
            if o.get("entra", "pop") == "pop" and e.i > 0 or o.get("entra") == "pop":
                esc_vis = ease_out_back(min(1, max(0, (u - 0.1) / 0.4)))
        if "dibujar" in {ev.get("hace") for ev in evs}:
            estado["_dibujo"] = 0.0
        if "contar" in {ev.get("hace") for ev in evs}:
            estado["_cuenta"] = 0.0
        for ev in evs:
            hace = ev.get("hace")
            t0, dur = ev["_t0"], ev["_dur"]
            if u < t0:
                continue
            pr = min(1.0, (u - t0) / dur)
            if hace == "aparecer":
                esc_vis = ease_out_back(pr)
            elif hace == "desaparecer":
                esc_vis *= 1 - ease_in(pr)
            elif hace == "romper":
                estado["_roto"] = ease_out(pr)
            elif hace == "brillar":
                estado["_brillo"] = ease_out(pr)
            elif hace == "dibujar":
                estado["_dibujo"] = ease_in_out(pr)
            elif hace == "contar":
                estado["_cuenta"] = ease_out(pr)
            elif hace == "temblar" and pr < 1:
                x += math.sin(u * 60) * 10
                rot += math.sin(u * 45) * 4
            elif hace == "flotar":
                y += math.sin((u - t0) * 2.4) * 22
                rot += math.sin((u - t0) * 1.7) * 3
            elif hace == "girar":
                rot += 360 * ease_in_out(pr)
            elif hace == "crecer":
                esc *= lerp(1, ev.get("factor", 1.35), ease_out_back(pr))
            elif hace == "caer":
                yd = _px(ev.get("a", SUELO / H), H) - 40
                k = pr
                rebote = abs(math.sin(k * math.pi * 2.5)) * (1 - k) * 0.25 if k > 0.6 else 0
                y = lerp(y, yd, min(1, ease_in(min(1, k / 0.6)))) - rebote * 200
                rot += 25 * k
        if o.get("flotar"):
            y += math.sin(t * 2.2) * 14
        esc *= esc_vis
        if esc <= 0.002:
            return
        if tipo == "figura" and o.get("ancho_cte"):
            estado["_rot"] = rot    # la figura gira, pero las rectas de la anchura se quedan horizontales
            rot = 0
        cv.save()
        cv.translate(x, y)
        cv.rotate(rot)
        cv.scale(esc, esc)
        if alpha < 1:
            cv.saveLayerAlpha(None, int(alpha * 255))
            objetos.dibujar(cv, tipo, t, estado)
            cv.restore()
        else:
            objetos.dibujar(cv, tipo, t, estado)
        cv.restore()

    # ------------------------------------------------------------ efectos
    def _origen(self, e: Escena, ev: dict):
        if "x" in ev or "y" in ev:
            return _px(ev.get("x", 0.5), W), _px(ev.get("y", 0.45), H)
        a = e.actores.get(ev.get("quien"))
        if a:
            return _px(a.get("x", 0.5), W), _px(a.get("y", SUELO / H), H) - 450
        for o in e.objetos:
            if o["id"] == ev.get("quien"):
                return _px(o.get("x", 0.5), W), _px(o.get("y", 0.55), H)
        return W / 2, H * 0.45

    def _efectos(self, cv, e: Escena, u: float, t: float):
        for n, ev in enumerate(e.eventos):
            hace = ev.get("hace")
            pr = ventana(u, ev["_t0"], ev["_dur"])
            if pr is None:
                continue
            x0, y0 = self._origen(e, ev)
            tau = u - ev["_t0"]
            if hace == "confeti" or (hace == "celebrar" and ev.get("confeti", True)):
                self._confeti(cv, x0 if hace == "confeti" else x0, y0 - 100, tau, f"{e.i}-{n}", pr)
            elif hace == "destellos" or hace == "brillar" or hace == "aparecer":
                self._destellos(cv, x0, y0, tau, f"{e.i}-{n}", pr)
            elif hace == "humo" or hace == "desaparecer":
                for k in range(7):
                    ang = k * math.tau / 7
                    d = 40 + 140 * ease_out(pr)
                    forma(cv, circulo(x0 + math.cos(ang) * d, y0 + math.sin(ang) * d * 0.6, 60 * (1 - pr) + 6),
                          "#f1f3f5", 5, alpha=1 - pr)

    def _onomatopeyas(self, cv, e: Escena, u: float):
        """Textos tipo cómic ('¡CRACK!'), en coordenadas de pantalla para que nunca se salgan."""
        for n, ev in enumerate(e.eventos):
            hace = ev.get("hace")
            if hace not in ("texto", "romper"):
                continue
            pr = ventana(u, ev["_t0"], DURACION["texto"])
            if pr is None:
                continue
            x0, y0 = self._origen(e, ev)
            if hace == "romper":
                txt, c, y0 = ev.get("texto", "¡CRACK!"), "#ff6b6b", H * 0.29
            else:
                txt, c = ev.get("texto", "¡PUM!"), ev.get("color", "#ffd43b")
                if "y" not in ev:
                    y0 -= 120
            f = fuente("Rotulo.ttf", 120)
            media = f.measureText(txt) / 2 + 40
            x0 = min(max(x0, media), W - media)
            y0 = min(max(y0, H * 0.27), H * 0.8)
            self._onomatopeya(cv, txt, x0, y0, pr, c, n)

    def _confeti(self, cv, x0, y0, tau, sem, pr):
        r = rng("confeti", sem)
        cols = ["#ff6b6b", "#ffd43b", "#51cf66", "#339af0", "#cc5de8", "#ff922b"]
        for i in range(70):
            vx = r.uniform(-700, 700)
            vy = r.uniform(-1500, -600)
            rs = r.uniform(-600, 600)
            c = cols[i % len(cols)]
            x = x0 + vx * tau
            y = y0 + vy * tau + 1700 * tau * tau
            cv.save()
            cv.translate(x, y)
            cv.rotate(rs * tau)
            cv.drawRect(skia.Rect.MakeXYWH(-11, -6, 22, 12 * abs(math.cos(tau * 9 + i))), relleno(c, 1 - pr ** 3))
            cv.restore()

    def _destellos(self, cv, x0, y0, tau, sem, pr):
        r = rng("brillo", sem)
        for i in range(9):
            ang = r.uniform(0, math.tau)
            d = r.uniform(120, 330) * ease_out(min(1, tau * 2.5))
            s = r.uniform(18, 34) * math.sin(math.pi * pr)
            px, py = x0 + math.cos(ang) * d, y0 + math.sin(ang) * d
            p = poligono([(px, py - s * 2), (px + s * 0.5, py - s * 0.5), (px + s * 2, py), (px + s * 0.5, py + s * 0.5),
                          (px, py + s * 2), (px - s * 0.5, py + s * 0.5), (px - s * 2, py), (px - s * 0.5, py - s * 0.5)])
            cv.drawPath(p, relleno("#fff3bf"))
            cv.drawPath(p, trazo("#fab005", 3))

    def _onomatopeya(self, cv, txt, x, y, pr, c, n):
        f = fuente("Rotulo.ttf", 120)
        k = ease_out_back(min(1, pr * 4)) * (1 - ease_in(max(0, (pr - 0.8) / 0.2)))
        if k <= 0.01:
            return
        cv.save()
        cv.translate(x, y)
        cv.rotate(-8 + (n % 3) * 8)
        cv.scale(k, k)
        ancho = f.measureText(txt)
        borde = skia.Paint(Color=color(TINTA), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=26,
                           StrokeJoin=skia.Paint.kRound_Join)
        cv.drawString(txt, -ancho / 2, 40, f, borde)
        cv.drawString(txt, -ancho / 2, 40, f, relleno(c))
        cv.restore()

    def _flash(self, cv, e: Escena, u: float):
        a = 0.0
        if e.i > 0 and e.d.get("transicion") == "flash":
            a = max(a, 1 - u / 0.25)
        for ev in e.eventos:
            if ev.get("hace") == "flash":
                pr = ventana(u, ev["_t0"], ev["_dur"])
                if pr is not None:
                    a = max(a, 1 - pr)
        if a > 0:
            cv.drawRect(skia.Rect.MakeWH(W, H), relleno("#ffffff", a * 0.85))

    # ------------------------------------------------------------ textos
    def _subtitulos(self, cv, e: Escena, u: float):
        if not e.palabras or self.estilo_subs == "ninguno":
            return
        idx = None
        for k, (tok, ini, fin) in enumerate(e.palabras):
            if u >= ini - 0.02:
                idx = k
        if idx is None:
            return
        tok, ini, fin = e.palabras[idx]
        sig = e.palabras[idx + 1][1] if idx + 1 < len(e.palabras) else e.dur
        if u > max(fin, sig - 0.02) + 0.6:   # silencio largo: no dejar el texto colgado
            return
        if self.estilo_subs == "palabra":
            self._sub_palabra(cv, e, tok, ini, u)
        else:
            self._sub_karaoke(cv, e, idx, u)

    def _sub_karaoke(self, cv, e: Escena, idx: int, u: float):
        """Como en los vídeos de referencia: la frase en gris, la palabra que suena en blanco
        y las palabras clave dentro de un recuadro."""
        bloque = next(b for b in e.bloques if b[0] <= idx < b[1])
        palabras = e.palabras[bloque[0]:bloque[1]]
        f = fuente("Sans800.ttf", 70)
        esp = f.measureText(" ")
        # reparte en 1 o 2 líneas
        lineas, cur, ancho_cur = [], [], 0.0
        for k, w in enumerate(palabras):
            a = f.measureText(w[0])
            if cur and ancho_cur + esp + a > W * 0.84:
                lineas.append(cur)
                cur, ancho_cur = [], 0.0
            cur.append((bloque[0] + k, w[0], a))
            ancho_cur += (esp if len(cur) > 1 else 0) + a
        if cur:
            lineas.append(cur)
        if len(lineas) == 2 and len(lineas[1]) == 1 and len(lineas[0]) >= 3:   # que no quede una palabra sola
            lineas[1].insert(0, lineas[0].pop())
        m = f.getMetrics()
        alto = 88
        y0 = H * 0.15 - (len(lineas) - 1) * alto / 2
        aparece = ease_out(min(1, (u - e.palabras[bloque[0]][1]) / 0.15))
        sombra = skia.Paint(Color=color("#000000", 0.6), AntiAlias=True,
                            MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 10))
        for li, linea in enumerate(lineas):
            total = sum(a for _, _, a in linea) + esp * (len(linea) - 1)
            x = W / 2 - total / 2
            y = y0 + li * alto - (m.fAscent + m.fDescent) / 2 + (1 - aparece) * 18
            for k, txt, a in linea:
                clave = normaliza(txt) in e.destacar
                dicha = k <= idx
                if clave and dicha:
                    caja = skia.Rect.MakeXYWH(x - 12, y + m.fAscent - 6, a + 24, -m.fAscent + m.fDescent + 18)
                    cv.drawRRect(skia.RRect.MakeRectXY(caja, 12, 12), relleno("#1c3d8f", 0.55 * aparece))
                    cv.drawRRect(skia.RRect.MakeRectXY(caja, 12, 12), trazo("#74a7ff", 5, aparece, redondo=False))
                cv.drawString(txt, x + 3, y + 5, f, sombra)
                cv.drawString(txt, x, y, f, skia.Paint(Color=color("#14141f", 0.8 * aparece), AntiAlias=True,
                                                       Style=skia.Paint.kStroke_Style, StrokeWidth=9,
                                                       StrokeJoin=skia.Paint.kRound_Join))
                if k == idx:
                    col = "#ffffff"
                elif dicha:
                    col = "#e9ecef"
                else:
                    col = "#ced4da"
                alpha = (1.0 if k == idx else 0.9 if dicha else 0.6) * aparece
                cv.drawString(txt, x, y, f, relleno(col, alpha))
                x += a + esp

    def _sub_palabra(self, cv, e: Escena, tok: str, ini: float, u: float):
        """Una sola palabra grande en el centro (estilo 'Rolls-Royce')."""
        destacada = normaliza(tok) in e.destacar
        f = fuente("Sans800.ttf", 100)
        k = 0.82 + 0.18 * ease_out_back(min(1, (u - ini) / 0.12))
        ancho = f.measureText(tok)
        if ancho > W * 0.86:
            f = fuente("Sans800.ttf", 100 * W * 0.86 / ancho)
            ancho = f.measureText(tok)
        cv.save()
        cv.translate(W / 2, H * 0.17)
        cv.scale(k, k)
        borde = skia.Paint(Color=color("#1a1a1a"), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=16,
                           StrokeJoin=skia.Paint.kRound_Join)
        cv.drawString(tok, -ancho / 2, 36, f, borde)
        cv.drawString(tok, -ancho / 2, 36, f, relleno("#ffd43b" if destacada else "#ffffff"))
        cv.restore()

    def _vineta(self, cv):
        """Oscurece suavemente los bordes: da profundidad y hace legibles los subtítulos."""
        cv.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial(
            (W / 2, H * 0.52), H * 0.72, [color("#000000", 0), color("#000000", 0), color("#000000", 0.42)],
            [0.0, 0.55, 1.0])))
        cv.drawRect(skia.Rect.MakeWH(W, H * 0.3), skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeLinear(
            [(0, 0), (0, H * 0.3)], [color("#000000", 0.38), color("#000000", 0)])))

    def _sello(self, cv, u: float, txt="danidemiguel.com"):
        """Sello redondo de la marca, como el de 'Ahora lo pillo'."""
        k = ease_out_back(min(1, max(0, u - 0.15) / 0.5))
        if k <= 0:
            return
        cv.save()
        cv.translate(W / 2, H * 0.53)
        cv.rotate(-6 + math.sin(u * 2.2) * 3)
        cv.scale(k, k)
        R = 290
        for i in range(36):   # borde dentado
            a = i * math.tau / 36 + u * 0.4
            cv.drawCircle(math.cos(a) * R, math.sin(a) * R, 34, relleno("#ffd43b"))
        disco = skia.Path()
        disco.addCircle(0, 0, R)
        from .personajes import vol
        vol(cv, disco, "#ffd43b", 9)
        cv.drawCircle(0, 0, R - 34, trazo("#1a1a1a", 6, 0.85))
        # icono: compás estilizado
        cv.save()
        cv.translate(0, -120)
        cv.scale(0.42, 0.42)
        objetos.dibujar(cv, "compas", u, {})
        cv.restore()
        f1 = fuente("Rotulo.ttf", 82)
        f2 = fuente("Rotulo.ttf", 70)
        borde = skia.Paint(Color=color("#ffffff"), AntiAlias=True, Style=skia.Paint.kStroke_Style, StrokeWidth=14,
                           StrokeJoin=skia.Paint.kRound_Join)
        for txt_, ff, y in (("danidemiguel", f1, 40), (".com", f2, 125)):
            a = ff.measureText(txt_)
            cv.drawString(txt_, -a / 2, y, ff, borde)
            cv.drawString(txt_, -a / 2, y, ff, relleno("#1a1a1a"))
        cv.restore()

    def _rotulo(self, cv, txt: str, u: float):
        """Rótulo fijo abajo (por ejemplo 'danidemiguel.com')."""
        f = fuente("Rotulo.ttf", 64)
        k = ease_out_back(min(1, u / 0.4))
        ancho = f.measureText(txt) + 80
        cv.save()
        cv.translate(W / 2, H * 0.86)
        cv.scale(k, k)
        forma(cv, _pildora(ancho, 110), "#ffffff", 8)
        m = f.getMetrics()
        cv.drawString(txt, -f.measureText(txt) / 2, -(m.fAscent + m.fDescent) / 2, f, relleno("#1c7ed6"))
        cv.restore()


def _pildora(w, h):
    p = skia.Path()
    p.addRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(-w / 2, -h / 2, w, h), h / 2, h / 2))
    return p
