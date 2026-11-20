"""Module 4: AI Reconstruction & Inpainting Engine — distinguishes original vs algorithmic vs AI pixels."""
import json
import os
import subprocess
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional
import cv2
import numpy as np
from PIL import Image

STUDIO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGE_MJS = os.path.join(STUDIO_ROOT, "core", "ai_vision_bridge.mjs")
LAMA_ONNX = os.path.join(STUDIO_ROOT, "models", "lama", "inpainting_lama_2025jan.onnx")


def _imread_unicode(path: str, flags=cv2.IMREAD_COLOR):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), flags)


def _run_lama_local(bgr: np.ndarray, bin_mask: np.ndarray) -> Optional[np.ndarray]:
    """Run local LaMa ONNX model cleanly. Uses native 512x512 crop for small holes, global 512x512 for large masks."""
    if not os.path.exists(LAMA_ONNX):
        return None
    h, w = bgr.shape[:2]
    ys, xs = np.where(bin_mask > 0)
    if len(xs) == 0:
        return bgr.copy()

    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    bw, bh = x2 - x1, y2 - y1

    with tempfile.TemporaryDirectory() as td:
        in_p = os.path.join(td, "in.png")
        m_p = os.path.join(td, "mask.png")
        out_p = os.path.join(td, "out.png")

        if bw <= 420 and bh <= 420 and w >= 512 and h >= 512:
            # 1:1 native 512x512 crop centered around the hole for maximum sharpness!
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            rx1 = max(0, min(w - 512, cx - 256))
            ry1 = max(0, min(h - 512, cy - 256))
            rx2, ry2 = rx1 + 512, ry1 + 512
            cv2.imencode(".png", bgr[ry1:ry2, rx1:rx2])[1].tofile(in_p)
            cv2.imencode(".png", bin_mask[ry1:ry2, rx1:rx2])[1].tofile(m_p)
            res = subprocess.run(["node", BRIDGE_MJS, "lama_inpaint", in_p, m_p, out_p], capture_output=True, text=True, timeout=90, check=False)
            if res.returncode == 0 and os.path.exists(out_p):
                patch = _imread_unicode(out_p, cv2.IMREAD_COLOR)
                if patch is not None:
                    rebuilt = bgr.copy()
                    rebuilt[ry1:ry2, rx1:rx2] = cv2.resize(patch, (512, 512), interpolation=cv2.INTER_LINEAR)
                    return rebuilt
            return None

        # Global scene context for large masks -> resize ONLY inside mask back cleanly
        cv2.imencode(".png", bgr)[1].tofile(in_p)
        cv2.imencode(".png", bin_mask)[1].tofile(m_p)
        res = subprocess.run(["node", BRIDGE_MJS, "lama_inpaint", in_p, m_p, out_p], capture_output=True, text=True, timeout=90, check=False)
        if res.returncode == 0 and os.path.exists(out_p):
            patch = _imread_unicode(out_p, cv2.IMREAD_COLOR)
            if patch is not None:
                return cv2.resize(patch, (w, h), interpolation=cv2.INTER_LANCZOS4)
    return None


def reconstruct_region(
    image_path: str,
    mask_path: str,
    out_image_path: str,
    mode: str = "auto",
    provider_mgr=None,
    provider_id: str = "local_engine",
    user_confirmed: bool = False,
    prompt: str = "",
) -> Dict[str, Any]:
    """Reconstruct occluded background/texture/gradient behind a removed object mask.
    Explicitly records pixel_origin: 'algorithmic_inpaint' (local) or 'ai_generated' (cloud).
    """
    bgr = _imread_unicode(image_path, cv2.IMREAD_COLOR)
    mask = _imread_unicode(mask_path, cv2.IMREAD_GRAYSCALE)
    if bgr is None or mask is None:
        raise ValueError("Cannot read image or mask for reconstruction")

    h, w = bgr.shape[:2]
    if mask.shape[:2] != (h, w):
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)

    _, bin_mask = cv2.threshold(mask, 64, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(bin_mask, np.ones((9, 9), np.uint8), iterations=1)
    coverage_pct = round(float(np.mean(dilated > 0)) * 100.0, 2)

    pixel_origin = "algorithmic_inpaint"
    used_provider = "local_engine"
    note = "Local multi-scale LAB-guided Telea + gradient/texture blend reconstruction."

    # Optional Cloud API path (ONLY when user explicitly enables HYBRID + confirms upload)
    if provider_mgr is not None and provider_id != "local_engine":
        cloud_res = provider_mgr.execute_cloud_inpaint(
            provider_id=provider_id,
            image_path=image_path,
            mask_path=mask_path,
            prompt=prompt or "Seamlessly reconstruct background behind removed object",
            user_confirmed=user_confirmed,
        )
        if cloud_res.get("ok"):
            pixel_origin = "ai_generated"
            used_provider = provider_id
            note = f"Cloud generative inpainting via {provider_id}."
        else:
            note = f"Cloud skipped/fallback ({cloud_res.get('error', 'unavailable')}); executed local algorithmic fallback."

    # Local algorithmic reconstruction (prefer LaMa 2025jan ONNX when available, fallback to OpenCV Telea)
    if mode == "gradient":
        # Smooth multi-pass blur interpolation for sky/gradient backdrops
        sm = cv2.resize(bgr, (max(32, w // 8), max(32, h // 8)), interpolation=cv2.INTER_AREA)
        sm_m = cv2.resize(dilated, (sm.shape[1], sm.shape[0]), interpolation=cv2.INTER_NEAREST)
        inp_sm = cv2.inpaint(sm, sm_m, 7, cv2.INPAINT_NS)
        inp_sm = cv2.GaussianBlur(inp_sm, (11, 11), 0)
        rebuilt = cv2.resize(inp_sm, (w, h), interpolation=cv2.INTER_CUBIC)
        engine_used = "opencv-navier-gradient"
    else:
        lama_out = _run_lama_local(bgr, dilated)
        if lama_out is not None:
            rebuilt = lama_out
            engine_used = "lama-2025jan-onnx"
            if used_provider == "local_engine":
                note = "Local LaMa 2025jan ONNX neural inpainting reconstruction."
        else:
            scale = min(1.0, 640.0 / max(w, h))
            sw, sh = max(64, int(w * scale)), max(64, int(h * scale))
            bgr_sm = cv2.resize(bgr, (sw, sh), interpolation=cv2.INTER_AREA)
            m_sm = cv2.resize(dilated, (sw, sh), interpolation=cv2.INTER_NEAREST)
            inp_sm = cv2.inpaint(bgr_sm, m_sm, 7, cv2.INPAINT_TELEA)
            rebuilt = cv2.resize(inp_sm, (w, h), interpolation=cv2.INTER_CUBIC)
            blur_bg = cv2.GaussianBlur(rebuilt, (19, 19), 0)
            rebuilt = (rebuilt * 0.65 + blur_bg * 0.35).astype(np.uint8)
            engine_used = "opencv-telea"

    # Feather transition ONLY at the mask boundary so original unmasked pixels stay 100% untouched
    alpha_w = (cv2.GaussianBlur(dilated.astype(np.float32), (9, 9), 0) / 255.0)[:, :, None]
    out_bgr = np.where(dilated[:, :, None] == 0, bgr, (bgr * (1.0 - alpha_w) + rebuilt * alpha_w).astype(np.uint8))

    os.makedirs(os.path.dirname(out_image_path), exist_ok=True)
    out_rgb = cv2.cvtColor(out_bgr, cv2.COLOR_BGR2RGB)
    Image.fromarray(out_rgb, "RGB").save(out_image_path)

    ys, xs = np.where(dilated > 0)
    region_box = [int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1)] if len(xs) else [0, 0, 0, 0]

    history_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "pixel_origin": pixel_origin,
        "provider": used_provider,
        "engine": engine_used,
        "mode": mode,
        "region": region_box,
        "coverage_pct": coverage_pct,
        "note": note,
    }
    return {
        "ok": True,
        "out_image_path": out_image_path,
        "pixel_origin": pixel_origin,
        "provider": used_provider,
        "engine": engine_used,
        "coverage_pct": coverage_pct,
        "history_entry": history_entry,
    }
