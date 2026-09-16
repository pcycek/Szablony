import math
from pathlib import Path
from PIL import Image, ImageDraw

data_stale = Path(__file__).resolve().parent / "data" / "obrazy_stałe"
data_stale.mkdir(parents=True, exist_ok=True)

def create_shape(name, draw_fn):
    img = Image.new("RGB", (300, 300), "white")
    draw = ImageDraw.Draw(img)
    draw_fn(draw)
    img.save(data_stale / f"{name}.jpg", "JPEG", quality=95)

def draw_trojkat(draw):
    draw.polygon([(150, 35), (35, 265), (265, 265)], fill="#2980b9", outline="black", width=6)

def draw_kolo(draw):
    draw.ellipse([35, 35, 265, 265], fill="#e74c3c", outline="black", width=6)

def draw_kwadrat(draw):
    draw.rectangle([40, 40, 260, 260], fill="#27ae60", outline="black", width=6)

def draw_serce(draw):
    points = [
        (150, 90), (190, 45), (250, 45), (275, 95), (275, 140),
        (150, 265),
        (25, 140), (25, 95), (50, 45), (110, 45), (150, 90)
    ]
    draw.polygon(points, fill="#e84393", outline="black", width=6)

def draw_gwiazda(draw):
    pts = []
    cx, cy = 150, 150
    for i in range(10):
        r = 120 if i % 2 == 0 else 55
        angle = i * math.pi / 5 - math.pi / 2
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(pts, fill="#f1c40f", outline="black", width=6)

if __name__ == "__main__":
    create_shape("trojkat", draw_trojkat)
    create_shape("kolo", draw_kolo)
    create_shape("kwadrat", draw_kwadrat)
    create_shape("serce", draw_serce)
    create_shape("gwiazda", draw_gwiazda)
    print("Sample shapes created successfully in data/obrazy_stałe")
