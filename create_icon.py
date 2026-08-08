"""Генерация иконки для FinalTime."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def create_icon(output_path: Path):
    """Создаёт иконку 256x256 с таймером и текстом FT."""
    size = 256
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = 115  # радиус основного круга

    # --- Фон: тёмно-синий градиент (круг) ---
    for i in range(r, 0, -1):
        ratio = i / r
        # Градиент от тёмно-синего к синему
        red = int(15 + 20 * ratio)
        green = int(25 + 55 * ratio)
        blue = int(80 + 100 * ratio)
        draw.ellipse(
            [cx - i, cy - i, cx + i, cy + i],
            fill=(red, green, blue, 255),
        )

    # --- Внешнее кольцо (серебристое) ---
    draw.ellipse(
        [cx - r, cy - r, cx + r, cy + r],
        outline=(180, 190, 200, 255),
        width=4,
    )

    # --- Внутренний круг (чуть светлее) ---
    r_inner = r - 12
    draw.ellipse(
        [cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner],
        outline=(100, 120, 160, 200),
        width=2,
    )

    # --- Деления на циферблате (12 штук, как часы) ---
    import math
    for i in range(12):
        angle = math.radians(i * 30 - 90)
        x1 = cx + int((r - 20) * math.cos(angle))
        y1 = cy + int((r - 20) * math.sin(angle))
        x2 = cx + int((r - 8) * math.cos(angle))
        y2 = cy + int((r - 8) * math.sin(angle))
        w = 3 if i % 3 == 0 else 1
        draw.line([x1, y1, x2, y2], fill=(200, 210, 220, 255), width=w)

    # --- Стрелки таймера ---
    # Часовая (короткая, толстая) — на 10 часов
    angle_h = math.radians(300 - 90)
    hx = cx + int(50 * math.cos(angle_h))
    hy = cy + int(50 * math.sin(angle_h))
    draw.line([cx, cy, hx, hy], fill=(255, 255, 255, 230), width=6)

    # Минутная (длиннее) — на 2 минуты
    angle_m = math.radians(60 - 90)
    mx = cx + int(80 * math.cos(angle_m))
    my = cy + int(80 * math.sin(angle_m))
    draw.line([cx, cy, mx, my], fill=(255, 255, 255, 240), width=4)

    # Секундная (тонкая, красная) — на 8 секунд
    angle_s = math.radians(240 - 90)
    sx = cx + int(90 * math.cos(angle_s))
    sy = cy + int(90 * math.sin(angle_s))
    draw.line([cx, cy, sx, sy], fill=(220, 60, 60, 255), width=2)

    # Центральная точка
    draw.ellipse([cx - 5, cy - 5, cx + 5, cy + 5], fill=(220, 60, 60, 255))

    # --- Текст "FT" внизу циферблата ---
    try:
        font_large = ImageFont.truetype("arial.ttf", 52)
    except OSError:
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)
        except OSError:
            font_large = ImageFont.load_default()

    text = "FT"
    bbox = draw.textbbox((0, 0), text, font=font_large)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = cx - tw // 2
    ty = cy + 30  # ниже центра

    # Обводка текста для читаемости
    for dx in [-2, -1, 0, 1, 2]:
        for dy in [-2, -1, 0, 1, 2]:
            draw.text((tx + dx, ty + dy), text, font=font_large, fill=(0, 0, 0, 180))
    draw.text((tx, ty), text, font=font_large, fill=(255, 220, 80, 255))

    # --- Сохранение в разные размеры для .ico ---
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    images = []
    for s in sizes:
        resized = img.resize(s, Image.LANCZOS)
        images.append(resized)

    # Сохраняем .ico с несколькими размерами
    images[-1].save(
        output_path,
        format="ICO",
        sizes=[(s[0], s[1]) for s in sizes],
        append_images=images[:-1],
    )
    print(f"Icon created: {output_path}")

    # Также сохраняем .png для превью
    png_path = output_path.with_suffix(".png")
    img.save(png_path)
    print(f"PNG preview: {png_path}")


if __name__ == "__main__":
    icon_dir = Path(__file__).parent / "finaltime" / "assets"
    icon_dir.mkdir(parents=True, exist_ok=True)
    create_icon(icon_dir / "icon.ico")
