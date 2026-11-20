"""MODE B (GENERATE) Engine — multi-asset composition using Design Knowledge & intact commercial products."""
import os
import textwrap
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from core.design_document import create_document, make_layer, save_document
from core.image_analyzer import extract_product_rgba, sharpen_fullhd


CANVAS_PRESETS = {
    "square_1080": (1080, 1080),
    "portrait_4x5": (1080, 1350),
    "landscape_16x9": (1920, 1080),
    "fullhd_square": (2048, 2048),
}


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


def _make_gradient_bg(w: int, h: int, c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> Image.Image:
    y_grad = np.linspace(0.0, 1.0, h)[:, None, None]
    x_grad = np.linspace(0.0, 1.0, w)[None, :, None]
    t = 0.65 * y_grad + 0.35 * x_grad
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

    # Word wrap to fit max_width
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

    style = knowledge_ctx.get("style", {})
    palettes = style.get("palettes", [])
    pal = palettes[0] if palettes else {"bg": "#071B14", "bg_alt": "#0D3B2A", "accent": "#10B981", "text": "#FFFFFF", "subtext": "#A7F3D0"}

    c_bg1 = _hex_to_rgb(brief.get("bg_color") or pal.get("bg", "#071B14"))
    c_bg2 = _hex_to_rgb(brief.get("bg_alt_color") or pal.get("bg_alt", "#0D3B2A"))
    c_acc = _hex_to_rgb(brief.get("accent_color") or pal.get("accent", "#10B981"))
    c_txt = _hex_to_rgb(brief.get("text_color") or pal.get("text", "#FFFFFF"))
    c_sub = _hex_to_rgb(brief.get("subtext_color") or pal.get("subtext", "#A7F3D0"))

    layers: List[Dict[str, Any]] = []
    z = 0

    # 1. Background Gradient Layer
    bg_im = _make_gradient_bg(W, H, c_bg1, c_bg2)
    bg_file = "layers/01_Background_Gradient.png"
    bg_im.save(os.path.join(project_dir, bg_file))
    layers.append(make_layer(
        name="01_Background_Gradient", layer_type="background", source_file=bg_file,
        x=0, y=0, width=W, height=H, z_index=z, group="1_Background_&_Effects"
    ))
    z += 1

    # 2. Geometric Accent Shape Layer
    shape_im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shape_im)
    if layout == "hero_split":
        sd.polygon([(0, 0), (int(W * 0.56), 0), (int(W * 0.44), H), (0, H)], fill=(*c_acc, 45))
    else:
        sd.ellipse([int(W * 0.55), -int(H * 0.15), int(W * 1.18), int(H * 0.48)], outline=(*c_acc, 70), width=max(4, W // 180))
        sd.rectangle([0, H - int(H * 0.08), W, H], fill=(*c_acc, 230))
    shape_file = "layers/02_Shape_Accent.png"
    shape_im.save(os.path.join(project_dir, shape_file))
    layers.append(make_layer(
        name="02_Shape_Accent", layer_type="shape", source_file=shape_file,
        x=0, y=0, width=W, height=H, z_index=z, group="1_Background_&_Effects"
    ))
    z += 1

    # 3. Product(s) Placement + Separate Light Glow & Contact Shadow (never alter original commercial product!)
    product_paths = brief.get("product_paths") or []
    is_landscape = W > H
    prod_center_x = int(W * 0.70) if is_landscape else int(W * 0.56)
    prod_center_y = int(H * 0.54) if is_landscape else int(H * 0.62)

    if product_paths:
        # Radial glow behind primary product
        glow_sz = int(min(W, H) * 0.72)
        glow_im = _make_radial_glow(glow_sz, c_acc)
        glow_file = "layers/03_Light_RadialGlow.png"
        glow_im.save(os.path.join(project_dir, glow_file))
        layers.append(make_layer(
            name="03_Light_RadialGlow", layer_type="light_effect", source_file=glow_file,
            x=prod_center_x - glow_sz // 2, y=prod_center_y - glow_sz // 2,
            width=glow_sz, height=glow_sz, z_index=z, opacity=0.75, blend_mode="screen",
            group="1_Background_&_Effects"
        ))
        z += 1

        n_prods = len(product_paths)
        for idx, p_path in enumerate(product_paths):
            if not os.path.exists(p_path):
                continue
            prod_rgba = extract_product_rgba(p_path, remove_white_bg=bool(brief.get("remove_white_bg", True)))
            max_pw = int(W * (0.44 if is_landscape else 0.66) / max(1, min(2, n_prods)))
            max_ph = int(H * (0.68 if is_landscape else 0.46))
            scale = min(max_pw / prod_rgba.width, max_ph / prod_rgba.height)
            pw, ph = max(16, int(prod_rgba.width * scale)), max(16, int(prod_rgba.height * scale))
            prod_resized = sharpen_fullhd(prod_rgba.resize((pw, ph), Image.Resampling.LANCZOS), radius=1.0, percent=110)

            offset_x = int((idx - (n_prods - 1) / 2.0) * (pw * 0.85))
            px = max(20, min(W - pw - 20, prod_center_x - pw // 2 + offset_x))
            py = max(20, min(H - ph - int(H * 0.10), prod_center_y - ph // 2))

            # Contact shadow layer under product
            sh_w, sh_h = int(pw * 0.92), max(24, int(ph * 0.16))
            sh_im = _make_contact_shadow(sh_w, sh_h)
            sh_file = f"layers/04_Shadow_Product_{idx + 1}.png"
            sh_im.save(os.path.join(project_dir, sh_file))
            layers.append(make_layer(
                name=f"04_Shadow_Product_{idx + 1}", layer_type="shadow", source_file=sh_file,
                x=px + (pw - sh_w) // 2, y=py + ph - int(sh_h * 0.45),
                width=sh_w, height=sh_h, z_index=z, opacity=0.55, blend_mode="multiply",
                group="2_Products_&_Shadows"
            ))
            z += 1

            prod_file = f"layers/05_Product_{idx + 1}_Original.png"
            prod_resized.save(os.path.join(project_dir, prod_file))
            layers.append(make_layer(
                name=f"05_Product_{idx + 1}_Original", layer_type="product", source_file=prod_file,
                x=px, y=py, width=pw, height=ph, z_index=z,
                group="2_Products_&_Shadows",
                metadata={"original_asset": os.path.basename(p_path), "preserved_pixels": True}
            ))
            z += 1

    # 4. Logo Placement (top-left)
    margin_x = int(W * 0.065)
    margin_y = int(H * 0.06)
    logo_path = brief.get("logo_path", "")
    text_start_y = margin_y
    if logo_path and os.path.exists(logo_path):
        logo_rgba = extract_product_rgba(logo_path, remove_white_bg=True)
        l_scale = min((W * 0.24) / logo_rgba.width, (H * 0.09) / logo_rgba.height)
        lw, lh = max(24, int(logo_rgba.width * l_scale)), max(24, int(logo_rgba.height * l_scale))
        logo_res = logo_rgba.resize((lw, lh), Image.Resampling.LANCZOS)
        logo_file = "layers/06_Logo_Brand.png"
        logo_res.save(os.path.join(project_dir, logo_file))
        layers.append(make_layer(
            name="06_Logo_Brand", layer_type="logo", source_file=logo_file,
            x=margin_x, y=margin_y, width=lw, height=lh, z_index=z,
            group="3_Brand_&_Texts"
        ))
        z += 1
        text_start_y = margin_y + lh + int(H * 0.035)

    # 5. Typography Layers (Rendered pixel PNG + Editable Photoshop Type metadata!)
    text_max_w = int(W * (0.44 if is_landscape else 0.86))
    headline = (brief.get("headline") or "GIẢI PHÁP THÔNG MINH").strip()
    subheadline = (brief.get("subheadline") or "Thiết kế chuẩn nhận diện thương hiệu").strip()
    cta_text = (brief.get("cta_text") or "Liên hệ ngay • Hotline / Website").strip()

    f_head_sz = max(36, int(W * (0.048 if is_landscape else 0.068)))
    f_sub_sz = max(20, int(f_head_sz * 0.44))
    f_cta_sz = max(18, int(H * 0.026))

    # Headline
    h_im, hw, hh = render_text_layer_png(headline, _load_font(studio_root, f_head_sz, bold=True), c_txt, text_max_w)
    h_file = "layers/07_Text_Headline.png"
    h_im.save(os.path.join(project_dir, h_file))
    layers.append(make_layer(
        name="07_Text_Headline", layer_type="text", source_file=h_file,
        x=margin_x, y=text_start_y, width=hw, height=hh, z_index=z,
        group="3_Brand_&_Texts",
        text_data={"text": headline, "font": "Poppins-ExtraBold", "font_size": f_head_sz, "color": list(c_txt)}
    ))
    z += 1

    # Subheadline
    s_y = text_start_y + hh + int(H * 0.022)
    s_im, sw, sh = render_text_layer_png(subheadline, _load_font(studio_root, f_sub_sz, bold=False), c_sub, text_max_w)
    s_file = "layers/08_Text_Subheadline.png"
    s_im.save(os.path.join(project_dir, s_file))
    layers.append(make_layer(
        name="08_Text_Subheadline", layer_type="text", source_file=s_file,
        x=margin_x, y=s_y, width=sw, height=sh, z_index=z,
        group="3_Brand_&_Texts",
        text_data={"text": subheadline, "font": "Poppins-Regular", "font_size": f_sub_sz, "color": list(c_sub)}
    ))
    z += 1

    # CTA / Footer Bar text
    c_im, cw, ch = render_text_layer_png(cta_text, _load_font(studio_root, f_cta_sz, bold=True), (255, 255, 255), int(W * 0.88))
    c_file = "layers/09_Text_CTA.png"
    c_im.save(os.path.join(project_dir, c_file))
    cta_y = H - int(H * 0.04) - ch // 2
    layers.append(make_layer(
        name="09_Text_CTA", layer_type="text", source_file=c_file,
        x=margin_x, y=cta_y, width=cw, height=ch, z_index=z,
        group="3_Brand_&_Texts",
        text_data={"text": cta_text, "font": "Poppins-Bold", "font_size": f_cta_sz, "color": [255, 255, 255]}
    ))

    doc = create_document(
        project_id=project_id,
        title=brief.get("title") or headline,
        mode="GENERATE",
        width=W,
        height=H,
        layers=layers,
        brand={"industry": brief.get("industry", "tech_automotive"), "palette": pal, "layout": layout},
        notes=[
            f"Generated via MODE B ({layout}, {W}x{H}).",
            "Original commercial product pixels preserved intact; glow and shadow created as independent blend layers.",
        ],
    )
    save_document(doc, project_dir)
    return doc
