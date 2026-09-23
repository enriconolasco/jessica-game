from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "visual-direction-v0.1"
FONT_DIR = OUT / "font"
SPRITE_DIR = OUT / "sprites"


def _trim_alpha(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    box = alpha.getbbox()
    if box is None:
        raise ValueError("Imagem sem conteúdo visível")
    return rgba.crop(box)


def _normalize_sprite(source: Path, stem: str, logical_size: int) -> None:
    image = _trim_alpha(Image.open(source))
    padding = 3 if logical_size == 48 else 2
    inner = logical_size - padding * 2
    scale = min(inner / image.width, inner / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    reduced = image.resize(size, Image.Resampling.BOX)
    reduced = reduced.quantize(
        colors=18,
        method=Image.Quantize.FASTOCTREE,
        dither=Image.Dither.NONE,
    ).convert("RGBA")
    canvas = Image.new("RGBA", (logical_size, logical_size), (0, 0, 0, 0))
    x = (logical_size - reduced.width) // 2
    y = logical_size - padding - reduced.height
    canvas.alpha_composite(reduced, (x, y))
    canvas.save(SPRITE_DIR / f"{stem}-{logical_size}.png")
    preview = canvas.resize((logical_size * 8, logical_size * 8), Image.Resampling.NEAREST)
    preview.save(SPRITE_DIR / f"{stem}-{logical_size}-preview.png")
    shutil.copy2(source, SPRITE_DIR / f"{stem}-master.png")


def _build_font(source_font: Path) -> None:
    sys.path.insert(0, str(ROOT / "vendor" / "font-build"))
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.ttLib import TTFont

    chars = "".join(chr(i) for i in range(32, 127))
    chars += "".join(chr(i) for i in range(160, 256))
    chars += "€–—‘’“”•…←↑→↓"
    chars = "".join(dict.fromkeys(chars))
    pil_font = ImageFont.truetype(str(source_font), 42)
    pixel_unit = 22
    ascender, descender = 820, -220

    glyph_order = [".notdef"]
    cmap: dict[int, str] = {}
    glyphs = {}
    metrics = {}

    pen = TTGlyphPen(None)
    pen.moveTo((80, 0)); pen.lineTo((480, 0)); pen.lineTo((480, 700)); pen.lineTo((80, 700)); pen.closePath()
    pen.moveTo((145, 65)); pen.lineTo((145, 635)); pen.lineTo((415, 635)); pen.lineTo((415, 65)); pen.closePath()
    glyphs[".notdef"] = pen.glyph()
    metrics[".notdef"] = (560, 80)

    for cp, char in ((ord(c), c) for c in chars):
        name = f"uni{cp:04X}"
        glyph_order.append(name)
        cmap[cp] = name
        if char == " ":
            glyphs[name] = TTGlyphPen(None).glyph()
            metrics[name] = (300, 0)
            continue

        left, top, right, bottom = pil_font.getbbox(char, anchor="ls")
        width = max(1, right - left)
        height = max(1, bottom - top)
        mask = Image.new("L", (width + 8, height + 8), 0)
        draw = ImageDraw.Draw(mask)
        baseline_y = 4 - top
        draw.text((4 - left, baseline_y), char, fill=255, font=pil_font, anchor="ls")
        # A limiar preserva o aspecto caligráfico, mas força uma malha de pixels inequívoca.
        px = mask.load()
        pen = TTGlyphPen(None)
        for y in range(mask.height):
            for x in range(mask.width):
                if px[x, y] < 112:
                    continue
                x0 = 45 + x * pixel_unit
                y0 = (baseline_y - y) * pixel_unit
                pen.moveTo((x0, y0))
                pen.lineTo((x0 + pixel_unit, y0))
                pen.lineTo((x0 + pixel_unit, y0 + pixel_unit))
                pen.lineTo((x0, y0 + pixel_unit))
                pen.closePath()
        glyphs[name] = pen.glyph()
        advance = max(260, round(pil_font.getlength(char) * pixel_unit) + 90)
        metrics[name] = (advance, 45)

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=ascender, descent=descender)
    fb.setupOS2(
        sTypoAscender=ascender,
        sTypoDescender=descender,
        usWinAscent=ascender,
        usWinDescent=abs(descender),
        sxHeight=470,
        sCapHeight=700,
    )
    fb.setupNameTable({
        "familyName": "Jessica Caligrafica Pixel",
        "styleName": "Display",
        "uniqueFontIdentifier": "JessicaCaligraficaPixel-Display-v0.1",
        "fullName": "Jessica Caligrafica Pixel Display",
        "psName": "JessicaCaligraficaPixel-Display",
        "version": "Version 0.1",
        "description": "Fonte display pixelada provisoria para o jogo Jessica.",
    })
    fb.setupPost(italicAngle=-10)
    fb.setupMaxp()
    ttf_path = FONT_DIR / "JessicaCaligraficaPixel-Display-v0.1.ttf"
    fb.save(ttf_path)

    webfont = TTFont(ttf_path)
    webfont.flavor = "woff2"
    webfont.save(FONT_DIR / "JessicaCaligraficaPixel-Display-v0.1.woff2")

    preview_font = ImageFont.truetype(str(ttf_path), 72)
    preview = Image.new("RGB", (1600, 900), "#071a25")
    draw = ImageDraw.Draw(preview)
    lines = [
        "JÉSSICA",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
        "abcdefghijklmnopqrstuvwxyz",
        "Á À Â Ã É Ê Í Ó Ô Õ Ú Ç",
        "0123456789  Vida 4/6",
        "Artefatos  Resistência",
    ]
    y = 60
    for i, line in enumerate(lines):
        font = ImageFont.truetype(str(ttf_path), 132 if i == 0 else 56)
        draw.text((70, y), line, font=font, fill="#efd49a")
        y += 180 if i == 0 else 112
    preview.save(FONT_DIR / "JessicaCaligraficaPixel-Display-v0.1-specimen.png")

    loaded = TTFont(ttf_path)
    missing = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÁÀÂÃÉÊÍÓÔÕÚÇáàâãéêíóôõúç0123456789" if ord(c) not in loaded.getBestCmap()]
    if missing:
        raise RuntimeError(f"Glifos ausentes: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--orc", type=Path, required=True)
    parser.add_argument("--dwarf", type=Path, required=True)
    parser.add_argument("--ori", type=Path, required=True)
    parser.add_argument("--orc-icon", type=Path, required=True)
    parser.add_argument("--source-font", type=Path, required=True)
    args = parser.parse_args()

    FONT_DIR.mkdir(parents=True, exist_ok=True)
    SPRITE_DIR.mkdir(parents=True, exist_ok=True)
    _normalize_sprite(args.orc, "orc-troop", 48)
    _normalize_sprite(args.dwarf, "dwarf-troop", 48)
    _normalize_sprite(args.ori, "ori-hero", 48)
    _normalize_sprite(args.orc_icon, "orc-face-icon", 32)
    _build_font(args.source_font)


if __name__ == "__main__":
    main()
