from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).with_name("flipfocus.ico")

def draw_icon(size: int) -> Image.Image:
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def s(v):
        return int(round(v * size / 64))

    d.rounded_rectangle(
        (s(4), s(4), s(60), s(60)),
        radius=s(15),
        fill=(18, 18, 21, 255),
        outline=(58, 58, 64, 255),
        width=max(1, s(1)),
    )
    d.rounded_rectangle(
        (s(13), s(12), s(51), s(52)),
        radius=s(8),
        fill=(34, 34, 38, 255),
        outline=(72, 72, 79, 255),
        width=max(1, s(1)),
    )
    d.rectangle((s(16), s(31), s(48), s(33)), fill=(7, 7, 9, 230))

    white = (247, 247, 249, 255)
    d.rounded_rectangle((s(23), s(20), s(29), s(45)), radius=s(2), fill=white)
    d.rounded_rectangle((s(26), s(20), s(42), s(26)), radius=s(2), fill=white)
    d.rounded_rectangle((s(26), s(30), s(38), s(35)), radius=s(2), fill=white)
    return im

sizes = [16, 24, 32, 48, 64, 128, 256]
images = [draw_icon(size) for size in sizes]
images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in sizes], append_images=images[:-1])
print(f"Created {OUT}")
