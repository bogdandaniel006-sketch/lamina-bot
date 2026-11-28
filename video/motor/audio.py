"""Voz en off (Edge TTS, gratis), tiempos de cada palabra, efectos de sonido y mezcla final."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
import random
import re
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from .util import ASSETS, RAIZ, normaliza

SR = 44100
CACHE = RAIZ / ".cache" / "voz"


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise SystemExit("No encuentro ffmpeg. Instala las dependencias: pip install -r requirements.txt")


def leer_audio(ruta: Path) -> np.ndarray:
    """Decodifica cualquier audio a float32 mono 44.1 kHz."""
    out = subprocess.run([ffmpeg_exe(), "-v", "error", "-i", str(ruta), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


# ------------------------------------------------------------------ voz
def _tokens(texto: str) -> list[str]:
    return [t for t in texto.split() if t.strip()]


def _alinear(tokens: list[str], marcas: list[tuple[str, float, float]], total: float):
    """Asigna a cada palabra del guion (con su puntuación) el tiempo que dio el TTS."""
    out = []
    j = 0
    for tok in tokens:
        nt = normaliza(tok)
        hit = None
        for k in range(j, min(j + 4, len(marcas))):
            nm = normaliza(marcas[k][0])
            if nt and nm and (nt.startswith(nm) or nm.startswith(nt)):
                hit = k
                break
        if hit is not None:
            # palabras compuestas que el TTS trocea: juntar hasta cubrir el token
            ini, fin = marcas[hit][1], marcas[hit][2]
            j = hit + 1
            acum = normaliza(marcas[hit][0])
            while j < len(marcas) and len(acum) < len(nt) and nt.startswith(acum + normaliza(marcas[j][0])[:1]):
                acum += normaliza(marcas[j][0])
                fin = marcas[j][2]
                j += 1
            out.append([tok, ini, fin])
        else:
            out.append([tok, None, None])
    # rellenar huecos interpolando
    for i, w in enumerate(out):
        if w[1] is None:
            prev = out[i - 1][2] if i else 0.0
            nxt = next((x[1] for x in out[i + 1:] if x[1] is not None), total)
            huecos = 1 + next((k for k, x in enumerate(out[i + 1:]) if x[1] is not None), len(out) - i - 1)
            paso = (nxt - prev) / max(1, huecos)
            w[1], w[2] = prev, prev + paso
    return [tuple(w) for w in out]


def _estimar(texto: str):
    """Sin voz: tiempos aproximados (≈ 2,8 palabras/segundo, pausas en la puntuación)."""
    t = 0.15
    out = []
    for tok in _tokens(texto):
        d = 0.16 + 0.055 * len(normaliza(tok))
        out.append((tok, t, t + d))
        t += d + (0.28 if re.search(r"[.!?…]$", tok) else 0.12 if tok.endswith(",") else 0.02)
    return out, t + 0.1


async def _tts(texto, voz, velocidad, mp3: Path):
    import edge_tts
    com = edge_tts.Communicate(texto, voz, rate=velocidad, boundary="WordBoundary")
    marcas = []
    with open(mp3, "wb") as f:
        async for ch in com.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                ini = ch["offset"] / 1e7
                marcas.append((ch["text"], ini, ini + ch["duration"] / 1e7))
    return marcas


def narrar(texto: str, voz: str, velocidad: str = "+8%", sin_voz: bool = False):
    """Devuelve (audio float32 | None, palabras [(token, ini, fin)], duración)."""
    if sin_voz or not texto.strip():
        pal, dur = _estimar(texto)
        return None, pal, dur
    CACHE.mkdir(parents=True, exist_ok=True)
    clave = hashlib.sha1(f"{voz}|{velocidad}|{texto}".encode()).hexdigest()[:16]
    mp3, js = CACHE / f"{clave}.mp3", CACHE / f"{clave}.json"
    try:
        if not (mp3.exists() and js.exists()):
            marcas = asyncio.run(_tts(texto, voz, velocidad, mp3))
            js.write_text(json.dumps(marcas))
        marcas = [tuple(m) for m in json.loads(js.read_text())]
        audio = leer_audio(mp3)
        # recorta silencio final
        nz = np.nonzero(np.abs(audio) > 0.01)[0]
        if len(nz):
            audio = audio[: nz[-1] + int(0.05 * SR)]
        dur = len(audio) / SR
        return audio, _alinear(_tokens(texto), marcas, dur), dur
    except Exception as e:
        mp3.unlink(missing_ok=True)
        print(f"  ⚠ No he podido generar la voz ({e.__class__.__name__}: {e}). Sigo sin voz.")
        pal, dur = _estimar(texto)
        return None, pal, dur


# ------------------------------------------------------------------ efectos de sonido sintetizados
def _env(n, ataque=0.005, caida=8.0):
    t = np.arange(n) / SR
    a = np.clip(t / max(ataque, 1e-4), 0, 1)
    return a * np.exp(-t * caida)


def _sfx(nombre: str) -> np.ndarray:
    r = np.random.default_rng(7)
    if nombre == "pop":
        n = int(0.12 * SR)
        t = np.arange(n) / SR
        f = 900 - 500 * t / t[-1]
        return 0.5 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.002, 30)
    if nombre == "boing":
        n = int(0.35 * SR)
        t = np.arange(n) / SR
        f = 180 + 260 * np.abs(np.sin(t * 40)) * np.exp(-t * 6)
        return 0.45 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(n, 0.003, 7)
    if nombre == "crack":
        n = int(0.4 * SR)
        ruido = r.standard_normal(n)
        golpe = ruido * _env(n, 0.001, 18)
        t = np.arange(n) / SR
        grave = np.sin(2 * np.pi * 90 * t) * _env(n, 0.001, 12)
        return 0.55 * (golpe * 0.8 + grave)
    if nombre == "whoosh":
        n = int(0.45 * SR)
        ruido = r.standard_normal(n)
        k = np.hanning(n)
        suav = np.convolve(ruido, np.ones(40) / 40, mode="same")
        return 0.6 * suav * k
    if nombre == "ding":
        n = int(1.2 * SR)
        t = np.arange(n) / SR
        s = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((1318, 1), (1975, 0.5), (2637, 0.25)))
        return 0.25 * s * _env(n, 0.002, 3.5)
    if nombre == "magia":
        n = int(1.4 * SR)
        t = np.arange(n) / SR
        out = np.zeros(n)
        for i, f in enumerate((1046, 1318, 1568, 2093, 2637, 3136)):
            ini = int(i * 0.09 * SR)
            m = n - ini
            out[ini:] += np.sin(2 * np.pi * f * t[:m]) * _env(m, 0.002, 5) * 0.18
        return out
    if nombre == "tic":
        n = int(0.05 * SR)
        return 0.35 * r.standard_normal(n) * _env(n, 0.0005, 90)
    if nombre == "fail":
        n = int(0.9 * SR)
        t = np.arange(n) / SR
        out = np.zeros(n)
        for i, f in enumerate((392, 370, 349, 330)):
            ini = int(i * 0.2 * SR)
            m = min(int(0.3 * SR), n - ini)
            out[ini:ini + m] += np.sign(np.sin(2 * np.pi * f * t[:m])) * 0.12 * _env(m, 0.005, 4)
        return out
    if nombre == "aplausos":
        n = int(1.6 * SR)
        out = np.zeros(n)
        for _ in range(140):
            ini = int(r.uniform(0, n - 3000))
            m = 1800
            out[ini:ini + m] += r.standard_normal(m) * _env(m, 0.0005, 60) * 0.25
        return out * np.hanning(n) * 1.4
    return np.zeros(1)


SFX_DE_ACCION = {
    "saltar": "boing", "sorpresa": "pop", "aparecer": "pop", "romper": "crack", "andar": None, "brillar": "magia",
    "celebrar": "aplausos", "caer": "whoosh", "texto": "pop", "flash": "whoosh", "confeti": "ding", "llorar": "fail",
    "sacudir": "crack", "dibujar": "tic", "desaparecer": "whoosh", "crecer": "pop", "girar": "whoosh", "contar": "tic",
}


def mezclar(pistas_voz, efectos, duracion: float, salida: Path, musica: Path | None = None, vol_musica=0.10):
    """pistas_voz: [(inicio_s, array)]; efectos: [(inicio_s, nombre)]."""
    n = int(duracion * SR) + SR
    mix = np.zeros(n, dtype=np.float32)
    voz_on = np.zeros(n, dtype=np.float32)
    for ini, a in pistas_voz:
        i = int(ini * SR)
        m = min(len(a), n - i)
        if m > 0:
            mix[i:i + m] += a[:m]
            voz_on[i:i + m] = 1
    cache = {}
    for ini, nombre in efectos:
        if not nombre:
            continue
        s = cache.setdefault(nombre, _sfx(nombre).astype(np.float32))
        i = int(ini * SR)
        m = min(len(s), n - i)
        if m > 0:
            mix[i:i + m] += s[:m] * 0.55
    if musica and musica.exists():
        mu = leer_audio(musica)
        if len(mu):
            rep = np.tile(mu, int(math.ceil(n / len(mu))))[:n]
            # baja la música mientras se habla (suavizado de ~0,3 s)
            k = int(0.3 * SR)
            env = np.convolve(voz_on, np.ones(k) / k, mode="same")
            gan = vol_musica * (1 - 0.55 * env)
            fade = np.ones(n, dtype=np.float32)
            f = int(1.0 * SR)
            fade[-f:] = np.linspace(1, 0, f)
            mix += rep * gan * fade
    pico = np.max(np.abs(mix)) if len(mix) else 1
    if pico > 0.98:
        mix *= 0.98 / pico
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(salida), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def musica_aleatoria(semilla: str) -> Path | None:
    pistas = sorted(p for p in (ASSETS / "musica").glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg"))
    if not pistas:
        return None
    return random.Random(semilla).choice(pistas)
