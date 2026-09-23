"""Build the small, editable vector map markers for the twelve peoples."""

from pathlib import Path
import html


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "visual-direction-v0.2" / "icons"


def path(d, color, stroke=None, width=1):
    border = f' stroke="{stroke}" stroke-width="{width}" stroke-linejoin="round"' if stroke else ""
    return f'<path d="{d}" fill="{color}"{border}/>'


def circle(x, y, r, color):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'


def line(d, color, width=1):
    return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'


INK = "#18202b"
LIGHT = "#f2e6c7"
GOLD = "#dbb66a"


def portrait(name, accent, shapes):
    title = html.escape(name)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32" role="img" aria-label="{title}">
<title>{title}</title>
<rect x="1" y="1" width="30" height="30" rx="6" fill="{INK}" stroke="{accent}" stroke-width="2"/>
{shapes}
</svg>
'''


ICONS = {
    "humanos": ("Humanos — mulher negra", "#c7995c", "".join([
        path("M5 25V11C5 5 10 3 16 3S27 5 27 11V25Z", "#241821"),
        path("M8 22V12Q8 6 16 6T24 12V22Q22 27 16 27T8 22Z", "#985b3d"),
        path("M7 14Q5 10 9 7Q13 3 19 6Q25 6 25 14L22 12L20 9Q16 12 10 11Z", "#241821"),
        path("M5 27Q9 23 12 23H20Q23 23 27 27V29H5Z", "#526f9d"),
        line("M11 16H14 M18 16H21 M14 22Q16 23 18 22", "#231923", 1.5),
        circle(12, 13, 1, GOLD), circle(20, 13, 1, GOLD),
    ])),
    "anoes": ("Anões", "#cda15e", "".join([
        path("M5 12L7 7L11 5H21L25 7L27 12V16H5Z", "#697b88"),
        path("M7 13H25V17H7Z", "#b8c5c7"),
        path("M9 15H23V22L20 25H12L9 22Z", "#c18a61"),
        path("M8 19L11 20L13 18L16 20L19 18L21 20L24 19L22 25L18 29H14L10 25Z", "#a95232"),
        line("M11 17H14 M18 17H21 M15 24H17", INK, 1.5),
        path("M15 8H17V13H15Z", GOLD),
    ])),
    "orcs": ("Orcs verdes", "#88a357", "".join([
        path("M7 10L3 8L4 17L8 18L10 24L16 27L22 24L24 18L28 17L29 8L25 10Q22 5 16 5T7 10Z", "#5c803d"),
        path("M8 16L5 12L5 16L9 19ZM24 16L27 12L27 16L23 19Z", "#94aa58"),
        path("M9 12Q16 8 23 12L22 16H10Z", "#354d31"),
        line("M10 16L14 17 M18 17L22 16", "#ead69a", 1.7),
        path("M10 23L12 19L14 24ZM18 24L20 19L22 23Z", LIGHT),
        line("M13 24H19", "#2c392c", 1.5),
    ])),
    "fadas": ("Fadas — elfa loira", "#b7d978", "".join([
        path("M6 19L2 12L9 14L10 8Q16 2 22 8L23 14L30 12L26 19L23 26H9Z", "#e7b648"),
        path("M8 17L3 14L9 21ZM24 17L29 14L23 21Z", "#e7b389"),
        path("M10 11Q16 8 22 11V20Q21 26 16 27Q11 26 10 20Z", "#e9ae83"),
        path("M9 13L10 8L14 6H20L23 10L22 15L19 10L15 12Z", "#f2cf68"),
        circle(13, 17, 1.3, "#358d60"), circle(19, 17, 1.3, "#358d60"),
        line("M14 22Q16 23 18 22", "#835a4a"),
    ])),
    "vampiros": ("Vampiros", "#ad6178", "".join([
        path("M5 28L8 19L9 9Q12 4 16 4T23 9L24 19L27 28Z", "#332537"),
        path("M10 13Q16 10 22 13V22Q19 27 16 27T10 22Z", "#d4c6bd"),
        path("M8 14L10 7L16 9L22 7L24 14L20 11L16 14L12 11Z", "#24202f"),
        line("M11 17H14 M18 17H21", "#ae495e", 1.6),
        path("M12 22L14 24L15 22ZM17 22L18 24L20 22Z", LIGHT),
        path("M5 29L11 25H21L27 29Z", "#733244"),
    ])),
    "lobisomens": ("Lobisomens", "#a08265", "".join([
        path("M4 3L11 7Q16 4 21 7L28 3L27 17L24 23L19 28H13L8 23L5 17Z", "#755e4e"),
        path("M7 8L11 11L8 14ZM25 8L21 11L24 14Z", "#c09a75"),
        path("M8 15L13 13L16 17L19 13L24 15L22 22L16 27L10 22Z", "#a28669"),
        line("M9 16L14 18 M18 18L23 16", "#e5bd6c", 1.7),
        path("M13 21H19L16 24Z", "#2b2b2b"),
        path("M11 23L13 25L14 22ZM18 22L19 25L21 23Z", LIGHT),
    ])),
    "gigantes": ("Gigantes", "#a6a087", "".join([
        path("M5 11L9 5H23L27 11V23L23 28H9L5 23Z", "#7c786a"),
        path("M7 11L11 7H21L25 11V16H7Z", "#a69d88"),
        path("M9 17H14V20H9ZM18 17H23V20H18Z", INK),
        path("M14 19H18L20 24H12Z", "#b7ab92"),
        line("M10 25H22", "#443f3c", 2),
        line("M8 12L12 14 M20 14L24 12", "#635f56"),
    ])),
    "mortos-vivos": ("Mortos-vivos", "#c7c4a4", "".join([
        path("M8 5L13 3H19L24 5L27 11V19L22 25V29H10V25L5 19V11Z", "#ddd8bf"),
        path("M7 13L13 11L15 18L10 19ZM25 13L19 11L17 18L22 19Z", "#343742"),
        path("M14 19L18 19L16 23Z", "#65666c"),
        path("M10 24H22V27H10Z", "#eee8d1"),
        line("M13 24V27 M16 24V27 M19 24V27", "#62636a"),
        circle(11, 15, 1, "#76a2a7"), circle(21, 15, 1, "#76a2a7"),
    ])),
    "filhos-floresta": ("Filhos da floresta", "#81ad6d", "".join([
        path("M16 2L19 8L25 5L23 12L29 14L23 18L25 25L18 23L16 29L14 23L7 25L9 18L3 14L9 12L7 5L13 8Z", "#4e8751"),
        path("M11 9Q16 6 21 9L23 17L19 24H13L9 17Z", "#806044"),
        path("M15 9H17V25H15Z", "#a1784b"),
        circle(12, 16, 1.5, "#c6dc83"), circle(20, 16, 1.5, "#c6dc83"),
        line("M12 22Q16 24 20 22", "#435f3a"),
    ])),
    "gnomos-duendes": ("Gnomos e duendes", "#a6aa7c", "".join([
        path("M5 13L11 5L22 5L27 13L24 15H8Z", "#754868"),
        path("M8 14L3 12L5 20L9 20ZM24 14L29 12L27 20L23 20Z", "#9dac72"),
        path("M9 14H23V22L19 27H13L9 22Z", "#a6b47b"),
        circle(12, 18, 2, LIGHT), circle(20, 18, 2, LIGHT),
        circle(12, 18, 0.9, INK), circle(20, 18, 0.9, INK),
        path("M14 20L19 20L18 23H14Z", "#c88d56"),
        line("M13 25Q16 27 20 24", "#485a3e"),
    ])),
    "dragoes": ("Dragões", "#61a9a5", "".join([
        path("M3 5L10 10L16 5L22 10L29 5L26 15L23 24L16 29L9 24L6 15Z", "#358485"),
        path("M6 8L10 14L5 16ZM26 8L22 14L27 16Z", "#7cbbb0"),
        path("M10 16L16 13L22 16L23 22L16 27L9 22Z", "#79aaa0"),
        line("M9 17L14 19 M18 19L23 17", "#e9a852", 1.7),
        path("M13 22L16 19L19 22L17 25H15Z", "#2a565e"),
        circle(10, 8, 1, GOLD), circle(22, 8, 1, GOLD),
    ])),
    "demonios": ("Demônios", "#c67065", "".join([
        path("M4 4L11 10L16 7L21 10L28 4L26 17L23 25L16 28L9 25L6 17Z", "#a63d45"),
        path("M4 4L7 13L11 10ZM28 4L25 13L21 10Z", "#e2bd8c"),
        path("M10 12Q16 9 22 12L24 21L20 26H12L8 21Z", "#b94a4e"),
        line("M10 17L14 19 M18 19L22 17", "#f1bb6b", 1.8),
        path("M13 23L16 21L19 23L17 25H15Z", "#5f2633"),
        line("M7 27L11 25 M21 25L25 27", "#6b2834", 2),
    ])),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for key, (name, accent, shapes) in ICONS.items():
        (OUT / f"people-{key}-32.svg").write_text(portrait(name, accent, shapes), encoding="utf-8")
    symbols = []
    for index, (key, (name, _, _)) in enumerate(ICONS.items()):
        x, y = (index % 4) * 132, (index // 4) * 144
        symbols.append(f'<image x="{x + 20}" y="{y + 12}" width="96" height="96" href="people-{key}-32.svg"/>')
        symbols.append(f'<text x="{x + 66}" y="{y + 126}" text-anchor="middle" fill="{LIGHT}" font-size="11" font-family="sans-serif">{html.escape(name)}</text>')
    sheet = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 528 432" width="528" height="432"><rect width="528" height="432" fill="#111a26"/>\n' + "\n".join(symbols) + "</svg>\n"
    (OUT / "contact-sheet.svg").write_text(sheet, encoding="utf-8")


if __name__ == "__main__":
    main()
