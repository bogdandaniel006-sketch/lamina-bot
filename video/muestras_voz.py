#!/usr/bin/env python3
"""Genera una muestra de cada voz en español de Microsoft (Edge TTS) para elegir la del canal.

Uso: python video/muestras_voz.py [carpeta_salida]
Crea voz_<nombre>.mp3 por cada voz y todas_las_voces.mp3 con todas seguidas.
"""
import asyncio
import subprocess
import sys
from pathlib import Path

import edge_tts

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motor.audio import ffmpeg_exe  # noqa: E402

TEXTO = ("Hola, soy {n}. ¿Por qué casi todas las tapas de alcantarilla son redondas? "
         "No es por estética. Es por seguridad. Y la respuesta es pura geometría.")


async def main(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    voces = [v for v in await edge_tts.list_voices() if v["Locale"].startswith("es-ES")]
    voces += [v for v in await edge_tts.list_voices() if v["Locale"] in ("es-MX",)][:2]
    archivos = []
    for v in voces:
        corto = v["ShortName"]
        nombre = corto.split("-")[-1].replace("Neural", "").replace("Multilingual", "")
        f = out / f"voz_{corto}.mp3"
        await edge_tts.Communicate(TEXTO.format(n=nombre), corto, rate="+6%").save(str(f))
        archivos.append(f)
        print(f"✅ {corto} ({v.get('Gender')})")
    # todas seguidas, con medio segundo de silencio entre voces
    lista = out / "lista.txt"
    sil = out / "silencio.mp3"
    subprocess.run([ffmpeg_exe(), "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "0.7",
                    "-q:a", "4", str(sil)], check=True)
    lista.write_text("".join(f"file '{a.name}'\nfile '{sil.name}'\n" for a in archivos))
    subprocess.run([ffmpeg_exe(), "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-c:a", "libmp3lame", "-q:a", "3", str(out / "todas_las_voces.mp3")], check=True)
    lista.unlink()
    sil.unlink()


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1] if len(sys.argv) > 1 else "video/salida/voces")))
