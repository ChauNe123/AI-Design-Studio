# -*- coding: utf-8 -*-
"""AI Design Studio v1.5 — Garena Esports & Graphic Banner 5-Module Reverse-Engineering Engine.

Implements the 5-Module Reverse-Engineering Architecture analyzed from `Banner Công bố.psd`:
  Module 1: Dual-Version Typography (Visible OrigFX Bitmap + Hidden Editable Vector TySh + LayerFX) & Skewed Ribbons
  Module 2: Multi-Object Podium & Prize Decomposition (SlimSAM-77 ROI + Amodal Podium Top Inpainting)
  Module 3: Peripheral Decor, 3D Gaming Gear, Logos, Stars & Confetti Extraction (+ LayerFX)
  Module 4: Sequential LaMa Neural Background Reconstruction (Clean Stadium + Clouds + Live Atmosphere Stack)
  Module 5: Structured Multi-Group Photoshop PSD Packaging + 4-Step Progression Grid & Checkerboard Contact Sheet
"""
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw

from core.design_document import (
    create_document,
    make_layer,
    make_semantic_object,
    save_document,
)
from core.project_manager import save_version
from core.reconstruction_engine import _run_lama_local
from core.segmentation_engine import (
    _imread_unicode,
    refine_mask,
    run_rmbg_salient,
    segment_interactive,
)
from core.typography_engine import extract_typography_objects, list_local_fonts, render_styled_text


def _save_rgba(rgba: np.ndarray, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.clip(rgba, 0, 255).astype(np.uint8), "RGBA").save(path)
    return path


def _save_rgb(rgb: np.ndarray, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB").save(path)
    return path


def _save_gray(gray: np.ndarray, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    Image.fromarray(np.clip(gray, 0, 255).astype(np.uint8), "L").save(path)
    return path


def _tight_crop_rgba(
    src_rgb: np.ndarray,
    alpha_u8: np.ndarray,
    pad: int = 2,
    decontaminate: bool = True,
) -> Optional[Tuple[int, int, int, int, np.ndarray]]:
    """Crop RGBA region tightly where alpha > 12; optionally decolorize translucent rim."""
    h, w = src_rgb.shape[:2]
    ys, xs = np.where(alpha_u8 > 14)
    if len(xs) < 12:
        return None
    x1 = max(0, int(xs.min()) - pad)
    y1 = max(0, int(ys.min()) - pad)
    x2 = min(w, int(xs.max()) + 1 + pad)
    y2 = min(h, int(ys.max()) + 1 + pad)
    bw, bh = x2 - x1, y2 - y1
    if bw < 4 or bh < 4:
        return None

    crop_rgb = src_rgb[y1:y2, x1:x2].copy()
    crop_a = alpha_u8[y1:y2, x1:x2].copy()
    if decontaminate and min(bw, bh) > 8:
        solid = crop_a > 230
        semi = (crop_a > 12) & (crop_a <= 230)
        if np.any(solid) and np.any(semi):
            blurred = cv2.GaussianBlur(crop_rgb, (5, 5), 0)
            crop_rgb[semi] = blurred[semi]
    rgba = np.dstack([crop_rgb, crop_a])
    return x1, y1, bw, bh, rgba


def _pick_display_font(prefer_bold_display: bool = True) -> Tuple[str, str]:
    fonts = list_local_fonts()
    if not fonts:
        return "Arial-BoldMT", ""
    prefs = ["Anton", "Be Vietnam Pro Black", "Be Vietnam Pro ExtraBold", "FZ Poppins Bold", "FZ Poppins"] if prefer_bold_display else ["Be Vietnam Pro Bold", "FZ Poppins", "Segoe UI"]
    for want in prefs:
        hit = next((f for f in fonts if want.lower() in f["name"].lower()), None)
        if hit:
            return hit["name"], hit["file"]
    return fonts[0]["name"], fonts[0]["file"]


def _flood_outside_bg(bgr: np.ndarray, thresh: float = 20.0) -> np.ndarray:
    """Return foreground binary mask (255=fg, 0=border-connected background) protecting interior whites."""
    h, w = bgr.shape[:2]
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    border = np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]], axis=0)
    dom = np.median(border, axis=0)
    dist = np.linalg.norm(lab - dom, axis=2)
    bg_cand = (dist < thresh).astype(np.uint8) * 255
    padded = cv2.copyMakeBorder(bg_cand, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=255)
    ff = np.zeros((padded.shape[0] + 2, padded.shape[1] + 2), np.uint8)
    cv2.floodFill(padded, ff, (0, 0), 128)
    fg = np.where(padded[1:-1, 1:-1] == 128, 0, 255).astype(np.uint8)
    return fg


class BannerDecomposer:
    """5-Module Esports & Graphic Banner Reverse-Engineering Pipeline."""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.layers_dir = os.path.join(project_dir, "layers")
        self.masks_dir = os.path.join(project_dir, "masks")
        os.makedirs(self.layers_dir, exist_ok=True)
        os.makedirs(self.masks_dir, exist_ok=True)
        self.z_counter = 10  # Leave 0..9 for Background & Atmosphere stack
        self.doc_layers: List[Dict[str, Any]] = []
        self.semantic_objects: List[Dict[str, Any]] = []

    def _add_raster_layer(
        self,
        name: str,
        layer_type: str,
        group: str,
        src_rgb: np.ndarray,
        mask_u8: np.ndarray,
        cat: str,
        confidence: float = 0.90,
        psd_effects: Optional[Dict[str, Any]] = None,
        visible: bool = True,
        z_override: Optional[int] = None,
        decontaminate: bool = True,
    ) -> Optional[Dict[str, Any]]:
        cropped = _tight_crop_rgba(src_rgb, mask_u8, pad=2, decontaminate=decontaminate)
        if not cropped:
            return None
        x, y, bw, bh, rgba = cropped
        safe_name = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
        rel_img = f"layers/{safe_name}_{uuid.uuid4().hex[:4]}.png"
        _save_rgba(rgba, os.path.join(self.project_dir, rel_img))

        rel_msk = f"masks/m_{safe_name}_{uuid.uuid4().hex[:4]}.png"
        _save_gray(mask_u8[y:y + bh, x:x + bw], os.path.join(self.project_dir, rel_msk))

        z_val = z_override if z_override is not None else self.z_counter
        if z_override is None:
            self.z_counter += 1

        lyr = make_layer(
            name=name,
            layer_type=layer_type,
            source_file=rel_img,
            mask_file=rel_msk,
            x=x,
            y=y,
            width=bw,
            height=bh,
            z_index=z_val,
            visible=visible,
            group=group,
            psd_effects=psd_effects,
            confidence_score=confidence,
            metadata={"banner_module": cat},
        )
        self.doc_layers.append(lyr)
        self.semantic_objects.append(make_semantic_object(
            object_id=f"obj_{safe_name}_{z_val}",
            object_name=name,
            object_category=cat,
            bounding_box=[x, y, bw, bh],
            z_index=z_val,
            confidence_score=confidence,
            segmentation_mask=rel_msk,
            source_asset=rel_img,
            reconstruction_status="extracted_banner_element",
            editability_status="layer_and_fx_editable" if psd_effects else "raster_editable",
            linked_layer_id=lyr["id"],
        ))
        return lyr

    def _add_backup_text_layer(
        self,
        name: str,
        text_str: str,
        x: int,
        y: int,
        font_size: int,
        color: List[int],
        group: str = "6_Typography_OrigFX_&_Editable",
        align: str = "center",
        stroke_enabled: bool = True,
        stroke_color: Optional[List[int]] = None,
        stroke_width: int = 4,
        gradient_enabled: bool = False,
        gradient_c2: Optional[List[int]] = None,
        psd_effects: Optional[Dict[str, Any]] = None,
        prefer_display_font: bool = True,
        confidence: float = 0.90,
        visible: bool = False,
    ) -> Dict[str, Any]:
        font_name, font_file = _pick_display_font(prefer_bold_display=prefer_display_font)
        s_col = stroke_color or [255, 255, 255]
        g_c2 = gradient_c2 or [80, 255, 160]
        ed_im = render_styled_text(
            text=text_str,
            font_file=font_file,
            font_size=max(14, int(font_size)),
            color=tuple(color[:3]),
            align=align,
            stroke_enabled=stroke_enabled,
            stroke_color=tuple(s_col[:3]),
            stroke_width=stroke_width,
            shadow_enabled=False,  # Handled natively via live Photoshop LayerFX!
            gradient_enabled=gradient_enabled,
            gradient_c2=tuple(g_c2[:3]),
        )
        safe = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
        rel = f"layers/{safe}_{uuid.uuid4().hex[:4]}.png"
        ed_im.save(os.path.join(self.project_dir, rel))
        z_val = self.z_counter
        self.z_counter += 1

        lyr = make_layer(
            name=name,
            layer_type="text",
            source_file=rel,
            x=max(0, x),
            y=max(0, y),
            width=ed_im.width,
            height=ed_im.height,
            z_index=z_val,
            visible=visible,
            group=group,
            psd_effects=psd_effects,
            text_data={
                "text": text_str,
                "font": font_name,
                "font_file": font_file,
                "font_size": int(font_size),
                "color": color,
                "align": align,
                "tracking": 0,
                "leading": 8,
                "stroke_enabled": stroke_enabled,
                "stroke_color": s_col,
                "stroke_width": stroke_width,
                "gradient_enabled": gradient_enabled,
                "gradient_c2": g_c2,
                "shadow_enabled": False,
                "glow_enabled": False,
                "extrude_3d_depth": 0,
            },
            text_reconstruction={
                "ocr_text": text_str,
                "ocr_confidence": confidence,
                "estimated_font": font_name,
                "matched_font_file": font_file,
                "dual_strategy": "hidden_editable_vector_with_live_layerfx",
                "needs_user_confirmation": False,
            },
            confidence_score=confidence,
        )
        self.doc_layers.append(lyr)
        return lyr

    # ------------------------------------------------------------------
    # MODULE 2: 3 Isometric Podiums (+ Amodal Top Fill) & Prize Items
    # ------------------------------------------------------------------
    def _decompose_podiums_and_prizes(
        self,
        bgr: np.ndarray,
        rgb: np.ndarray,
        hsv: np.ndarray,
        lab: np.ndarray,
        src_ref_path: str,
        rmbg_salient_u8: np.ndarray,
    ) -> np.ndarray:
        """Extract 3 Isometric Podiums with Amodal Top Completion + All Prize Sub-Items."""
        h, w = bgr.shape[:2]
        claimed_all = np.zeros((h, w), dtype=np.uint8)

        # 1. Detect Warm Orange-Gold Isometric 3D Podiums in y in [58%..83.8%]
        podium_raw = (
            (hsv[:, :, 0] >= 10)
            & (hsv[:, :, 0] <= 26)
            & (hsv[:, :, 1] >= 135)
            & (hsv[:, :, 2] >= 165)
        ).astype(np.uint8) * 255
        podium_raw[:int(h * 0.58), :] = 0
        podium_raw[int(h * 0.838):, :] = 0  # Podiums 1, 2, 3 end at ~83.3% H; floor orange stripes sit below 83.8% or x < 12.5%
        podium_raw[:, :int(w * 0.125)] = 0
        podium_raw[:, int(w * 0.845):] = 0
        podium_clean = cv2.morphologyEx(podium_raw, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        podium_clean = cv2.morphologyEx(podium_clean, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

        num_p, p_lbl, p_stats, _ = cv2.connectedComponentsWithStats(podium_clean, 8)
        podium_boxes: List[Tuple[int, int, int, int, int, np.ndarray]] = []
        min_p_area = int(w * h * 0.008)
        for pi in range(1, num_p):
            px, py, pw, ph, area = [int(v) for v in p_stats[pi]]
            if area >= min_p_area and ph >= int(h * 0.08) and pw >= int(w * 0.08):
                pmask_raw = np.where(p_lbl == pi, 255, 0).astype(np.uint8)
                # Seal interior number emblem (1, 2, 3) inside podium silhouette via exterior floodFill
                p_crop = cv2.morphologyEx(pmask_raw[py:py + ph, px:px + pw], cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8))
                p_pad = cv2.copyMakeBorder(p_crop, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
                p_ff = np.zeros((p_pad.shape[0] + 2, p_pad.shape[1] + 2), np.uint8)
                cv2.floodFill(p_pad, p_ff, (0, 0), 128)
                pmask = np.zeros((h, w), dtype=np.uint8)
                pmask[py:py + ph, px:px + pw] = np.where(p_pad[1:-1, 1:-1] == 128, 0, 255).astype(np.uint8)
                podium_boxes.append((px, py, pw, ph, area, pmask))

        # Sort left-to-right; label center/tallest as Bục 1, left as Bục 2, right as Bục 3
        podium_boxes.sort(key=lambda t: t[0])
        if len(podium_boxes) >= 3:
            # Largest height is Podium 1
            tall_idx = max(range(len(podium_boxes)), key=lambda i: podium_boxes[i][3])
            podium_roles = []
            for i in range(len(podium_boxes)):
                if i == tall_idx:
                    podium_roles.append((2, "Buc_Vinh_Quang_So_1_Center", podium_boxes[i]))
                elif podium_boxes[i][0] < podium_boxes[tall_idx][0]:
                    podium_roles.append((1, "Buc_Vinh_Quang_So_2_Left", podium_boxes[i]))
                else:
                    podium_roles.append((3, "Buc_Vinh_Quang_So_3_Right", podium_boxes[i]))
        else:
            podium_roles = [(i + 1, f"Buc_Vinh_Quang_{i + 1}", pb) for i, pb in enumerate(podium_boxes)]

        # Order z-index cleanly so Podium 2 & 3 sit behind/beside Podium 1
        for rank_order, p_name, (px, py, pw, ph, _, pmask) in podium_roles:
            # Amodal Top-Face Reconstruction: fill concave coin/shadow notches along top border of podium
            amodal_rgb = rgb.copy()
            hull_mask = np.zeros_like(pmask)
            cnts, _ = cv2.findContours(pmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if cnts:
                big_cnt = max(cnts, key=cv2.contourArea)
                hull = cv2.convexHull(big_cnt)
                cv2.drawContours(hull_mask, [hull], -1, 255, -1)
            # Only repair indentations in top 32% of podium bbox where coins/merch sit on top
            notch_hole = cv2.subtract(hull_mask, pmask)
            notch_hole[py + int(ph * 0.34):, :] = 0
            notch_hole[:py, :] = 0
            notch_hole[:, :px] = 0
            notch_hole[:, px + pw:] = 0
            if int(np.sum(notch_hole > 0)) > 25:
                # Reconstruct missing orange podium top face smoothly via directional TELEA inpaint
                p_bgr = bgr.copy()
                # Sample clean orange podium top color as seed guide for large indentations
                orange_px = bgr[pmask > 0]
                if len(orange_px) > 50:
                    top_rows_o = pmask[py + int(ph * 0.05):py + int(ph * 0.25), px:px + pw]
                    if np.any(top_rows_o > 0):
                        med_orange = np.median(bgr[py + int(ph * 0.05):py + int(ph * 0.25), px:px + pw][top_rows_o > 0], axis=0)
                        p_bgr[notch_hole > 0] = med_orange.astype(np.uint8)
                p_bgr = cv2.inpaint(p_bgr, notch_hole, 5, cv2.INPAINT_TELEA)
                amodal_rgb = cv2.cvtColor(p_bgr, cv2.COLOR_BGR2RGB)
                pmask = np.maximum(pmask, notch_hole)

            self._add_raster_layer(
                name=p_name,
                layer_type="product",
                group="2_Podiums_3D_Isometric",
                src_rgb=amodal_rgb,
                mask_u8=pmask,
                cat="podium_3d",
                confidence=0.94,
                decontaminate=True,
            )
            claimed_all = cv2.bitwise_or(claimed_all, pmask)

        # 2. Decompose Each Prize Cluster Above the 3 Podiums
        # Define horizontal search zones matching Podium positions (or default 3-column pyramid zones)
        if len(podium_roles) == 3:
            left_x1, left_x2 = max(0, podium_roles[0][2][0] - int(w * 0.06)), podium_roles[0][2][0] + podium_roles[0][2][2] + int(w * 0.04)
            mid_x1, mid_x2 = max(0, podium_roles[1][2][0] - int(w * 0.06)), podium_roles[1][2][0] + podium_roles[1][2][2] + int(w * 0.07)
            right_x1, right_x2 = max(0, podium_roles[2][2][0] - int(w * 0.06)), min(w, podium_roles[2][2][0] + podium_roles[2][2][2] + int(w * 0.07))
            prize_zones = [
                ("1st", "Giai_Nhat", mid_x1, int(h * 0.29), mid_x2, podium_roles[1][2][1] + 4, "Ao_Thun_FC_Online"),
                ("2nd", "Giai_Nhi", left_x1, int(h * 0.42), left_x2, podium_roles[0][2][1] + 4, "Non_Ket_FC_Online"),
                ("3rd", "Giai_Ba", right_x1, int(h * 0.43), right_x2, podium_roles[2][2][1] + 4, "Vong_Tay_FC_Online"),
            ]
        else:
            prize_zones = [
                ("1st", "Giai_Nhat", int(w * 0.27), int(h * 0.29), int(w * 0.72), int(h * 0.65), "Ao_Thun_FC_Online"),
                ("2nd", "Giai_Nhi", int(w * 0.05), int(h * 0.42), int(w * 0.40), int(h * 0.73), "Non_Ket_FC_Online"),
                ("3rd", "Giai_Ba", int(w * 0.62), int(h * 0.43), int(w * 0.94), int(h * 0.74), "Vong_Tay_FC_Online"),
            ]

        for idx_z, (rank_tag, group_label, zx1, zy1, zx2, zy2, merch_name) in enumerate(prize_zones):
            zone_mask = np.zeros((h, w), dtype=np.uint8)
            zone_mask[max(0, zy1):min(h, zy2), max(0, zx1):min(w, zx2)] = 255
            # Subtract already extracted podiums & claimed items cleanly
            avail_zone = cv2.subtract(zone_mask, cv2.erode(claimed_all, np.ones((3, 3), np.uint8), iterations=1))

            # (a) Extract Prize Medal Badges + Red Ribbons (`Huy_Hieu_Giai_...`) FIRST so bursts never puncture medals
            red_ribbon = (
                (avail_zone > 0)
                & ((hsv[:, :, 0] >= 162) | (hsv[:, :, 0] <= 8))
                & (hsv[:, :, 1] >= 105)
                & (hsv[:, :, 2] >= 90)
            ).astype(np.uint8) * 255
            red_ribbon = cv2.morphologyEx(red_ribbon, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            num_rr, rr_lbl, rr_stats, _ = cv2.connectedComponentsWithStats(red_ribbon, 8)
            rr_cands = [i for i in range(1, num_rr) if int(rr_stats[i, cv2.CC_STAT_AREA]) >= 140 and rr_stats[i, cv2.CC_STAT_TOP] < zy1 + int((zy2 - zy1) * 0.65)]
            if rr_cands:
                # Merge paired crimson ribbon tails below the circular badge before computing badge center & radius
                best_rr = max(rr_cands, key=lambda i: rr_stats[i, cv2.CC_STAT_AREA])
                br_x, br_y, br_w, br_h, _ = [int(v) for v in rr_stats[best_rr]]
                br_cx = br_x + br_w * 0.5
                rr_mask = np.zeros((h, w), dtype=np.uint8)
                for ri in rr_cands:
                    rx_i, ry_i, rw_i, rh_i, _ = [int(v) for v in rr_stats[ri]]
                    if abs(ry_i - br_y) <= 35 and abs((rx_i + rw_i * 0.5) - br_cx) <= 75:
                        rr_mask[rr_lbl == ri] = 255
                rys, rxs = np.where(rr_mask > 0)
                rr_x1, rr_y1, rr_x2, rr_y2 = int(rxs.min()), int(rys.min()), int(rxs.max()), int(rys.max())
                rr_w = rr_x2 - rr_x1 + 1
                rx_m = int((rr_x1 + rr_x2) * 0.5)
                ry_m = max(zy1 + 10, int(rr_y1 - int(rr_w * 0.40)))
                m_rad = max(50, int(rr_w * 0.72))
                mx1, my1 = max(0, rx_m - m_rad), max(0, ry_m - m_rad)
                mx2, my2 = min(w, rx_m + m_rad), min(h, rr_y2 + 8)
                m_box = [mx1, my1, mx2, my2]
                sam_medal_path = os.path.join(self.masks_dir, f"sam_medal_{rank_tag}.png")
                segment_interactive(
                    src_ref_path,
                    sam_medal_path,
                    points=[[rx_m, ry_m], [rx_m, rr_y1 + 6]],
                    labels=[1, 1],
                    box=m_box,
                    mask_level=1,
                    tmp_dir=self.masks_dir,
                )
                if os.path.exists(sam_medal_path):
                    m_sam = _imread_unicode(sam_medal_path, cv2.IMREAD_GRAYSCALE)
                    if m_sam is not None:
                        if m_sam.shape[:2] != (h, w):
                            m_sam = cv2.resize(m_sam, (w, h), interpolation=cv2.INTER_LINEAR)
                        m_sam_u8 = (m_sam > 110).astype(np.uint8) * 255
                        m_sam_box = np.zeros((h, w), dtype=np.uint8)
                        m_sam_box[my1:my2, mx1:mx2] = m_sam_u8[my1:my2, mx1:mx2]

                        # Restrict SlimSAM above ribbon top edge to circular radius (rr_w * 0.62) so adjacent sleeve/stadium cannot leak
                        yy_m, xx_m = np.ogrid[my1:my2, mx1:mx2]
                        dist_sq_m = (xx_m - rx_m) ** 2 + (yy_m - ry_m) ** 2
                        above_h = max(0, rr_y1 - my1)
                        if above_h > 0:
                            circle_gate = (dist_sq_m[:above_h, :] <= (rr_w * 0.62) ** 2)
                            m_sam_box[my1:my1 + above_h, mx1:mx2] = np.where(
                                circle_gate,
                                m_sam_box[my1:my1 + above_h, mx1:mx2],
                                0,
                            ).astype(np.uint8)
                        raw_medal = cv2.bitwise_or(rr_mask, cv2.bitwise_and(m_sam_box, avail_zone))

                        # Include circular disc warm/metallic badge pixels within tightened radius (rr_w * 0.54) excluding bright white/gray sky
                        circ_disc = dist_sq_m <= (rr_w * 0.54) ** 2
                        crop_hsv = hsv[my1:my2, mx1:mx2]
                        not_bright_sky = ~((crop_hsv[:, :, 1] < 24) & (crop_hsv[:, :, 2] > 212))
                        disc_pixels = np.where(circ_disc & not_bright_sky & (avail_zone[my1:my2, mx1:mx2] > 0), 255, 0).astype(np.uint8)
                        raw_crop = cv2.bitwise_or(raw_medal[my1:my2, mx1:mx2], disc_pixels)

                        # Seal any interior holes inside the circular medal badge via exterior floodFill inside padded ROI
                        medal_crop = cv2.morphologyEx(raw_crop, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
                        m_pad = cv2.copyMakeBorder(medal_crop, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
                        m_ff = np.zeros((m_pad.shape[0] + 2, m_pad.shape[1] + 2), np.uint8)
                        cv2.floodFill(m_pad, m_ff, (0, 0), 128)
                        medal_filled_crop = np.where(m_pad[1:-1, 1:-1] == 128, 0, 255).astype(np.uint8)
                        medal_mask = np.zeros((h, w), dtype=np.uint8)
                        medal_mask[my1:my2, mx1:mx2] = cv2.bitwise_and(medal_filled_crop, avail_zone[my1:my2, mx1:mx2])
                        medal_mask = cv2.bitwise_or(medal_mask, rr_mask)
                        if int(np.sum(medal_mask > 127)) >= 600:
                            self._add_raster_layer(
                                name=f"Huy_Hieu_{group_label}",
                                layer_type="icon",
                                group="3_Prizes_&_Items",
                                src_rgb=rgb,
                                mask_u8=medal_mask,
                                cat="prize_medal",
                                confidence=0.92,
                                psd_effects={
                                    "dropShadow": [{"enabled": True, "size": 10, "distance": 4, "angle": 120, "color": [0, 0, 0], "opacity": 0.45}],
                                    "innerShadow": [{"enabled": True, "size": 5, "distance": 2, "angle": 120, "color": [0, 0, 0], "opacity": 0.3}],
                                },
                            )
                            claimed_all = cv2.bitwise_or(claimed_all, medal_mask)
                            avail_zone = cv2.subtract(avail_zone, medal_mask)

            # (b) Extract Metallic Emerald-Green FC Coin Stacks (`Coc_Xu_FC`) from lower coin stack only
            coin_seed_mask = (
                (avail_zone > 0)
                & (hsv[:, :, 0] >= 52)
                & (hsv[:, :, 0] <= 86)
                & (hsv[:, :, 1] >= 65)
                & (hsv[:, :, 2] >= 70)
            ).astype(np.uint8) * 255
            if rank_tag == "1st":
                # Keep coin seeds below sleeve text ("ONLINE") on Ao_Thun
                coin_seed_mask[:max(0, zy1 + int((zy2 - zy1) * 0.50)), :] = 0
                coin_seed_mask[:, :max(0, zx1 + int((zx2 - zx1) * 0.48))] = 0
            elif rank_tag == "3rd":
                # Keep coin seeds below green "FC ONLINE" band on Vong_Tay
                coin_seed_mask[:max(0, zy1 + int((zy2 - zy1) * 0.52)), :] = 0
            else:
                coin_seed_mask[:max(0, zy1 + int((zy2 - zy1) * 0.44)), :] = 0
            coin_seed_mask = cv2.morphologyEx(coin_seed_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            # Prune thin printed green text strokes ("ONLINE" / "FC ONLINE") via 9x9 ellipse morphological opening
            coin_core = cv2.morphologyEx(coin_seed_mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
            coin_core_dil = cv2.dilate(coin_core, np.ones((7, 7), np.uint8), iterations=1)
            num_c, c_lbl, c_stats, _ = cv2.connectedComponentsWithStats(coin_seed_mask, 8)
            cands_c = [
                ci for ci in range(1, num_c)
                if int(c_stats[ci, cv2.CC_STAT_AREA]) >= 250 and np.any(coin_core_dil[c_lbl == ci] > 0)
            ]
            big_coin_seeds = np.zeros((h, w), dtype=np.uint8)
            if cands_c:
                best_ci = max(cands_c, key=lambda ci: int(c_stats[ci, cv2.CC_STAT_AREA]))
                bx1_c, by1_c, bw_c, bh_c, _ = [int(v) for v in c_stats[best_ci]]
                bx2_c, by2_c = bx1_c + bw_c, by1_c + bh_c
                for ci in cands_c:
                    cx1_c, cy1_c, cw_c, ch_c, _ = [int(v) for v in c_stats[ci]]
                    cx2_c, cy2_c = cx1_c + cw_c, cy1_c + ch_c
                    if not (cx2_c < bx1_c - 35 or cx1_c > bx2_c + 35 or cy2_c < by1_c - 35 or cy1_c > by2_c + 35):
                        big_coin_seeds[c_lbl == ci] = 255
            if int(np.sum(big_coin_seeds > 0)) >= 400:
                cys, cxs = np.where(big_coin_seeds > 0)
                c_cx, c_cy = int(np.median(cxs)), int(np.median(cys))
                # Expand with SlimSAM ROI around green coin cluster, clamped cleanly to c_box
                c_box = [max(0, int(cxs.min()) - 14), max(0, int(cys.min()) - 14), min(w, int(cxs.max()) + 14), min(h, int(cys.max()) + 14)]
                coin_sam_path = os.path.join(self.masks_dir, f"sam_coin_{rank_tag}.png")
                neg_pts = []
                if cxs.min() > zx1 + 30:
                    neg_pts.append([max(0, int(cxs.min()) - 28), c_cy])
                segment_interactive(
                    src_ref_path,
                    coin_sam_path,
                    points=[[c_cx, c_cy], [int(np.percentile(cxs, 25)), int(np.percentile(cys, 75))]] + neg_pts,
                    labels=[1, 1] + [0] * len(neg_pts),
                    box=c_box,
                    mask_level=1,
                    tmp_dir=self.masks_dir,
                )
                c_sam = _imread_unicode(coin_sam_path, cv2.IMREAD_GRAYSCALE) if os.path.exists(coin_sam_path) else big_coin_seeds
                c_sam_clamped = np.zeros((h, w), dtype=np.uint8)
                if c_sam is not None:
                    if c_sam.shape[:2] != (h, w):
                        c_sam = cv2.resize(c_sam, (w, h), interpolation=cv2.INTER_LINEAR)
                    c_sam_clamped[c_box[1]:c_box[3], c_box[0]:c_box[2]] = c_sam[c_box[1]:c_box[3], c_box[0]:c_box[2]]
                # Combine SlimSAM coin prediction with vivid emerald coin pixels & subtract orange podium
                coin_final = cv2.bitwise_or(big_coin_seeds, cv2.bitwise_and(c_sam_clamped, avail_zone))
                coin_final = cv2.morphologyEx(coin_final, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
                # Protect purely dark black fabric inside merch from leaking into coin stack
                dark_fabric = (hsv[:, :, 2] < 48) & (hsv[:, :, 1] < 50)
                coin_final[dark_fabric] = 0
                if int(np.sum(coin_final > 127)) >= 400:
                    self._add_raster_layer(
                        name=f"Coc_Xu_FC_{group_label}",
                        layer_type="product",
                        group="3_Prizes_&_Items",
                        src_rgb=rgb,
                        mask_u8=coin_final,
                        cat="prize_coins",
                        confidence=0.91,
                    )
                    claimed_all = cv2.bitwise_or(claimed_all, coin_final)
                    avail_zone = cv2.subtract(avail_zone, coin_final)

            # (c) Extract Yellow Comic Starburst (`Burst`) AFTER Medals so medal circles stay untouched
            burst_cand = (
                (avail_zone > 0)
                & (hsv[:, :, 0] >= 22)
                & (hsv[:, :, 0] <= 34)
                & (hsv[:, :, 1] >= 145)
                & (hsv[:, :, 2] >= 210)
            ).astype(np.uint8) * 255
            burst_clean = cv2.morphologyEx(burst_cand, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            num_b, b_lbl, b_stats, _ = cv2.connectedComponentsWithStats(burst_clean, 8)
            burst_mask = np.zeros((h, w), dtype=np.uint8)
            for bi in range(1, num_b):
                if int(b_stats[bi, cv2.CC_STAT_AREA]) >= 250:
                    burst_mask[b_lbl == bi] = 255
            if int(np.sum(burst_mask > 0)) >= 400:
                self._add_raster_layer(
                    name=f"Comic_Burst_{group_label}",
                    layer_type="decor",
                    group="3_Prizes_&_Items",
                    src_rgb=rgb,
                    mask_u8=burst_mask,
                    cat="comic_burst",
                    confidence=0.90,
                )
                claimed_all = cv2.bitwise_or(claimed_all, burst_mask)
                avail_zone = cv2.subtract(avail_zone, burst_mask)

            # (d) Extract Merch (Shirt / Cap / Wristband) + Attached Lanyard/Keychain cleanly without stadium bleed
            zy1_c, zy2_c = max(0, zy1), min(h, zy2)
            zx1_c, zx2_c = max(0, zx1), min(w, zx2)
            dark_core = (
                (avail_zone > 0)
                & (
                    ((hsv[:, :, 2] < 78) & ((hsv[:, :, 1] >= 18) | (hsv[:, :, 2] < 66)))
                    | ((hsv[:, :, 0] >= 34) & (hsv[:, :, 0] <= 82) & (hsv[:, :, 1] >= 85) & (hsv[:, :, 2] < 215))
                )
            ).astype(np.uint8) * 255
            dark_closed_crop = cv2.morphologyEx(
                dark_core[zy1_c:zy2_c, zx1_c:zx2_c],
                cv2.MORPH_CLOSE,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19)),
            )
            dc_pad = cv2.copyMakeBorder(dark_closed_crop, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
            dc_ff = np.zeros((dc_pad.shape[0] + 2, dc_pad.shape[1] + 2), np.uint8)
            cv2.floodFill(dc_pad, dc_ff, (0, 0), 128)
            dark_filled = np.zeros((h, w), dtype=np.uint8)
            dark_filled[zy1_c:zy2_c, zx1_c:zx2_c] = cv2.bitwise_and(
                np.where(dc_pad[1:-1, 1:-1] == 128, 0, 255).astype(np.uint8),
                avail_zone[zy1_c:zy2_c, zx1_c:zx2_c],
            )

            apparel_sal = cv2.bitwise_and(rmbg_salient_u8, avail_zone)
            # Include silver metallic EA SPORTS FC triangle keychain tag attached within 15px of dark_filled in lower-left pocket
            kc_pocket = np.zeros((h, w), dtype=np.uint8)
            kc_x_end = zx1_c + int((zx2_c - zx1_c) * 0.48)
            kc_y_beg = zy1_c + int((zy2_c - zy1_c) * 0.46)
            kc_pocket[kc_y_beg:zy2_c, zx1_c:kc_x_end] = 255
            dark_halo15 = cv2.dilate(dark_filled, np.ones((15, 15), np.uint8), iterations=1)
            not_olive_or_sky = (
                ~((hsv[:, :, 0] >= 18) & (hsv[:, :, 0] <= 55) & (hsv[:, :, 1] >= 42))
                & (hsv[:, :, 2] <= 215)
            )
            keychain_sal = np.where((apparel_sal > 0) & (kc_pocket > 0) & (dark_halo15 > 0) & not_olive_or_sky, 255, 0).astype(np.uint8)

            neutral_stadium_gray = (hsv[:, :, 1] < 38) & (hsv[:, :, 2] >= 72) & (hsv[:, :, 2] <= 238)
            sal_non_gray = np.where(
                (apparel_sal > 0) & ((dark_filled > 0) | (~neutral_stadium_gray)),
                255,
                0,
            ).astype(np.uint8)
            dark_halo = cv2.dilate(dark_filled, np.ones((11, 11), np.uint8), iterations=1)
            sal_attached = cv2.bitwise_and(sal_non_gray, dark_halo)

            merch_cand = cv2.bitwise_or(dark_filled, cv2.bitwise_or(sal_attached, keychain_sal))
            merch_cand = cv2.morphologyEx(merch_cand, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
            num_mc, mc_lbl, mc_stats, _ = cv2.connectedComponentsWithStats(merch_cand, 8)
            valid_mcs = [i for i in range(1, num_mc) if int(mc_stats[i, cv2.CC_STAT_AREA]) >= 350]
            if valid_mcs:
                valid_mcs.sort(key=lambda i: int(mc_stats[i, cv2.CC_STAT_AREA]), reverse=True)
                main_i = valid_mcs[0]
                main_mask = np.where(mc_lbl == main_i, 255, 0).astype(np.uint8)
                main_dil13 = cv2.dilate(main_mask, np.ones((13, 13), np.uint8), iterations=1)
                merged_merch = main_mask.copy()
                for sec_i in valid_mcs[1:]:
                    if int(mc_stats[sec_i, cv2.CC_STAT_AREA]) >= 450 and np.any(main_dil13[mc_lbl == sec_i] > 0):
                        merged_merch[mc_lbl == sec_i] = 255
                self._add_raster_layer(
                    name=merch_name,
                    layer_type="product",
                    group="3_Prizes_&_Items",
                    src_rgb=rgb,
                    mask_u8=merged_merch,
                    cat="prize_apparel",
                    confidence=0.90,
                )
                claimed_all = cv2.bitwise_or(claimed_all, merged_merch)

        return claimed_all

    # ------------------------------------------------------------------
    # MODULE 1: Dual-Version Typography + Skewed Ribbons
    # ------------------------------------------------------------------
    def _extract_typography_and_ribbons(
        self,
        bgr: np.ndarray,
        rgb: np.ndarray,
        hsv: np.ndarray,
        lab: np.ndarray,
        src_ref_path: str,
        already_claimed: np.ndarray,
    ) -> np.ndarray:
        """Extract Artistic Headline (`OrigFX` + hidden `Editable TySh`), Ribbons, Medal Text & Footer Text."""
        h, w = bgr.shape[:2]
        claimed = already_claimed.copy()

        # 1. Extract Date Ribbon Shape (`y in 21.5..29.5%, x in 14..88%`) including pale-yellow top edge under headline glow
        ry1, ry2 = int(h * 0.215), int(h * 0.295)
        rx1, rx2 = int(w * 0.14), int(w * 0.88)
        rib_bgr_crop = bgr[ry1:ry2, rx1:rx2].copy()
        rib_luma = cv2.cvtColor(rib_bgr_crop, cv2.COLOR_BGR2GRAY)
        rib_sat = hsv[ry1:ry2, rx1:rx2, 1]
        ribbon_hsv_c = (hsv[ry1:ry2, rx1:rx2, 0] >= 16) & (hsv[ry1:ry2, rx1:rx2, 0] <= 72) & (rib_sat >= 42) & (hsv[ry1:ry2, rx1:rx2, 2] >= 145)
        rib_local = (ribbon_hsv_c.astype(np.uint8)) * 255
        # Seal dark/white text holes horizontally inside yellow-green ribbon so Ribbon Shape is 1 solid graphic layer!
        rib_closed = cv2.morphologyEx(rib_local, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 13)))
        rib_pad = cv2.copyMakeBorder(rib_closed, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
        ff = np.zeros((rib_pad.shape[0] + 2, rib_pad.shape[1] + 2), np.uint8)
        cv2.floodFill(rib_pad, ff, (0, 0), 128)
        rib_filled = np.where(rib_pad[1:-1, 1:-1] == 128, 0, 255).astype(np.uint8)

        # Extract complete date glyphs (`9h00 ngày 15.09.2024`) including tops protruding ABOVE the skewed yellow ribbon
        rc_h, rc_w = rib_filled.shape[:2]
        text_zone = np.zeros_like(rib_luma)
        text_zone[int(rc_h * 0.08):int(rc_h * 0.84), int(rc_w * 0.20):int(rc_w * 0.80)] = 255
        near_rib = cv2.dilate(rib_filled, np.ones((27, 27), np.uint8), iterations=1)
        text_search = cv2.bitwise_and(text_zone, near_rib)
        not_blue_head = ~((hsv[ry1:ry2, rx1:rx2, 0] >= 82) & (hsv[ry1:ry2, rx1:rx2, 0] <= 145) & (rib_sat >= 60))
        dark_glyphs = ((text_search > 0) & not_blue_head & (rib_luma < 162) & (rib_sat < 95)).astype(np.uint8) * 255
        white_bevel = ((text_search > 0) & (rib_filled > 0) & (rib_sat < 55) & (rib_luma > 228)).astype(np.uint8) * 255
        white_bevel = cv2.bitwise_and(white_bevel, cv2.dilate(dark_glyphs, np.ones((3, 3), np.uint8), iterations=1))
        text_on_rib = cv2.bitwise_or(dark_glyphs, white_bevel)

        clean_pix = (rib_filled > 0) & (text_on_rib == 0)
        pre_rib_bgr = rib_bgr_crop.copy()
        dil_text_rib = cv2.bitwise_and(cv2.dilate(text_on_rib, np.ones((5, 5), np.uint8), iterations=1), rib_filled)
        if np.any(clean_pix):
            global_med = np.median(rib_bgr_crop[clean_pix], axis=0)
            for ci in range(rib_bgr_crop.shape[1]):
                col_target = dil_text_rib[:, ci] > 0
                if not np.any(col_target):
                    continue
                col_clean = clean_pix[:, ci]
                col_color = np.median(rib_bgr_crop[col_clean, ci], axis=0) if np.any(col_clean) else global_med
                pre_rib_bgr[col_target, ci] = col_color.astype(np.uint8)

        inpaint_rib_mask = cv2.bitwise_and(cv2.dilate(text_on_rib, np.ones((3, 3), np.uint8), iterations=1), rib_filled)
        clean_ribbon_bgr = cv2.inpaint(pre_rib_bgr, inpaint_rib_mask, 5, cv2.INPAINT_TELEA)
        full_rib_rgb = rgb.copy()
        full_rib_rgb[ry1:ry2, rx1:rx2] = cv2.cvtColor(clean_ribbon_bgr, cv2.COLOR_BGR2RGB)
        rib_mask_full = np.zeros((h, w), dtype=np.uint8)
        rib_mask_full[ry1:ry2, rx1:rx2] = rib_filled

        if int(np.sum(rib_filled > 0)) > 800:
            self._add_raster_layer(
                name="Ribbon_Shape_Date_Bar",
                layer_type="shape",
                group="6_Typography_OrigFX_&_Editable",
                src_rgb=full_rib_rgb,
                mask_u8=rib_mask_full,
                cat="ribbon_shape",
                confidence=0.93,
            )
            claimed = cv2.bitwise_or(claimed, rib_mask_full)

        # 2. Extract Main Artistic Headline Bitmap (`CÔNG BỐ GIẢI ĐẤU`, `y in 10..23%, x in 14..86%`)
        ty1, ty2 = int(h * 0.105), int(h * 0.228)
        tx1, tx2 = int(w * 0.14), int(w * 0.86)
        t_bgr = bgr[ty1:ty2, tx1:tx2]
        t_hsv = hsv[ty1:ty2, tx1:tx2]
        # Sample surrounding soft sky color per row from outer clear columns of headline band
        sky_l = np.median(t_bgr[:, :min(24, t_bgr.shape[1] // 8)], axis=1, keepdims=True)
        sky_r = np.median(t_bgr[:, max(0, t_bgr.shape[1] - 24):], axis=1, keepdims=True)
        sky_row = ((sky_l.astype(np.float32) + sky_r.astype(np.float32)) * 0.5)
        t_dist = np.linalg.norm(t_bgr.astype(np.float32) - sky_row, axis=2)

        # Colorful blue/cyan gradient fill + pure white outline stroke + tight shadow around characters
        char_core = ((t_hsv[:, :, 1] >= 70) & (t_dist > 22)).astype(np.uint8) * 255
        white_stroke = cv2.dilate(char_core, np.ones((11, 11), np.uint8), iterations=1)
        t_alpha_local = np.where((char_core > 0) | ((white_stroke > 0) & (t_dist > 9)), 255, np.clip((t_dist - 8) * 14, 0, 220)).astype(np.uint8)
        t_alpha_local = np.where(white_stroke > 0, t_alpha_local, 0).astype(np.uint8)
        t_alpha_local = cv2.GaussianBlur(t_alpha_local, (3, 3), 0)

        head_mask_full = np.zeros((h, w), dtype=np.uint8)
        head_mask_full[ty1:ty2, tx1:tx2] = t_alpha_local

        garena_headline_fx = {
            "dropShadow": [
                {"enabled": True, "size": 4, "distance": 4, "angle": 120, "color": [10, 20, 45], "opacity": 0.80},
                {"enabled": True, "size": 35, "distance": 25, "angle": 120, "color": [15, 35, 70], "opacity": 0.30},
            ],
            "stroke": [{"enabled": True, "size": 4, "position": "outside", "color": [255, 255, 255], "opacity": 1.0}],
            "gradientOverlay": [{
                "enabled": True, "angle": 90, "opacity": 1.0,
                "colorStops": [
                    {"color": [11, 43, 104], "location": 0.0},
                    {"color": [80, 255, 160], "location": 1.0},
                ],
            }],
        }

        # Run OCR on upscaled Headline, Date Ribbon, Medals & Footer to populate exact editable text twins!
        ocr_items = extract_typography_objects(src_ref_path, self.project_dir)
        joined_ocr = " | ".join([it.get("ocr_text", "") for it in ocr_items])

        # Helper to extract exact headline/date/footer string cleanly from Tesseract items inside bbox
        def _find_ocr_text(rx1_f: float, ry1_f: float, rx2_f: float, ry2_f: float, fallback: str) -> Tuple[str, float]:
            hits = []
            for it in ocr_items:
                bx, by, bw_i, bh_i = it["bbox"]
                cx_n, cy_n = (bx + bw_i * 0.5) / w, (by + bh_i * 0.5) / h
                if rx1_f <= cx_n <= rx2_f and ry1_f <= cy_n <= ry2_f and len(it["ocr_text"].strip()) >= 2:
                    hits.append(it)
            if not hits:
                return fallback, 0.72
            hits.sort(key=lambda x: (x["bbox"][1], x["bbox"][0]))
            txt = " ".join([ht["ocr_text"].strip() for ht in hits])
            conf = float(np.mean([ht.get("confidence", 0.8) for ht in hits]))
            return txt, conf

        head_txt, head_conf = _find_ocr_text(0.14, 0.10, 0.86, 0.23, "CÔNG BỐ GIẢI ĐẤU")
        date_txt, date_conf = _find_ocr_text(0.20, 0.22, 0.80, 0.30, "9h00 ngày 15.09.2024")
        venue_txt, venue_conf = _find_ocr_text(0.14, 0.90, 0.45, 0.99, "VIKINGS XVNT")
        foot_txt, foot_conf = _find_ocr_text(0.55, 0.80, 0.98, 0.98, "STUDENT CUP 2024")

        if int(np.sum(t_alpha_local > 127)) > 300:
            self._add_raster_layer(
                name="Title_CongBoGiaiDau_OrigFX",
                layer_type="object",
                group="6_Typography_OrigFX_&_Editable",
                src_rgb=rgb,
                mask_u8=head_mask_full,
                cat="typography_orig_fx",
                confidence=0.95,
            )
            self._add_backup_text_layer(
                name="Title_CongBoGiaiDau_Editable_Backup",
                text_str=head_txt,
                x=int(w * 0.18),
                y=int(h * 0.12),
                font_size=max(48, int(h * 0.082)),
                color=[22, 135, 250],
                gradient_enabled=True,
                gradient_c2=[80, 255, 160],
                stroke_enabled=True,
                stroke_color=[255, 255, 255],
                stroke_width=5,
                psd_effects=garena_headline_fx,
                confidence=head_conf,
                visible=False,
            )
            claimed = cv2.bitwise_or(claimed, head_mask_full)

        # Date Text OrigFX + Hidden Editable Twin
        date_mask_full = np.zeros((h, w), dtype=np.uint8)
        if int(np.sum(text_on_rib > 64)) > 150:
            date_mask_full[ry1:ry2, rx1:rx2] = cv2.dilate(text_on_rib, np.ones((3, 3), np.uint8), iterations=1)
            self._add_raster_layer(
                name="Date_Time_Text_OrigFX",
                layer_type="object",
                group="6_Typography_OrigFX_&_Editable",
                src_rgb=rgb,
                mask_u8=date_mask_full,
                cat="typography_orig_fx",
                confidence=0.91,
            )
            self._add_backup_text_layer(
                name="Date_Time_Text_Editable_Backup",
                text_str=date_txt,
                x=int(w * 0.30),
                y=int(h * 0.238),
                font_size=max(24, int(h * 0.032)),
                color=[12, 18, 28],
                stroke_enabled=False,
                psd_effects={
                    "dropShadow": [{"enabled": True, "size": 4, "distance": 2, "angle": 120, "color": [255, 255, 255], "opacity": 0.9}],
                    "innerShadow": [{"enabled": True, "size": 3, "distance": 2, "angle": 120, "color": [0, 0, 0], "opacity": 0.4}],
                },
                prefer_display_font=False,
                confidence=date_conf,
                visible=False,
            )
        # Widen background exclusion halo around headline, date ribbon & top-protruding date glyphs
        if int(np.sum(head_mask_full > 0)) > 0:
            claimed = cv2.bitwise_or(claimed, cv2.dilate(head_mask_full, np.ones((19, 19), np.uint8), iterations=1))
        if int(np.sum(rib_mask_full > 0)) > 0:
            claimed = cv2.bitwise_or(claimed, cv2.dilate(rib_mask_full, np.ones((19, 19), np.uint8), iterations=1))
        if int(np.sum(date_mask_full > 0)) > 0:
            claimed = cv2.bitwise_or(claimed, cv2.dilate(date_mask_full, np.ones((11, 11), np.uint8), iterations=1))

        # 3. Extract Bottom-Left Venue Ribbon Bar (`VIKINGS XVNT`) + Location Pin + Bottom-Right Event Title Block
        # Bottom-left Location Pin (`[x: 11..22%, y: 89..99%]`) + Venue Bar (`[0..42% W, 93..100% H]`)
        pin_y1, pin_y2 = int(h * 0.89), h
        pin_x1, pin_x2 = int(w * 0.11), int(w * 0.22)
        pin_luma = cv2.cvtColor(bgr[pin_y1:pin_y2, pin_x1:pin_x2], cv2.COLOR_BGR2GRAY)
        pin_local = (pin_luma < 65).astype(np.uint8) * 255
        pin_local = cv2.morphologyEx(pin_local, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        if int(np.sum(pin_local > 0)) > 300:
            pin_mask = np.zeros((h, w), dtype=np.uint8)
            pin_mask[pin_y1:pin_y2, pin_x1:pin_x2] = pin_local
            self._add_raster_layer(
                name="Location_Pin_Vikings",
                layer_type="icon",
                group="5_Logos_&_Footer",
                src_rgb=rgb,
                mask_u8=pin_mask,
                cat="venue_icon",
                confidence=0.92,
            )
            claimed = cv2.bitwise_or(claimed, pin_mask)

        v_y1, v_y2 = int(h * 0.935), h
        v_x1, v_x2 = 0, int(w * 0.42)
        v_mask = np.zeros((h, w), dtype=np.uint8)
        # Clean bottom-left blue-green trapezoidal strip
        v_hsv = hsv[v_y1:v_y2, v_x1:v_x2]
        v_bar = ((v_hsv[:, :, 0] >= 48) & (v_hsv[:, :, 0] <= 125) & (v_hsv[:, :, 1] >= 120)).astype(np.uint8) * 255
        v_bar = cv2.morphologyEx(v_bar, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        v_mask[v_y1:v_y2, v_x1:v_x2] = cv2.subtract(v_bar, claimed[v_y1:v_y2, v_x1:v_x2])
        if int(np.sum(v_mask > 0)) > 800:
            self._add_raster_layer(
                name="Ribbon_Venue_Bar_Vikings",
                layer_type="shape",
                group="5_Logos_&_Footer",
                src_rgb=rgb,
                mask_u8=v_mask,
                cat="venue_bar",
                confidence=0.90,
            )
            self._add_backup_text_layer(
                name="Venue_Vikings_XVNT_Editable",
                text_str=venue_txt,
                x=int(w * 0.21),
                y=int(h * 0.955),
                font_size=max(16, int(h * 0.021)),
                color=[12, 16, 22],
                stroke_enabled=False,
                prefer_display_font=False,
                confidence=venue_conf,
                visible=False,
            )
            claimed = cv2.bitwise_or(claimed, v_mask)

        # Bottom-right Student Cup 2024 Event Typography + Black Banner Ribbon (`x: 56..98%, y: 82..98%`)
        ev_y1, ev_y2 = int(h * 0.825), int(h * 0.985)
        ev_x1, ev_x2 = int(w * 0.56), int(w * 0.98)
        ev_dark = (cv2.cvtColor(bgr[ev_y1:ev_y2, ev_x1:ev_x2], cv2.COLOR_BGR2GRAY) < 85).astype(np.uint8) * 255
        ev_dark = cv2.morphologyEx(ev_dark, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        if int(np.sum(ev_dark > 0)) > 600:
            ev_mask = np.zeros((h, w), dtype=np.uint8)
            ev_mask[ev_y1:ev_y2, ev_x1:ev_x2] = cv2.subtract(ev_dark, claimed[ev_y1:ev_y2, ev_x1:ev_x2])
            self._add_raster_layer(
                name="Event_Name_Student_Cup_OrigFX",
                layer_type="object",
                group="5_Logos_&_Footer",
                src_rgb=rgb,
                mask_u8=ev_mask,
                cat="event_typography",
                confidence=0.92,
            )
            self._add_backup_text_layer(
                name="Event_Student_Cup_Editable",
                text_str=foot_txt,
                x=int(w * 0.59),
                y=int(h * 0.865),
                font_size=max(26, int(h * 0.036)),
                color=[15, 20, 28],
                stroke_enabled=False,
                confidence=foot_conf,
                visible=False,
            )
            claimed = cv2.bitwise_or(claimed, ev_mask)

        # Also add hidden Editable Vector Text twins for GIẢI NHẤT / GIẢI NHÌ / GIẢI BA
        for m_name, m_txt, mx, my in [
            ("Giai_Nhat_Text_Editable", "GIẢI NHẤT", int(w * 0.52), int(h * 0.36)),
            ("Giai_Nhi_Text_Editable", "GIẢI NHÌ", int(w * 0.13), int(h * 0.50)),
            ("Giai_Ba_Text_Editable", "GIẢI BA", int(w * 0.77), int(h * 0.52)),
        ]:
            self._add_backup_text_layer(
                name=m_name,
                text_str=m_txt,
                x=mx,
                y=my,
                font_size=max(18, int(h * 0.022)),
                color=[18, 22, 28],
                stroke_enabled=False,
                psd_effects={
                    "dropShadow": [{"enabled": True, "size": 4, "distance": 2, "angle": 120, "color": [255, 255, 255], "opacity": 0.65}],
                    "innerShadow": [{"enabled": True, "size": 2, "distance": 1, "angle": 120, "color": [0, 0, 0], "opacity": 0.3}],
                },
                prefer_display_font=False,
                visible=False,
            )

        return claimed

    # ------------------------------------------------------------------
    # MODULE 3: Logos, 3D Gaming Gear (Laptop/Gamepad), Stars, Confetti & Leaf
    # ------------------------------------------------------------------
    def _extract_decor_logos_and_gear(
        self,
        bgr: np.ndarray,
        rgb: np.ndarray,
        hsv: np.ndarray,
        src_ref_path: str,
        already_claimed: np.ndarray,
    ) -> np.ndarray:
        h, w = bgr.shape[:2]
        claimed = already_claimed.copy()

        # 1. Top-Left Brand Logo (`Logo_EA_SPORTS_FC_ONLINE`: x in [5..25% W], y in [2..12% H])
        l1x1, l1y1, l1x2, l1y2 = int(w * 0.06), int(h * 0.02), int(w * 0.25), int(h * 0.115)
        l1_bgr = bgr[l1y1:l1y2, l1x1:l1x2]
        l1_luma = cv2.cvtColor(l1_bgr, cv2.COLOR_BGR2GRAY)
        l1_dark = (l1_luma < 85).astype(np.uint8) * 255
        # Keep interior white "EA SPORTS" text inside black badge using border floodfill on closed badge
        l1_closed = cv2.morphologyEx(l1_dark, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        l1_pad = cv2.copyMakeBorder(255 - l1_closed, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=255)
        ff = np.zeros((l1_pad.shape[0] + 2, l1_pad.shape[1] + 2), np.uint8)
        cv2.floodFill(l1_pad, ff, (0, 0), 128)
        l1_fg = np.where(l1_pad[1:-1, 1:-1] == 128, 0, 255).astype(np.uint8)
        if int(np.sum(l1_fg > 0)) > 400:
            m1 = np.zeros((h, w), dtype=np.uint8)
            m1[l1y1:l1y2, l1x1:l1x2] = cv2.subtract(l1_fg, claimed[l1y1:l1y2, l1x1:l1x2])
            self._add_raster_layer("Logo_EA_SPORTS_FC_ONLINE", "logo", "5_Logos_&_Footer", rgb, m1, "brand_logo", 0.94)
            claimed = cv2.bitwise_or(claimed, m1)

        # 2. Top-Right Tournament Crest Logo (`Logo_SVC_Student_Cup_2024`: x in [81..96% W], y in [1..12% H])
        l2x1, l2y1, l2x2, l2y2 = int(w * 0.81), int(h * 0.015), int(w * 0.96), int(h * 0.125)
        l2_fg = _flood_outside_bg(bgr[l2y1:l2y2, l2x1:l2x2], thresh=18.0)
        if int(np.sum(l2_fg > 0)) > 250:
            m2 = np.zeros((h, w), dtype=np.uint8)
            m2[l2y1:l2y2, l2x1:l2x2] = cv2.subtract(l2_fg, claimed[l2y1:l2y2, l2x1:l2x2])
            self._add_raster_layer("Logo_SVC_Student_Cup_2024", "logo", "5_Logos_&_Footer", rgb, m2, "brand_logo", 0.92)
            claimed = cv2.bitwise_or(claimed, m2)

        # 3. Bottom-Left 3D Cyan Laptop (`x in [0..18% W], y in [78..95% H]`) via SlimSAM ROI
        lx1, ly1, lx2, ly2 = 0, int(h * 0.78), int(w * 0.18), int(h * 0.955)
        lap_hsv = hsv[ly1:ly2, lx1:lx2]
        lap_cand = ((lap_hsv[:, :, 0] >= 55) & (lap_hsv[:, :, 0] <= 102) & (lap_hsv[:, :, 1] >= 48) & (lap_hsv[:, :, 2] >= 120)).astype(np.uint8) * 255
        lap_cand = cv2.morphologyEx(lap_cand, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        num_lp, lp_lbl, lp_stats, _ = cv2.connectedComponentsWithStats(lap_cand, 8)
        best_lp = max(range(1, num_lp), key=lambda i: lp_stats[i, cv2.CC_STAT_AREA], default=0)
        if best_lp > 0 and int(lp_stats[best_lp, cv2.CC_STAT_AREA]) >= 400:
            lp_seed_y, lp_seed_x = np.where(lp_lbl == best_lp)
            sam_lap = os.path.join(self.masks_dir, "sam_laptop.png")
            segment_interactive(
                src_ref_path,
                sam_lap,
                points=[[lx1 + int(np.median(lp_seed_x)), ly1 + int(np.median(lp_seed_y))]],
                labels=[1],
                box=[lx1, ly1, lx2, ly2],
                mask_level=1,
                tmp_dir=self.masks_dir,
            )
            l_m = _imread_unicode(sam_lap, cv2.IMREAD_GRAYSCALE) if os.path.exists(sam_lap) else np.zeros((h, w), dtype=np.uint8)
            if l_m is None:
                l_m = np.zeros((h, w), dtype=np.uint8)
            elif l_m.shape[:2] != (h, w):
                l_m = cv2.resize(l_m, (w, h), interpolation=cv2.INTER_LINEAR)
            lp_fallback = np.zeros((h, w), dtype=np.uint8)
            lp_fallback[ly1:ly2, lx1:lx2] = np.where(lp_lbl == best_lp, 255, 0).astype(np.uint8)
            lap_mask = cv2.bitwise_or(lp_fallback, (l_m > 127).astype(np.uint8) * 255)
            lap_mask[:ly1, :] = 0
            lap_mask[ly2:, :] = 0
            lap_mask[:, lx2:] = 0
            lap_mask = cv2.subtract(lap_mask, claimed)
            self._add_raster_layer("Laptop_Gaming_3D_Cyan", "object", "4_Decor_&_Gaming_Gear", rgb, lap_mask, "gaming_gear_3d", 0.91)
            claimed = cv2.bitwise_or(claimed, lap_mask)

        # 4. Bottom-Right 3D Neon Gamepad (`x in [80..99% W], y in [73..91% H]`) + DropShadow LayerFX
        gx1, gy1, gx2, gy2 = int(w * 0.80), int(h * 0.72), w, int(h * 0.91)
        gp_hsv = hsv[gy1:gy2, gx1:gx2]
        gp_cand = ((gp_hsv[:, :, 0] >= 42) & (gp_hsv[:, :, 0] <= 100) & (gp_hsv[:, :, 1] >= 55) & (gp_hsv[:, :, 2] >= 120)).astype(np.uint8) * 255
        gp_cand = cv2.morphologyEx(gp_cand, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        num_gp, gp_lbl, gp_stats, _ = cv2.connectedComponentsWithStats(gp_cand, 8)
        best_gp = max(range(1, num_gp), key=lambda i: gp_stats[i, cv2.CC_STAT_AREA], default=0)
        if best_gp > 0 and int(gp_stats[best_gp, cv2.CC_STAT_AREA]) >= 600:
            gpy, gpx = np.where(gp_lbl == best_gp)
            sam_gp = os.path.join(self.masks_dir, "sam_gamepad.png")
            segment_interactive(
                src_ref_path,
                sam_gp,
                points=[[gx1 + int(np.median(gpx)), gy1 + int(np.median(gpy))]],
                labels=[1],
                box=[gx1, gy1, gx2, gy2],
                mask_level=1,
                tmp_dir=self.masks_dir,
            )
            g_m = _imread_unicode(sam_gp, cv2.IMREAD_GRAYSCALE) if os.path.exists(sam_gp) else np.zeros((h, w), dtype=np.uint8)
            if g_m is None:
                g_m = np.zeros((h, w), dtype=np.uint8)
            elif g_m.shape[:2] != (h, w):
                g_m = cv2.resize(g_m, (w, h), interpolation=cv2.INTER_LINEAR)
            gp_fallback = np.zeros((h, w), dtype=np.uint8)
            gp_fallback[gy1:gy2, gx1:gx2] = np.where(gp_lbl == best_gp, 255, 0).astype(np.uint8)
            gp_mask = cv2.bitwise_or(gp_fallback, (g_m > 127).astype(np.uint8) * 255)
            gp_mask[:gy1, :] = 0
            gp_mask[gy2:, :] = 0
            gp_mask[:, :gx1] = 0
            gp_mask = cv2.subtract(gp_mask, claimed)
            self._add_raster_layer(
                name="Console_Gamepad_3D_Neon",
                layer_type="object",
                group="4_Decor_&_Gaming_Gear",
                src_rgb=rgb,
                mask_u8=gp_mask,
                cat="gaming_gear_3d",
                confidence=0.92,
                psd_effects={"dropShadow": [{"enabled": True, "size": 18, "distance": 10, "angle": 120, "color": [0, 35, 30], "opacity": 0.45}]},
            )
            claimed = cv2.bitwise_or(claimed, gp_mask)

        # 5. Top Floating Green Paper Card Fragment (`y < 8%, x in [44..64%]`)
        pf_y2, pf_x1, pf_x2 = int(h * 0.075), int(w * 0.44), int(w * 0.65)
        pf_hsv = hsv[:pf_y2, pf_x1:pf_x2]
        pf_cand = ((pf_hsv[:, :, 0] >= 55) & (pf_hsv[:, :, 0] <= 88) & (pf_hsv[:, :, 1] >= 55) & (pf_hsv[:, :, 2] >= 130)).astype(np.uint8) * 255
        pf_cand = cv2.morphologyEx(pf_cand, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        if int(np.sum(pf_cand > 0)) > 350:
            pf_mask = np.zeros((h, w), dtype=np.uint8)
            pf_mask[:pf_y2, pf_x1:pf_x2] = cv2.subtract(pf_cand, claimed[:pf_y2, pf_x1:pf_x2])
            self._add_raster_layer("Paper_Floating_Top", "decor", "4_Decor_&_Gaming_Gear", rgb, pf_mask, "decor_floating", 0.88)
            claimed = cv2.bitwise_or(claimed, pf_mask)

        # 6. Golden 4-Point Sparkle Stars (`Stars_4Point_Sparkles` with InnerShadow FX) & Confetti Chips
        # Search unclaimed sky & stadium zones for small vivid golden/green/orange isolated shapes
        unclaimed = 255 - cv2.dilate(claimed, np.ones((5, 5), np.uint8), iterations=1)
        # Protect bottom-right green wave & top-left lime wave from confetti detector
        unclaimed[int(h * 0.85):, int(w * 0.50):] = 0
        unclaimed[:int(h * 0.11), :int(w * 0.34)] = 0

        star_cand = (
            (unclaimed > 0)
            & (hsv[:, :, 0] >= 20)
            & (hsv[:, :, 0] <= 29)
            & (hsv[:, :, 1] >= 175)
            & (hsv[:, :, 2] >= 220)
        ).astype(np.uint8) * 255
        confetti_cand = (
            (unclaimed > 0)
            & (hsv[:, :, 1] >= 140)
            & (hsv[:, :, 2] >= 165)
            & ((hsv[:, :, 0] >= 48) | (hsv[:, :, 0] <= 19))
        ).astype(np.uint8) * 255

        # Separate 4-point symmetric stars vs confetti strips by area & bounding compactness
        num_st, st_lbl, st_stats, _ = cv2.connectedComponentsWithStats(star_cand, 8)
        stars_all = np.zeros((h, w), dtype=np.uint8)
        extra_conf = np.zeros((h, w), dtype=np.uint8)
        for si in range(1, num_st):
            area = int(st_stats[si, cv2.CC_STAT_AREA])
            bw_s, bh_s = int(st_stats[si, cv2.CC_STAT_WIDTH]), int(st_stats[si, cv2.CC_STAT_HEIGHT])
            if 120 <= area <= 7000:
                if bh_s >= bw_s * 1.15:  # Taller diamond 4-point star
                    stars_all[st_lbl == si] = 255
                else:
                    extra_conf[st_lbl == si] = 255

        if int(np.sum(stars_all > 0)) >= 200:
            self._add_raster_layer(
                name="Stars_4Point_Sparkles",
                layer_type="decor",
                group="4_Decor_&_Gaming_Gear",
                src_rgb=rgb,
                mask_u8=stars_all,
                cat="decor_stars",
                confidence=0.90,
                psd_effects={"innerShadow": [{"enabled": True, "size": 4, "distance": 2, "angle": 120, "color": [190, 110, 0], "opacity": 0.45}]},
            )
            claimed = cv2.bitwise_or(claimed, stars_all)

        # Keep valid small confetti particles (`80 <= area <= 3500`, avoid floor stripes below y=78%)
        confetti_cand[:int(h * 0.02), :] = 0
        confetti_cand[int(h * 0.78):, :] = 0
        confetti_cand = cv2.bitwise_or(confetti_cand, extra_conf)
        num_cf, cf_lbl, cf_stats, _ = cv2.connectedComponentsWithStats(confetti_cand, 8)
        conf_all = np.zeros((h, w), dtype=np.uint8)
        for ci in range(1, num_cf):
            if 80 <= int(cf_stats[ci, cv2.CC_STAT_AREA]) <= 3500:
                conf_all[cf_lbl == ci] = 255
        if int(np.sum(conf_all > 0)) >= 150:
            self._add_raster_layer("Confetti_Particles", "decor", "4_Decor_&_Gaming_Gear", rgb, conf_all, "decor_confetti", 0.88)
            claimed = cv2.bitwise_or(claimed, conf_all)

        return claimed

    # ------------------------------------------------------------------
    # MODULE 4: Sequential LaMa Stadium Background Reconstruction
    # ------------------------------------------------------------------
    def _reconstruct_clean_stadium_background(
        self,
        bgr: np.ndarray,
        total_fg_mask: np.ndarray,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Remove all podiums, prizes, titles, logos, gear, and decor simultaneously then refine via native 512x512 LaMa tiles."""
        h, w = bgr.shape[:2]
        work_bgr = bgr.copy()
        dil_fg = cv2.dilate(total_fg_mask, np.ones((15, 15), np.uint8), iterations=1)

        # Widen upper headline & ribbon shadow band (`23px`) so soft drop shadows leave zero ghost smudges
        sky_dil = cv2.dilate(total_fg_mask, np.ones((23, 23), np.uint8), iterations=1)
        sy1, sy2 = int(h * 0.08), int(h * 0.33)
        sx1, sx2 = int(w * 0.10), int(w * 0.90)
        dil_fg[sy1:sy2, sx1:sx2] = cv2.bitwise_or(dil_fg[sy1:sy2, sx1:sx2], sky_dil[sy1:sy2, sx1:sx2])

        # Catch any leftover bright orange podium rim/bevel pixels in mid-ground so zero podium fragments survive
        hsv_bg = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        orange_band = np.zeros((h, w), dtype=np.uint8)
        oy1, oy2 = int(h * 0.30), int(h * 0.92)
        orange_mask = (
            (hsv_bg[oy1:oy2, :, 0] >= 5)
            & (hsv_bg[oy1:oy2, :, 0] <= 24)
            & (hsv_bg[oy1:oy2, :, 1] >= 115)
            & (hsv_bg[oy1:oy2, :, 2] >= 135)
        ).astype(np.uint8) * 255
        orange_band[oy1:oy2, :] = cv2.dilate(orange_mask, np.ones((15, 15), np.uint8), iterations=1)
        dil_fg = cv2.bitwise_or(dil_fg, orange_band)

        # Row-wise pre-clear ALL masked holes simultaneously from unmasked outer sky/stadium columns BEFORE LaMa
        # so adjacent orange podiums or headline letters are completely gone from LaMa's surrounding context!
        pre_bgr = work_bgr.copy()
        clean_rows_y = np.where(np.sum(dil_fg == 0, axis=1) >= 24)[0]
        fallback_row_val = (
            np.median(work_bgr[dil_fg == 0], axis=0)
            if np.any(dil_fg == 0)
            else np.array([120, 115, 105], dtype=np.float32)
        )
        for ry in range(h):
            masked_x = np.where(dil_fg[ry, :] > 0)[0]
            if len(masked_x) == 0:
                continue
            unmasked_x = np.where(dil_fg[ry, :] == 0)[0]
            if len(unmasked_x) >= 12:
                ux_f = unmasked_x.astype(np.float32)
                mx_f = masked_x.astype(np.float32)
                for ch in range(3):
                    pre_bgr[ry, masked_x, ch] = np.clip(
                        np.interp(mx_f, ux_f, work_bgr[ry, unmasked_x, ch].astype(np.float32)),
                        0,
                        255,
                    ).astype(np.uint8)
            elif len(clean_rows_y) > 0:
                nearest_ry = int(clean_rows_y[np.argmin(np.abs(clean_rows_y - ry))])
                unm2 = np.where(dil_fg[nearest_ry, :] == 0)[0]
                ux_f2 = unm2.astype(np.float32)
                mx_f = masked_x.astype(np.float32)
                for ch in range(3):
                    pre_bgr[ry, masked_x, ch] = np.clip(
                        np.interp(mx_f, ux_f2, work_bgr[nearest_ry, unm2, ch].astype(np.float32)),
                        0,
                        255,
                    ).astype(np.uint8)
            else:
                pre_bgr[ry, masked_x] = fallback_row_val.astype(np.uint8)

        sm_pre = cv2.GaussianBlur(pre_bgr, (15, 15), 0)
        work_bgr = np.where(dil_fg[:, :, None] > 0, sm_pre, work_bgr)

        # Native-resolution overlapping LaMa refinement tiles (tile_sz=340 <= 420 guarantees 1:1 512x512 crop!)
        tile_sz, step = 340, 260
        y_starts = list(range(0, max(1, h - tile_sz + 1), step))
        if not y_starts or y_starts[-1] + tile_sz < h:
            y_starts.append(max(0, h - tile_sz))
        x_starts = list(range(0, max(1, w - tile_sz + 1), step))
        if not x_starts or x_starts[-1] + tile_sz < w:
            x_starts.append(max(0, w - tile_sz))

        for ty1 in y_starts:
            ty2 = min(h, ty1 + tile_sz)
            for tx1 in x_starts:
                tx2 = min(w, tx1 + tile_sz)
                sub_m = np.zeros((h, w), dtype=np.uint8)
                sub_m[ty1:ty2, tx1:tx2] = dil_fg[ty1:ty2, tx1:tx2]
                if int(np.sum(sub_m > 0)) < 150:
                    continue
                tile_l = _run_lama_local(work_bgr, sub_m)
                if tile_l is not None:
                    work_bgr = np.where(sub_m[:, :, None] > 0, tile_l, work_bgr)

        # Gentle blend on outer mask edges so transitions disappear seamlessly
        edge_band = cv2.subtract(cv2.dilate(dil_fg, np.ones((5, 5), np.uint8)), cv2.erode(dil_fg, np.ones((5, 5), np.uint8)))
        if np.any(edge_band > 0):
            sm_bgr = cv2.GaussianBlur(work_bgr, (5, 5), 0)
            work_bgr[edge_band > 0] = sm_bgr[edge_band > 0]

        bg_rgb = cv2.cvtColor(work_bgr, cv2.COLOR_BGR2RGB)
        return bg_rgb, {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "pixel_origin": "algorithmic_inpaint",
            "engine": "lama-2025jan-tiled-3pass",
            "coverage_pct": round(float(np.mean(dil_fg > 0)) * 100.0, 2),
        }


def _render_banner_visual_reports(
    doc_layers: List[Dict[str, Any]],
    project_dir: str,
    w: int,
    h: int,
    bg_clean_rgb: np.ndarray,
    full_composite_rgb: np.ndarray,
) -> Tuple[str, str]:
    """Render 4-Step Garena Progression Grid (`banner_progression_grid.jpg`) & Layers Checkerboard Sheet."""
    def _compose_groups(group_prefixes: Tuple[str, ...], start_with_bg: bool = True) -> Image.Image:
        base = Image.fromarray(bg_clean_rgb, "RGB").convert("RGBA") if start_with_bg else Image.new("RGBA", (w, h), (16, 18, 24, 255))
        for lyr in sorted(doc_layers, key=lambda x: x.get("z_index", 0)):
            if not lyr.get("visible", True) or lyr.get("type") in ("adjustment", "background"):
                continue
            if not any((lyr.get("group") or "").startswith(p) for p in group_prefixes):
                continue
            src = lyr.get("source_file")
            if not src or not os.path.exists(os.path.join(project_dir, src)):
                continue
            im = Image.open(os.path.join(project_dir, src)).convert("RGBA")
            tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            tmp.paste(im, (int(lyr["x"]), int(lyr["y"])))
            base = Image.alpha_composite(base, tmp)
        return base

    step1 = Image.fromarray(bg_clean_rgb, "RGB")
    step2 = _compose_groups(("2_Podiums", "3_Prizes"), start_with_bg=True).convert("RGB")
    step3 = _compose_groups(("4_Decor", "5_Logos", "6_Typography"), start_with_bg=False).convert("RGB")
    step4 = Image.fromarray(full_composite_rgb, "RGB")

    pw, ph = 580, max(240, int(round(580 * h / max(1, w))))
    grid = Image.new("RGB", (pw * 2 + 12, ph * 2 + 12), (16, 18, 24))
    dr = ImageDraw.Draw(grid)
    panels = [
        (0, 0, step1, "STEP 1: LaMa Clean Stadium & Cloud BG"),
        (pw + 12, 0, step2, "STEP 2: + 3D Podiums & Separated Prizes"),
        (0, ph + 12, step3, "STEP 3: + Dual Typography & 3D Gaming Decor"),
        (pw + 12, ph + 12, step4, "STEP 4: Final Reconstructed Banner Composite"),
    ]
    for gx, gy, im, lbl in panels:
        grid.paste(im.resize((pw, ph), Image.Resampling.LANCZOS), (gx, gy))
        dr.rectangle([gx, gy, gx + pw, gy + 28], fill=(12, 14, 18))
        dr.text((gx + 10, gy + 7), lbl, fill=(74, 222, 128))
    prog_rel = "banner_progression_grid.jpg"
    grid.save(os.path.join(project_dir, prog_rel), quality=92)

    # Extracted Layers Checkerboard Sheet (up to 16 visible raster objects)
    raster_vis = [l for l in sorted(doc_layers, key=lambda x: x.get("z_index", 0)) if l.get("visible", True) and l.get("type") not in ("adjustment",) and l.get("source_file")]
    cols, rows = 4, max(1, (min(16, len(raster_vis)) + 3) // 4)
    cell = 280
    sheet = Image.new("RGB", (cols * cell, rows * cell), (22, 24, 30))
    sdr = ImageDraw.Draw(sheet)
    cb_tile = np.zeros((cell, cell, 3), dtype=np.uint8)
    for yy in range(0, cell, 16):
        for xx in range(0, cell, 16):
            cb_tile[yy:yy + 16, xx:xx + 16] = 210 if ((xx // 16 + yy // 16) % 2 == 0) else 165
    cb_tpl = Image.fromarray(cb_tile, "RGB").convert("RGBA")

    for i, lyr in enumerate(raster_vis[:16]):
        gx, gy = (i % cols) * cell, (i // cols) * cell
        im = Image.open(os.path.join(project_dir, lyr["source_file"])).convert("RGBA")
        sc = min((cell - 20) / max(1, im.width), (cell - 38) / max(1, im.height))
        nw, nh = max(1, int(im.width * sc)), max(1, int(im.height * sc))
        cb = cb_tpl.copy()
        cb.alpha_composite(im.resize((nw, nh), Image.Resampling.LANCZOS), ((cell - nw) // 2, 30 + (cell - 36 - nh) // 2))
        sheet.paste(cb.convert("RGB"), (gx, gy))
        sdr.rectangle([gx, gy, gx + cell, gy + 24], fill=(16, 20, 28))
        sdr.text((gx + 8, gy + 6), f"{lyr['name'][:26]} ({lyr['width']}x{lyr['height']})", fill=(147, 197, 253))
    sheet_rel = "banner_layers_sheet.jpg"
    sheet.save(os.path.join(project_dir, sheet_rel), quality=92)
    return prog_rel, sheet_rel


def run_banner_decomposition_pipeline(
    image_path: str,
    project_dir: str,
    project_id: Optional[str] = None,
    title: str = "Garena Banner 5-Module Decomposition",
    max_dim: int = 2048,
) -> Dict[str, Any]:
    """Execute complete 5-Module Esports/Graphic Banner Reverse-Engineering & PSD Packaging."""
    bgr = _imread_unicode(image_path)
    if bgr is None:
        raise ValueError(f"Cannot read banner image: {image_path}")

    os.makedirs(project_dir, exist_ok=True)
    pid = project_id or f"banner_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"

    oh, ow = bgr.shape[:2]
    if max(ow, oh) > max_dim:
        sc = max_dim / float(max(ow, oh))
        bgr = cv2.resize(bgr, (int(round(ow * sc)), int(round(oh * sc))), interpolation=cv2.INTER_AREA)
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)

    src_rel = "source_reference.png"
    src_abs = os.path.join(project_dir, src_rel)
    _save_rgb(rgb, src_abs)

    # Salient RMBG map to assist multi-item apparel cutouts
    rmbg_path = os.path.join(project_dir, "masks", "rmbg_banner_salient.png")
    os.makedirs(os.path.dirname(rmbg_path), exist_ok=True)
    rmbg_res = run_rmbg_salient(src_abs, rmbg_path)
    rmbg_u8 = np.zeros((h, w), dtype=np.uint8)
    if rmbg_res.get("ok") and os.path.exists(rmbg_path):
        rm_tmp = _imread_unicode(rmbg_path, cv2.IMREAD_GRAYSCALE)
        if rm_tmp is not None:
            if rm_tmp.shape[:2] != (h, w):
                rm_tmp = cv2.resize(rm_tmp, (w, h), interpolation=cv2.INTER_LINEAR)
            rmbg_u8 = (rm_tmp > 115).astype(np.uint8) * 255

    decomposer = BannerDecomposer(project_dir)

    # Module 2: Podiums (+ Amodal Top Fill) & Prize Clusters
    claimed = decomposer._decompose_podiums_and_prizes(bgr, rgb, hsv, lab, src_abs, rmbg_u8)

    # Module 1: Skewed Ribbons & Dual Typography (`OrigFX` + hidden `Editable Vector TySh` with LayerFX)
    claimed = decomposer._extract_typography_and_ribbons(bgr, rgb, hsv, lab, src_abs, claimed)

    # Module 3: Logos, 3D Gaming Gear (Laptop & Gamepad), Pin, Paper, Stars & Confetti
    claimed = decomposer._extract_decor_logos_and_gear(bgr, rgb, hsv, src_abs, claimed)

    # Module 4: Clean LaMa Stadium + Clouds Background + Subtle Non-Destructive Atmosphere Stack
    bg_clean_rgb, recon_meta = decomposer._reconstruct_clean_stadium_background(bgr, claimed)
    bg_rel = "layers/01_Background_Stadium_Clean.png"
    _save_rgba(np.dstack([bg_clean_rgb, np.full((h, w), 255, dtype=np.uint8)]), os.path.join(project_dir, bg_rel))

    bg_layer = make_layer(
        name="01_Background_Stadium_Clean",
        layer_type="background",
        source_file=bg_rel,
        x=0,
        y=0,
        width=w,
        height=h,
        z_index=0,
        group="1_BG_&_Atmosphere",
        ai_reconstructed=True,
        reconstruction_history=[recon_meta],
        confidence_score=0.92,
    )
    # Include hidden backup raw reference at bottom for instant A/B inspection inside Photoshop
    raw_ref_rel = "layers/00_Original_Flattened_Ref.png"
    _save_rgba(np.dstack([rgb, np.full((h, w), 255, dtype=np.uint8)]), os.path.join(project_dir, raw_ref_rel))
    raw_ref_layer = make_layer(
        name="00_Original_Flattened_Ref",
        layer_type="background",
        source_file=raw_ref_rel,
        x=0,
        y=0,
        width=w,
        height=h,
        z_index=0,
        visible=False,
        group="1_BG_&_Atmosphere",
        locked=True,
    )
    # Re-sequence z-indices cleanly: Raw Ref=0, Clean Stadium BG=1, Atmosphere curves=2, Extracted items>=10
    bg_layer["z_index"] = 1
    curves_stadium = make_layer(
        name="Curves_Stadium_Contrast",
        layer_type="adjustment",
        source_file=None,
        x=0,
        y=0,
        width=w,
        height=h,
        z_index=2,
        opacity=0.20,
        visible=False,  # Clean BG already matches original tonal grading; keep available for designer tweak!
        group="1_BG_&_Atmosphere",
        adjustment_data={
            "type": "curves",
            "presetKind": 2,
            "channels": [[{"input": 0, "output": 0}, {"input": 72, "output": 62}, {"input": 185, "output": 196}, {"input": 255, "output": 255}]],
        },
        metadata={"role": "optional_stadium_contrast_grade"},
    )
    cb_stadium = make_layer(
        name="ColorBalance_Stadium_Mint",
        layer_type="adjustment",
        source_file=None,
        x=0,
        y=0,
        width=w,
        height=h,
        z_index=3,
        opacity=0.25,
        visible=False,
        group="1_BG_&_Atmosphere",
        adjustment_data={
            "type": "color balance",
            "shadows": {"cyanRed": -4, "magentaGreen": 6, "yellowBlue": -2},
            "midtones": {"cyanRed": -6, "magentaGreen": 10, "yellowBlue": -4},
            "highlights": {"cyanRed": 0, "magentaGreen": 4, "yellowBlue": 0},
            "preserveLuminosity": True,
        },
        metadata={"role": "optional_brand_mint_grade"},
    )

    all_layers = [raw_ref_layer, bg_layer, curves_stadium, cb_stadium] + decomposer.doc_layers

    # Compose faithful reconstructed preview from all visible extracted layers over clean stadium BG
    comp_im = Image.fromarray(bg_clean_rgb, "RGB").convert("RGBA")
    for lyr in sorted(all_layers, key=lambda l: l.get("z_index", 0)):
        if not lyr.get("visible", True) or lyr.get("type") in ("adjustment", "background"):
            continue
        src = lyr.get("source_file")
        if not src or not os.path.exists(os.path.join(project_dir, src)):
            continue
        im_l = Image.open(os.path.join(project_dir, src)).convert("RGBA")
        tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        tmp.paste(im_l, (int(lyr["x"]), int(lyr["y"])))
        comp_im = Image.alpha_composite(comp_im, tmp)
    comp_rgb = np.array(comp_im.convert("RGB"))

    comp_rel = "composite_after.png"
    _save_rgb(comp_rgb, os.path.join(project_dir, comp_rel))

    prog_rel, sheet_rel = _render_banner_visual_reports(
        all_layers, project_dir, w, h, bg_clean_rgb, comp_rgb
    )

    doc = create_document(
        project_id=pid,
        title=title,
        mode="BANNER_DECOMPOSE",
        width=w,
        height=h,
        layers=all_layers,
        source_image=src_rel,
        brand={
            "pipeline": "garena_5_module_reverse_engineering_v1_5",
            "extracted_palette": ["#75FF50", "#50FFA0", "#FFE500", "#FF9900", "#0B2B68"],
            "custom_groups": [
                "1_BG_&_Atmosphere",
                "2_Podiums_3D_Isometric",
                "3_Prizes_&_Items",
                "4_Decor_&_Gaming_Gear",
                "5_Logos_&_Footer",
                "6_Typography_OrigFX_&_Editable",
            ],
        },
        semantic_objects=decomposer.semantic_objects,
        notes=[
            "Garena Banner 5-Module Reverse-Engineering Pipeline v1.5.",
            "Dual-Version Typography: OrigFX Bitmap visible by default + Hidden Editable Vector TySh with real Photoshop LayerFX.",
            "Podiums repaired with Amodal Top-Face Inpainting; Clean Stadium BG reconstructed via 3-Pass LaMa 2025jan ONNX.",
        ],
    )
    doc["composite_preview"] = comp_rel
    doc["banner_progression_grid"] = prog_rel
    doc["banner_layers_sheet"] = sheet_rel
    save_document(doc, project_dir)
    save_version(doc, project_dir, note="Initial 5-Module Banner Reverse-Engineering & LayerFX Decomposition")

    return {
        "ok": True,
        "project_id": pid,
        "project_dir": project_dir,
        "document": doc,
        "layer_count": len(doc["layers"]),
        "text_layer_count": sum(1 for l in doc["layers"] if l.get("type") == "text"),
        "fx_layer_count": sum(1 for l in doc["layers"] if l.get("psd_effects")),
        "banner_progression_grid": prog_rel,
        "banner_layers_sheet": sheet_rel,
    }
