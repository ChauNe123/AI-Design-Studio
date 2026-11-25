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


def _match_background_grain(
    rebuilt_bgr: np.ndarray,
    orig_bgr: np.ndarray,
    mask_u8: np.ndarray,
    seed: int = 42,
) -> np.ndarray:
    """Measure true unmasked background high-frequency sensor grain and synthesize matching isotropic noise inside mask."""
    valid_bg = cv2.erode((mask_u8 == 0).astype(np.uint8) * 255, np.ones((7, 7), np.uint8), iterations=1) > 0
    if int(np.sum(valid_bg)) > 200:
        orig_f = orig_bgr.astype(np.float32)
        hf = orig_f - cv2.GaussianBlur(orig_f, (5, 5), 0)
        sigma = float(np.clip(np.std(hf[valid_bg]), 0.55, 1.6))
    else:
        sigma = 0.75
    rng = np.random.default_rng(seed)
    grain = rng.normal(0.0, sigma, rebuilt_bgr.shape).astype(np.float32)
    mask_f = (mask_u8 > 0).astype(np.float32)[:, :, None]
    out = np.clip(rebuilt_bgr.astype(np.float32) + grain * mask_f, 0.0, 255.0).astype(np.uint8)
    return out


def _run_lama_local(bgr: np.ndarray, bin_mask: np.ndarray) -> Optional[np.ndarray]:
    """Run local LaMa ONNX model cleanly with 2D Navier-Stokes pre-guidance for large masks and matched grain."""
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
                    return _match_background_grain(rebuilt, bgr, bin_mask)
            return None

        # Pre-guide large masked zones via 2D Navier-Stokes PDE before running LaMa scene pass + smoothly feathered local tiles
        guided_bgr = cv2.inpaint(bgr, (bin_mask > 0).astype(np.uint8) * 255, 18, cv2.INPAINT_NS)
        cv2.imencode(".png", guided_bgr)[1].tofile(in_p)
        cv2.imencode(".png", bin_mask)[1].tofile(m_p)
        res = subprocess.run(["node", BRIDGE_MJS, "lama_inpaint", in_p, m_p, out_p], capture_output=True, text=True, timeout=90, check=False)
        if res.returncode == 0 and os.path.exists(out_p):
            patch = _imread_unicode(out_p, cv2.IMREAD_COLOR)
            if patch is not None:
                work = np.where((bin_mask > 0)[:, :, None], cv2.resize(patch, (w, h), interpolation=cv2.INTER_LANCZOS4), bgr)
                # Blend boundary smoothly with 2D Navier-Stokes over 8px perimeter
                ns_edge_dt = cv2.distanceTransform((bin_mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
                w_global = np.clip(ns_edge_dt / 8.0, 0.0, 1.0)[:, :, None]
                work = np.where(
                    (bin_mask > 0)[:, :, None],
                    np.clip(work.astype(np.float32) * w_global + guided_bgr.astype(np.float32) * (1.0 - w_global), 0, 255).astype(np.uint8),
                    bgr,
                )
                # Refine local 512x512 patches ONLY where >= 65% unmasked context exists, using 32px cosine-tapered window (ZERO hard tile seams!)
                if w >= 512 and h >= 512:
                    tile_sz, step = 360, 280
                    # Prebuild smooth 512x512 raised-cosine edge taper (`40px` margin -> zero rectangular step edges)
                    win_1d = np.ones(512, dtype=np.float32)
                    ramp = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, 40, dtype=np.float32))
                    win_1d[:40] = ramp
                    win_1d[-40:] = ramp[::-1]
                    win_2d = (win_1d[:, None] * win_1d[None, :])[:, :, None]

                    for ty1 in range(0, max(1, h - tile_sz + 1), step):
                        ty2 = min(h, ty1 + tile_sz)
                        for tx1 in range(0, max(1, w - tile_sz + 1), step):
                            tx2 = min(w, tx1 + tile_sz)
                            sub_m = bin_mask[ty1:ty2, tx1:tx2]
                            if int(np.sum(sub_m > 0)) < 250:
                                continue
                            cx, cy = (tx1 + tx2) // 2, (ty1 + ty2) // 2
                            rx1 = max(0, min(w - 512, cx - 256))
                            ry1 = max(0, min(h - 512, cy - 256))
                            rx2, ry2 = rx1 + 512, ry1 + 512
                            tile_m = bin_mask[ry1:ry2, rx1:rx2]
                            # Strictly require >= 65% genuine unmasked pixels in 512x512 crop so LaMa never pulls murky fill across large blind spots
                            if float(np.mean(tile_m == 0)) < 0.65:
                                continue
                            cv2.imencode(".png", work[ry1:ry2, rx1:rx2])[1].tofile(in_p)
                            cv2.imencode(".png", tile_m)[1].tofile(m_p)
                            tr = subprocess.run(["node", BRIDGE_MJS, "lama_inpaint", in_p, m_p, out_p], capture_output=True, text=True, timeout=90, check=False)
                            if tr.returncode == 0 and os.path.exists(out_p):
                                t_patch = _imread_unicode(out_p, cv2.IMREAD_COLOR)
                                if t_patch is not None:
                                    t_patch = cv2.resize(t_patch, (512, 512), interpolation=cv2.INTER_LINEAR).astype(np.float32)
                                    t_dt = np.clip(cv2.distanceTransform((tile_m > 0).astype(np.uint8), cv2.DIST_L2, 5) / 10.0, 0.0, 1.0)[:, :, None]
                                    alpha_blend = np.where((tile_m > 0)[:, :, None], win_2d * t_dt, 0.0)
                                    cur_roi = work[ry1:ry2, rx1:rx2].astype(np.float32)
                                    blended = cur_roi * (1.0 - alpha_blend) + t_patch * alpha_blend
                                    work[ry1:ry2, rx1:rx2] = np.clip(blended, 0, 255).astype(np.uint8)
                return _match_background_grain(work, bgr, bin_mask)
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
    # 17px elliptical dilation (15-20px halo purge) to completely erase drop shadows and color bleed
    dilated = cv2.dilate(bin_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35)), iterations=1)
    coverage_pct = round(float(np.mean(dilated > 0)) * 100.0, 2)

    pixel_origin = "algorithmic_inpaint"
    used_provider = "local_engine"
    note = "Local 2D Navier-Stokes PDE + LaMa 2025jan ONNX + matched grain reconstruction."

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

    # Local algorithmic reconstruction: pure 2D structural Navier-Stokes / LaMa ONNX + uniform grain matching
    if mode == "gradient":
        inp_ns = cv2.inpaint(bgr, dilated, 15, cv2.INPAINT_NS)
        rebuilt = _match_background_grain(inp_ns, bgr, dilated)
        engine_used = "opencv-navier-stokes-2d"
    else:
        lama_out = _run_lama_local(bgr, dilated)
        if lama_out is not None:
            rebuilt = lama_out
            engine_used = "lama-2025jan-onnx-2d"
            if used_provider == "local_engine":
                note = "Local 2D Navier-Stokes guided LaMa 2025jan ONNX + matched grain reconstruction."
        else:
            rebuilt = _match_background_grain(cv2.inpaint(bgr, dilated, 15, cv2.INPAINT_NS), bgr, dilated)
            engine_used = "opencv-navier-stokes-2d"

    # Smooth boundary transition without touching unmasked pixels or blurring texture inside hole
    dist_out = cv2.distanceTransform((dilated > 0).astype(np.uint8), cv2.DIST_L2, 5)
    alpha_w = np.clip(dist_out / 5.0, 0.0, 1.0)[:, :, None]
    out_bgr = np.where(dilated[:, :, None] == 0, bgr, np.clip(bgr.astype(np.float32) * (1.0 - alpha_w) + rebuilt.astype(np.float32) * alpha_w, 0, 255).astype(np.uint8))

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
