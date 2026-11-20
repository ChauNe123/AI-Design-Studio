"""Module 5: Non-Destructive Layer Rendering Engine (Transform, Tone, Color & Effects)."""
import os
from typing import Any, Dict, Tuple
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter


def render_layer_non_destructive(
    source_path: str,
    adjustments: Dict[str, Any],
    effects: Dict[str, Any],
    scale: float = 1.0,
    rotation: float = 0.0,
    crop_rect: Dict[str, int] = None,
    mask_path: str = None,
) -> Tuple[Image.Image, Tuple[int, int]]:
    """Render layer non-destructively from immutable source_path. Returns (RGBA Image, (pad_x, pad_y))."""
    im = Image.open(source_path).convert("RGBA")

    # 1. Optional standalone mask (if same dimension as source)
    if mask_path and os.path.exists(mask_path):
        m = Image.open(mask_path).convert("L")
        if m.size == im.size:
            r, g, b, a = im.split()
            comb_a = Image.fromarray(
                ((np.array(a, dtype=np.float32) / 255.0) * (np.array(m, dtype=np.float32))).astype(np.uint8),
                "L",
            )
            im = Image.merge("RGBA", (r, g, b, comb_a))

    # 2. Non-destructive crop (supports dict {x,y,w,h} or list [x,y,w,h])
    if crop_rect:
        if isinstance(crop_rect, (list, tuple)) and len(crop_rect) == 4:
            cx, cy, cw, ch = [int(v) for v in crop_rect]
        else:
            cx = int(crop_rect.get("x", 0))
            cy = int(crop_rect.get("y", 0))
            cw = int(crop_rect.get("w", im.width))
            ch = int(crop_rect.get("h", im.height))
        cx = max(0, cx)
        cy = max(0, cy)
        cw = max(1, cw)
        ch = max(1, ch)
        im = im.crop((cx, cy, min(im.width, cx + cw), min(im.height, cy + ch)))

    # 3. Scale & Rotate
    if abs(float(scale) - 1.0) > 0.01:
        nw = max(1, int(round(im.width * float(scale))))
        nh = max(1, int(round(im.height * float(scale))))
        im = im.resize((nw, nh), Image.Resampling.LANCZOS)

    if abs(float(rotation)) > 0.1:
        im = im.rotate(-float(rotation), resample=Image.Resampling.BICUBIC, expand=True)

    # 4. Tone & Color Adjustments (Hue, Sat, Bright, Contrast, Exposure, Temperature, Shadow/Highlight)
    adj = adjustments or {}
    hue = float(adj.get("hue", 0.0))
    sat = float(adj.get("sat", 100.0)) / 100.0
    bright = float(adj.get("bright", 100.0)) / 100.0
    contrast = float(adj.get("contrast", 100.0)) / 100.0
    exposure = float(adj.get("exposure", 0.0))  # -2.0 to +2.0 EV
    temperature = float(adj.get("temperature", 0.0))  # -100 cool to +100 warm
    shadow_adj = float(adj.get("shadow", 0.0))  # -100 to +100
    highlight_adj = float(adj.get("highlight", 0.0))  # -100 to +100

    rgba = np.array(im)
    rgb = rgba[:, :, :3].astype(np.float32)
    alpha = rgba[:, :, 3]

    if abs(hue) > 1.0:
        hsv = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.int16)
        hsv[:, :, 0] = (hsv[:, :, 0] + int(round(hue / 2.0))) % 180
        rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB).astype(np.float32)

    if abs(exposure) > 0.01:
        rgb = np.clip(rgb * (2.0 ** exposure), 0, 255)

    if abs(temperature) > 1.0:
        shift = (temperature / 100.0) * 32.0
        rgb[:, :, 0] = np.clip(rgb[:, :, 0] + shift, 0, 255)
        rgb[:, :, 2] = np.clip(rgb[:, :, 2] - shift, 0, 255)

    if abs(shadow_adj) > 1.0 or abs(highlight_adj) > 1.0:
        lum = (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]) / 255.0
        if abs(shadow_adj) > 1.0:
            sh_w = np.clip(1.0 - lum * 2.0, 0.0, 1.0)[:, :, None]
            rgb = np.clip(rgb + sh_w * (shadow_adj * 0.65), 0, 255)
        if abs(highlight_adj) > 1.0:
            hi_w = np.clip((lum - 0.5) * 2.0, 0.0, 1.0)[:, :, None]
            rgb = np.clip(rgb + hi_w * (highlight_adj * 0.65), 0, 255)

    pil_rgb = Image.fromarray(rgb.astype(np.uint8), "RGB")
    if abs(sat - 1.0) > 0.02:
        pil_rgb = ImageEnhance.Color(pil_rgb).enhance(sat)
    if abs(bright - 1.0) > 0.02:
        pil_rgb = ImageEnhance.Brightness(pil_rgb).enhance(bright)
    if abs(contrast - 1.0) > 0.02:
        pil_rgb = ImageEnhance.Contrast(pil_rgb).enhance(contrast)

    # 5. Effects: Color Overlay, Gradient Overlay, Feather, Blur
    eff = effects or {}
    rgb_arr = np.array(pil_rgb, dtype=np.float32)

    co = eff.get("color_overlay") or {}
    if co.get("enabled"):
        col = np.array(co.get("color", [255, 255, 255]), dtype=np.float32)
        op = float(co.get("opacity", 0.5))
        rgb_arr = rgb_arr * (1.0 - op) + col * op

    go = eff.get("gradient_overlay") or {}
    if go.get("enabled"):
        c1 = np.array(go.get("c1", [16, 185, 129]), dtype=np.float32)
        c2 = np.array(go.get("c2", [6, 95, 70]), dtype=np.float32)
        op = float(go.get("opacity", 0.6))
        gh, gw = rgb_arr.shape[:2]
        yg = np.linspace(0.0, 1.0, gh)[:, None, None]
        grad = c1 * (1.0 - yg) + c2 * yg
        rgb_arr = rgb_arr * (1.0 - op) + grad * op

    im_proc = Image.fromarray(np.dstack([np.clip(rgb_arr, 0, 255).astype(np.uint8), alpha]), "RGBA")

    feather = int(eff.get("feather", 0))
    if feather > 0:
        r, g, b, a = im_proc.split()
        a = a.filter(ImageFilter.GaussianBlur(radius=feather))
        im_proc = Image.merge("RGBA", (r, g, b, a))

    blur_r = float(eff.get("blur", 0.0))
    if blur_r > 0.2:
        im_proc = im_proc.filter(ImageFilter.GaussianBlur(radius=blur_r))

    # 6. Outer Glow & Drop Shadow (expand canvas padding cleanly)
    glow = eff.get("glow") or {}
    ds = eff.get("drop_shadow") or {}
    pad = 0
    if glow.get("enabled"):
        pad = max(pad, int(glow.get("radius", 12)) * 2 + 4)
    if ds.get("enabled"):
        pad = max(pad, int(ds.get("blur", 12)) * 2 + max(abs(int(ds.get("dx", 6))), abs(int(ds.get("dy", 8)))) + 4)

    if pad == 0:
        return im_proc, (0, 0)

    cw, ch = im_proc.width + pad * 2, im_proc.height + pad * 2
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    src_a = im_proc.split()[3]

    if glow.get("enabled"):
        g_col = tuple(int(c) for c in glow.get("color", [16, 185, 129]))
        g_rad = int(glow.get("radius", 14))
        g_op = float(glow.get("opacity", 0.75))
        g_mask = Image.new("RGBA", (cw, ch), (*g_col, 0))
        g_a = Image.new("L", (cw, ch), 0)
        g_a.paste(src_a, (pad, pad))
        g_a = g_a.filter(ImageFilter.GaussianBlur(radius=g_rad))
        g_a = Image.fromarray((np.array(g_a, dtype=np.float32) * g_op).astype(np.uint8), "L")
        g_mask.putalpha(g_a)
        canvas = Image.alpha_composite(canvas, g_mask)

    if ds.get("enabled"):
        d_col = tuple(int(c) for c in ds.get("color", [0, 0, 0]))
        dx, dy = int(ds.get("dx", 6)), int(ds.get("dy", 8))
        d_blur = int(ds.get("blur", 12))
        d_op = float(ds.get("opacity", 0.55))
        d_mask = Image.new("RGBA", (cw, ch), (*d_col, 0))
        d_a = Image.new("L", (cw, ch), 0)
        d_a.paste(src_a, (pad + dx, pad + dy))
        d_a = d_a.filter(ImageFilter.GaussianBlur(radius=d_blur))
        d_a = Image.fromarray((np.array(d_a, dtype=np.float32) * d_op).astype(np.uint8), "L")
        d_mask.putalpha(d_a)
        canvas = Image.alpha_composite(canvas, d_mask)

    canvas.alpha_composite(im_proc, (pad, pad))
    return canvas, (pad, pad)
