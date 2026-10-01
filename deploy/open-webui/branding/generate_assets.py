"""Regenerate original Corvus artwork from repository-native drawing primitives.

The SVG and raster icons share the polygon below. Splash text uses the system
DejaVu Sans font as a rasterization input; no font software is redistributed.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parent / "assets"
BIRD = [(110, 320), (190, 235), (250, 195), (320, 105), (367, 120),
        (388, 153), (450, 170), (390, 190), (363, 266), (294, 322),
        (230, 340), (185, 395), (193, 340)]
LIGHT = "#f4f0e7"
DARK = "#171a21"


def icon(size, dark=False):
    image = Image.new("RGB", (1024, 1024), DARK if dark else LIGHT)
    draw = ImageDraw.Draw(image)
    points = [(x * 2, y * 2) for x, y in BIRD]
    draw.polygon(points, fill=LIGHT if dark else DARK)
    draw.ellipse((710, 281, 722, 293), fill=DARK if dark else LIGHT)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    polygon = " ".join(f"{x},{y}" for x, y in BIRD)
    (ROOT / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
        '<title>Corvus</title>'
        f'<rect width="512" height="512" rx="112" fill="{LIGHT}"/>'
        f'<polygon points="{polygon}" fill="{DARK}"/>'
        f'<circle cx="358" cy="144" r="3" fill="{LIGHT}"/></svg>\n'
    )
    for name, size, dark in [
        ("favicon.png", 500, False), ("favicon-dark.png", 500, True),
        ("favicon-96x96.png", 96, False), ("logo.png", 500, False),
        ("apple-touch-icon.png", 180, False),
        ("web-app-manifest-192x192.png", 192, False),
        ("web-app-manifest-512x512.png", 512, False),
    ]:
        icon(size, dark).save(ROOT / name, optimize=False)
    icon(256).save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 64)
    for dark in [False, True]:
        image = icon(500, dark)
        draw = ImageDraw.Draw(image)
        draw.text((250, 445), "Corvus", font=font, anchor="mm", fill=LIGHT if dark else DARK)
        image.save(ROOT / ("splash-dark.png" if dark else "splash.png"), optimize=False)


if __name__ == "__main__":
    main()
