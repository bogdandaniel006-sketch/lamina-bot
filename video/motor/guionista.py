"""Escribe historias nuevas con Gemini en el formato JSON que entiende el motor."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

from .escena import ACCIONES_OBJETO, ACCIONES_PERSONAJE, BRAZOS, EFECTOS
from .fondos import FONDOS
from .objetos import OBJETOS
from .personajes import CARAS, PELOS
from .util import RAIZ

HISTORIAS = RAIZ / "historias"

REPARTO_FIJO = {
    "lucia": {
        "color": "#ff6b6b",
        "pelo": "coleta",
        "pelo_color": "#4a2f20",
        "piel": "media"
    },
    "pablo": {
        "color": "#4dabf7",
        "pelo": "pincho",
        "pelo_color": "#1f1f2e",
        "gafas": True,
        "piel": "clara",
        "ojos_color": "#2f6fb3"
    },
    "marta": {
        "color": "#51cf66",
        "pelo": "melena",
        "pelo_color": "#c98b3a",
        "piel": "morena",
        "ojos_color": "#3a7d44"
    },
    "dani": {
        "color": "#845ef7",
        "pelo": "flequillo",
        "pelo_color": "#4a2f20",
        "piel": "clara"
    },
    "profe": {
        "color": "#495057",
        "pelo": "calvo",
        "pelo_color": "#9aa0a6",
        "gafas": True,
        "bigote": True,
        "altura": 1.1,
        "piel": "rosada"
    }
}


def _clave_gemini() -> str:
    k = os.getenv("GEMINI_API_KEY", "")
    env = RAIZ / ".env"
    if not k and env.exists():
        for ln in env.read_text(encoding="utf-8").splitlines():
            if ln.strip().startswith("GEMINI_API_KEY="):
                k = ln.split("=", 1)[1].strip().strip('"')
    if not k:
        raise SystemExit("Falta GEMINI_API_KEY: ponla en el archivo .env (ver LEEME.md).")
    return k


def _previas(n=12):
    titulos = []
    for p in sorted(HISTORIAS.glob("*.json"))[-n:]:
        try:
            titulos.append(json.loads(p.read_text(encoding="utf-8")).get("titulo", p.stem))
        except Exception:
            pass
    return titulos


def prompt(idea: str | None) -> str:
    ejemplo = (HISTORIAS / "ejemplo_compas_roto.json").read_text(encoding="utf-8")
    previas = "\n".join(f"- {t}" for t in _previas()) or "(ninguna)"
    return f"""Eres guionista de vídeos cortos de TikTok (vertical, 40-60 s) para @danidemiguel_, que promociona
danidemiguel.com: una web GRATIS para practicar láminas y ejercicios de Dibujo Técnico de 2º de Bachillerato y PAU
en el ordenador, sin imprimir, sin compás ni reglas.

Estilo: animación 2D de muñecos de cabeza redonda con voz en off de narrador contando una historia inventada,
graciosa y con giro, como los vídeos de curiosidades de TikTok. Español de España, frases cortas y con ritmo,
tono de estudiante. Nada de lenguaje de anuncio.

ESTRUCTURA
1. Gancho en la primera frase (menos de 3 s) que haga quedarse: misterio, desastre o situación absurda.
2. Problema que se va complicando (2-4 escenas), con humor de 2º de Bachillerato.
3. Giro: alguien descubre "una web" mágica (danidemiguel.com) que lo soluciona.
4. Final feliz o remate gracioso. NO escribas la escena de cierre con la llamada a la acción: se añade sola.
Total: 7-11 escenas, cada "narracion" de 6 a 22 palabras. Unas 110-150 palabras en total.
Menciona "danidemiguel.com" como mucho una vez en la historia.

Historias ya hechas (NO repitas la idea):
{previas}

{"IDEA PEDIDA: " + idea if idea else "Inventa tú la idea."}

FORMATO: devuelve SOLO un JSON como el del ejemplo, usando únicamente este vocabulario:
- fondo: {", ".join(FONDOS)}
- personajes del reparto (usa 2-4; puedes añadir alguno nuevo con color/pelo propios): {json.dumps(REPARTO_FIJO, ensure_ascii=False)}
  pelo: {", ".join(PELOS)}
- actores[].cara: {", ".join(CARAS)} · actores[].brazos: {", ".join(BRAZOS)}
- actores[].x de 0.12 a 0.88 (separados al menos 0.25), "mira": "izquierda"/"derecha", "entra": "pop"/"izquierda"/"derecha"
- objetos[].tipo: {", ".join(OBJETOS)}; x, y (0-1; el suelo está en y≈0.74, la pared por encima de 0.6), escala (0.4-1.6),
  "capa": "detras" para cosas en la pared; texto/nota en pizarra, cartel, examen, bocadillo, calendario.
  Los objetos sobre la mesa o en la mano van a y≈0.55-0.65 y escala 0.5-0.8.
- eventos[]: {{"quien": id de actor u objeto (o nada para efectos), "hace": acción, "palabra": palabra de la narración
  en la que ocurre (o "momento": 0-1)}}.
  acciones de personaje: {", ".join(sorted(ACCIONES_PERSONAJE))} ("andar"/"salir" llevan "a": x destino; "cara" lleva "cara")
  acciones de objeto: {", ".join(sorted(ACCIONES_OBJETO))}
  efectos: {", ".join(sorted(EFECTOS))} ("texto" lleva "texto": onomatopeya corta como "¡CRACK!", y x,y)
- camara: zoom_in, zoom_out, paneo_izq, paneo_der, enfoque (con "foco": id), fijo · transicion: corte, flash
- destacar: 1-2 palabras clave de la narración que saldrán en amarillo.
Cada escena debe tener movimiento: al menos 1-3 eventos repartidos en palabras distintas.

EJEMPLO:
{ejemplo}
"""


def _json(texto: str) -> dict:
    texto = texto.strip()
    m = re.search(r"\{.*\}", texto, re.S)
    return json.loads(m.group(0) if m else texto)


def limpiar(h: dict) -> dict:
    """Quita lo que el motor no entiende para que nunca falle el renderizado."""
    h.setdefault("reparto", {})
    for e in h.get("escenas", []):
        for a in e.get("actores", []):
            a["id"] = str(a.get("id", "")).lower()
            if a["id"] not in h["reparto"]:
                h["reparto"][a["id"]] = REPARTO_FIJO.get(a["id"], {"color": "#20c997", "pelo": "corto"})
            if a.get("cara") not in CARAS:
                a.pop("cara", None)
            if a.get("brazos") not in BRAZOS:
                a.pop("brazos", None)
        e["objetos"] = [o for o in e.get("objetos", []) if o.get("tipo") in OBJETOS]
        validas = ACCIONES_PERSONAJE | ACCIONES_OBJETO | EFECTOS
        for ev in e.get("eventos", []):
            if isinstance(ev.get("quien"), str) and ev["quien"].lower() in h["reparto"]:
                ev["quien"] = ev["quien"].lower()
        e["eventos"] = [ev for ev in e.get("eventos", []) if ev.get("hace") in validas]
        if e.get("fondo") not in FONDOS and not str(e.get("fondo", "")).lower().endswith((".jpg", ".png")):
            e["fondo"] = "aula"
    return h


def escribir(idea: str | None = None, modelo: str | None = None) -> Path:
    from google import genai
    from google.genai import types
    cli = genai.Client(api_key=_clave_gemini())
    candidatos = [modelo] if modelo else []
    try:
        nombres = [m.name.split("/")[-1] for m in cli.models.list()]
        flash = [n for n in nombres if n.startswith("gemini") and "flash" in n and not any(
            b in n for b in ("image", "tts", "lite", "live", "audio", "embedding", "exp"))]
        flash.sort(key=lambda n: (float((re.findall(r"\d+(?:\.\d+)?", n) or ["0"])[0]), "preview" not in n), reverse=True)
        candidatos += flash[:3]
    except Exception:
        pass
    candidatos += ["gemini-2.5-flash"]
    ultimo = None
    for m in dict.fromkeys(c for c in candidatos if c):
        try:
            r = cli.models.generate_content(model=m, contents=prompt(idea), config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=1.0))
            h = limpiar(_json(r.text))
            break
        except Exception as e:
            ultimo = e
            print(f"  ⚠ {m}: {e}")
    else:
        raise SystemExit(f"Gemini no ha podido escribir la historia: {ultimo}")
    HISTORIAS.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", h.get("titulo", "historia").lower())[:40].strip("_")
    ruta = HISTORIAS / f"{datetime.now():%Y%m%d-%H%M}_{slug}.json"
    ruta.write_text(json.dumps(h, ensure_ascii=False, indent=2), encoding="utf-8")
    return ruta
