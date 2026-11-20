"""Module 3: Editable Typography Engine — Vietnamese OCR, Font Matching, Effects & Reconstruction."""
import json
import math
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

STUDIO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGE_MJS = os.path.join(STUDIO_ROOT, "core", "ai_vision_bridge.mjs")


def _imread_unicode(path: str):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def list_local_fonts() -> List[Dict[str, str]]:
    """Scan local project fonts and Windows system fonts."""
    fonts = []
    search_dirs = [
        (os.path.join(STUDIO_ROOT, "assets", "fonts"), "project"),
        (r"C:\Windows\Fonts", "windows"),
    ]
    for d, src in search_dirs:
        if not os.path.exists(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.lower().endswith((".ttf", ".otf")):
                fonts.append({
                    "name": os.path.splitext(fn)[0],
                    "file": os.path.join(d, fn),
                    "source": src,
                })
    return fonts


def match_local_font(
    estimated_weight: str = "bold",
    is_italic: bool = False,
    prefer_vietnamese: bool = True,
    is_condensed_headline: bool = False,
    is_uppercase: bool = False,
) -> Dict[str, Any]:
    """Select an appropriate Vietnamese-ready font family based on stroke weight, condensed look & role."""
    fonts = list_local_fonts()
    if is_condensed_headline and is_uppercase and not is_italic:
        prefs = ["Anton-Regular", "FZ Poppins-ExtraBold", "BeVietnamPro-ExtraBold", "impact", "arialbd"]
    elif estimated_weight in ("extrabold", "black"):
        prefs = ["FZ Poppins-Black", "FZ Poppins-ExtraBold", "BeVietnamPro-ExtraBold", "BeVietnamPro-Bold", "seguib", "arialbd"]
    elif estimated_weight == "bold":
        prefs = ["BeVietnamPro-Bold", "FZ Poppins-Bold", "BeVietnamPro-ExtraBold", "seguisb", "arialbd"]
    elif estimated_weight == "medium":
        prefs = ["BeVietnamPro-Medium", "FZ Poppins-Medium", "segoeui", "arial"]
    else:
        prefs = ["BeVietnamPro-Regular", "FZ Poppins-Regular", "BeVietnamPro-Medium", "segoeui", "arial"]
    if is_italic:
        prefs = ["FZ Poppins-BoldItalic", "FZ Poppins-Italic", "arialbi", "ariali"] + prefs

    by_lower = {f["name"].lower(): f for f in fonts}
    for p in prefs:
        if p.lower() in by_lower:
            picked = by_lower[p.lower()]
            return {
                "font_name": picked["name"],
                "font_file": picked["file"],
                "is_exact_font_match": False,
                "match_note": f"Chọn font tiếng Việt hợp vai trò & độ đậm từ thư viện ({picked['name']}); không đảm bảo trùng 100% font raster gốc.",
            }
    fallback = fonts[0] if fonts else {"name": "default", "file": ""}
    return {
        "font_name": fallback["name"],
        "font_file": fallback["file"],
        "is_exact_font_match": False,
        "match_note": "Dùng font mặc định hệ thống.",
    }


def run_vietnamese_ocr(image_path: str, timeout_s: int = 60) -> Dict[str, Any]:
    """Run tesseract.js (vie+eng) OCR and return line bboxes, baselines, words, and confidence."""
    res = subprocess.run(
        ["node", BRIDGE_MJS, "ocr", image_path, "vie+eng"],
        capture_output=True, text=True, timeout=timeout_s, check=False,
    )
    if res.returncode != 0:
        return {"ok": False, "lines": [], "error": res.stderr.strip() or res.stdout.strip()}
    return json.loads(res.stdout.strip().splitlines()[-1])


def analyze_text_line_appearance(bgr_img: np.ndarray, bbox: List[int]) -> Dict[str, Any]:
    """Estimate fill color, stroke presence, rotation angle, alignment, and weight from raster crop."""
    h, w = bgr_img.shape[:2]
    x, y, bw, bh = bbox
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(w, x + bw), min(h, y + bh)
    crop = bgr_img[y1:y2, x1:x2]
    if crop.size == 0:
        return {"fill_color": [255, 255, 255], "rotation": 0.0, "estimated_weight": "bold", "has_stroke_or_3d": False}

    rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # Border median represents surrounding background
    border = np.vstack([rgb[0, :], rgb[-1, :], rgb[:, 0], rgb[:, -1]])
    bg_rgb = np.median(border, axis=0)
    dist = np.linalg.norm(rgb.astype(np.float32) - bg_rgb.astype(np.float32), axis=2)
    fg_mask = dist > max(22.0, float(np.percentile(dist, 62)))

    fill_rgb = [255, 255, 255]
    if np.any(fg_mask):
        fg_pixels = rgb[fg_mask]
        med_fg = np.median(fg_pixels, axis=0).astype(int)
        fill_rgb = [int(med_fg[0]), int(med_fg[1]), int(med_fg[2])]

    # Estimate angle using minAreaRect on foreground points
    pts = np.column_stack(np.where(fg_mask))
    angle = 0.0
    if len(pts) > 20:
        rect = cv2.minAreaRect(pts[:, ::-1].astype(np.float32))
        ang = rect[2]
        if ang < -45:
            ang += 90
        elif ang > 45:
            ang -= 90
        if abs(ang) < 25:
            angle = round(float(ang), 1)

    fg_density = float(np.mean(fg_mask))
    weight = "extrabold" if fg_density > 0.34 else ("bold" if fg_density > 0.22 else "regular")

    # Check if text has outline/3D (significant gradient variance around edges)
    edges = cv2.Canny(gray, 50, 150)
    has_stroke_3d = bool(np.mean(edges > 0) > 0.14 and np.std(rgb[fg_mask]) > 25 if np.any(fg_mask) else False)

    cx = x + bw / 2.0
    align = "center" if abs(cx - w / 2.0) < w * 0.12 else ("left" if cx < w / 2.0 else "right")

    return {
        "fill_color": fill_rgb,
        "rotation": angle,
        "estimated_weight": weight,
        "alignment": align,
        "has_stroke_or_3d": has_stroke_3d,
        "letter_spacing_est": round(max(0.0, (bw / max(1, bh)) * 0.15), 2),
    }


def render_styled_text(
    text: str,
    font_file: str,
    font_size: int = 48,
    color: Tuple[int, int, int] = (255, 255, 255),
    align: str = "left",
    tracking: int = 0,
    leading: int = 10,
    stroke_enabled: bool = False,
    stroke_color: Tuple[int, int, int] = (0, 0, 0),
    stroke_width: int = 3,
    shadow_enabled: bool = False,
    shadow_color: Tuple[int, int, int] = (0, 0, 0),
    shadow_offset: Tuple[int, int] = (4, 6),
    shadow_blur: int = 6,
    glow_enabled: bool = False,
    glow_color: Tuple[int, int, int] = (16, 185, 129),
    glow_radius: int = 10,
    gradient_enabled: bool = False,
    gradient_c2: Tuple[int, int, int] = (16, 185, 129),
    extrude_3d_depth: int = 0,
    rotation: float = 0.0,
) -> Image.Image:
    """Render full-featured editable text with tracking, leading, stroke, shadow, glow, gradient, 3D & rotation."""
    try:
        font = ImageFont.truetype(font_file, size=max(8, int(font_size))) if font_file and os.path.exists(font_file) else ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    lines = (text or " ").splitlines() or [" "]
    dummy = Image.new("RGBA", (10, 10))
    d0 = ImageDraw.Draw(dummy)

    def measure_line(ln: str) -> Tuple[int, int]:
        if tracking == 0:
            bb = d0.textbbox((0, 0), ln, font=font, stroke_width=stroke_width if stroke_enabled else 0)
            return max(4, bb[2] - bb[0]), max(8, bb[3] - bb[1])
        tw = 0
        mh = int(font_size * 1.2)
        for ch in ln:
            bb = d0.textbbox((0, 0), ch, font=font)
            tw += max(2, bb[2] - bb[0]) + tracking
            mh = max(mh, bb[3] - bb[1])
        return max(4, tw), mh

    measured = [measure_line(ln) for ln in lines]
    max_lw = max(m[0] for m in measured)
    line_h = max(int(font_size * 1.15), max(m[1] for m in measured))

    pad = 24 + (stroke_width if stroke_enabled else 0) + (glow_radius * 2 if glow_enabled else 0) + abs(extrude_3d_depth) + (shadow_blur * 2 if shadow_enabled else 0)
    W = max_lw + pad * 2
    H = line_h * len(lines) + leading * max(0, len(lines) - 1) + pad * 2

    # Helper to draw text onto a canvas at (ox, oy)
    def draw_text_mask(canvas: Image.Image, fill_rgba: Tuple[int, int, int, int], ox: int = 0, oy: int = 0, sw: int = 0, s_col=None):
        dr = ImageDraw.Draw(canvas)
        cy = pad + oy
        for idx, ln in enumerate(lines):
            lw, _ = measured[idx]
            if align == "center":
                cx = pad + (max_lw - lw) // 2 + ox
            elif align == "right":
                cx = pad + (max_lw - lw) + ox
            else:
                cx = pad + ox
            if tracking == 0:
                dr.text((cx, cy), ln, font=font, fill=fill_rgba, stroke_width=sw, stroke_fill=s_col)
            else:
                cur_x = cx
                for ch in ln:
                    dr.text((cur_x, cy), ch, font=font, fill=fill_rgba, stroke_width=sw, stroke_fill=s_col)
                    bb = d0.textbbox((0, 0), ch, font=font)
                    cur_x += max(2, bb[2] - bb[0]) + tracking
            cy += line_h + leading

    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # Glow layer
    if glow_enabled:
        gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_text_mask(gl, (*glow_color, 220))
        gl = gl.filter(ImageFilter.GaussianBlur(radius=max(1, glow_radius)))
        out = Image.alpha_composite(out, gl)

    # Drop shadow layer
    if shadow_enabled:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_text_mask(sh, (*shadow_color, 180), ox=shadow_offset[0], oy=shadow_offset[1])
        if shadow_blur > 0:
            sh = sh.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        out = Image.alpha_composite(out, sh)

    # 3D Extrusion steps
    if extrude_3d_depth > 0:
        dark_3d = (max(0, color[0] - 80), max(0, color[1] - 80), max(0, color[2] - 80), 255)
        for step in range(extrude_3d_depth, 0, -1):
            ex = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            draw_text_mask(ex, dark_3d, ox=step, oy=step)
            out = Image.alpha_composite(out, ex)

    # Main fill (+ optional gradient + optional stroke)
    fg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sw_px = stroke_width if stroke_enabled else 0
    s_rgba = (*stroke_color, 255) if stroke_enabled else None
    draw_text_mask(fg, (*color, 255), sw=sw_px, s_col=s_rgba)

    if gradient_enabled:
        fill_only = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_text_mask(fill_only, (255, 255, 255, 255))
        fa = np.array(fill_only)[:, :, 3] > 20
        fg_arr = np.array(fg)
        yg = np.linspace(0.0, 1.0, H)[:, None, None]
        grad = (np.array(color)[None, None, :] * (1.0 - yg) + np.array(gradient_c2)[None, None, :] * yg).astype(np.uint8)
        fg_arr[fa, :3] = np.broadcast_to(grad, (H, W, 3))[fa]
        fg = Image.fromarray(fg_arr, "RGBA")

    out = Image.alpha_composite(out, fg)
    if abs(rotation) > 0.1:
        out = out.rotate(-float(rotation), resample=Image.Resampling.BICUBIC, expand=True)
    return out


def extract_typography_objects(image_path: str, project_dir: str) -> List[Dict[str, Any]]:
    """Run OCR, analyze raster text appearance, match local fonts, and generate reconstruction records."""
    bgr = _imread_unicode(image_path)
    if bgr is None:
        return []
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = bgr.shape[:2]

    ocr_res = run_vietnamese_ocr(image_path)
    lines = ocr_res.get("lines", [])
    raster_dir = os.path.join(project_dir, "text_refs")
    os.makedirs(raster_dir, exist_ok=True)

    results = []
    for idx, ln in enumerate(lines, start=1):
        txt = ln["text"]
        conf = float(ln.get("confidence", 0.0))
        bx, by, bw, bh = ln["bbox"]

        # Refine line text and bbox using word-level confidences when available to drop false overlapping tokens
        words = ln.get("words") or []
        good_words = [
            wd for wd in words
            if wd.get("confidence", conf) >= 0.48 and any(ch.isalnum() for ch in wd.get("text", ""))
        ]
        if good_words:
            txt = " ".join(wd["text"].strip() for wd in good_words if wd.get("text", "").strip())
            wx1 = min(int(wd["bbox"][0]) for wd in good_words)
            wy1 = min(int(wd["bbox"][1]) for wd in good_words)
            wx2 = max(int(wd["bbox"][0]) + int(wd["bbox"][2]) for wd in good_words)
            wy2 = max(int(wd["bbox"][1]) + int(wd["bbox"][3]) for wd in good_words)
            bx, by, bw, bh = wx1, wy1, max(1, wx2 - wx1), max(1, wy2 - wy1)
            conf = round(sum(float(wd.get("confidence", conf)) for wd in good_words) / len(good_words), 3)

        # Filter obvious OCR background texture noise
        compact = txt.replace(" ", "")
        alpha_cnt = sum(1 for c in compact if c.isalnum())
        noise_cnt = sum(1 for c in compact if c in "~|=⁄`“—.;/\\")
        if len(compact) < 2 or alpha_cnt < 2 or bw < 16 or bh < 10:
            continue
        if conf < 0.52 or (alpha_cnt / max(1, len(compact))) < 0.70 or noise_cnt >= 2:
            continue
        if alpha_cnt <= 3 and conf < 0.78:
            continue
        if bw > w * 0.72 and conf < 0.68:
            continue

        app = analyze_text_line_appearance(bgr, [bx, by, bw, bh])
        is_upper = sum(1 for c in compact if c.isupper()) >= max(2, int(len(compact) * 0.65))
        is_cond = (bh >= 28 and (bw / max(1, len(compact))) < bh * 0.75)
        font_match = match_local_font(
            app["estimated_weight"],
            is_italic=False,
            prefer_vietnamese=True,
            is_condensed_headline=is_cond,
            is_uppercase=is_upper,
        )

        # Save Original Raster Text Reference crop
        x1, y1, x2, y2 = max(0, bx), max(0, by), min(w, bx + bw), min(h, by + bh)
        crop_im = Image.fromarray(rgb[y1:y2, x1:x2], "RGB")
        orig_raster_rel = f"text_refs/orig_text_{idx:02d}.png"
        crop_im.save(os.path.join(project_dir, orig_raster_rel))

        is_stylized_top_logo = (by < h * 0.14 and bw < w * 0.30 and len(compact) <= 8)
        needs_confirm = conf < 0.88 or is_stylized_top_logo or any(ch in txt for ch in ("~", "|", "“", "_"))
        est_font_size = max(14, int(bh * 0.78))

        results.append({
            "index": idx,
            "ocr_text": txt,
            "confidence": conf,
            "bbox": [x1, y1, x2 - x1, y2 - y1],
            "baseline_y": ln.get("baseline_y", y2),
            "alignment": app["alignment"],
            "rotation": app["rotation"],
            "letter_spacing": app["letter_spacing_est"],
            "estimated_weight": app["estimated_weight"],
            "fill_color": app["fill_color"],
            "has_stroke_or_3d": app["has_stroke_or_3d"],
            "font_match": font_match,
            "font_size": est_font_size,
            "original_raster_file": orig_raster_rel,
            "needs_user_confirmation": needs_confirm,
            "warning": "Chữ có thể bị che/uốn cong hoặc OCR chưa chắc chắn — vui lòng xác nhận lại nội dung." if needs_confirm else "",
        })
    return results
