from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "visual-direction-v0.1" / "icons"
S = 16
T = (0, 0, 0, 0)
K = "#17151b"


def canvas():
    image = Image.new("RGBA", (S, S), T)
    return image, ImageDraw.Draw(image)


def humanos():
    im, d = canvas()
    hair = "#241b22"; skin = "#78452f"; light = "#a66543"; indigo = "#4e4b9b"
    d.polygon([(4,1),(11,1),(13,3),(14,7),(13,12),(11,14),(4,14),(2,12),(1,7),(2,3)], fill=K)
    d.polygon([(4,2),(11,2),(13,4),(13,8),(12,8),(12,5),(10,4),(5,4),(3,5),(3,8),(2,8),(2,4)], fill=hair)
    d.polygon([(4,4),(11,4),(12,6),(12,11),(10,13),(5,13),(3,11),(3,6)], fill=skin)
    d.rectangle((3,4,12,5), fill=indigo)
    d.point([(5,7),(10,7)], fill=K)
    d.point([(6,7),(11,7),(7,9)], fill=light)
    d.line((6,11,9,11), fill=K)
    d.point((7,12), fill=light)
    return im


def anoes():
    im, d = canvas()
    steel = "#59616f"; shine = "#aeb8bd"; skin = "#b56d43"; beard = "#a94725"; gold = "#d39b3a"
    d.polygon([(4,1),(11,1),(13,4),(13,7),(11,8),(4,8),(2,7),(2,4)], fill=K)
    d.polygon([(4,2),(11,2),(12,4),(12,6),(3,6),(3,4)], fill=steel)
    d.line((7,2,7,6), fill=shine); d.line((8,2,8,6), fill=K)
    d.point([(4,3),(11,3)], fill=gold)
    d.polygon([(4,6),(11,6),(12,8),(11,10),(4,10),(3,8)], fill=skin)
    d.point([(5,7),(10,7)], fill=K); d.point((8,8), fill=shine)
    d.polygon([(3,9),(5,9),(6,10),(7,9),(8,10),(9,9),(12,9),(11,13),(9,15),(6,15),(4,13)], fill=K)
    d.polygon([(4,9),(6,10),(7,11),(8,10),(10,9),(11,10),(10,13),(8,14),(6,13),(4,11)], fill=beard)
    d.point([(6,11),(9,11),(7,13)], fill=gold)
    return im


def orcs():
    im, d = canvas()
    dark = "#344d27"; green = "#66843b"; light = "#8da44d"; tusk = "#e7d9ad"; clay = "#a6472c"
    d.polygon([(4,2),(11,2),(13,4),(13,5),(15,5),(15,9),(13,10),(12,13),(10,15),(5,15),(3,13),(2,10),(0,9),(0,5),(2,5),(2,4)], fill=K)
    d.rectangle((1,6,3,8), fill=dark); d.rectangle((12,6,14,8), fill=dark)
    d.polygon([(4,3),(11,3),(12,5),(12,11),(10,14),(5,14),(3,11),(3,5)], fill=green)
    d.line((4,5,6,6), fill=dark); d.line((9,6,11,5), fill=dark)
    d.point([(5,7),(10,7)], fill=K); d.point([(6,7),(11,7),(7,9)], fill=light)
    d.line((5,10,10,10), fill=K)
    d.point([(5,11),(10,11)], fill=tusk)
    d.line((6,13,9,13), fill=dark)
    d.point([(3,4),(12,4)], fill=clay)
    return im


def fadas():
    im, d = canvas()
    gold = "#d6a62e"; gold2 = "#ffdd62"; skin = "#d99267"; light = "#f1b48a"; green = "#2fa65a"
    d.polygon([(4,1),(11,1),(13,3),(13,5),(15,6),(15,8),(13,9),(12,14),(10,15),(5,15),(3,14),(2,9),(0,8),(0,6),(2,5),(2,3)], fill=K)
    d.polygon([(4,2),(11,2),(12,4),(12,13),(10,14),(10,5),(5,5),(5,14),(3,13),(3,4)], fill=gold)
    d.point([(4,3),(11,3),(3,6),(12,6)], fill=gold2)
    d.polygon([(1,6),(3,6),(3,8),(1,7)], fill=skin); d.polygon([(12,6),(14,6),(14,7),(12,8)], fill=skin)
    d.polygon([(5,4),(10,4),(11,6),(11,11),(9,13),(6,13),(4,11),(4,6)], fill=light)
    d.point([(5,7),(10,7)], fill=K); d.point([(6,7),(9,7)], fill=green)
    d.point((7,9), fill=skin); d.line((6,11,9,11), fill=K)
    return im


def vampiros():
    im, d = canvas()
    hair = "#251d31"; pale = "#c8b7b4"; shade = "#826b76"; red = "#a83246"; fang = "#f2e8d5"
    d.polygon([(4,1),(11,1),(13,3),(13,11),(11,14),(4,14),(2,11),(2,3)], fill=K)
    d.polygon([(4,2),(11,2),(12,4),(10,3),(8,5),(6,3),(3,4),(3,7),(2,7),(2,3)], fill=hair)
    d.polygon([(4,4),(11,4),(12,6),(12,10),(10,13),(5,13),(3,10),(3,6)], fill=pale)
    d.point([(5,7),(10,7)], fill=red); d.point((7,9), fill=shade)
    d.line((5,11,10,11), fill=K); d.point([(6,12),(9,12)], fill=fang)
    return im


def lobisomens():
    im, d = canvas()
    dark = "#3a302e"; fur = "#665348"; light = "#927760"; amber = "#e1a63b"; fang = "#e6dac1"
    d.polygon([(2,1),(6,3),(9,3),(13,1),(13,6),(15,8),(13,12),(10,15),(5,15),(2,12),(0,8),(2,6)], fill=K)
    d.polygon([(3,3),(6,4),(9,4),(12,3),(12,7),(14,8),(12,11),(9,14),(6,14),(3,11),(1,8),(3,7)], fill=fur)
    d.polygon([(5,5),(10,5),(11,8),(10,10),(9,9),(6,9),(5,10),(4,8)], fill=dark)
    d.point([(5,7),(10,7)], fill=amber)
    d.polygon([(5,10),(10,10),(11,12),(9,14),(6,14),(4,12)], fill=light)
    d.rectangle((7,10,8,11), fill=K); d.point([(5,12),(10,12)], fill=fang)
    return im


def gigantes():
    im, d = canvas()
    stone = "#777064"; shade = "#4c4944"; light = "#aaa08d"; ochre = "#b67a35"; eye = "#ded2b6"
    d.polygon([(3,1),(12,1),(15,4),(15,12),(12,15),(3,15),(0,12),(0,4)], fill=K)
    d.polygon([(3,2),(12,2),(14,5),(14,11),(11,14),(4,14),(1,11),(1,5)], fill=stone)
    d.rectangle((3,4,12,6), fill=shade); d.point([(4,4),(11,4)], fill=ochre)
    d.rectangle((4,7,6,8), fill=K); d.rectangle((9,7,11,8), fill=K)
    d.point([(5,7),(10,7)], fill=eye); d.rectangle((7,8,8,11), fill=light)
    d.line((4,12,11,12), fill=shade); d.point([(5,13),(10,13)], fill=ochre)
    return im


def mortos_vivos():
    im, d = canvas()
    bone = "#d8cfaf"; shade = "#958c73"; light = "#f1ead0"; cold = "#647587"; dark = "#302f35"
    d.polygon([(4,1),(11,1),(14,4),(14,10),(12,12),(11,15),(4,15),(3,12),(1,10),(1,4)], fill=K)
    d.polygon([(4,2),(11,2),(13,4),(13,9),(11,11),(10,13),(5,13),(4,11),(2,9),(2,4)], fill=bone)
    d.polygon([(4,5),(6,5),(7,7),(6,9),(3,8)], fill=dark); d.polygon([(9,5),(11,5),(12,8),(9,9),(8,7)], fill=dark)
    d.point([(5,6),(10,6)], fill=cold); d.rectangle((7,8,8,10), fill=shade)
    d.rectangle((5,11,10,13), fill=light); d.line((6,11,6,13), fill=K); d.line((8,11,8,13), fill=K); d.line((10,11,10,13), fill=K)
    return im


def filhos_floresta():
    im, d = canvas()
    forest = "#24472f"; leaf = "#477a40"; moss = "#79a34f"; bark = "#6b4a31"; glow = "#b7d56d"
    d.polygon([(7,0),(9,3),(13,2),(12,5),(15,7),(12,9),(13,13),(9,12),(7,16),(5,12),(1,13),(2,9),(0,7),(3,5),(2,2),(6,3)], fill=K)
    d.polygon([(7,1),(8,4),(12,3),(10,6),(14,7),(10,8),(12,12),(8,10),(7,14),(6,10),(2,12),(4,8),(1,7),(5,6),(3,3),(6,4)], fill=leaf)
    d.polygon([(5,5),(10,5),(11,8),(9,12),(6,12),(4,8)], fill=bark)
    d.point([(5,7),(10,7)], fill=glow); d.line((7,6,7,11), fill=forest)
    d.point([(6,10),(8,10),(7,3)], fill=moss)
    return im


def gnomos_duendes():
    im, d = canvas()
    hood = "#493050"; skin = "#8e9a55"; light = "#bac66d"; orange = "#c46a2d"; eye = "#e7db9d"
    d.polygon([(5,1),(10,1),(13,4),(13,5),(15,5),(15,9),(13,10),(12,14),(3,14),(2,10),(0,9),(0,5),(2,5),(2,4)], fill=K)
    d.polygon([(5,2),(10,2),(12,4),(11,5),(4,5),(3,4)], fill=hood)
    d.rectangle((1,6,3,8), fill=skin); d.rectangle((12,6,14,8), fill=skin)
    d.polygon([(4,5),(11,5),(12,7),(11,12),(9,13),(5,13),(3,11),(3,7)], fill=skin)
    d.point([(5,7),(10,7)], fill=eye); d.point([(6,7),(9,7)], fill=K)
    d.rectangle((7,8,9,9), fill=light); d.line((6,11,10,10), fill=K)
    d.point([(4,11),(11,11)], fill=orange)
    return im


def dragoes():
    im, d = canvas()
    dark = "#17454a"; teal = "#27747a"; light = "#55a39a"; copper = "#b65f32"; ember = "#f09a3e"
    d.polygon([(2,0),(6,3),(9,3),(13,0),(12,5),(15,7),(13,10),(12,14),(9,16),(6,16),(3,14),(2,10),(0,7),(3,5)], fill=K)
    d.polygon([(3,2),(6,4),(9,4),(12,2),(11,6),(13,7),(11,9),(11,13),(8,15),(7,15),(4,13),(4,9),(2,7),(4,6)], fill=teal)
    d.polygon([(5,5),(10,5),(11,8),(9,9),(6,9),(4,8)], fill=dark)
    d.point([(5,7),(10,7)], fill=ember)
    d.polygon([(5,9),(10,9),(11,12),(9,14),(6,14),(4,12)], fill=light)
    d.point([(6,11),(9,11)], fill=K); d.point([(3,3),(12,3)], fill=copper)
    return im


def demonios():
    im, d = canvas()
    crimson = "#8f2731"; dark = "#4c1d28"; light = "#c54a39"; horn = "#b79a72"; ember = "#f2a13d"
    d.polygon([(1,0),(6,3),(9,3),(14,0),(12,5),(14,7),(13,12),(10,15),(5,15),(2,12),(1,7),(3,5)], fill=K)
    d.polygon([(2,1),(6,4),(5,5),(2,3)], fill=horn); d.polygon([(13,1),(9,4),(10,5),(13,3)], fill=horn)
    d.polygon([(4,4),(11,4),(13,7),(12,12),(9,14),(6,14),(3,12),(2,7)], fill=crimson)
    d.line((4,6,6,7), fill=dark); d.line((9,7,11,6), fill=dark)
    d.point([(5,7),(10,7)], fill=ember); d.rectangle((7,8,8,10), fill=light)
    d.line((5,12,10,12), fill=K); d.point([(3,10),(12,10)], fill=dark)
    return im


def save_icon(name, image):
    path = OUT / f"people-{name}-16.png"
    image.save(path)
    image.resize((256, 256), Image.Resampling.NEAREST).save(OUT / f"people-{name}-16-preview.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    icons = [
        ("humanos", humanos()), ("anoes", anoes()), ("orcs", orcs()), ("fadas", fadas()),
        ("vampiros", vampiros()), ("lobisomens", lobisomens()), ("gigantes", gigantes()),
        ("mortos-vivos", mortos_vivos()), ("filhos-floresta", filhos_floresta()),
        ("gnomos-duendes", gnomos_duendes()), ("dragoes", dragoes()), ("demonios", demonios()),
    ]
    for name, image in icons:
        save_icon(name, image)

    sheet = Image.new("RGBA", (640, 720), "#071820")
    labels = [
        "HUMANOS", "ANÕES", "ORCS", "FADAS", "VAMPIROS", "LOBISOMENS",
        "GIGANTES", "MORTOS-VIVOS", "FILHOS DA FLORESTA", "GNOMOS/DUENDES",
        "DRAGÕES", "DEMÔNIOS",
    ]
    for index, ((_, icon), label) in enumerate(zip(icons, labels)):
        col, row = index % 4, index // 4
        x, y = col * 160 + 16, row * 224 + 24
        sheet.alpha_composite(icon.resize((128, 128), Image.Resampling.NEAREST), (x, y))
        ImageDraw.Draw(sheet).text((x, y + 148), label, fill="#e9e2cc", font=ImageFont.load_default())
    sheet.save(OUT / "people-icons-all-contact-sheet.png")


if __name__ == "__main__":
    main()
