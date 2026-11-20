"""MODE B (GENERATE v1.3) — Multi-product, reference-guided, DVF Art Movements, 6 Color Harmonies & Layout Safeguards."""
import colorsys
import math
import os
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from core.design_document import create_document, make_layer, save_document
from core.image_analyzer import extract_product_rgba, sharpen_fullhd
from core.project_manager import save_version
from core.reference_analyzer import analyze_reference_image

CANVAS_PRESETS = {
    "square_1080": (1080, 1080),
    "portrait_4x5": (1080, 1350),
    "story_9x16": (1080, 1920),
    "landscape_16x9": (1920, 1080),
    "fullhd_square": (2048, 2048),
}

ART_MOVEMENT_PRESETS = {
    "bauhaus": {
        "label": "Bauhaus (1919–1933)",
        "bg": "#F4EFE6",
        "bg_alt": "#E9E1D2",
        "accent": "#D92B2B",
        "secondary": "#1D4ED8",
        "highlight": "#F5B700",
        "text": "#111111",
        "subtext": "#374151",
    },
    "pop_art": {
        "label": "Pop Art (1958–1972)",
        "bg": "#FFE600",
        "bg_alt": "#FFD000",
        "accent": "#FF1E8E",
        "secondary": "#00D4FF",
        "highlight": "#FFFFFF",
        "text": "#111111",
        "subtext": "#1F2937",
    },
    "art_deco": {
        "label": "Art Deco (1920–1939)",
        "bg": "#0B101E",
        "bg_alt": "#161E31",
        "accent": "#D4AF37",
        "secondary": "#F3D06B",
        "highlight": "#E5E7EB",
        "text": "#F8FAFC",
        "subtext": "#E2C779",
    },
    "memphis": {
        "label": "Memphis (1981–1988)",
        "bg": "#FCE7F3",
        "bg_alt": "#DBEAFE",
        "accent": "#EC4899",
        "secondary": "#06B6D4",
        "highlight": "#FACC15",
        "text": "#111827",
        "subtext": "#374151",
    },
    "swiss_modern": {
        "label": "Swiss Modern (International Typographic Style)",
        "bg": "#FAFAFA",
        "bg_alt": "#F1F5F9",
        "accent": "#DC2626",
        "secondary": "#111827",
        "highlight": "#E2E8F0",
        "text": "#0F172A",
        "subtext": "#475569",
    },
}


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        max(0, min(255, int(rgb[0]))),
        max(0, min(255, int(rgb[1]))),
        max(0, min(255, int(rgb[2]))),
    )


def _hls_to_rgb255(h: float, l: float, s: float) -> Tuple[int, int, int]:
    r, g, b = colorsys.hls_to_rgb(h % 1.0, max(0.0, min(1.0, l)), max(0.0, min(1.0, s)))
    return int(round(r * 255)), int(round(g * 255)), int(round(b * 255))


def _relative_luminance(rgb: Tuple[int, int, int]) -> float:
    def ch(v):
        c = v / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(rgb[0]) + 0.7152 * ch(rgb[1]) + 0.0722 * ch(rgb[2])


def generate_color_harmony(base_hex: str, scheme: str = "complementary") -> Dict[str, Any]:
    """Generate a 60-30-10 DVF color harmony palette from a base color."""
    base_rgb = _hex_to_rgb(base_hex, (16, 185, 129))
    h, l, s = colorsys.rgb_to_hls(base_rgb[0] / 255.0, base_rgb[1] / 255.0, base_rgb[2] / 255.0)
    sat = max(0.42, min(0.88, s))
    sc = (scheme or "complementary").lower().strip()

    if sc == "monochrome":
        c_bg1 = _hls_to_rgb255(h, 0.14, sat * 0.75)
        c_bg2 = _hls_to_rgb255(h, 0.26, sat * 0.85)
        c_acc = _hls_to_rgb255(h, 0.56, min(0.95, sat * 1.1))
    elif sc == "split_complementary":
        c_bg1 = _hls_to_rgb255(h, 0.16, sat * 0.8)
        c_bg2 = _hls_to_rgb255(h + 5.0 / 12.0, 0.24, sat * 0.75)
        c_acc = _hls_to_rgb255(h + 7.0 / 12.0, 0.55, min(0.95, sat * 1.1))
    elif sc == "analogous":
        c_bg1 = _hls_to_rgb255(h, 0.16, sat * 0.8)
        c_bg2 = _hls_to_rgb255(h + 1.0 / 12.0, 0.25, sat * 0.85)
        c_acc = _hls_to_rgb255(h - 1.0 / 12.0, 0.56, min(0.95, sat * 1.1))
    elif sc == "triadic":
        c_bg1 = _hls_to_rgb255(h, 0.16, sat * 0.8)
        c_bg2 = _hls_to_rgb255(h + 1.0 / 3.0, 0.24, sat * 0.75)
        c_acc = _hls_to_rgb255(h + 2.0 / 3.0, 0.56, min(0.95, sat * 1.1))
    elif sc == "tetradic":
        c_bg1 = _hls_to_rgb255(h, 0.15, sat * 0.78)
        c_bg2 = _hls_to_rgb255(h + 0.25, 0.23, sat * 0.75)
        c_acc = _hls_to_rgb255(h + 0.5, 0.56, min(0.95, sat * 1.1))
    else:  # complementary
        c_bg1 = _hls_to_rgb255(h, 0.16, sat * 0.82)
        c_bg2 = _hls_to_rgb255(h, 0.25, sat * 0.85)
        c_acc = _hls_to_rgb255(h + 0.5, 0.56, min(0.95, sat * 1.1))

    is_dark = _relative_luminance(c_bg1) < 0.35
    c_txt = (255, 255, 255) if is_dark else (15, 23, 42)
    c_sub = (214, 232, 224) if is_dark else (51, 65, 85)
    return {
        "scheme": sc,
        "ratio": "60-30-10",
        "bg": _rgb_to_hex(c_bg1),
        "bg_alt": _rgb_to_hex(c_bg2),
        "accent": _rgb_to_hex(c_acc),
        "text": _rgb_to_hex(c_txt),
        "subtext": _rgb_to_hex(c_sub),
    }


def _draw_art_movement_shapes(
    shape_im: Image.Image,
    art_movement: str,
    W: int,
    H: int,
    c_acc: Tuple[int, int, int],
    c_sec: Tuple[int, int, int],
    c_hi: Tuple[int, int, int],
) -> None:
    """Render distinctive geometric/graphic motifs for the 5 DVF Art Movement presets."""
    sd = ImageDraw.Draw(shape_im)
    if art_movement == "bauhaus":
        # Asymmetric geometric grid: primary circle, bold horizontal bar, vertical dividing line
        sd.ellipse([int(W * 0.56), int(H * 0.12), int(W * 1.04), int(H * 0.60)], fill=(*c_hi, 220))
        sd.rectangle([int(W * 0.06), int(H * 0.84), int(W * 0.94), int(H * 0.93)], fill=(*c_acc, 240))
        sd.rectangle([int(W * 0.46), 0, int(W * 0.475), H], fill=(17, 17, 17, 210))
        sd.polygon([(int(W * 0.475), int(H * 0.62)), (int(W * 0.72), int(H * 0.84)), (int(W * 0.475), int(H * 0.84))], fill=(*c_sec, 215))
    elif art_movement == "pop_art":
        # Subtle Ben-Day halftone dots across canvas + bold comic stripe & footer
        step = max(24, W // 36)
        rad = max(3, step // 6)
        for yy in range(step // 2, H, step):
            offset_x = (step // 2) if ((yy // step) % 2 == 1) else 0
            for xx in range(offset_x, W, step):
                sd.ellipse([xx - rad, yy - rad, xx + rad, yy + rad], fill=(*c_acc, 55))
        sd.rectangle([0, H - int(H * 0.10), W, H], fill=(17, 17, 17, 245))
        sd.rectangle([0, H - int(H * 0.108), W, H - int(H * 0.098)], fill=(*c_acc, 255))
        sd.ellipse([int(W * 0.52), int(H * 0.16), int(W * 0.96), int(H * 0.60)], fill=(*c_sec, 120), outline=(17, 17, 17, 220), width=5)
    elif art_movement == "art_deco":
        # Symmetric stepped Ziggurat corner frames & gold sunburst lines
        m = int(min(W, H) * 0.035)
        sd.rectangle([m, m, W - m, H - m], outline=(*c_acc, 230), width=4)
        m2 = m + int(min(W, H) * 0.018)
        sd.rectangle([m2, m2, W - m2, H - m2], outline=(*c_sec, 160), width=2)
        # Stepped ziggurat top-center ornament
        cx = W // 2
        sd.polygon([(cx - 120, m), (cx + 120, m), (cx + 85, m + 28), (cx - 85, m + 28)], fill=(*c_acc, 210))
        sd.rectangle([m2, H - int(H * 0.115), W - m2, H - m2], fill=(*c_acc, 230))
    elif art_movement == "memphis":
        # Anti-design pastel/neon polka dots, zigzag lines, tilted triangles
        for (px, py, r, col) in [
            (0.82, 0.14, 0.07, c_hi),
            (0.12, 0.72, 0.05, c_sec),
            (0.88, 0.74, 0.06, c_acc),
        ]:
            rr = int(min(W, H) * r)
            cx, cy = int(W * px), int(H * py)
            sd.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(*col, 210), outline=(17, 24, 39, 200), width=3)
        # Zigzag decoration
        pts = [(int(W * (0.56 + i * 0.045)), int(H * (0.08 if i % 2 == 0 else 0.12))) for i in range(8)]
        sd.line(pts, fill=(*c_acc, 235), width=max(5, W // 180))
        sd.polygon([(int(W * 0.72), int(H * 0.25)), (int(W * 0.86), int(H * 0.22)), (int(W * 0.79), int(H * 0.36))], fill=(*c_sec, 180))
        sd.rectangle([0, H - int(H * 0.095), W, H], fill=(17, 24, 39, 240))
    elif art_movement == "swiss_modern":
        # Pure International Typographic grid + crimson accent bar + generous whitespace
        gx = int(W * 0.09)
        sd.line([(gx, int(H * 0.06)), (gx, int(H * 0.86))], fill=(15, 23, 42, 45), width=2)
        sd.line([(int(W * 0.50), int(H * 0.06)), (int(W * 0.50), int(H * 0.86))], fill=(15, 23, 42, 35), width=1)
        sd.rectangle([gx, int(H * 0.055), int(W * 0.28), int(H * 0.072)], fill=(*c_acc, 245))
        sd.rectangle([0, H - int(H * 0.085), W, H], fill=(*c_acc, 240))


def _hex_to_rgb(hex_str: str, fallback: Tuple[int, int, int] = (16, 185, 129)) -> Tuple[int, int, int]:
    s = (hex_str or "").strip().lstrip("#")
    if len(s) == 6:
        try:
            return int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
        except ValueError:
            pass
    return fallback


def _load_font(studio_root: str, size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    fonts_dir = os.path.join(studio_root, "assets", "fonts")
    candidates = [
        os.path.join(fonts_dir, "FZ Poppins-ExtraBold.ttf" if bold else "FZ Poppins-Regular.ttf"),
        os.path.join(fonts_dir, "FZ Poppins-Bold.ttf" if bold else "FZ Poppins-Medium.ttf"),
        r"C:\Windows\Fonts\seguisb.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _make_gradient_bg(w: int, h: int, c1: Tuple[int, int, int], c2: Tuple[int, int, int], angle: float = 0.65) -> Image.Image:
    y_grad = np.linspace(0.0, 1.0, h)[:, None, None]
    x_grad = np.linspace(0.0, 1.0, w)[None, :, None]
    t = angle * y_grad + (1.0 - angle) * x_grad
    arr = (np.array(c1)[None, None, :] * (1.0 - t) + np.array(c2)[None, None, :] * t).astype(np.uint8)
    alpha = np.full((h, w, 1), 255, dtype=np.uint8)
    return Image.fromarray(np.concatenate([arr, alpha], axis=2), "RGBA")


def _make_radial_glow(size: int, color: Tuple[int, int, int]) -> Image.Image:
    y, x = np.ogrid[:size, :size]
    cx = cy = size / 2.0
    dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (size / 2.0)
    falloff = np.clip(1.0 - dist, 0.0, 1.0) ** 2.2
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    rgba[:, :, 0] = color[0]
    rgba[:, :, 1] = color[1]
    rgba[:, :, 2] = color[2]
    rgba[:, :, 3] = (falloff * 210).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def _make_contact_shadow(w: int, h: int) -> Image.Image:
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([int(w * 0.08), int(h * 0.2), int(w * 0.92), int(h * 0.8)], fill=(0, 0, 0, 175))
    return im.filter(ImageFilter.GaussianBlur(radius=max(10, h // 4)))


def render_text_layer_png(
    text: str,
    font: ImageFont.FreeTypeFont,
    fill_rgb: Tuple[int, int, int],
    max_width: int,
    align: str = "left",
    stroke_rgb: Optional[Tuple[int, int, int]] = None,
    stroke_width: int = 0,
) -> Tuple[Image.Image, int, int]:
    """Render crisp Vietnamese/Unicode text to tightly bounded RGBA PNG."""
    dummy = Image.new("RGBA", (10, 10))
    draw = ImageDraw.Draw(dummy)
    words = text.split()
    lines = []
    cur = ""
    for w_tok in words:
        cand = f"{cur} {w_tok}".strip()
        bbox = draw.textbbox((0, 0), cand, font=font, stroke_width=stroke_width)
        if (bbox[2] - bbox[0]) <= max_width or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = w_tok
    if cur:
        lines.append(cur)
    wrapped = "\n".join(lines) if lines else text

    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, spacing=10, align=align, stroke_width=stroke_width)
    pad = 12 + stroke_width
    tw = max(4, (bbox[2] - bbox[0]) + pad * 2)
    th = max(4, (bbox[3] - bbox[1]) + pad * 2)

    out = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(out)
    d2.multiline_text(
        (pad - bbox[0], pad - bbox[1]),
        wrapped,
        font=font,
        fill=(*fill_rgb, 255),
        spacing=10,
        align=align,
        stroke_width=stroke_width,
        stroke_fill=(*stroke_rgb, 255) if stroke_rgb else None,
    )
    return out, tw, th


def _place_products_multi(
    layers: List[Dict[str, Any]],
    project_dir: str,
    product_paths: List[str],
    remove_white_bg: bool,
    zone_x: int,
    zone_y: int,
    zone_w: int,
    zone_h: int,
    z_start: int,
    accent_rgb: Tuple[int, int, int],
    with_glow: bool = True,
) -> int:
    """Arrange 1..N commercial products intact (never redrawing product pixels) with separate shadow & glow."""
    z = z_start
    valid_paths = [p for p in product_paths if p and os.path.exists(p)]
    if not valid_paths:
        return z

    if with_glow:
        glow_sz = int(min(zone_w, zone_h) * 1.1)
        glow_im = _make_radial_glow(glow_sz, accent_rgb)
        glow_file = "layers/03_Light_RadialGlow.png"
        glow_im.save(os.path.join(project_dir, glow_file))
        layers.append(make_layer(
            name="03_Light_RadialGlow", layer_type="light_effect", source_file=glow_file,
            x=zone_x + zone_w // 2 - glow_sz // 2, y=zone_y + zone_h // 2 - glow_sz // 2,
            width=glow_sz, height=glow_sz, z_index=z, opacity=0.72, blend_mode="screen",
            group="1_Background_&_Effects",
        ))
        z += 1

    n = len(valid_paths)
    # Hero product gets prominent center/front placement; additional products flank neatly
    for idx, p_path in enumerate(valid_paths):
        prod_rgba = extract_product_rgba(p_path, remove_white_bg=remove_white_bg)
        if n == 1:
            slot_w, slot_h = zone_w, zone_h
            cx = zone_x + zone_w // 2
            cy = zone_y + zone_h // 2
        elif n == 2:
            slot_w, slot_h = int(zone_w * 0.44), int(zone_h * 0.72)
            cx = zone_x + int(zone_w * (0.26 if idx == 0 else 0.74))
            cy = zone_y + int(zone_h * 0.52)
        elif idx == 0:
            slot_w, slot_h = int(zone_w * 0.52), int(zone_h * 0.80)
            cx = zone_x + int(zone_w * 0.50)
            cy = zone_y + int(zone_h * 0.54)
        else:
            slot_w, slot_h = int(zone_w * 0.36), int(zone_h * 0.54)
            side = -1 if idx % 2 == 1 else 1
            step = (idx + 1) // 2
            cx = zone_x + int(zone_w * (0.50 + side * min(0.36, 0.28 * step)))
            cy = zone_y + int(zone_h * 0.48)

        scale = min(slot_w / prod_rgba.width, slot_h / prod_rgba.height)
        pw = max(16, int(prod_rgba.width * scale))
        ph = max(16, int(prod_rgba.height * scale))
        prod_res = sharpen_fullhd(prod_rgba.resize((pw, ph), Image.Resampling.LANCZOS), radius=1.0, percent=110)

        px = cx - pw // 2
        py = cy - ph // 2

        sh_w, sh_h = int(pw * 0.90), max(22, int(ph * 0.15))
        sh_im = _make_contact_shadow(sh_w, sh_h)
        sh_file = f"layers/04_Shadow_Product_{idx + 1}.png"
        sh_im.save(os.path.join(project_dir, sh_file))
        layers.append(make_layer(
            name=f"04_Shadow_Product_{idx + 1}", layer_type="shadow", source_file=sh_file,
            x=px + (pw - sh_w) // 2, y=py + ph - int(sh_h * 0.45),
            width=sh_w, height=sh_h, z_index=z, opacity=0.52, blend_mode="multiply",
            group="2_Products_&_Shadows",
        ))
        z += 1

        prod_file = f"layers/05_Product_{idx + 1}_Original.png"
        prod_res.save(os.path.join(project_dir, prod_file))
        layers.append(make_layer(
            name=f"05_Product_{idx + 1}_Original", layer_type="product", source_file=prod_file,
            x=px, y=py, width=pw, height=ph, z_index=z,
            group="2_Products_&_Shadows",
            metadata={"original_asset": os.path.basename(p_path), "preserved_pixels": True, "role": "hero" if idx == 0 else "supporting"},
        ))
        z += 1
    return z


def run_generate(
    studio_root: str,
    project_dir: str,
    project_id: str,
    brief: Dict[str, Any],
    knowledge_ctx: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate a full multi-layer design + DesignDocument preserving original commercial product assets."""
    layers_dir = os.path.join(project_dir, "layers")
    os.makedirs(layers_dir, exist_ok=True)

    preset = brief.get("canvas_preset", "square_1080")
    W, H = CANVAS_PRESETS.get(preset, (1080, 1080))
    layout = brief.get("layout", "tech_dark_glow")
    art_movement = (brief.get("art_movement") or "none").lower().strip()
    color_harmony = (brief.get("color_harmony") or "none").lower().strip()
    if art_movement not in ART_MOVEMENT_PRESETS:
        art_movement = "none"

    # Analyze reference images if supplied so layout/palette adapts to extracted principles
    ref_analyses = []
    for rp in (brief.get("reference_paths") or []):
        if rp and os.path.exists(rp):
            try:
                ref_analyses.append(analyze_reference_image(rp))
            except Exception:
                pass

    style = knowledge_ctx.get("style", {})
    palettes = style.get("palettes", [])
    pal = palettes[0] if palettes else {"bg": "#071B14", "bg_alt": "#0D3B2A", "accent": "#10B981", "text": "#FFFFFF", "subtext": "#A7F3D0"}

    # Resolve palette priority: explicit Art Movement Preset -> DVF Color Harmony -> Reference -> Brief / Industry default
    harmony_meta = None
    c_sec = (59, 130, 246)
    c_hi = (250, 204, 21)
    if art_movement != "none":
        am = ART_MOVEMENT_PRESETS[art_movement]
        c_bg1 = _hex_to_rgb(am["bg"])
        c_bg2 = _hex_to_rgb(am["bg_alt"])
        c_acc = _hex_to_rgb(am["accent"])
        c_sec = _hex_to_rgb(am["secondary"])
        c_hi = _hex_to_rgb(am["highlight"])
        c_txt = _hex_to_rgb(am["text"])
        c_sub = _hex_to_rgb(am["subtext"])
    elif color_harmony not in ("", "none"):
        base_seed = brief.get("accent_color") or brief.get("bg_color") or pal.get("accent", "#10B981")
        harmony_meta = generate_color_harmony(base_seed, color_harmony)
        c_bg1 = _hex_to_rgb(harmony_meta["bg"])
        c_bg2 = _hex_to_rgb(harmony_meta["bg_alt"])
        c_acc = _hex_to_rgb(harmony_meta["accent"])
        c_txt = _hex_to_rgb(harmony_meta["text"])
        c_sub = _hex_to_rgb(harmony_meta["subtext"])
    elif ref_analyses and not brief.get("bg_color"):
        rp0 = ref_analyses[0]["palette"]
        c_bg1 = _hex_to_rgb(rp0.get("bg_hex", pal["bg"]))
        c_bg2 = _hex_to_rgb(rp0.get("bg_alt_hex", pal["bg_alt"]))
        c_acc = _hex_to_rgb(brief.get("accent_color") or rp0.get("accent_hex", pal["accent"]))
        c_txt = _hex_to_rgb(brief.get("text_color") or rp0.get("text_hex", pal["text"]))
        c_sub = _hex_to_rgb(brief.get("subtext_color") or rp0.get("subtext_hex", pal["subtext"]))
    else:
        c_bg1 = _hex_to_rgb(brief.get("bg_color") or pal.get("bg", "#071B14"))
        c_bg2 = _hex_to_rgb(brief.get("bg_alt_color") or pal.get("bg_alt", "#0D3B2A"))
        c_acc = _hex_to_rgb(brief.get("accent_color") or pal.get("accent", "#10B981"))
        c_txt = _hex_to_rgb(brief.get("text_color") or pal.get("text", "#FFFFFF"))
        c_sub = _hex_to_rgb(brief.get("subtext_color") or pal.get("subtext", "#A7F3D0"))

    if art_movement == "none" and color_harmony in ("", "none") and layout == "clean_card_modern" and not brief.get("bg_color"):
        c_bg1, c_bg2 = (244, 247, 250), (226, 232, 240)
        c_txt, c_sub = (15, 23, 42), (71, 85, 105)

    layers: List[Dict[str, Any]] = []
    z = 0

    # 1. Background
    bg_im = _make_gradient_bg(W, H, c_bg1, c_bg2, angle=0.7 if layout != "hero_split" else 0.35)
    bg_file = "layers/01_Background_Gradient.png"
    bg_im.save(os.path.join(project_dir, bg_file))
    layers.append(make_layer(
        name="01_Background_Gradient", layer_type="background", source_file=bg_file,
        x=0, y=0, width=W, height=H, z_index=z, group="1_Background_&_Effects",
    ))
    z += 1

    # 2. Structural Shape Accent (Art Movement Preset overrides generic layout shape)
    shape_im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if art_movement != "none":
        _draw_art_movement_shapes(shape_im, art_movement, W, H, c_acc, c_sec, c_hi)
    else:
        sd = ImageDraw.Draw(shape_im)
        if layout == "hero_split":
            sd.polygon([(0, 0), (int(W * 0.56), 0), (int(W * 0.44), H), (0, H)], fill=(*c_acc, 55))
            sd.rectangle([0, H - int(H * 0.085), W, H], fill=(*c_acc, 235))
        elif layout == "clean_card_modern":
            pad = int(min(W, H) * 0.04)
            sd.rounded_rectangle([pad, pad, W - pad, H - pad], radius=36, fill=(255, 255, 255, 235), outline=(*c_acc, 220), width=4)
            sd.rounded_rectangle([pad, H - int(H * 0.12), W - pad, H - pad], radius=24, fill=(*c_acc, 240))
        else:
            sd.ellipse([int(W * 0.52), -int(H * 0.16), int(W * 1.18), int(H * 0.50)], outline=(*c_acc, 85), width=max(4, W // 180))
            sd.rectangle([0, H - int(H * 0.085), W, H], fill=(*c_acc, 235))
    shape_file = "layers/02_Shape_Accent.png"
    shape_im.save(os.path.join(project_dir, shape_file))
    layers.append(make_layer(
        name="02_Shape_Accent", layer_type="shape", source_file=shape_file,
        x=0, y=0, width=W, height=H, z_index=z, group="1_Background_&_Effects",
    ))
    z += 1

    # 3. DVF Layout Safeguards: Negative Space (>=20-25% breathing room) + Rule of Thirds focal zone (45-55% right/bottom)
    is_wide = (W > H) or (layout == "hero_split") or (art_movement in ("bauhaus", "swiss_modern"))
    margin_ratio = 0.09 if art_movement == "swiss_modern" else 0.075
    margin_x = int(W * margin_ratio)
    margin_y = int(H * 0.07)

    if is_wide:
        # Focal subject sits on right third (~46% width, centered near 2/3 X)
        prod_zone = (int(W * 0.50), int(H * 0.15), int(W * 0.43), int(H * 0.66))
        text_max_w = int(W * 0.38)
    else:
        # Focal subject sits on lower half (~44% height, leaving >=25% negative space)
        prod_zone = (int(W * 0.14), int(H * 0.44), int(W * 0.72), int(H * 0.41))
        text_max_w = int(W * 0.80)

    product_paths = brief.get("product_paths") or []
    z = _place_products_multi(
        layers=layers,
        project_dir=project_dir,
        product_paths=product_paths,
        remove_white_bg=bool(brief.get("remove_white_bg", True)),
        zone_x=prod_zone[0], zone_y=prod_zone[1], zone_w=prod_zone[2], zone_h=prod_zone[3],
        z_start=z, accent_rgb=c_acc, with_glow=(layout != "clean_card_modern" and art_movement not in ("bauhaus", "swiss_modern", "memphis")),
    )

    # 4. Logo
    logo_path = brief.get("logo_path", "")
    text_start_y = margin_y
    if logo_path and os.path.exists(logo_path):
        logo_rgba = extract_product_rgba(logo_path, remove_white_bg=True)
        l_scale = min((W * 0.24) / logo_rgba.width, (H * 0.085) / logo_rgba.height)
        lw, lh = max(24, int(logo_rgba.width * l_scale)), max(24, int(logo_rgba.height * l_scale))
        logo_res = logo_rgba.resize((lw, lh), Image.Resampling.LANCZOS)
        logo_file = "layers/06_Logo_Brand.png"
        logo_res.save(os.path.join(project_dir, logo_file))
        layers.append(make_layer(
            name="06_Logo_Brand", layer_type="logo", source_file=logo_file,
            x=margin_x, y=margin_y, width=lw, height=lh, z_index=z, group="3_Brand_&_Badges",
        ))
        z += 1
        text_start_y = margin_y + lh + int(H * 0.032)

    # 5. Typography Hierarchy
    headline = (brief.get("headline") or "GIẢI PHÁP THÔNG MINH").strip()
    subheadline = (brief.get("subheadline") or "Thiết kế chuẩn nhận diện thương hiệu").strip()
    cta_text = (brief.get("cta_text") or "Liên hệ ngay • Hotline / Website").strip()
    bullets = [b.strip() for b in (brief.get("bullets") or []) if b.strip()][:3]

    # DVF Hierarchy Safeguard: Headline MUST be at least 2.0x-2.5x larger than Subheadline
    f_head_sz = max(44, int(W * (0.052 if is_wide else 0.068)))
    f_sub_sz = min(max(18, int(f_head_sz / 2.25)), int(f_head_sz / 2.0))
    f_cta_sz = max(18, int(H * 0.025))

    stroke_rgb = (255, 255, 255) if art_movement == "pop_art" else None
    stroke_w = 3 if art_movement == "pop_art" else 0
    h_im, hw, hh = render_text_layer_png(
        headline, _load_font(studio_root, f_head_sz, bold=True), c_txt, text_max_w,
        stroke_rgb=stroke_rgb, stroke_width=stroke_w,
    )
    h_file = "layers/07_Text_Headline.png"
    h_im.save(os.path.join(project_dir, h_file))
    layers.append(make_layer(
        name="07_Text_Headline", layer_type="text", source_file=h_file,
        x=margin_x, y=text_start_y, width=hw, height=hh, z_index=z, group="4_Typography",
        text_data={"text": headline, "font": "FZPoppins-ExtraBold", "font_size": f_head_sz, "color": list(c_txt)},
    ))
    z += 1

    s_y = text_start_y + hh + int(H * 0.020)
    s_im, sw, sh = render_text_layer_png(subheadline, _load_font(studio_root, f_sub_sz, bold=False), c_sub, text_max_w)
    s_file = "layers/08_Text_Subheadline.png"
    s_im.save(os.path.join(project_dir, s_file))
    layers.append(make_layer(
        name="08_Text_Subheadline", layer_type="text", source_file=s_file,
        x=margin_x, y=s_y, width=sw, height=sh, z_index=z, group="4_Typography",
        text_data={"text": subheadline, "font": "FZPoppins-Regular", "font_size": f_sub_sz, "color": list(c_sub)},
    ))
    z += 1

    # Optional Feature Pills (for bullets)
    cur_y = s_y + sh + int(H * 0.022)
    for b_idx, b_txt in enumerate(bullets, start=1):
        b_sz = max(16, int(f_sub_sz * 0.85))
        b_im, bw, bh = render_text_layer_png(f"• {b_txt}", _load_font(studio_root, b_sz, bold=True), c_txt, text_max_w)
        b_file = f"layers/09_Text_Feature_{b_idx}.png"
        b_im.save(os.path.join(project_dir, b_file))
        layers.append(make_layer(
            name=f"09_Text_Feature_{b_idx}", layer_type="text", source_file=b_file,
            x=margin_x, y=cur_y, width=bw, height=bh, z_index=z, group="4_Typography",
            text_data={"text": f"• {b_txt}", "font": "FZPoppins-Bold", "font_size": b_sz, "color": list(c_txt)},
        ))
        z += 1
        cur_y += bh + 8

    # CTA / Footer Bar
    c_im, cw, ch = render_text_layer_png(cta_text, _load_font(studio_root, f_cta_sz, bold=True), (255, 255, 255), int(W * 0.86))
    c_file = "layers/10_Text_CTA.png"
    c_im.save(os.path.join(project_dir, c_file))
    cta_y = H - int(H * (0.075 if layout == "clean_card_modern" else 0.042)) - ch // 2
    layers.append(make_layer(
        name="10_Text_CTA", layer_type="text", source_file=c_file,
        x=margin_x, y=cta_y, width=cw, height=ch, z_index=z, group="4_Typography",
        text_data={"text": cta_text, "font": "FZPoppins-Bold", "font_size": f_cta_sz, "color": [255, 255, 255]},
    ))

    doc = create_document(
        project_id=project_id,
        title=brief.get("title") or headline,
        mode="GENERATE",
        width=W,
        height=H,
        layers=layers,
        brand={
            "industry": brief.get("industry", "tech_automotive"),
            "palette": harmony_meta or pal,
            "layout": layout,
            "art_movement": art_movement,
            "color_harmony": color_harmony,
            "hierarchy_ratio": round(f_head_sz / max(1, f_sub_sz), 2),
            "guideline_rules": (knowledge_ctx.get("brand") or {}).get("rules", []),
            "reference_insights": [r.get("visual_hierarchy") for r in ref_analyses],
        },
        notes=[
            f"Generated via MODE B ({layout}, art={art_movement}, harmony={color_harmony}, {W}x{H}) with {len(product_paths)} product asset(s).",
            f"DVF Safeguards: Headline/Sub={f_head_sz}/{f_sub_sz} ({f_head_sz/max(1,f_sub_sz):.2f}x >= 2.0x), Rule of Thirds focal zone.",
            f"Reference images analyzed: {len(ref_analyses)}. Commercial product pixels preserved intact.",
        ],
    )
    save_document(doc, project_dir)
    save_version(doc, project_dir, note="Initial MODE B generation")
    return doc


def generate_layout_variants(
    studio_root: str,
    projects_root: str,
    base_id: str,
    brief: Dict[str, Any],
    knowledge_ctx: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Propose & generate 3 distinct layout variants for comparison."""
    variants_spec = [
        ("tech_dark_glow", "Concept A — Tech Glow"),
        ("hero_split", "Concept B — Hero Split"),
        ("clean_card_modern", "Concept C — Editorial Card"),
    ]
    out = []
    for idx, (lay, label) in enumerate(variants_spec, start=1):
        vid = f"{base_id}_v{idx}"
        vdir = os.path.join(projects_root, vid)
        os.makedirs(vdir, exist_ok=True)
        vbrief = dict(brief)
        vbrief["layout"] = lay
        vbrief["title"] = f"{brief.get('title', 'Design')} ({label})"
        doc = run_generate(studio_root, vdir, vid, vbrief, knowledge_ctx)
        out.append({"variant_label": label, "layout": lay, "project_id": vid, "project_dir": vdir, "document": doc})
    return out
