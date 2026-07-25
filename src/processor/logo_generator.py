import os
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from src.config import BASE_DIR

def generate_metallic_channel_logos():
    """
    Generates high-resolution sharp HD metallic gradient logos for "7/24 Mizah Deposu"
    in 3 variants: Transparent, Dark, Light background.
    """
    assets_dir = BASE_DIR / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    # Ultra high resolution (1200x440 px) for extreme clarity & sharpness
    width, height = 1200, 440
    
    variants = [
        {"name": "logo_724mizah_transparent.png", "bg_color": (0, 0, 0, 0)},
        {"name": "logo_724mizah_dark.png", "bg_color": (11, 16, 29, 245)},
        {"name": "logo_724mizah_light.png", "bg_color": (255, 255, 255, 245)}
    ]

    for var in variants:
        img = Image.new("RGBA", (width, height), var["bg_color"])
        draw = ImageDraw.Draw(img)

        # Draw outer rounded border badge frame with sharp glow
        pad = 24
        border_box = [pad, pad, width - pad, height - pad]
        
        # Outer neon cyan glow border
        draw.rounded_rectangle(border_box, radius=36, outline=(6, 182, 212, 255), width=8)
        
        # Inner metallic dark/light fill if not transparent
        inner_box = [pad + 12, pad + 12, width - pad - 12, height - pad - 12]
        if var["bg_color"][3] > 0:
            fill_c = (7, 11, 18, 240) if var["bg_color"][0] < 100 else (245, 247, 250, 240)
            draw.rounded_rectangle(inner_box, radius=28, fill=fill_c, outline=(245, 158, 11, 220), width=4)

        # High-res Fonts
        font_large_size = 96
        font_small_size = 64
        try:
            font_large = ImageFont.truetype("arialbd.ttf", font_large_size)
            font_small = ImageFont.truetype("arialbd.ttf", font_small_size)
        except Exception:
            try:
                font_large = ImageFont.truetype("arial.ttf", font_large_size)
                font_small = ImageFont.truetype("arial.ttf", font_small_size)
            except Exception:
                font_large = ImageFont.load_default()
                font_small = ImageFont.load_default()

        t1 = "7 / 24"
        t2 = "MİZAH DEPOSU"

        # Metallic Gold / Cyan Gradient Text Rendering with Drop Shadow
        cy1, cy2 = 120, 290

        # Drop shadow
        draw.text((width // 2 + 5, cy1 + 5), t1, font=font_large, fill=(0, 0, 0, 220), anchor="mm")
        draw.text((width // 2 + 5, cy2 + 5), t2, font=font_small, fill=(0, 0, 0, 220), anchor="mm")

        # Main Text colors (Vibrant Gold & Cyan Metallic)
        draw.text((width // 2, cy1), t1, font=font_large, fill=(245, 158, 11, 255), anchor="mm")
        draw.text((width // 2, cy2), t2, font=font_small, fill=(6, 182, 212, 255), anchor="mm")

        # Underline metallic purple bar
        bar_w = 600
        bar_x1 = (width - bar_w) // 2
        bar_y = 205
        draw.line([(bar_x1, bar_y), (bar_x1 + bar_w, bar_y)], fill=(168, 85, 247, 255), width=6)

        out_path = assets_dir / var["name"]
        img.save(out_path, format="PNG")
        print(f"Generated HD sharp logo: {out_path}")

    return str(assets_dir / "logo_724mizah_transparent.png")

if __name__ == "__main__":
    generate_metallic_channel_logos()
