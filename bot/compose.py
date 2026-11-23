"""Monta cada slide: foto de fondo 1080x1920 + texto con los estilos de los TikToks de Dani.

Estilos (copiados de los carruseles que mejor han funcionado):
  - "outline": blanco con borde negro (el clásico de TikTok)          -> "Yo haciendo todo sin imprimir..."
  - "black":   negro sin borde, más fino                               -> "Dibujo técnico es muy difícil"
  - "red":     rojo/rosa con borde blanco                              -> "Qué pereza estudiar dibujo técnico"
  - "green":   verde con borde blanco                                  -> "Qué ganas de estudiar dibujo técnico"
  - "pill":    texto blanco dentro de una etiqueta azul redondeada     -> "danidemiguel.com"
Una slide puede llevar varios bloques (p. ej. una "pill" con la web + un "outline" debajo).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "TikTokSans.ttf"
EMOJI_DIR = ROOT / "assets" / "emoji"

W, H = 1080, 1920

STYLES = {
    "outline": dict(fill=(255, 255, 255), stroke=(0, 0, 0), stroke_w=8, weight=700, size=84),
    "black": dict(fill=(17, 17, 17), stroke=None, stroke_w=0, weight=500, size=86),
    "red": dict(fill=(232, 62, 82), stroke=(255, 255, 255), stroke_w=6, weight=700, size=80),
    "green": dict(fill=(64, 186, 70), stroke=(255, 255, 255), stroke_w=6, weight=700, size=80),
    "pill": dict(fill=(255, 255, 255), stroke=None, stroke_w=0, weight=700, size=80, bg=(31, 150, 243)),
}

# Posición vertical del centro del bloque, en fracción de la altura
POSITIONS = {"top": 0.20, "upper": 0.33, "center": 0.50, "lower": 0.68, "bottom": 0.80}


def _font(size: int, weight: int) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONT_PATH), size)
    try:
        f.set_variation_by_axes([36, 100, weight, 0])  # opsz, wdth, wght, slnt
    except Exception:
        pass
    return f


def _emoji_files() -> dict[str, Path]:
    out = {}
    for p in EMOJI_DIR.glob("*.png"):
        seq = "".join(chr(int(h, 16)) for h in p.stem.split("-"))
        out[seq] = p
        out[seq.replace("️", "")] = p
    return out


EMOJI = _emoji_files()
EMOJI_MAXLEN = max((len(k) for k in EMOJI), default=1)


def _tokens(text: str) -> list[tuple[str, str]]:
    """Divide el texto en trozos ('t', texto) y ('e', emoji). Los emojis desconocidos se quitan."""
    toks: list[tuple[str, str]] = []
    i, buf = 0, ""
    while i < len(text):
        hit = None
        for L in range(min(EMOJI_MAXLEN, len(text) - i), 0, -1):
            cand = text[i:i + L]
            if cand in EMOJI:
                hit = cand
                break
        if hit:
            if buf:
                toks.append(("t", buf)); buf = ""
            toks.append(("e", hit)); i += len(hit)
            while i < len(text) and text[i] in "️‍":
                i += 1
            continue
        ch = text[i]
        if ord(ch) > 0x2600 and not ch.isalnum():  # emoji sin imagen o símbolo raro: se omite
            i += 1; continue
        buf += ch; i += 1
    if buf:
        toks.append(("t", buf))
    return toks


def _words(text: str) -> list[list[tuple[str, str]]]:
    """Agrupa tokens en 'palabras' (separadas por espacio) para poder partir líneas."""
    words, cur = [], []
    for kind, val in _tokens(text):
        if kind == "e":
            cur.append((kind, val)); continue
        parts = val.split(" ")
        for j, part in enumerate(parts):
            if j > 0:
                if cur:
                    words.append(cur)
                cur = []
            if part:
                cur.append(("t", part))
    if cur:
        words.append(cur)
    return words


def _word_w(word, font, emoji_px) -> int:
    w = 0
    for kind, val in word:
        w += emoji_px + 6 if kind == "e" else int(font.getlength(val))
    return w


def _wrap(text: str, font, emoji_px: int, max_w: int):
    space = int(font.getlength(" "))
    lines, cur, cur_w = [], [], 0
    for word in _words(text):
        ww = _word_w(word, font, emoji_px)
        add = ww if not cur else cur_w + space + ww
        if cur and add > max_w:
            lines.append((cur, cur_w)); cur, cur_w = [word], ww
        else:
            cur.append(word); cur_w = add
    if cur:
        lines.append((cur, cur_w))
    return lines, space


def _draw_line(img, draw, line, x, y, font, st, emoji_px, space):
    for wi, word in enumerate(line):
        if wi:
            x += space
        for kind, val in word:
            if kind == "t":
                draw.text((x, y), val, font=font, fill=st["fill"],
                          stroke_width=st["stroke_w"], stroke_fill=st["stroke"])
                x += int(font.getlength(val))
            else:
                em = Image.open(EMOJI[val]).convert("RGBA").resize((emoji_px, emoji_px), Image.LANCZOS)
                img.alpha_composite(em, (int(x + 3), int(y + font.size * 0.12)))
                x += emoji_px + 6


def _region_luma(img, cy_frac, h_px=420) -> float:
    y0 = max(0, int(H * cy_frac - h_px / 2)); y1 = min(H, y0 + h_px)
    reg = img.crop((int(W * 0.08), y0, int(W * 0.92), y1)).convert("L").resize((64, 32))
    return sum(reg.getdata()) / (64 * 32)


def draw_block(img: Image.Image, text: str, style: str = "outline", position: str | float = "center"):
    cy_frac = POSITIONS.get(position, 0.5) if isinstance(position, str) else float(position)
    # El texto negro solo se lee sobre fondo claro (papel, láminas). Si el fondo es oscuro, pasa a blanco con borde.
    if style == "black" and _region_luma(img, cy_frac) < 150:
        style = "outline"
    st = STYLES[style]
    size = st["size"]
    max_w = int(W * (0.78 if style == "pill" else 0.86))
    # Reduce la letra si el texto es muy largo (máx. 5 líneas)
    while True:
        font = _font(size, st["weight"])
        emoji_px = int(size * 0.95)
        lines, space = _wrap(text, font, emoji_px, max_w)
        if len(lines) <= 5 or size <= 44:
            break
        size -= 4
    line_h = int(size * 1.18)
    block_h = line_h * len(lines)
    cy = POSITIONS.get(position, 0.5) if isinstance(position, str) else float(position)
    y0 = int(H * cy - block_h / 2)
    draw = ImageDraw.Draw(img)
    if style == "pill":
        bw = max(w for _, w in lines) + 64
        x0 = (W - bw) // 2
        draw.rounded_rectangle([x0, y0 - 18, x0 + bw, y0 + block_h + 14], radius=22, fill=st["bg"])
    for i, (line, lw) in enumerate(lines):
        x = (W - lw) // 2
        _draw_line(img, draw, line, x, y0 + i * line_h, font, st, emoji_px, space)
    return y0, y0 + block_h


def fit_background(path_or_img) -> Image.Image:
    im = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(path_or_img)
    im = ImageOps.exif_transpose(im).convert("RGB")
    return ImageOps.fit(im, (W, H), Image.LANCZOS).convert("RGBA")


def render_slide(background, blocks: list[dict]) -> Image.Image:
    """blocks: [{"text": ..., "style": "outline", "position": "lower"}, ...]"""
    img = fit_background(background)
    for b in blocks:
        draw_block(img, b["text"], b.get("style", "outline"), b.get("position", "center"))
    return img.convert("RGB")


def save_jpeg(img: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "JPEG", quality=92, optimize=True)
