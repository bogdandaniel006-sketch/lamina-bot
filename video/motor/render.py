"""Renderizado: dibuja los fotogramas en paralelo (todos los núcleos) y los codifica con la gráfica."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import skia

from . import audio
from .escena import Video
from .util import FPS, H, W

# ------------------------------------------------------------------ codificador (GPU si hay)
CODIFICADORES = [
    ("h264_nvenc", ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "20", "-b:v", "0"], "NVIDIA"),
    ("h264_amf", ["-c:v", "h264_amf", "-quality", "quality", "-rc", "cqp", "-qp_i", "20", "-qp_p", "22"], "AMD"),
    ("h264_qsv", ["-c:v", "h264_qsv", "-global_quality", "21"], "Intel"),
    ("h264_videotoolbox", ["-c:v", "h264_videotoolbox", "-b:v", "12M"], "Mac"),
    ("libx264", ["-c:v", "libx264", "-preset", "medium", "-crf", "19"], "CPU"),
]


def elegir_codificador(forzar: str | None = None):
    ff = audio.ffmpeg_exe()
    for nombre, args, quien in CODIFICADORES:
        if forzar and nombre != forzar:
            continue
        prueba = [ff, "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1", "-frames:v", "2",
                  *args, "-f", "null", "-"]
        try:
            if subprocess.run(prueba, capture_output=True, timeout=20).returncode == 0:
                return nombre, args, quien
        except Exception:
            pass
    return CODIFICADORES[-1]


# ------------------------------------------------------------------ trabajo de cada núcleo
_V: Video | None = None
_S = None
_ESCALA = 1.0


def _init(historia, tiempos, escala):
    global _V, _S, _ESCALA
    _V = Video(historia, tiempos)
    _ESCALA = escala
    info = skia.ImageInfo.Make(int(W * escala), int(H * escala), skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)
    _S = skia.Surface.MakeRaster(info)


def _frame(i: int) -> bytes:
    cv = _S.getCanvas()
    cv.clear(0xFF000000)
    cv.save()
    cv.scale(_ESCALA, _ESCALA)
    _V.dibujar(cv, i / FPS)
    cv.restore()
    return _S.makeImageSnapshot().tobytes()


# ------------------------------------------------------------------ preparar tiempos (voz)
def preparar_tiempos(historia: dict, sin_voz: bool):
    voz = historia.get("voz", "es-ES-AlvaroNeural")
    vel = historia.get("velocidad", "+8%")
    tiempos, pistas = [], []
    t = 0.0
    for i, e in enumerate(historia["escenas"]):
        txt = e.get("narracion", "")
        a, palabras, dur = audio.narrar(txt, voz, vel, sin_voz)
        pausa = e.get("pausa", 0.25)
        dur_esc = max(float(e.get("duracion_min", 1.2)), dur + pausa)
        tiempos.append({"dur": dur_esc, "palabras": [list(p) for p in palabras]})
        if a is not None:
            pistas.append((t, a))
        t += dur_esc
        print(f"  escena {i + 1:>2}: {dur_esc:4.1f} s  «{txt[:60]}{'…' if len(txt) > 60 else ''}»")
    return tiempos, pistas, t


def renderizar(historia: dict, salida: Path, *, sin_voz=False, borrador=False, nucleos=None, codificador=None,
               musica: Path | None = None):
    inicio = time.time()
    print("🎙️  Voz y tiempos…")
    tiempos, pistas, dur = preparar_tiempos(historia, sin_voz)
    video = Video(historia, tiempos)
    salida.parent.mkdir(parents=True, exist_ok=True)

    print("🔊 Mezclando audio…")
    wav = salida.with_suffix(".wav")
    if musica is None and historia.get("musica", True):
        musica = audio.musica_aleatoria(historia.get("titulo", ""))
    audio.mezclar(pistas, video.efectos_sonido(), dur, wav, musica, historia.get("volumen_musica", 0.10))

    escala = 0.5 if borrador else 1.0
    w, h = int(W * escala), int(H * escala)
    nombre, args, quien = elegir_codificador(codificador)
    total = int(dur * FPS)
    nucleos = nucleos or max(1, (os.cpu_count() or 2) - 1)
    print(f"🎬 {total} fotogramas ({dur:.1f} s) a {w}x{h} · {nucleos} núcleos · codificador {nombre} ({quien})")

    cmd = [audio.ffmpeg_exe(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w}x{h}",
           "-r", str(FPS), "-i", "-", "-i", str(wav), *args, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", str(salida)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    ctx = mp.get_context("spawn")
    with ctx.Pool(nucleos, initializer=_init, initargs=(historia, tiempos, escala)) as pool:
        for k, datos in enumerate(pool.imap(_frame, range(total), chunksize=4)):
            ff.stdin.write(datos)
            if k % FPS == 0 or k == total - 1:
                pct = (k + 1) / total
                print(f"\r   {'█' * int(pct * 30):<30} {pct * 100:5.1f}%  ({time.time() - inicio:4.0f} s)", end="",
                      flush=True)
    ff.stdin.close()
    ff.wait()
    print()
    wav.unlink(missing_ok=True)
    if ff.returncode != 0:
        raise SystemExit("ffmpeg ha fallado al codificar el vídeo.")
    print(f"✅ {salida}  ({time.time() - inicio:.0f} s)")
    return salida


def fotograma(historia: dict, t: float, salida: Path, sin_voz=True):
    """Guarda un PNG de un instante concreto (para revisar una escena sin renderizar todo)."""
    tiempos, _, _ = preparar_tiempos(historia, sin_voz)
    _init(historia, tiempos, 1.0)
    cv = _S.getCanvas()
    cv.clear(0xFF000000)
    _V.dibujar(cv, t)
    _S.makeImageSnapshot().save(str(salida), skia.kPNG)
    return salida
