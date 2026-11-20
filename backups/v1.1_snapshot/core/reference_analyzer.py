"""Design Knowledge Reference Analyzer — extracts structured layout, color, typography & lighting principles."""
import os
from typing import Any, Dict, List
import cv2
import numpy as np


def _rgb_to_hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def analyze_reference_image(image_path: str, ref_name: str = "") -> Dict[str, Any]:
    bgr = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Cannot read reference image: {image_path}")

    oh, ow = bgr.shape[:2]
    # Resize to standard analysis grid for deterministic performance
    aw, ah = 360, max(180, int(round(360 * (oh / max(1, ow)))))
    bgr_s = cv2.resize(bgr, (aw, ah), interpolation=cv2.INTER_AREA)
    rgb_s = cv2.cvtColor(bgr_s, cv2.COLOR_BGR2RGB)
    hsv_s = cv2.cvtColor(bgr_s, cv2.COLOR_BGR2HSV)
    gray_s = cv2.cvtColor(bgr_s, cv2.COLOR_BGR2GRAY)

    # 1. Color Palette via k-means (k=5)
    pixels = rgb_s.reshape(-1, 3).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 16, 1.0)
    _, labels, centers = cv2.kmeans(pixels, 5, None, criteria, 3, cv2.KMEANS_PP_CENTERS)
    counts = np.bincount(labels.flatten(), minlength=5)
    order = np.argsort(-counts)
    palette = []
    for idx in order:
        c = np.clip(centers[idx], 0, 255).astype(int)
        pct = round(float(counts[idx]) / len(labels) * 100.0, 1)
        palette.append({"hex": _rgb_to_hex(c), "rgb": [int(c[0]), int(c[1]), int(c[2])], "share_pct": pct})

    # Border dominant background vs most saturated accent
    border_rgb = np.vstack([rgb_s[0:8, :, :].reshape(-1, 3), rgb_s[-8:, :, :].reshape(-1, 3)])
    bg_med = np.median(border_rgb, axis=0).astype(int)
    bg_lum = float(0.299 * bg_med[0] + 0.587 * bg_med[1] + 0.114 * bg_med[2])
    mood = "dark" if bg_lum < 95 else ("light" if bg_lum > 185 else "vibrant")

    # Pick accent with highest saturation & distance from bg
    best_acc = palette[0]
    best_score = -1.0
    for p in palette:
        r, g, b = p["rgb"]
        mx, mn = max(r, g, b), min(r, g, b)
        sat = (mx - mn) / max(1.0, float(mx))
        dist = float(np.linalg.norm(np.array(p["rgb"]) - bg_med))
        sc = sat * 1.5 + (dist / 255.0)
        if sc > best_score:
            best_score = sc
            best_acc = p

    text_hex = "#FFFFFF" if bg_lum < 135 else "#0F172A"
    subtext_hex = "#CBD5E1" if bg_lum < 135 else "#334155"

    # 2. 3x3 Visual Weight & Whitespace Analysis
    gx = cv2.Sobel(gray_s, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray_s, cv2.CV_32F, 0, 1, ksize=3)
    energy = np.sqrt(gx * gx + gy * gy)
    whitespace_ratio = round(float(np.mean(energy < 18.0)) * 100.0, 1)

    grid_energy = np.zeros((3, 3), dtype=float)
    cell_h, cell_w = ah // 3, aw // 3
    for r in range(3):
        for c in range(3):
            patch = energy[r * cell_h:(r + 1) * cell_h, c * cell_w:(c + 1) * cell_w]
            grid_energy[r, c] = float(np.mean(patch))

    max_r, max_c = np.unravel_index(np.argmax(grid_energy), (3, 3))
    zone_names = [
        ["top_left", "top_center", "top_right"],
        ["mid_left", "center", "mid_right"],
        ["bottom_left", "bottom_center", "bottom_right"],
    ]
    focal_zone = zone_names[int(max_r)][int(max_c)]

    left_e = float(np.mean(grid_energy[:, 0]))
    right_e = float(np.mean(grid_energy[:, 2]))
    center_e = float(np.mean(grid_energy[:, 1]))
    symmetry_score = round(1.0 - min(1.0, abs(left_e - right_e) / max(1.0, left_e + right_e)), 2)

    # 3. Lighting & Shadow detection
    v_chan = hsv_s[:, :, 2].astype(np.float32)
    has_radial_glow = bool(np.percentile(v_chan, 95) - np.median(v_chan) > 55 and mood == "dark")
    has_strong_shadow = bool(np.percentile(v_chan, 10) < 35 and np.mean(v_chan) > 70)

    # 4. Typography band estimation (horizontal edge runs)
    row_energy = np.mean(energy, axis=1)
    top_text_band = bool(np.mean(row_energy[:ah // 3]) > np.mean(row_energy) * 0.7)
    bottom_cta_band = bool(np.mean(row_energy[int(ah * 0.8):]) > 10.0)

    # Suggest layout strategy based on structural principles (not pixel copying)
    if abs(left_e - right_e) > max(left_e, right_e) * 0.22:
        suggested_layout = "hero_split"
        product_zone = "right" if right_e >= left_e else "left"
    elif center_e >= max(left_e, right_e) * 0.95:
        suggested_layout = "tech_dark_glow" if mood == "dark" else "clean_card_modern"
        product_zone = "center_bottom"
    else:
        suggested_layout = "asymmetric_showcase"
        product_zone = focal_zone

    style_tags = [
        f"mood_{mood}",
        f"layout_{suggested_layout}",
        f"focal_{focal_zone}",
        "high_whitespace" if whitespace_ratio > 55 else "dense_composition",
    ]
    if has_radial_glow:
        style_tags.append("radial_glow")
    if has_strong_shadow:
        style_tags.append("drop_shadow")

    return {
        "name": ref_name or os.path.basename(image_path),
        "source_size": f"{ow}x{oh}",
        "aspect_ratio": round(ow / max(1, oh), 2),
        "palette": {
            "bg_hex": _rgb_to_hex(bg_med),
            "bg_alt_hex": palette[1]["hex"] if len(palette) > 1 else _rgb_to_hex(bg_med),
            "accent_hex": best_acc["hex"],
            "text_hex": text_hex,
            "subtext_hex": subtext_hex,
            "dominant_colors": palette,
        },
        "visual_hierarchy": {
            "mood": mood,
            "whitespace_pct": whitespace_ratio,
            "focal_zone": focal_zone,
            "product_zone": product_zone,
            "symmetry_score": symmetry_score,
            "top_text_band": top_text_band,
            "bottom_cta_band": bottom_cta_band,
            "suggested_layout": suggested_layout,
        },
        "lighting_and_shadow": {
            "radial_glow": has_radial_glow,
            "contact_shadow": has_strong_shadow,
        },
        "style_tags": style_tags,
        "design_principles_extracted": [
            f"Bố cục đề xuất: {suggested_layout} (trọng tâm tại {focal_zone}, khoảng trắng {whitespace_ratio}%).",
            f"Tông màu chủ đạo: nền { _rgb_to_hex(bg_med) } ({mood}), màu nhấn {best_acc['hex']}, chữ {text_hex}.",
            f"Ánh sáng & bóng: {'Có radial glow' if has_radial_glow else 'Ánh sáng phẳng đều'}, {'có bóng đổ tách khối' if has_strong_shadow else 'bóng nhẹ'}.",
        ],
    }
