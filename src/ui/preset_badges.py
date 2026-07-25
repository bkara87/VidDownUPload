import os
from PIL import Image, ImageDraw, ImageFont

PRESET_BADGES = [
    {
        "id": "trending",
        "title": "🔥 Trending",
        "bg_color": (239, 68, 68, 235), # Red
        "text_color": (255, 255, 255, 255),
        "text": "🔥 TRENDING REEL"
    },
    {
        "id": "viral",
        "title": "⚡ Viral Clip",
        "bg_color": (245, 158, 11, 235), # Amber/Yellow
        "text_color": (0, 0, 0, 255),
        "text": "⚡ VIRAL CLIP"
    },
    {
        "id": "follow",
        "title": "📌 Follow",
        "bg_color": (59, 130, 246, 235), # Blue
        "text_color": (255, 255, 255, 255),
        "text": "📌 FOLLOW FOR MORE"
    },
    {
        "id": "sound_on",
        "title": "🎵 Sound On",
        "bg_color": (168, 85, 247, 235), # Purple
        "text_color": (255, 255, 255, 255),
        "text": "🎵 SOUND ON"
    },
    {
        "id": "vip",
        "title": "👑 VIP",
        "bg_color": (16, 185, 129, 235), # Emerald Green
        "text_color": (255, 255, 255, 255),
        "text": "👑 VIP CONTENT"
    },
    {
        "id": "daily_shorts",
        "title": "💥 Shorts",
        "bg_color": (236, 72, 153, 235), # Pink
        "text_color": (255, 255, 255, 255),
        "text": "💥 DAILY SHORTS"
    },
    {
        "id": "mizah_special",
        "title": "🎭 7/24 Mizah",
        "bg_color": (6, 182, 212, 235), # Cyan
        "text_color": (255, 255, 255, 255),
        "text": "🎭 7/24 MİZAH DEPOSU"
    },
    {
        "id": "top_pick",
        "title": "🏆 Top Pick",
        "bg_color": (234, 179, 8, 235), # Gold
        "text_color": (15, 23, 42, 255),
        "text": "🏆 TOP PICK"
    },
    {
        "id": "exclusive",
        "title": "💎 Exclusive",
        "bg_color": (99, 102, 241, 235), # Indigo
        "text_color": (255, 255, 255, 255),
        "text": "💎 EXCLUSIVE"
    },
    {
        "id": "new",
        "title": "✨ New",
        "bg_color": (20, 184, 166, 235), # Teal
        "text_color": (255, 255, 255, 255),
        "text": "✨ NEW RELEASE"
    }
]

def render_badge_overlay(preset_id: str, frame_width: int, frame_height: int) -> Image.Image:
    """
    Renders a high quality transparent RGBA badge overlay image matching frame dimensions.
    """
    badge_data = next((b for b in PRESET_BADGES if b["id"] == preset_id), PRESET_BADGES[0])

    overlay = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_size = int(frame_height * 0.038)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    text = badge_data["text"]
    
    pad_x = int(font_size * 0.8)
    pad_y = int(font_size * 0.4)
    
    try:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except Exception:
        tw = font_size * len(text) * 0.6
        th = font_size

    box_w = tw + pad_x * 2
    box_h = th + pad_y * 2

    x1 = frame_width - box_w - int(frame_width * 0.05)
    y1 = int(frame_height * 0.05)
    x2 = x1 + box_w
    y2 = y1 + box_h

    radius = int(box_h / 2)
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=badge_data["bg_color"])

    tx = x1 + pad_x
    ty = y1 + pad_y - 2
    draw.text((tx, ty), text, font=font, fill=badge_data["text_color"])

    return overlay

def get_badge_icon_pil(preset_id: str, size=(110, 32)) -> Image.Image:
    """
    Generates Canva/TikTok style transparent background sticker thumbnail preview for UI button cards.
    """
    badge_data = next((b for b in PRESET_BADGES if b["id"] == preset_id), PRESET_BADGES[0])
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arialbd.ttf", 11)
    except Exception:
        font = ImageFont.load_default()

    text = badge_data["text"]
    if len(text) > 16:
        text = text[:15] + ".."

    radius = int(h / 2)
    draw.rounded_rectangle([2, 2, w - 2, h - 2], radius=radius, fill=badge_data["bg_color"])

    draw.text((w // 2, h // 2 - 1), text, font=font, fill=badge_data["text_color"], anchor="mm")
    return img
