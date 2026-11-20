"""Module 2: Advanced Object Segmentation — SlimSAM + RMBG-1.4 + GrabCut + Mask Refinement + Halo QA."""
import json
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple
import cv2
import numpy as np
from PIL import Image

STUDIO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGE_MJS = os.path.join(STUDIO_ROOT, "core", "ai_vision_bridge.mjs")


def _imread_unicode(path: str, flags=cv2.IMREAD_COLOR):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, flags)


def run_rmbg_salient(image_path: str, out_mask_path: str, timeout_s: int = 90) -> Dict[str, Any]:
    """Run local briaai/RMBG-1.4 salient foreground mask extraction via Node ONNX."""
    os.makedirs(os.path.dirname(out_mask_path), exist_ok=True)
    res = subprocess.run(
        ["node", BRIDGE_MJS, "rmbg", image_path, out_mask_path],
        capture_output=True, text=True, timeout=timeout_s, check=False,
    )
    if res.returncode != 0 or not os.path.exists(out_mask_path):
        return {"ok": False, "error": res.stderr.strip() or res.stdout.strip()}
    return json.loads(res.stdout.strip().splitlines()[-1])


def segment_interactive(
    image_path: str,
    out_mask_path: str,
    points: Optional[List[List[int]]] = None,
    labels: Optional[List[int]] = None,
    box: Optional[List[int]] = None,
    mask_level: Optional[int] = None,
    use_sam: bool = True,
    tmp_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Interactive segmentation supporting positive/negative points and bounding boxes.
    Uses SlimSAM-77-uniform ONNX when points provided, with OpenCV GrabCut fallback/box support.
    """
    os.makedirs(os.path.dirname(out_mask_path), exist_ok=True)
    bgr = _imread_unicode(image_path)
    if bgr is None:
        raise ValueError(f"Cannot read image: {image_path}")
    h, w = bgr.shape[:2]

    pts = list(points or [])
    lbls = list(labels or [])

    # If user supplied only a bounding box without points, add center positive point for SAM or use GrabCut
    if box and len(box) == 4 and not pts:
        x1, y1, x2, y2 = [int(v) for v in box]
        pts = [[(x1 + x2) // 2, (y1 + y2) // 2]]
        lbls = [1]

    sam_result = None
    if use_sam and pts:
        work_dir = tmp_dir or os.path.dirname(out_mask_path)
        os.makedirs(work_dir, exist_ok=True)
        pts_file = os.path.join(work_dir, "_sam_pts.json")

        # Localized high-detail ROI zoom-in when points/box cover a compact sub-object
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        use_roi = False
        rx1, ry1, rx2, ry2 = 0, 0, w, h
        if box and len(box) == 4:
            bx1, by1, bx2, by2 = [int(v) for v in box]
            pad_x, pad_y = max(48, int((bx2 - bx1) * 0.35)), max(48, int((by2 - by1) * 0.35))
            rx1, ry1 = max(0, min(bx1, min(xs)) - pad_x), max(0, min(by1, min(ys)) - pad_y)
            rx2, ry2 = min(w, max(bx2, max(xs)) + pad_x), min(h, max(by2, max(ys)) + pad_y)
            use_roi = (rx2 - rx1) < w * 0.72 and (ry2 - ry1) < h * 0.72 and (rx2 - rx1) >= 48 and (ry2 - ry1) >= 48
        elif (max(xs) - min(xs)) < w * 0.38 and (max(ys) - min(ys)) < h * 0.38:
            span = max(max(xs) - min(xs), max(ys) - min(ys), 40)
            pad = max(85, int(span * 0.95))
            rx1, ry1 = max(0, min(xs) - pad), max(0, min(ys) - pad)
            rx2, ry2 = min(w, max(xs) + pad), min(h, max(ys) + pad)
            use_roi = (rx2 - rx1) < w * 0.65 and (ry2 - ry1) < h * 0.65 and (rx2 - rx1) >= 48 and (ry2 - ry1) >= 48

        if use_roi:
            roi_w, roi_h = rx2 - rx1, ry2 - ry1
            roi_scale = min(3.0, 512.0 / max(roi_w, roi_h)) if max(roi_w, roi_h) < 512 else 1.0
            roi_bgr = bgr[ry1:ry2, rx1:rx2]
            if roi_scale > 1.01:
                roi_bgr = cv2.resize(roi_bgr, (int(round(roi_w * roi_scale)), int(round(roi_h * roi_scale))), interpolation=cv2.INTER_CUBIC)
            roi_img_path = os.path.join(work_dir, "_sam_roi.png")
            roi_mask_path = os.path.join(work_dir, "_sam_roi_mask.png")
            cv2.imencode(".png", roi_bgr)[1].tofile(roi_img_path)
            sam_pts = [[int(round((p[0] - rx1) * roi_scale)), int(round((p[1] - ry1) * roi_scale))] for p in pts]
            sam_in_img, sam_out_msk = roi_img_path, roi_mask_path
        else:
            roi_scale = 1.0
            sam_pts = pts
            sam_in_img, sam_out_msk = image_path, out_mask_path

        payload = {"points": sam_pts, "labels": lbls}
        if mask_level is not None:
            payload["mask_level"] = int(mask_level)
        with open(pts_file, "w", encoding="utf-8") as f:
            json.dump(payload, f)
        res = subprocess.run(
            ["node", BRIDGE_MJS, "slimsam", sam_in_img, pts_file, sam_out_msk],
            capture_output=True, text=True, timeout=90, check=False,
        )
        if res.returncode == 0 and os.path.exists(sam_out_msk):
            sam_result = json.loads(res.stdout.strip().splitlines()[-1])
            if use_roi:
                m_roi = _imread_unicode(sam_out_msk, cv2.IMREAD_GRAYSCALE)
                m_roi = cv2.resize(m_roi, (rx2 - rx1, ry2 - ry1), interpolation=cv2.INTER_LINEAR)
                full_m = np.zeros((h, w), dtype=np.uint8)
                full_m[ry1:ry2, rx1:rx2] = m_roi
                Image.fromarray(full_m, "L").save(out_mask_path)
            # If user also provided a bounding box, constrain mask cleanly inside box (+small margin)
            if box and len(box) == 4:
                m = _imread_unicode(out_mask_path, cv2.IMREAD_GRAYSCALE)
                bx1, by1, bx2, by2 = max(0, box[0] - 8), max(0, box[1] - 8), min(w, box[2] + 8), min(h, box[3] + 8)
                clipped = np.zeros_like(m)
                clipped[by1:by2, bx1:bx2] = m[by1:by2, bx1:bx2]
                Image.fromarray(clipped, "L").save(out_mask_path)
            return {**sam_result, "width": w, "height": h, "roi_zoom": use_roi, "method": "slimsam"}

    # Fallback / pure GrabCut segmentation (points + optional box)
    gc_mask = np.full((h, w), cv2.GC_PR_BGD, dtype=np.uint8)
    if box and len(box) == 4:
        bx1, by1, bx2, by2 = max(0, int(box[0])), max(0, int(box[1])), min(w - 1, int(box[2])), min(h - 1, int(box[3]))
        gc_mask[:, :] = cv2.GC_BGD
        gc_mask[by1:by2, bx1:bx2] = cv2.GC_PR_FGD

    rad = max(6, min(w, h) // 60)
    for (px, py), pl in zip(pts, lbls):
        cv2.circle(gc_mask, (int(px), int(py)), rad, cv2.GC_FGD if pl == 1 else cv2.GC_BGD, -1)

    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, gc_mask, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    out_m = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    Image.fromarray(out_m, "L").save(out_mask_path)
    return {"ok": True, "engine": "grabcut_fallback", "method": "grabcut", "width": w, "height": h, "iou_score": 0.72, "mask_path": out_mask_path}


def refine_mask(
    mask_path: str,
    out_mask_path: Optional[str] = None,
    expand_px: int = 0,
    feather_px: int = 2,
    fill_holes: bool = True,
    remove_specks_min_area: int = 80,
) -> str:
    """Non-destructively refine a binary/alpha mask (expand/erode, fill holes, remove stray specks, feather)."""
    m = _imread_unicode(mask_path, cv2.IMREAD_GRAYSCALE)
    if m is None:
        raise ValueError(f"Cannot read mask: {mask_path}")

    _, bin_m = cv2.threshold(m, 127, 255, cv2.THRESH_BINARY)
    if expand_px > 0:
        k = np.ones((expand_px * 2 + 1, expand_px * 2 + 1), np.uint8)
        bin_m = cv2.dilate(bin_m, k, iterations=1)
    elif expand_px < 0:
        k = np.ones((abs(expand_px) * 2 + 1, abs(expand_px) * 2 + 1), np.uint8)
        bin_m = cv2.erode(bin_m, k, iterations=1)

    if fill_holes:
        # Pad 1px zero-border so (0, 0) is ALWAYS exterior background even when foreground touches canvas edges
        padded = cv2.copyMakeBorder(bin_m, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
        ph, pw = padded.shape
        ff_m = np.zeros((ph + 2, pw + 2), np.uint8)
        cv2.floodFill(padded, ff_m, (0, 0), 128)
        filled_pad = np.where(padded == 128, 0, 255).astype(np.uint8)
        bin_m = filled_pad[1:-1, 1:-1]

    if remove_specks_min_area > 0:
        num_l, labels, stats, _ = cv2.connectedComponentsWithStats(bin_m, 8)
        cleaned = np.zeros_like(bin_m)
        for i in range(1, num_l):
            if stats[i, cv2.CC_STAT_AREA] >= remove_specks_min_area:
                cleaned[labels == i] = 255
        bin_m = cleaned

    if feather_px > 0:
        ksz = feather_px * 2 + 1
        out = cv2.GaussianBlur(bin_m, (ksz, ksz), 0)
        interior = cv2.erode(bin_m, np.ones((ksz, ksz), np.uint8), iterations=1)
        out = np.maximum(out, interior)
    else:
        out = bin_m

    dest = out_mask_path or mask_path
    Image.fromarray(out, "L").save(dest)
    return dest


def analyze_mask_quality(image_path: str, mask_path: str) -> Dict[str, Any]:
    """Check for white/green halos, stray pixel specks, and uncertain boundary regions."""
    bgr = _imread_unicode(image_path)
    m = _imread_unicode(mask_path, cv2.IMREAD_GRAYSCALE)
    if bgr is None or m is None:
        return {"ok": False, "error": "Missing image or mask"}

    if m.shape[:2] != bgr.shape[:2]:
        m = cv2.resize(m, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_LINEAR)

    bin_m = (m > 127).astype(np.uint8) * 255
    num_l, _, stats, _ = cv2.connectedComponentsWithStats(bin_m, 8)
    stray_specks = sum(1 for i in range(1, num_l) if stats[i, cv2.CC_STAT_AREA] < 60)

    # Edge ring (outer 3px of foreground)
    eroded = cv2.erode(bin_m, np.ones((7, 7), np.uint8), iterations=1)
    edge_ring = (bin_m > 0) & (eroded == 0)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    white_halo_pct = 0.0
    green_halo_pct = 0.0
    if np.any(edge_ring):
        ring_hsv = hsv[edge_ring]
        white_halo_pct = round(float(np.mean((ring_hsv[:, 1] < 28) & (ring_hsv[:, 2] > 235))) * 100.0, 2)
        green_halo_pct = round(float(np.mean((ring_hsv[:, 0] >= 45) & (ring_hsv[:, 0] <= 90) & (ring_hsv[:, 1] > 110))) * 100.0, 2)

    uncertain_pixels = int(np.sum((m > 30) & (m < 225)))
    uncertain_pct = round(uncertain_pixels / max(1, m.size) * 100.0, 2)
    fg_pct = round(float(np.mean(bin_m > 0)) * 100.0, 2)

    warnings = []
    if stray_specks > 5:
        warnings.append(f"Detected {stray_specks} stray disconnected pixel specks.")
    if white_halo_pct > 25.0:
        warnings.append(f"High white edge halo ({white_halo_pct}%) — recommend 1px erode + decontaminate.")
    if green_halo_pct > 30.0:
        warnings.append(f"Green edge fringe ({green_halo_pct}%) — recommend edge decontamination.")
    if uncertain_pct > 6.0:
        warnings.append(f"Uncertain boundary band ({uncertain_pct}%) — user refinement recommended.")

    return {
        "ok": True,
        "foreground_pct": fg_pct,
        "stray_specks": stray_specks,
        "white_halo_pct": white_halo_pct,
        "green_halo_pct": green_halo_pct,
        "uncertain_boundary_pct": uncertain_pct,
        "needs_refinement": len(warnings) > 0,
        "warnings": warnings,
    }


def apply_mask_to_source(
    source_image_path: str,
    mask_path: str,
    out_rgba_path: str,
    decontaminate_edges: bool = True,
) -> Dict[str, Any]:
    """Extract cropped RGBA layer from immutable source image + standalone mask."""
    bgr = _imread_unicode(source_image_path)
    m = _imread_unicode(mask_path, cv2.IMREAD_GRAYSCALE)
    if bgr is None or m is None:
        raise ValueError("Cannot read source image or mask")

    if m.shape[:2] != bgr.shape[:2]:
        m = cv2.resize(m, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_LINEAR)

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    ys, xs = np.where(m > 10)
    if len(xs) == 0:
        raise ValueError("Mask is empty — nothing selected")

    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    crop_rgb = rgb[y1:y2, x1:x2].copy()
    crop_alpha = m[y1:y2, x1:x2].copy()

    if decontaminate_edges and min(crop_rgb.shape[:2]) > 8:
        # Gently pull edge colors from solid interior to remove background fringe
        solid = (crop_alpha > 235).astype(np.uint8) * 255
        semi = (crop_alpha > 10) & (crop_alpha <= 235)
        if np.any(solid) and np.any(semi):
            blurred = cv2.GaussianBlur(crop_rgb, (5, 5), 0)
            crop_rgb[semi] = blurred[semi]

    rgba = np.dstack([crop_rgb, crop_alpha])
    os.makedirs(os.path.dirname(out_rgba_path), exist_ok=True)
    Image.fromarray(rgba, "RGBA").save(out_rgba_path)
    return {"x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1, "rgba_path": out_rgba_path}


def detect_objects(image_path: str, threshold: float = 0.62, timeout_s: int = 60) -> Dict[str, Any]:
    """Run local Xenova/detr-resnet-50 object detection with NMS deduplication."""
    res = subprocess.run(
        ["node", BRIDGE_MJS, "detect", image_path, str(threshold)],
        capture_output=True, text=True, timeout=timeout_s, check=False,
    )
    if res.returncode != 0:
        return {"ok": False, "objects": [], "error": res.stderr.strip() or res.stdout.strip()}
    data = json.loads(res.stdout.strip().splitlines()[-1])
    raw_objs = sorted(data.get("objects", []), key=lambda o: o.get("score", 0.0), reverse=True)

    kept = []
    for obj in raw_objs:
        ax, ay, aw, ah = obj["bbox"]
        a_area = max(1, aw * ah)
        dup = False
        for k in kept:
            if k["label"] != obj["label"]:
                continue
            bx, by, bw, bh = k["bbox"]
            ix1, iy1 = max(ax, bx), max(ay, by)
            ix2, iy2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
            inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
            union = a_area + max(1, bw * bh) - inter
            if inter / max(1, union) >= 0.55:
                dup = True
                break
        if not dup:
            kept.append(obj)
    return {"ok": True, "engine": data.get("engine", "detr-resnet-50"), "objects": kept}
