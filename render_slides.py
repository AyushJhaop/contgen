import json
import os
import zipfile
from typing import Dict, Any, List
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = "/Users/ayushjha/Desktop/contgen"
SLIDES_DIR = os.path.join(BASE_DIR, "slides")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
ARTIFACT_DIR = "/Users/ayushjha/.gemini/antigravity/brain/39ec6a8f-a4a6-4e1c-bc8c-ed0b56dd6b41"

THEMES: Dict[str, Dict[str, Any]] = {
    "obsidian_slate": {
        "name": "Obsidian Slate (Dark SaaS)",
        "canvas_bg": (11, 15, 25),
        "card_bg": (17, 24, 39),
        "card_outline": (45, 58, 82),
        "box_bg": (24, 35, 56),
        "box_outline": (56, 72, 102),
        "text_main": (248, 250, 252),
        "text_body": (203, 213, 225),
        "text_muted": (148, 163, 184),
        "pill_bg": (30, 41, 59),
    },
    "cobalt_executive": {
        "name": "Cobalt Executive (Deep Navy)",
        "canvas_bg": (7, 17, 38),
        "card_bg": (13, 28, 60),
        "card_outline": (38, 67, 120),
        "box_bg": (20, 42, 86),
        "box_outline": (54, 92, 160),
        "text_main": (248, 250, 252),
        "text_body": (214, 226, 245),
        "text_muted": (147, 174, 214),
        "pill_bg": (22, 46, 94),
    },
    "emerald_growth": {
        "name": "Emerald Growth (Forest FinTech)",
        "canvas_bg": (6, 22, 18),
        "card_bg": (11, 35, 29),
        "card_outline": (31, 79, 65),
        "box_bg": (17, 52, 43),
        "box_outline": (43, 107, 88),
        "text_main": (240, 253, 244),
        "text_body": (209, 250, 229),
        "text_muted": (134, 207, 178),
        "pill_bg": (19, 58, 48),
    },
    "editorial_ivory": {
        "name": "Editorial Ivory (Light Executive)",
        "canvas_bg": (241, 245, 249),
        "card_bg": (255, 255, 255),
        "card_outline": (203, 213, 225),
        "box_bg": (248, 250, 252),
        "box_outline": (203, 213, 225),
        "text_main": (15, 23, 42),
        "text_body": (51, 65, 85),
        "text_muted": (100, 116, 139),
        "pill_bg": (241, 245, 249),
    },
}

ACCENT_COLORS: Dict[str, tuple] = {
    "rose": (251, 113, 133),
    "sky": (56, 189, 248),
    "emerald": (52, 211, 153),
    "indigo": (129, 140, 248),
    "amber": (251, 191, 36),
}


def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    words = (text or "").split()
    lines: List[str] = []
    cur = ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def render_carousel_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Renders all slides in the payload to high-res PNGs, compiles a multi-page
    LinkedIn PDF, and creates an Instagram ZIP archive.
    """
    os.makedirs(SLIDES_DIR, exist_ok=True)
    os.makedirs(EXPORTS_DIR, exist_ok=True)

    brand_kit = payload.get("brand_kit", {})
    theme_id = brand_kit.get("theme_id", "obsidian_slate")
    theme = THEMES.get(theme_id, THEMES["obsidian_slate"])
    handle = brand_kit.get("handle", "@founder.playbook")
    aspect_ratio = payload.get("aspect_ratio", "4:5")

    W = 1080
    H = 1080 if aspect_ratio.startswith("1:1") else 1350

    f_tag = get_font(24, bold=True)
    f_kicker = get_font(26, bold=True)
    f_title = get_font(58 if H == 1350 else 50, bold=True)
    f_body = get_font(33 if H == 1350 else 29, bold=False)
    f_box_title = get_font(27, bold=True)
    f_box_line = get_font(29 if H == 1350 else 26, bold=False)
    f_footer = get_font(26, bold=True)

    slides = payload.get("slides", [])
    total = len(slides)
    rendered_images: List[Image.Image] = []
    slide_paths: List[str] = []

    for idx, s in enumerate(slides, 1):
        accent_key = s.get("accent_token", "sky")
        accent = ACCENT_COLORS.get(accent_key, ACCENT_COLORS["sky"])
        # Slightly darken accent on light editorial background for contrast
        if theme_id == "editorial_ivory":
            accent = tuple(max(0, int(c * 0.78)) for c in accent)

        img = Image.new("RGB", (W, H), theme["canvas_bg"])
        draw = ImageDraw.Draw(img)

        # Card container
        draw.rounded_rectangle(
            [36, 36, W - 36, H - 36],
            radius=36,
            fill=theme["card_bg"],
            outline=theme["card_outline"],
            width=3,
        )
        # Top accent bar
        draw.rounded_rectangle([36, 36, W - 36, 52], radius=8, fill=accent)

        # Header row
        header_tag = (s.get("header_tag") or "FOUNDER PLAYBOOK").upper()
        num_str = f"{idx:02d} / {total:02d}"
        draw.text((96, 100), header_tag, font=f_tag, fill=theme["text_muted"])
        draw.rounded_rectangle(
            [W - 220, 88, W - 96, 140],
            radius=24,
            fill=theme["pill_bg"],
            outline=accent,
            width=2,
        )
        draw.text((W - 194, 100), num_str, font=f_tag, fill=accent)

        # Kicker
        y = 215 if H == 1350 else 175
        kicker = (s.get("kicker") or "").upper()
        draw.text((96, y), kicker, font=f_kicker, fill=accent)
        y += 52

        # Headline
        headline = s.get("headline") or ""
        t_lines = wrap_text(draw, headline, f_title, W - 192)
        line_step = 72 if H == 1350 else 62
        for line in t_lines[:4]:
            draw.text((96, y), line, font=f_title, fill=theme["text_main"])
            y += line_step
        y += 24

        # Body
        body = s.get("body") or ""
        b_lines = wrap_text(draw, body, f_body, W - 192)
        body_step = 46 if H == 1350 else 40
        for line in b_lines[:4]:
            draw.text((96, y), line, font=f_body, fill=theme["text_body"])
            y += body_step
        y += 38

        # Callout Box
        bullets = s.get("callout_bullets") or []
        wrapped_bullets: List[str] = []
        for bl in bullets:
            wrapped_bullets.extend(wrap_text(draw, bl, f_box_line, W - 272))

        box_h = 104 + len(wrapped_bullets) * (48 if H == 1350 else 42)
        max_box_bottom = H - 175
        if y + box_h > max_box_bottom:
            box_h = max(140, max_box_bottom - y)

        draw.rounded_rectangle(
            [96, y, W - 96, y + box_h],
            radius=24,
            fill=theme["box_bg"],
            outline=theme["box_outline"],
            width=2,
        )
        callout_title = (s.get("callout_title") or "KEY TAKEAWAY").upper()
        draw.text((136, y + 28), callout_title, font=f_box_title, fill=accent)

        by = y + 78
        for wbl in wrapped_bullets:
            if by + 36 > y + box_h - 12:
                break
            draw.text((136, by), wbl, font=f_box_line, fill=theme["text_main"])
            by += 48 if H == 1350 else 42

        # Footer divider
        fy = H - 140
        draw.line([(96, fy), (W - 96, fy)], fill=theme["card_outline"], width=2)
        draw.ellipse([96, fy + 30, 136, fy + 70], fill=accent)
        draw.text((152, fy + 36), handle, font=f_footer, fill=theme["text_main"])

        cta_text = s.get("footer_cta") or ("Save & Repost" if idx == total else "Swipe ->")
        cta_bbox = draw.textbbox((0, 0), cta_text, font=f_footer)
        cta_w = cta_bbox[2] - cta_bbox[0]
        draw.text((W - 96 - cta_w, fy + 36), cta_text, font=f_footer, fill=accent)

        fname = f"slide_{idx:02d}.png"
        out_path = os.path.join(SLIDES_DIR, fname)
        img.save(out_path, "PNG")
        if os.path.exists(ARTIFACT_DIR):
            img.save(os.path.join(ARTIFACT_DIR, fname), "PNG")

        rendered_images.append(img)
        slide_paths.append(f"/slides/{fname}")

    # Export multi-page PDF for LinkedIn Document Carousel
    pdf_path = os.path.join(EXPORTS_DIR, "linkedin_carousel.pdf")
    if rendered_images:
        rendered_images[0].save(
            pdf_path,
            "PDF",
            resolution=100.0,
            save_all=True,
            append_images=rendered_images[1:],
        )

    # Export ZIP bundle for Instagram + Caption + JSON payload
    zip_path = os.path.join(EXPORTS_DIR, "instagram_carousel_bundle.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for idx in range(1, total + 1):
            fname = f"slide_{idx:02d}.png"
            fpath = os.path.join(SLIDES_DIR, fname)
            if os.path.exists(fpath):
                zf.write(fpath, arcname=fname)
        caption = payload.get("post_caption", "")
        if caption:
            zf.writestr("post_caption.txt", caption)
        zf.writestr("carousel_payload.json", json.dumps(payload, indent=2))

    return {
        "slide_urls": slide_paths,
        "pdf_url": "/exports/linkedin_carousel.pdf",
        "zip_url": "/exports/instagram_carousel_bundle.zip",
        "slide_count": total,
        "dimensions": f"{W}x{H}",
    }


if __name__ == "__main__":
    payload_file = os.path.join(BASE_DIR, "sample_carousel_payload.json")
    if os.path.exists(payload_file):
        with open(payload_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        res = render_carousel_from_payload(data)
        print(f"Rendered {res['slide_count']} slides ({res['dimensions']}), PDF, and ZIP.")
