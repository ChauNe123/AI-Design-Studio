# -*- coding: utf-8 -*-
"""AI Design Studio v1.5 — Commercial Service Poster Decomposer & Amodal PSD Packager.

Decomposes commercial service posters (e.g., Melbourne Xpress Cabs - Taxi Service)
into a clean 6-Group non-destructive Photoshop `.PSD` project featuring:
  1_BG_&_Atmosphere        : Clean Twilight Sky (LaMa), Ferris Wheel Landmark, Amodal Curved Road + Curves/ColorBalance
  2_Hero_Subjects_&_Mockup : Amodal iPhone + Clean Map, Standalone Screen, Car Contact Shadow, SlimSAM Hero Taxi, Decal, Plate
  3_GPS_Route_&_Pins       : Orthogonal Blue GPS Path, Origin Red Pin, Destination Red Glow (+ LayerFX)
  4_Footer_Banners_&_Badges: Clean Translucent Strip, Clean Blue/Orange Diagonal Footer Wedges, Phone & Globe Icons
  5_Brand_Logo_TopLeft     : Top-Left Brand Silhouette Emblem & Wing Lines
  6_Typography_OrigFX_&_Editable : 9x Visible OrigFX Bitmaps paired with 9x Hidden Editable Vector TySh (+ LayerFX)
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
    segment_interactive,
)
from core.typography_engine import list_local_fonts, render_styled_text


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


def _smooth_contour_alpha(alpha_u8: np.ndarray, feather_px: int = 3) -> np.ndarray:
    """Smooth staircase cutout edges via 2x cubic contour smoothing + anti-aliased feather."""
    h, w = alpha_u8.shape[:2]
    up = cv2.resize(alpha_u8, (max(8, w * 2), max(8, h * 2)), interpolation=cv2.INTER_CUBIC)
    up_blur = cv2.GaussianBlur(up, (7, 7), 0)
    _, up_clean = cv2.threshold(up_blur, 128, 255, cv2.THRESH_BINARY)
    down = cv2.resize(up_clean, (w, h), interpolation=cv2.INTER_AREA)
    fk = max(3, feather_px | 1)
    return cv2.GaussianBlur(down, (fk, fk), 0)


def _decontaminate_rgba(
    src_rgb: np.ndarray,
    alpha_u8: np.ndarray,
    pad: int = 2,
    solid_thresh: int = 225,
) -> Optional[Tuple[int, int, int, int, np.ndarray]]:
    """Tightly crop RGBA layer and replace semi-transparent fringe RGB with nearest solid interior color."""
    h, w = src_rgb.shape[:2]
    ys, xs = np.where(alpha_u8 > 10)
    if len(xs) < 6:
        return None
    x1 = max(0, int(xs.min()) - pad)
    y1 = max(0, int(ys.min()) - pad)
    x2 = min(w, int(xs.max()) + 1 + pad)
    y2 = min(h, int(ys.max()) + 1 + pad)
    bw, bh = x2 - x1, y2 - y1
    if bw < 2 or bh < 2:
        return None

    crop_rgb = src_rgb[y1:y2, x1:x2].copy()
    crop_a = alpha_u8[y1:y2, x1:x2].copy()

    solid = crop_a >= solid_thresh
    semi = (crop_a > 10) & (~solid)
    if np.any(solid) and np.any(semi):
        # Normalized convolution pushes solid interior pixel RGB smoothly outward into anti-aliased rims
        w_f = solid.astype(np.float32)
        rgb_f = crop_rgb.astype(np.float32) * w_f[:, :, None]
        num = cv2.GaussianBlur(rgb_f, (7, 7), 0)
        den = cv2.GaussianBlur(w_f, (7, 7), 0)
        valid = den > 1e-4
        fill = np.where(valid[:, :, None], num / np.maximum(den[:, :, None], 1e-4), crop_rgb.astype(np.float32))
        crop_rgb[semi] = np.clip(fill[semi], 0, 255).astype(np.uint8)

    return x1, y1, bw, bh, np.dstack([crop_rgb, crop_a])


def _flood_seal_holes(bin_u8: np.ndarray) -> np.ndarray:
    """Seal interior dark/white enclosed holes inside a closed foreground binary mask."""
    pad = cv2.copyMakeBorder(bin_u8, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    ff = np.zeros((pad.shape[0] + 2, pad.shape[1] + 2), np.uint8)
    cv2.floodFill(pad, ff, (0, 0), 128)
    return np.where(pad[1:-1, 1:-1] == 128, 0, 255).astype(np.uint8)


def _rounded_rect_mask(h: int, w: int, x1: int, y1: int, x2: int, y2: int, r: int) -> np.ndarray:
    """Generate clean anti-aliased rounded-rectangle mask in [0..255]."""
    im = Image.new("L", (w, h), 0)
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([x1, y1, x2, y2], radius=r, fill=255)
    return np.array(im, dtype=np.uint8)


def _pick_poster_font(prefer_bold: bool = True) -> Tuple[str, str]:
    fonts = list_local_fonts()
    if not fonts:
        return "Arial-BoldMT", ""
    prefs = (
        ["FZ Poppins Bold", "Be Vietnam Pro Bold", "Be Vietnam Pro ExtraBold", "Segoe UI"]
        if prefer_bold
        else ["Be Vietnam Pro", "FZ Poppins", "Segoe UI"]
    )
    for want in prefs:
        hit = next((f for f in fonts if want.lower() in f["name"].lower()), None)
        if hit:
            return hit["name"], hit["file"]
    return fonts[0]["name"], fonts[0]["file"]


class PosterDecomposer:
    """Commercial Service Poster Decomposer (6-Group, 39-Layer Amodal + Dual Typography Pipeline)."""

    def __init__(self, project_dir: str):
        self.project_dir = project_dir
        self.layers_dir = os.path.join(project_dir, "layers")
        self.masks_dir = os.path.join(project_dir, "masks")
        os.makedirs(self.layers_dir, exist_ok=True)
        os.makedirs(self.masks_dir, exist_ok=True)
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
        z_index: int,
        confidence: float = 0.92,
        psd_effects: Optional[Dict[str, Any]] = None,
        visible: bool = True,
        opacity: float = 1.0,
        decontaminate: bool = True,
        ai_reconstructed: bool = False,
        reconstruction_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Any]]:
        res = _decontaminate_rgba(src_rgb, mask_u8, pad=2) if decontaminate else _decontaminate_rgba(src_rgb, mask_u8, pad=2, solid_thresh=0)
        if not res:
            return None
        x, y, bw, bh, rgba = res
        safe = re.sub(r"[^A-Za-z0-9_\-]", "_", name)
        rel_img = f"layers/{safe}.png"
        _save_rgba(rgba, os.path.join(self.project_dir, rel_img))

        rel_msk = f"masks/m_{safe}.png"
        _save_gray(mask_u8[y:y + bh, x:x + bw], os.path.join(self.project_dir, rel_msk))

        lyr = make_layer(
            name=name,
            layer_type=layer_type,
            source_file=rel_img,
            mask_file=rel_msk,
            x=x,
            y=y,
            width=bw,
            height=bh,
            z_index=z_index,
            visible=visible,
            opacity=opacity,
            group=group,
            psd_effects=psd_effects,
            confidence_score=confidence,
            ai_reconstructed=ai_reconstructed,
            reconstruction_history=reconstruction_history or [],
            metadata={"poster_module": cat},
        )
        self.doc_layers.append(lyr)
        self.semantic_objects.append(make_semantic_object(
            object_id=f"obj_{safe}",
            object_name=name,
            object_category=cat,
            bounding_box=[x, y, bw, bh],
            z_index=z_index,
            confidence_score=confidence,
            segmentation_mask=rel_msk,
            source_asset=rel_img,
            reconstruction_status="amodal_reconstructed" if ai_reconstructed else "extracted_poster_element",
            editability_status="layer_and_fx_editable" if psd_effects else "raster_editable",
            linked_layer_id=lyr["id"],
        ))
        return lyr

    def _add_dual_text_pair(
        self,
        orig_name: str,
        edit_name: str,
        text_str: str,
        src_rgb: np.ndarray,
        orig_mask_u8: np.ndarray,
        edit_x: int,
        edit_y: int,
        font_size: int,
        color: List[int],
        z_orig: int,
        z_edit: int,
        prefer_bold: bool = True,
        align: str = "left",
        psd_effects: Optional[Dict[str, Any]] = None,
        confidence: float = 0.94,
    ) -> None:
        self._add_raster_layer(
            name=orig_name,
            layer_type="object",
            group="6_Typography_OrigFX_&_Editable",
            src_rgb=src_rgb,
            mask_u8=orig_mask_u8,
            cat="typography_orig_fx",
            z_index=z_orig,
            confidence=confidence,
            decontaminate=True,
        )

        font_name, font_file = _pick_poster_font(prefer_bold=prefer_bold)
        ed_im = render_styled_text(
            text=text_str,
            font_file=font_file,
            font_size=max(12, int(font_size)),
            color=tuple(color[:3]),
            align=align,
            stroke_enabled=False,
            shadow_enabled=False,
            gradient_enabled=False,
        )
        safe = re.sub(r"[^A-Za-z0-9_\-]", "_", edit_name)
        rel = f"layers/{safe}.png"
        ed_im.save(os.path.join(self.project_dir, rel))

        lyr = make_layer(
            name=edit_name,
            layer_type="text",
            source_file=rel,
            x=max(0, edit_x),
            y=max(0, edit_y),
            width=ed_im.width,
            height=ed_im.height,
            z_index=z_edit,
            visible=False,
            group="6_Typography_OrigFX_&_Editable",
            psd_effects=psd_effects,
            text_data={
                "text": text_str,
                "font": font_name,
                "font_file": font_file,
                "font_size": int(font_size),
                "color": color,
                "align": align,
                "tracking": 0,
                "leading": 6,
                "stroke_enabled": False,
                "gradient_enabled": False,
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

    # ------------------------------------------------------------------
    # HERO TAXI + CHECKERED DECAL + LICENSE PLATE + CONTACT SHADOW
    # ------------------------------------------------------------------
    def _extract_taxi_group(
        self,
        bgr: np.ndarray,
        rgb: np.ndarray,
        hsv: np.ndarray,
        gray: np.ndarray,
        src_ref_path: str,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Extract clean Hero Yellow Taxi, Contact Shadow, Isolated Checkered Decal, and Front Plate."""
        h, w = bgr.shape[:2]

        # 1. SlimSAM-77 multi-point segmentation for full Hyundai taxi silhouette
        sam_car_path = os.path.join(self.masks_dir, "sam_taxi_hero.png")
        segment_interactive(
            src_ref_path,
            sam_car_path,
            points=[
                [270, 392], [360, 415],  # roof & windshield
                [150, 480], [250, 505],  # doors
                [480, 485], [575, 515],  # hood & fender
                [440, 495], [580, 530], [600, 555],  # headlight, grille & lower bumper
                [108, 548], [352, 588],  # rear & front wheels
                [30, 430],               # neg: left sky
                [40, 560], [240, 648], [648, 635],  # neg: asphalt road
                [480, 410], [595, 445],  # neg: iPhone map screen above hood
            ],
            labels=[1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0],
            box=[55, 360, 656, 654],
            mask_level=1,
            tmp_dir=self.masks_dir,
        )
        sam_u8 = np.zeros((h, w), dtype=np.uint8)
        if os.path.exists(sam_car_path):
            m = _imread_unicode(sam_car_path, cv2.IMREAD_GRAYSCALE)
            if m is not None:
                if m.shape[:2] != (h, w):
                    m = cv2.resize(m, (w, h), interpolation=cv2.INTER_LINEAR)
                sam_u8 = (m > 120).astype(np.uint8) * 255

        # 2. Chromatic yellow body + orange front plate
        yellow_body = (
            (hsv[:, :, 0] >= 13)
            & (hsv[:, :, 0] <= 36)
            & (hsv[:, :, 1] >= 88)
            & (hsv[:, :, 2] >= 115)
        ).astype(np.uint8) * 255
        yellow_body[:364, :] = 0
        yellow_body[650:, :] = 0
        yellow_body[:, :60] = 0
        yellow_body[:, 654:] = 0

        car_raw = cv2.bitwise_or(sam_u8, yellow_body)

        # Protect roof/hood upper line on right side against iPhone bezel & map bleed
        xx_g = np.arange(w)[None, :]
        yy_g = np.arange(h)[:, None]
        # Roofline slopes smoothly downward from x=390 (y=378) toward front nose x=648 (y=495)
        car_top_bound = np.where(
            xx_g < 390,
            360,
            np.round(378 + (xx_g - 390) * 0.43).astype(np.int32),
        )
        above_car = yy_g < car_top_bound
        car_raw[above_car] = 0
        car_raw[:, :60] = 0
        car_raw[:, 654:] = 0
        car_raw[653:, :] = 0

        # Ensure tire ellipses (dark rubber against dark asphalt) are 100% solid inside wheels
        wheel_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.ellipse(wheel_mask, (108, 545), (37, 50), 0, 0, 360, 255, -1)
        cv2.ellipse(wheel_mask, (352, 588), (54, 61), 0, 0, 360, 255, -1)
        car_raw = cv2.bitwise_or(car_raw, wheel_mask)

        # Exclude deep pitch-black road shadow outside yellow body & outside wheels below car sill
        car_hull_dil = cv2.dilate(yellow_body, np.ones((19, 19), np.uint8), iterations=1)
        black_road_leak = (yellow_body == 0) & (wheel_mask == 0) & (gray < 28) & (car_hull_dil == 0)
        car_raw[black_road_leak] = 0

        # Also trim any bright sky / bright iPhone screen leaking on car exterior perimeter
        bright_map_sky = (hsv[:, :, 1] < 42) & (gray > 188) & (yy_g < 500)
        car_closed = cv2.morphologyEx(car_raw, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        car_sealed = _flood_seal_holes(car_closed)
        # Re-open outside bright map pixels that sit directly along outer top rim (outside interior windshield/headlight)
        headlight_or_win = np.zeros((h, w), dtype=np.uint8)
        headlight_or_win[385:525, 130:515] = 255
        outer_sky_leak = bright_map_sky & (headlight_or_win == 0)
        car_sealed[outer_sky_leak] = 0

        # Keep single largest connected component (Hero Car)
        num_c, c_lbl, c_stats, _ = cv2.connectedComponentsWithStats(car_sealed, 8)
        best_c = max(range(1, num_c), key=lambda i: int(c_stats[i, cv2.CC_STAT_AREA]), default=0)
        taxi_bin = np.where(c_lbl == best_c, 255, 0).astype(np.uint8) if best_c > 0 else car_sealed
        taxi_bin = _flood_seal_holes(cv2.morphologyEx(taxi_bin, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
        taxi_alpha = _smooth_contour_alpha(taxi_bin, feather_px=3)

        self._add_raster_layer(
            name="09_Yellow_Taxi_Cab_Hero",
            layer_type="product",
            group="2_Hero_Subjects_&_Mockup",
            src_rgb=rgb,
            mask_u8=taxi_alpha,
            cat="hero_vehicle",
            z_index=14,
            confidence=0.95,
            psd_effects={
                "dropShadow": [{"enabled": True, "size": 16, "distance": 6, "angle": 115, "color": [0, 0, 0], "opacity": 0.40}],
            },
        )

        # 3. Taxi Contact Shadow on Asphalt directly underneath chassis & tires (z=12)
        shadow_band = np.zeros((h, w), dtype=np.uint8)
        cv2.ellipse(shadow_band, (365, 608), (305, 58), 3, 0, 360, 255, -1)
        shadow_band[:538, :] = 0
        shadow_band[664:, :] = 0
        # Use RGB chroma instead of HSV S (which explodes near V=0 on black shadow [1, 4, 8])
        rgb_chroma = np.ptp(bgr.astype(np.int16), axis=2)
        shadow_pixels = (shadow_band > 0) & (gray < 48) & (rgb_chroma < 24) & (taxi_bin == 0)
        shad_alpha = cv2.GaussianBlur(np.where(shadow_pixels, 250, 0).astype(np.uint8), (7, 7), 0)
        # Suppress faint residual outside elliptical ground band
        shad_alpha = cv2.bitwise_and(shad_alpha, shadow_band)
        if int(np.sum(shad_alpha > 20)) > 200:
            self._add_raster_layer(
                name="08_Taxi_Contact_Shadow_Road",
                layer_type="shadow",
                group="2_Hero_Subjects_&_Mockup",
                src_rgb=rgb,
                mask_u8=shad_alpha,
                cat="ground_shadow",
                z_index=12,
                opacity=0.95,
                confidence=0.92,
                decontaminate=False,
            )

        # 4. Isolated Black & White Checkered Taxi Decal Strip (`10_Taxi_Checkered_Decal_Strip`, hidden helper)
        decal_zone = np.zeros((h, w), dtype=np.uint8)
        decal_zone[425:496, 72:396] = 255
        decal_cand = ((decal_zone > 0) & (taxi_bin > 0) & (hsv[:, :, 1] < 85)).astype(np.uint8) * 255
        decal_cand = cv2.morphologyEx(decal_cand, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        num_dc, dc_lbl, dc_stats, _ = cv2.connectedComponentsWithStats(decal_cand, 8)
        best_dc = max(range(1, num_dc), key=lambda i: int(dc_stats[i, cv2.CC_STAT_AREA]), default=0)
        if best_dc > 0 and int(dc_stats[best_dc, cv2.CC_STAT_AREA]) > 200:
            decal_mask = np.where(dc_lbl == best_dc, 255, 0).astype(np.uint8)
            self._add_raster_layer(
                name="10_Taxi_Checkered_Decal_Strip",
                layer_type="object",
                group="2_Hero_Subjects_&_Mockup",
                src_rgb=rgb,
                mask_u8=decal_mask,
                cat="taxi_decal",
                z_index=15,
                visible=False,
                confidence=0.90,
            )

        # 5. Standalone Orange Front License Plate (`11_Taxi_Front_License_Plate_Orange`, z=16)
        plate_zone = np.zeros((h, w), dtype=np.uint8)
        plate_zone[530:578, 565:645] = 255
        plate_cand = (
            (plate_zone > 0)
            & (hsv[:, :, 0] >= 8)
            & (hsv[:, :, 0] <= 21)
            & (hsv[:, :, 1] >= 175)
            & (hsv[:, :, 2] >= 140)
        ).astype(np.uint8) * 255
        plate_cand = cv2.morphologyEx(plate_cand, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        plate_cand = _flood_seal_holes(plate_cand)
        num_pl, pl_lbl, pl_stats, _ = cv2.connectedComponentsWithStats(plate_cand, 8)
        best_pl = max(range(1, num_pl), key=lambda i: int(pl_stats[i, cv2.CC_STAT_AREA]), default=0)
        if best_pl > 0 and int(pl_stats[best_pl, cv2.CC_STAT_AREA]) > 250:
            plate_mask = cv2.dilate(np.where(pl_lbl == best_pl, 255, 0).astype(np.uint8), np.ones((3, 3), np.uint8))
            plate_alpha = _smooth_contour_alpha(plate_mask, feather_px=3)
            self._add_raster_layer(
                name="11_Taxi_Front_License_Plate_Orange",
                layer_type="shape",
                group="2_Hero_Subjects_&_Mockup",
                src_rgb=rgb,
                mask_u8=plate_alpha,
                cat="license_plate",
                z_index=16,
                confidence=0.93,
                psd_effects={
                    "stroke": [{"enabled": True, "size": 2, "position": "inside", "color": [25, 22, 20], "opacity": 0.85}],
                    "innerShadow": [{"enabled": True, "size": 3, "distance": 1, "angle": 120, "color": [0, 0, 0], "opacity": 0.35}],
                },
            )

        return taxi_bin, shad_alpha, wheel_mask

    # ------------------------------------------------------------------
    # IPHONE AMODAL MOCKUP & GOOGLE MAPS SCREEN
    # ------------------------------------------------------------------
    def _extract_iphone_amodal(
        self,
        bgr: np.ndarray,
        rgb: np.ndarray,
        hsv: np.ndarray,
        taxi_bin: np.ndarray,
        route_mask: np.ndarray,
        dest_pin_mask: np.ndarray,
    ) -> np.ndarray:
        """Reconstruct complete iPhone X/11 frame + Google Maps screen cleanly behind taxi and route line."""
        h, w = bgr.shape[:2]
        px1, py1, px2, py2 = 392, 80, 653, 530
        phone_outer_mask = _rounded_rect_mask(h, w, px1, py1, px2, py2, r=36)
        phone_bin = (phone_outer_mask > 127).astype(np.uint8) * 255

        work_bgr = bgr.copy()

        # 1. Tight route & red dot erase on upper map screen (`y: 265..362, x: 392..602` including left bezel crossing)
        erase_roi = np.zeros((h, w), dtype=np.uint8)
        erase_roi[265:362, 392:602] = 255
        bezel_strip = np.zeros((h, w), dtype=bool)
        bezel_strip[:, 392:409] = True
        blue_rt = (hsv[:, :, 0] >= 90) & (hsv[:, :, 0] <= 130) & (hsv[:, :, 1] >= np.where(bezel_strip, 68, 42))
        red_dt = ((hsv[:, :, 0] <= 16) | (hsv[:, :, 0] >= 162)) & (hsv[:, :, 1] >= 35)
        tight_overlay = np.where((erase_roi > 0) & (phone_bin > 0) & (blue_rt | red_dt), 255, 0).astype(np.uint8)
        screen_erase = cv2.bitwise_and(cv2.dilate(tight_overlay, np.ones((3, 3), np.uint8)), phone_bin)
        if np.any(screen_erase > 0):
            scr_only = screen_erase.copy()
            scr_only[:, :409] = 0
            work_bgr[scr_only > 0] = np.array([243, 244, 244], dtype=np.uint8)
            work_bgr = cv2.inpaint(work_bgr, screen_erase, 3, cv2.INPAINT_TELEA)

        # 2. Amodal reconstruction of the occluded lower portion covered by the yellow taxi (`y >= 345`)
        occl = (phone_bin > 0) & (cv2.dilate(taxi_bin, np.ones((9, 9), np.uint8)) > 0)
        if np.any(occl):
            amodal_canvas = work_bgr.copy()

            # (a) Sub-pixel vertical extension of the upper-left metallic bezel rail (`x: 392..409`) downward onto `y: 345..505`
            rail_src = work_bgr[170:250, 392:409].copy()
            rail_h = rail_src.shape[0]
            for ry in range(345, 505):
                sy = (ry - 345) % rail_h
                row_occl = occl[ry, 392:409]
                if np.any(row_occl):
                    amodal_canvas[ry, 392:409] = np.where(
                        row_occl[:, None],
                        rail_src[sy],
                        amodal_canvas[ry, 392:409],
                    )

            # (b) Fill remaining occluded inner map screen area (`x: 409..635, y: 355..512`) using upright map streets
            src_map = work_bgr[130:290, 412:635].copy()  # 160 x 223 upright map patch
            tile_h, tile_w = src_map.shape[:2]
            inner_mask = np.zeros((h, w), dtype=np.uint8)
            inner_mask[355:512, 409:635] = np.where(occl[355:512, 409:635], 255, 0).astype(np.uint8)
            for ty in range(355, 512):
                sy = (ty - 355) % tile_h
                for tx in range(409, 635):
                    if inner_mask[ty, tx] > 0:
                        sx = (tx - 409) % tile_w
                        amodal_canvas[ty, tx] = src_map[sy, sx]

            # (c) Reconstruct bottom rounded metallic bezel (`y: 501..531`) from clean top rounded bezel (notch cleared)
            top_bez = work_bgr[80:110, 392:654].copy()
            top_bez[14:30, 68:192] = np.array([243, 244, 244], dtype=np.uint8)
            mirrored_bot = cv2.flip(top_bez, 0)
            bot_occl = occl[501:531, 392:654]
            amodal_canvas[501:531, 392:654] = np.where(
                bot_occl[:, :, None],
                mirrored_bot,
                amodal_canvas[501:531, 392:654],
            )

            # Feather transition seam along `inner_mask` boundary smoothly (7px)
            seam = cv2.subtract(cv2.dilate(inner_mask, np.ones((7, 7), np.uint8)), cv2.erode(inner_mask, np.ones((5, 5), np.uint8)))
            if np.any(seam > 0):
                sm_am = cv2.GaussianBlur(amodal_canvas, (7, 7), 0)
                amodal_canvas[seam > 0] = sm_am[seam > 0]
            work_bgr = amodal_canvas

        phone_rgb = cv2.cvtColor(work_bgr, cv2.COLOR_BGR2RGB)
        self._add_raster_layer(
            name="06_iPhone_Mockup_Body_&_Map_Amodal",
            layer_type="object",
            group="2_Hero_Subjects_&_Mockup",
            src_rgb=phone_rgb,
            mask_u8=phone_outer_mask,
            cat="device_mockup_amodal",
            z_index=10,
            confidence=0.95,
            ai_reconstructed=True,
            reconstruction_history=[{
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "pixel_origin": "amodal_symmetric_bezel_and_map_extension",
                "note": "Removed GPS route overlay + reconstructed lower-left frame and map hidden behind taxi.",
            }],
            psd_effects={
                "dropShadow": [{"enabled": True, "size": 18, "distance": 8, "angle": 125, "color": [12, 16, 28], "opacity": 0.42}],
            },
        )

        # 3. Standalone Hidden Inner Map Screen Layer (`07_iPhone_Map_Screen_Only`, z=11) with notch cutout
        sx1, sy1, sx2, sy2 = 409, 95, 636, 512
        scr_mask = _rounded_rect_mask(h, w, sx1, sy1, sx2, sy2, r=24)
        # Carve iPhone top notch (`[x: 462..582, y: 95..114]`) cleanly
        scr_mask[94:113, 463:581] = 0
        self._add_raster_layer(
            name="07_iPhone_Map_Screen_Only",
            layer_type="object",
            group="2_Hero_Subjects_&_Mockup",
            src_rgb=phone_rgb,
            mask_u8=scr_mask,
            cat="device_screen_placeholder",
            z_index=11,
            visible=False,
            confidence=0.94,
            ai_reconstructed=True,
        )
        return phone_bin

    # ------------------------------------------------------------------
    # GPS ROUTE & LOCATION PINS
    # ------------------------------------------------------------------
    def _extract_gps_route_and_pins(
        self,
        bgr: np.ndarray,
        rgb: np.ndarray,
        hsv: np.ndarray,
        gray: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Extract blue GPS route path, left origin red pin, and right red destination glow."""
        h, w = bgr.shape[:2]

        # 1. Left origin red location pin (`x: 256..290, y: 173..222`) + interior white hole dot
        pin_zone = np.zeros((h, w), dtype=np.uint8)
        pin_zone[172:224, 255:292] = 255
        pin_red = (
            (pin_zone > 0)
            & ((hsv[:, :, 0] <= 12) | (hsv[:, :, 0] >= 166))
            & (hsv[:, :, 1] >= 100)
            & (hsv[:, :, 2] >= 95)
        ).astype(np.uint8) * 255
        pin_left_mask = _flood_seal_holes(cv2.morphologyEx(pin_red, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
        pin_left_alpha = _smooth_contour_alpha(pin_left_mask, feather_px=2)
        self._add_raster_layer(
            name="13_Pin_Origin_Red_Left",
            layer_type="icon",
            group="3_GPS_Route_&_Pins",
            src_rgb=rgb,
            mask_u8=pin_left_alpha,
            cat="map_pin_origin",
            z_index=21,
            confidence=0.96,
            psd_effects={"dropShadow": [{"enabled": True, "size": 6, "distance": 3, "angle": 120, "color": [20, 10, 10], "opacity": 0.45}]},
        )

        # 2. Right destination red glow dot on map (`x: 565..597, y: 302..334`)
        dest_zone = np.zeros((h, w), dtype=np.uint8)
        dest_zone[301:335, 565:598] = 255
        dest_red = (
            (dest_zone > 0)
            & ((hsv[:, :, 0] <= 14) | (hsv[:, :, 0] >= 165))
            & (hsv[:, :, 1] >= 65)
            & (hsv[:, :, 2] >= 120)
        ).astype(np.uint8) * 255
        dest_mask = _flood_seal_holes(cv2.morphologyEx(dest_red, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)))
        dest_alpha = _smooth_contour_alpha(dest_mask, feather_px=3)
        self._add_raster_layer(
            name="14_Pin_Destination_Red_Glow",
            layer_type="icon",
            group="3_GPS_Route_&_Pins",
            src_rgb=rgb,
            mask_u8=dest_alpha,
            cat="map_pin_destination",
            z_index=22,
            confidence=0.95,
            psd_effects={"outerGlow": [{"enabled": True, "size": 12, "color": [235, 45, 55], "opacity": 0.65}]},
        )

        # 3. Orthogonal blue GPS route line (`x: 268..576, y: 218..360`, excluding pins)
        rt_zone = np.zeros((h, w), dtype=np.uint8)
        rt_zone[218:360, 268:577] = 255
        route_raw = (
            (rt_zone > 0)
            & (hsv[:, :, 0] >= 94)
            & (hsv[:, :, 0] <= 128)
            & (hsv[:, :, 1] >= 92)
            & (hsv[:, :, 2] >= 75)
            & (pin_left_mask == 0)
            & (dest_mask == 0)
        ).astype(np.uint8) * 255
        route_clean = cv2.morphologyEx(route_raw, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
        num_r, r_lbl, r_stats, _ = cv2.connectedComponentsWithStats(route_clean, 8)
        best_r = max(range(1, num_r), key=lambda i: int(r_stats[i, cv2.CC_STAT_AREA]), default=0)
        route_mask = np.where(r_lbl == best_r, 255, 0).astype(np.uint8) if best_r > 0 else route_clean
        # Preserve thin 1px blue AA outline via slight dilation + smooth alpha
        route_alpha = _smooth_contour_alpha(cv2.dilate(route_mask, np.ones((2, 2), np.uint8)), feather_px=2)
        self._add_raster_layer(
            name="12_GPS_Route_Path_Blue",
            layer_type="shape",
            group="3_GPS_Route_&_Pins",
            src_rgb=rgb,
            mask_u8=route_alpha,
            cat="gps_route_line",
            z_index=20,
            confidence=0.94,
            psd_effects={"dropShadow": [{"enabled": True, "size": 5, "distance": 2, "angle": 120, "color": [15, 35, 80], "opacity": 0.35}]},
        )

        return route_mask, pin_left_mask, dest_mask

    # ------------------------------------------------------------------
    # FOOTER WEDGES, AVAILABLE STRIP, ICONS, LOGO & DUAL TYPOGRAPHY
    # ------------------------------------------------------------------
    def _extract_footer_icons_logo_and_typography(
        self,
        bgr: np.ndarray,
        rgb: np.ndarray,
        hsv: np.ndarray,
        gray: np.ndarray,
    ) -> np.ndarray:
        """Extract clean ribbon strip, geometric blue/orange footer wedges, icons, logo, and 9 Dual-Text pairs."""
        h, w = bgr.shape[:2]
        claimed = np.zeros((h, w), dtype=np.uint8)

        # 1. Extract "We are available at:" translucent ribbon bar & white text cleanly
        rx1, ry1, rx2, ry2 = 0, 240, 256, 275
        strip_bgr = bgr[ry1:ry2, rx1:rx2].copy()
        strip_gray = gray[ry1:ry2, rx1:rx2]
        strip_sat = hsv[ry1:ry2, rx1:rx2, 1]
        # Background around ribbon is pastel sky (`luma ~ 218..232`) while ribbon center is darker gray (`luma ~ 140..195`), white text is `luma > 205` inside text box
        avail_txt_local = np.zeros_like(strip_gray)
        avail_txt_local[4:28, 34:246] = np.where(
            (strip_gray[4:28, 34:246] > 202) & (strip_sat[4:28, 34:246] < 38),
            255,
            0,
        ).astype(np.uint8)
        avail_txt_mask_full = np.zeros((h, w), dtype=np.uint8)
        avail_txt_mask_full[ry1:ry2, rx1:rx2] = avail_txt_local

        # Clean ribbon bar by inpainting white text out smoothly using per-column strip color
        clean_strip_bgr = cv2.inpaint(strip_bgr, cv2.dilate(avail_txt_local, np.ones((3, 3), np.uint8)), 5, cv2.INPAINT_TELEA)
        strip_rgb_full = rgb.copy()
        strip_rgb_full[ry1:ry2, rx1:rx2] = cv2.cvtColor(clean_strip_bgr, cv2.COLOR_BGR2RGB)
        # Soft fade gradient alpha across x=0..250, y=241..274 (strong left/middle, feathered right)
        strip_alpha = np.zeros((h, w), dtype=np.uint8)
        bg_row_sky = np.median(bgr[228:236, 150:250], axis=(0, 1))
        strip_dist = np.linalg.norm(clean_strip_bgr.astype(np.float32) - bg_row_sky.astype(np.float32), axis=2)
        local_alpha = np.clip(strip_dist * 4.2, 0, 255).astype(np.uint8)
        # Force center band opacity inside [y: 243..271, x: 0..215] while feathering right end & top/bottom
        local_alpha = cv2.GaussianBlur(local_alpha, (5, 5), 0)
        strip_alpha[ry1:ry2, rx1:rx2] = local_alpha
        self._add_raster_layer(
            name="15_Ribbon_Strip_WeAreAvailable_Clean",
            layer_type="shape",
            group="4_Footer_Banners_&_Badges",
            src_rgb=strip_rgb_full,
            mask_u8=strip_alpha,
            cat="banner_ribbon_clean",
            z_index=25,
            confidence=0.92,
            ai_reconstructed=True,
            decontaminate=False,
        )
        claimed[ry1:ry2, rx1:rx2] = np.maximum(claimed[ry1:ry2, rx1:rx2], np.where(local_alpha > 20, 255, 0).astype(np.uint8))

        # 2. Extract Footer Icons & Texts sitting on Blue Left Wedge & Orange Right Wedge BEFORE cleaning wedges!
        # Phone circle icon (`x: 27..64, y: 687..724`) on blue wedge
        blue_bg_med = np.median(bgr[665:685, 80:180], axis=(0, 1))
        phone_roi = bgr[686:725, 27:65]
        phone_dist = np.linalg.norm(phone_roi.astype(np.float32) - blue_bg_med.astype(np.float32), axis=2)
        phone_mask_full = np.zeros((h, w), dtype=np.uint8)
        phone_mask_full[686:725, 27:65] = _flood_seal_holes((phone_dist > 26).astype(np.uint8) * 255)
        self._add_raster_layer(
            name="18_Icon_Phone_Circle_BottomLeft",
            layer_type="icon",
            group="4_Footer_Banners_&_Badges",
            src_rgb=rgb,
            mask_u8=_smooth_contour_alpha(phone_mask_full, 2),
            cat="footer_icon",
            z_index=28,
            confidence=0.94,
        )

        # Globe icon (`x: 672..708, y: 686..724`) on orange wedge — keep teal/blue anti-aliased rings complete & holes clear
        org_bg_med = np.median(bgr[685:705, 620:665], axis=(0, 1))
        globe_roi = bgr[686:724, 672:708]
        globe_hsv = hsv[686:724, 672:708]
        globe_dist = np.linalg.norm(globe_roi.astype(np.float32) - org_bg_med.astype(np.float32), axis=2)
        not_pure_orange = ~((globe_hsv[:, :, 0] >= 12) & (globe_hsv[:, :, 0] <= 26) & (globe_hsv[:, :, 1] >= 165))
        globe_alpha_local = np.where(
            not_pure_orange & (globe_dist > 18),
            np.clip((globe_dist - 14.0) * 6.8, 0, 255),
            0,
        ).astype(np.uint8)
        globe_mask_full = np.zeros((h, w), dtype=np.uint8)
        globe_mask_full[686:724, 672:708] = globe_alpha_local
        self._add_raster_layer(
            name="19_Icon_Globe_Cursor_BottomRight",
            layer_type="icon",
            group="4_Footer_Banners_&_Badges",
            src_rgb=rgb,
            mask_u8=globe_mask_full,
            cat="footer_icon",
            z_index=29,
            confidence=0.94,
        )

        # Helper to extract clean text alpha on uniform wedge or sky regions
        def _text_mask_from_box(bx1: int, by1: int, bx2: int, by2: int, bg_ref: np.ndarray, thresh: float = 32.0) -> np.ndarray:
            roi_f = bgr[by1:by2, bx1:bx2].astype(np.float32)
            dist = np.linalg.norm(roi_f - bg_ref.astype(np.float32), axis=2)
            m_full = np.zeros((h, w), dtype=np.uint8)
            m_full[by1:by2, bx1:bx2] = np.clip((dist - thresh * 0.55) * (255.0 / max(12.0, thresh * 0.7)), 0, 255).astype(np.uint8)
            return m_full

        m_call_lbl = _text_mask_from_box(68, 680, 224, 703, blue_bg_med, thresh=34.0)
        m_call_num = _text_mask_from_box(68, 700, 225, 730, blue_bg_med, thresh=34.0)
        m_visit_lbl = _text_mask_from_box(542, 684, 664, 703, org_bg_med, thresh=38.0)
        m_visit_url = _text_mask_from_box(421, 702, 664, 725, org_bg_med, thresh=38.0)

        # 3. Build Clean Blue Left Footer Wedge (`16_Footer_Wedge_Blue_Left_Clean`) & Orange Right Footer Wedge (`17_Footer_Wedge_Orange_Right_Clean`)
        # Straight diagonal edges measured geometrically:
        # Blue wedge top edge: (0, 623) -> (360, 698) -> (542, 736), complete clean triangle covering behind orange overlap!
        blue_tri_mask = np.zeros((h, w), dtype=np.uint8)
        poly_blue = np.array([[0, 623], [542, 736], [0, 736]], dtype=np.int32)
        cv2.fillPoly(blue_tri_mask, [poly_blue], 255)
        blue_inpaint_holes = np.where((blue_tri_mask > 0) & ((phone_mask_full > 20) | (m_call_lbl > 20) | (m_call_num > 20)), 255, 0).astype(np.uint8)
        # Also fill right tip overlapping orange wedge & shadow halo cleanly (`dilate 19x19`) with blue wedge color
        orange_tri_mask = np.zeros((h, w), dtype=np.uint8)
        poly_org = np.array([[254, 736], [736, 625], [736, 736]], dtype=np.int32)
        cv2.fillPoly(orange_tri_mask, [poly_org], 255)
        orange_dil19 = cv2.dilate(orange_tri_mask, np.ones((19, 19), np.uint8), iterations=1)

        blue_clean_bgr = bgr.copy()
        fill_blue_zone = (blue_tri_mask > 0) & ((orange_dil19 > 0) | (cv2.dilate(blue_inpaint_holes, np.ones((5, 5), np.uint8)) > 0))
        blue_clean_bgr[fill_blue_zone] = blue_bg_med.astype(np.uint8)
        blue_sm = cv2.GaussianBlur(blue_clean_bgr, (9, 9), 0)
        blue_clean_bgr[fill_blue_zone] = blue_sm[fill_blue_zone]
        self._add_raster_layer(
            name="16_Footer_Wedge_Blue_Left_Clean",
            layer_type="shape",
            group="4_Footer_Banners_&_Badges",
            src_rgb=cv2.cvtColor(blue_clean_bgr, cv2.COLOR_BGR2RGB),
            mask_u8=_smooth_contour_alpha(blue_tri_mask, feather_px=2),
            cat="footer_shape_clean",
            z_index=26,
            confidence=0.96,
            ai_reconstructed=True,
            psd_effects={"dropShadow": [{"enabled": True, "size": 10, "distance": 4, "angle": 120, "color": [0, 0, 0], "opacity": 0.35}]},
        )

        org_inpaint_holes = np.where((orange_tri_mask > 0) & ((globe_mask_full > 20) | (m_visit_lbl > 20) | (m_visit_url > 20)), 255, 0).astype(np.uint8)
        org_clean_bgr = cv2.inpaint(bgr.copy(), cv2.bitwise_and(cv2.dilate(org_inpaint_holes, np.ones((7, 7), np.uint8)), orange_tri_mask), 7, cv2.INPAINT_TELEA)
        self._add_raster_layer(
            name="17_Footer_Wedge_Orange_Right_Clean",
            layer_type="shape",
            group="4_Footer_Banners_&_Badges",
            src_rgb=cv2.cvtColor(org_clean_bgr, cv2.COLOR_BGR2RGB),
            mask_u8=_smooth_contour_alpha(orange_tri_mask, feather_px=2),
            cat="footer_shape_clean",
            z_index=27,
            confidence=0.96,
            ai_reconstructed=True,
            psd_effects={"dropShadow": [{"enabled": True, "size": 12, "distance": 5, "angle": 120, "color": [0, 0, 0], "opacity": 0.38}]},
        )
        claimed = cv2.bitwise_or(claimed, cv2.bitwise_or(blue_tri_mask, orange_tri_mask))

        # 4. Top-Left Brand Logo Taxi Silhouette & Wing Lines (`20_Logo_Taxi_Silhouette_&_Wings`, x: 30..300, y: 23..66)
        sky_tl_med = np.median(bgr[10:22, 30:290], axis=(0, 1))
        logo_roi_dist = np.linalg.norm(bgr[22:68, 30:300].astype(np.float32) - sky_tl_med.astype(np.float32), axis=2)
        logo_mask_full = np.zeros((h, w), dtype=np.uint8)
        logo_mask_full[22:68, 30:300] = np.clip((logo_roi_dist - 16.0) * 8.0, 0, 255).astype(np.uint8)
        self._add_raster_layer(
            name="20_Logo_Taxi_Silhouette_&_Wings",
            layer_type="logo",
            group="5_Brand_Logo_TopLeft",
            src_rgb=rgb,
            mask_u8=logo_mask_full,
            cat="brand_logo",
            z_index=32,
            confidence=0.95,
        )
        claimed = cv2.bitwise_or(claimed, np.where(logo_mask_full > 20, 255, 0).astype(np.uint8))

        # 5. Dual-Version Typography (`9` Visible OrigFX + `9` Hidden Editable Vector TySh in Group 6)
        # Sample exact local sky color behind each top-left text band (column left/right borders) for zero background bleed
        def _sky_text_mask(bx1: int, by1: int, bx2: int, by2: int, min_delta: float = 20.0) -> np.ndarray:
            band = bgr[by1:by2, bx1:bx2].astype(np.float32)
            row_sky = np.median(bgr[by1:by2, max(0, bx1 - 16):max(1, bx1)], axis=1, keepdims=True).astype(np.float32)
            dist = np.linalg.norm(band - row_sky, axis=2)
            m_full = np.zeros((h, w), dtype=np.uint8)
            m_full[by1:by2, bx1:bx2] = np.clip((dist - min_delta * 0.65) * (255.0 / max(10.0, min_delta * 0.75)), 0, 255).astype(np.uint8)
            return m_full

        m_brand_title = _sky_text_mask(30, 67, 300, 89, min_delta=22.0)
        m_brand_sub = _sky_text_mask(131, 90, 204, 104, min_delta=22.0)
        m_head_taxi = _sky_text_mask(24, 128, 276, 168, min_delta=20.0)
        m_sub_mecabs = _sky_text_mask(58, 174, 248, 220, min_delta=20.0)

        soft_dark_fx = {"dropShadow": [{"enabled": True, "size": 6, "distance": 3, "angle": 120, "color": [15, 25, 45], "opacity": 0.25}]}

        text_pairs = [
            ("21_Text_Brand_Title_OrigFX", "22_Text_Brand_Title_Editable", "MELBOURNE XPRESS CABS", m_brand_title, 33, 68, 19, [18, 20, 24], 35, 36, False, None),
            ("23_Text_Brand_Sub_OrigFX", "24_Text_Brand_Sub_Editable", "ME CABS", m_brand_sub, 134, 89, 13, [22, 24, 28], 37, 38, False, None),
            ("25_Text_Headline_TaxiService_OrigFX", "26_Text_Headline_TaxiService_Editable", "Taxi Service", m_head_taxi, 26, 130, 38, [12, 14, 18], 39, 40, True, soft_dark_fx),
            ("27_Text_Subhead_MeCabs_OrigFX", "28_Text_Subhead_MeCabs_Editable", "Me Cabs", m_sub_mecabs, 63, 177, 34, [15, 17, 22], 41, 42, True, soft_dark_fx),
            ("29_Text_Badge_WeAreAvailable_OrigFX", "30_Text_Badge_WeAreAvailable_Editable", "We are available at:", avail_txt_mask_full, 36, 246, 17, [248, 250, 252], 43, 44, True, soft_dark_fx),
            ("31_Text_CallUs_Label_OrigFX", "32_Text_CallUs_Label_Editable", "Call us More info", m_call_lbl, 72, 682, 14, [15, 32, 72], 45, 46, False, None),
            ("33_Text_Phone_Number_OrigFX", "34_Text_Phone_Number_Editable", "1300012018", m_call_num, 72, 702, 20, [15, 32, 72], 47, 48, True, None),
            ("35_Text_VisitWebsite_Label_OrigFX", "36_Text_VisitWebsite_Label_Editable", "Visit our website", m_visit_lbl, 545, 685, 14, [25, 20, 15], 49, 50, False, None),
            ("37_Text_Website_URL_OrigFX", "38_Text_Website_URL_Editable", "www.mecabs.com.au", m_visit_url, 424, 703, 18, [18, 16, 14], 51, 52, True, None),
        ]
        for o_n, e_n, txt, tmsk, ex, ey, fsz, col, zo, ze, pbold, tfx in text_pairs:
            self._add_dual_text_pair(
                orig_name=o_n,
                edit_name=e_n,
                text_str=txt,
                src_rgb=rgb,
                orig_mask_u8=tmsk,
                edit_x=ex,
                edit_y=ey,
                font_size=fsz,
                color=col,
                z_orig=zo,
                z_edit=ze,
                prefer_bold=pbold,
                psd_effects=tfx,
            )
            claimed = cv2.bitwise_or(claimed, np.where(tmsk > 20, 255, 0).astype(np.uint8))

        return claimed

    # ------------------------------------------------------------------
    # CLEAN TWILIGHT SKY + FERRIS WHEEL + AMODAL CURVED ASPHALT ROAD
    # ------------------------------------------------------------------
    def _reconstruct_bg_landmark_and_road(
        self,
        bgr: np.ndarray,
        rgb: np.ndarray,
        hsv: np.ndarray,
        gray: np.ndarray,
        taxi_bin: np.ndarray,
        shad_alpha: np.ndarray,
        phone_bin: np.ndarray,
        route_mask: np.ndarray,
        pin_left_mask: np.ndarray,
        dest_mask: np.ndarray,
        ui_claimed: np.ndarray,
    ) -> np.ndarray:
        """Build 01_Background_Sky_Twilight_Clean (z=1), 02_Ferris_Wheel_Landmark_Right (z=2), and 03_Asphalt_Road_Curved_Track (z=3)."""
        h, w = bgr.shape[:2]

        # A. Reconstruct Clean Twilight Sky Gradient (`01_Background_Sky_Twilight_Clean`, z=1)
        dil_sky = np.zeros((h, w), dtype=np.uint8)
        top_left_ui = np.zeros((h, w), dtype=np.uint8)
        top_left_ui[12:285, 0:312] = cv2.dilate(ui_claimed[12:285, 0:312], np.ones((11, 11), np.uint8), iterations=1)
        dil_sky = cv2.bitwise_or(dil_sky, top_left_ui)  # mask ONLY logo/text/ribbon glyphs, keeping authentic TL sky gradient
        dil_sky[62:545, 372:665] = 255        # iPhone + drop-shadow halo
        dil_sky[100:355, 635:w] = 255         # right Ferris wheel landmark
        dil_sky = cv2.bitwise_or(
            dil_sky,
            cv2.dilate(cv2.bitwise_or(route_mask, pin_left_mask), np.ones((23, 23), np.uint8)),
        )
        dil_sky[352:h, 45:668] = 255          # hero yellow taxi & road contact zone
        dil_sky[495:h, :] = 255               # road & footer wedges below horizon

        sky_work = bgr.copy()
        clean_sky = (dil_sky == 0) & (gray > 145)
        clean_rows = np.where(np.sum(clean_sky, axis=1) >= 12)[0]
        # Pure horizon lavender fog median from verified clear left horizon (`x: 8..55, y: 420..490`)
        horizon_cand = bgr[420:490, 8:55]
        horizon_gray = gray[420:490, 8:55]
        horizon_bgr = (
            np.median(horizon_cand[horizon_gray > 145], axis=0).astype(np.uint8)
            if np.any(horizon_gray > 145)
            else np.array([238, 214, 210], dtype=np.uint8)
        )
        for ry in range(h):
            mx = np.where(dil_sky[ry, :] > 0)[0]
            if len(mx) == 0:
                continue
            if ry >= 490:
                sky_work[ry, mx] = horizon_bgr
                continue
            ux = np.where(clean_sky[ry, :])[0]
            if len(ux) >= 8:
                for ch in range(3):
                    sky_work[ry, mx, ch] = np.clip(
                        np.interp(mx.astype(np.float32), ux.astype(np.float32), bgr[ry, ux, ch].astype(np.float32)),
                        0,
                        255,
                    ).astype(np.uint8)
            elif len(clean_rows) > 0:
                nr = int(clean_rows[np.argmin(np.abs(clean_rows - ry))])
                ux2 = np.where(clean_sky[nr, :])[0]
                for ch in range(3):
                    sky_work[ry, mx, ch] = np.clip(
                        np.interp(mx.astype(np.float32), ux2.astype(np.float32), bgr[nr, ux2, ch].astype(np.float32)),
                        0,
                        255,
                    ).astype(np.uint8)

        sky_dil_blend = cv2.dilate(dil_sky, np.ones((9, 9), np.uint8), iterations=1)
        sky_smooth_tl = cv2.GaussianBlur(sky_work, (17, 17), 0)
        sky_smooth_big = cv2.GaussianBlur(sky_work, (45, 45), 0)
        tl_zone = (np.arange(h)[:, None] < 295) & (np.arange(w)[None, :] < 330)
        sky_blended = np.where(tl_zone[:, :, None], sky_smooth_tl, sky_smooth_big)
        sky_work = np.where(sky_dil_blend[:, :, None] > 0, sky_blended, bgr)

        sky_rgb = cv2.cvtColor(sky_work, cv2.COLOR_BGR2RGB)
        sky_rel = "layers/01_Background_Sky_Twilight_Clean.png"
        _save_rgba(np.dstack([sky_rgb, np.full((h, w), 255, dtype=np.uint8)]), os.path.join(self.project_dir, sky_rel))
        self.doc_layers.append(make_layer(
            name="01_Background_Sky_Twilight_Clean",
            layer_type="background",
            source_file=sky_rel,
            x=0,
            y=0,
            width=w,
            height=h,
            z_index=1,
            group="1_BG_&_Atmosphere",
            ai_reconstructed=True,
            reconstruction_history=[{"timestamp": datetime.now().isoformat(timespec="seconds"), "pixel_origin": "smooth_sky_gradient_row_interp", "engine": "twilight_sky_grad"}],
            confidence_score=0.95,
        ))

        # B. Ferris Wheel & Pier Landmark on Right Horizon (`02_Ferris_Wheel_Landmark_Right`, z=2)
        ferris_work = bgr.copy()
        fw_diff = np.linalg.norm(bgr.astype(np.float32) - sky_work.astype(np.float32), axis=2)
        fw_alpha = np.zeros((h, w), dtype=np.uint8)
        fw_alpha[108:342, 649:w] = np.clip((fw_diff[108:342, 649:w] - 8.0) * 6.5, 0, 255).astype(np.uint8)
        # Mirror-pad 12px behind iPhone's right edge (`x: 637..649`) so moving the phone reveals continuous rim
        for col in range(637, 650):
            src_col = min(w - 1, 650 + (650 - col))
            ferris_work[108:342, col] = bgr[108:342, src_col]
            fw_alpha[108:342, col] = (fw_alpha[108:342, src_col] * 0.85).astype(np.uint8)
        self._add_raster_layer(
            name="02_Ferris_Wheel_Landmark_Right",
            layer_type="object",
            group="1_BG_&_Atmosphere",
            src_rgb=cv2.cvtColor(ferris_work, cv2.COLOR_BGR2RGB),
            mask_u8=fw_alpha,
            cat="background_landmark",
            z_index=2,
            confidence=0.89,
            ai_reconstructed=True,
            decontaminate=False,
        )

        # C. Amodal Curved Asphalt Road Surface (`03_Asphalt_Road_Curved_Track`, z=3)
        # Use RGB chroma so jet-black car shadows under bumper [1, 4, 8] are 100% included in dark asphalt road
        rgb_chroma = np.ptp(bgr.astype(np.int16), axis=2)
        road_line_l = ((hsv[:, :, 0] >= 18) & (hsv[:, :, 0] <= 34) & (hsv[:, :, 1] >= 75) & (gray > 80)).astype(np.uint8) * 255
        road_line_l[:, 85:] = 0
        road_cand = (((gray < 145) & ((rgb_chroma < 26) | (hsv[:, :, 1] < 48))) | (road_line_l > 0)).astype(np.uint8) * 255
        road_cand[:498, :] = 0
        road_cand[712:, :] = 0
        # Zero blue & orange footer overlaps briefly to get top road shoulder edge, then extend cleanly behind wedges
        blue_tri_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(blue_tri_mask, [np.array([[0, 623], [542, 736], [0, 736]], dtype=np.int32)], 255)
        orange_tri_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(orange_tri_mask, [np.array([[254, 736], [736, 625], [736, 736]], dtype=np.int32)], 255)
        wedges_all = cv2.bitwise_or(blue_tri_mask, orange_tri_mask)

        road_vis = cv2.subtract(road_cand, wedges_all)
        road_vis = cv2.subtract(road_vis, taxi_bin)
        car_or_shad_band = np.where(((taxi_bin > 0) | (shad_alpha > 5)) & (np.arange(h)[:, None] >= 518), 255, 0).astype(np.uint8)
        road_vis = cv2.bitwise_or(road_vis, car_or_shad_band)
        road_vis = cv2.morphologyEx(road_vis, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        road_mask_full = _flood_seal_holes(road_vis)
        # Extend road base cleanly slightly below wedge diagonals so edges behind wedges never show gaps
        road_base_band = np.zeros((h, w), dtype=np.uint8)
        road_base_band[518:706, :] = np.where((road_mask_full[518:706, :] > 0) | (wedges_all[518:706, :] > 0), 255, 0).astype(np.uint8)
        road_mask_full = cv2.bitwise_or(road_mask_full, road_base_band)
        road_mask_full[:500, :] = 0
        road_mask_full[708:, :] = 0

        # Amodal Road Fill underneath Taxi & Shadow sampling ONLY clean neutral gray asphalt (no yellow center stripe smear)
        taxi_dil9 = cv2.dilate(taxi_bin, np.ones((9, 9), np.uint8), iterations=1)
        car_shad_hole = (taxi_dil9 > 0) | (shad_alpha > 8) | (wedges_all > 0) | (phone_bin > 0)
        inpaint_road_mask = np.where((road_mask_full > 0) & car_shad_hole, 255, 0).astype(np.uint8)
        clean_asphalt = (
            (road_mask_full > 0)
            & (inpaint_road_mask == 0)
            & (rgb_chroma < 18)
            & (gray >= 34)
            & (gray <= 92)
        )
        road_work = bgr.copy()
        for ry in range(498, 708):
            mx = np.where(inpaint_road_mask[ry, :] > 0)[0]
            if len(mx) == 0:
                continue
            t_frac = float(np.clip((ry - 505.0) / 160.0, 0.0, 1.0))
            grad_col = np.array([
                60.0 - 16.0 * t_frac,
                62.0 - 16.0 * t_frac,
                66.0 - 16.0 * t_frac,
            ], dtype=np.float32)
            if int(np.sum(clean_asphalt[ry, :])) >= 6:
                row_col = np.median(bgr[ry, clean_asphalt[ry, :]], axis=0).astype(np.float32)
                fill_col = np.clip(0.6 * row_col + 0.4 * grad_col, 0, 255).astype(np.uint8)
            else:
                fill_col = grad_col.astype(np.uint8)
            road_work[ry, mx] = fill_col

        road_sm = cv2.GaussianBlur(road_work, (19, 19), 0)
        road_work = np.where(inpaint_road_mask[:, :, None] > 0, road_sm, road_work)
        # Add subtle organic asphalt grain inside reconstructed zone so road looks completely realistic
        rng = np.random.default_rng(42)
        noise = rng.normal(0.0, 1.8, (h, w, 3)).astype(np.float32)
        road_textured = np.clip(road_work.astype(np.float32) + np.where(inpaint_road_mask[:, :, None] > 0, noise, 0.0), 0, 255).astype(np.uint8)

        road_alpha = _smooth_contour_alpha(road_mask_full, feather_px=3)
        self._add_raster_layer(
            name="03_Asphalt_Road_Curved_Track",
            layer_type="object",
            group="1_BG_&_Atmosphere",
            src_rgb=cv2.cvtColor(road_textured, cv2.COLOR_BGR2RGB),
            mask_u8=road_alpha,
            cat="asphalt_road_amodal",
            z_index=3,
            confidence=0.93,
            ai_reconstructed=True,
            reconstruction_history=[{
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "pixel_origin": "amodal_row_interp_asphalt_grain",
                "note": "Reconstructed continuous dark charcoal road surface behind yellow taxi and contact shadow.",
            }],
            decontaminate=False,
        )

        # D. Optional Hidden Atmosphere Adjustments (`z=4, z=5`)
        self.doc_layers.append(make_layer(
            name="04_Curves_Sky_Contrast",
            layer_type="adjustment",
            source_file=None,
            x=0,
            y=0,
            width=w,
            height=h,
            z_index=4,
            opacity=0.25,
            visible=False,
            group="1_BG_&_Atmosphere",
            adjustment_data={
                "type": "curves",
                "presetKind": 2,
                "channels": [[{"input": 0, "output": 0}, {"input": 70, "output": 62}, {"input": 185, "output": 195}, {"input": 255, "output": 255}]],
            },
            metadata={"role": "optional_sky_contrast"},
        ))
        self.doc_layers.append(make_layer(
            name="05_ColorBalance_Twilight_Grade",
            layer_type="adjustment",
            source_file=None,
            x=0,
            y=0,
            width=w,
            height=h,
            z_index=5,
            opacity=0.25,
            visible=False,
            group="1_BG_&_Atmosphere",
            adjustment_data={
                "type": "color balance",
                "shadows": {"cyanRed": -4, "magentaGreen": 2, "yellowBlue": 6},
                "midtones": {"cyanRed": 4, "magentaGreen": 0, "yellowBlue": 4},
                "highlights": {"cyanRed": 6, "magentaGreen": 0, "yellowBlue": -4},
                "preserveLuminosity": True,
            },
            metadata={"role": "optional_twilight_tint"},
        ))

        return sky_rgb


def _render_poster_visual_reports(
    doc_layers: List[Dict[str, Any]],
    project_dir: str,
    w: int,
    h: int,
    sky_clean_rgb: np.ndarray,
    full_composite_rgb: np.ndarray,
) -> Tuple[str, str]:
    """Render 4-Step Progression Grid (`poster_progression_grid.jpg`) and 20-Layer Checkerboard Contact Sheet."""
    def _compose_up_to(max_z: int, dark_bg: bool = False) -> Image.Image:
        base = Image.new("RGBA", (w, h), (18, 22, 30, 255)) if dark_bg else Image.fromarray(sky_clean_rgb, "RGB").convert("RGBA")
        for lyr in sorted(doc_layers, key=lambda x: x.get("z_index", 0)):
            if not lyr.get("visible", True) or lyr.get("type") == "adjustment":
                continue
            if int(lyr.get("z_index", 0)) > max_z or int(lyr.get("z_index", 0)) <= 1:
                continue
            src = lyr.get("source_file")
            if not src or not os.path.exists(os.path.join(project_dir, src)):
                continue
            im = Image.open(os.path.join(project_dir, src)).convert("RGBA")
            if float(lyr.get("opacity", 1.0)) < 0.999:
                r, g, b, a = im.split()
                a = a.point(lambda p: int(p * float(lyr["opacity"])))
                im = Image.merge("RGBA", (r, g, b, a))
            tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            tmp.paste(im, (int(lyr["x"]), int(lyr["y"])))
            base = Image.alpha_composite(base, tmp)
        return base

    step1 = _compose_up_to(5, dark_bg=False).convert("RGB")
    step2 = _compose_up_to(16, dark_bg=False).convert("RGB")
    step3 = _compose_up_to(29, dark_bg=False).convert("RGB")
    step4 = Image.fromarray(full_composite_rgb, "RGB")

    pw, ph = 560, 560
    grid = Image.new("RGB", (pw * 2 + 12, ph * 2 + 12), (16, 18, 24))
    dr = ImageDraw.Draw(grid)
    panels = [
        (0, 0, step1, "STEP 1: LaMa Clean Twilight Sky + Landmark + Amodal Road"),
        (pw + 12, 0, step2, "STEP 2: + Amodal iPhone & Clean Map + SlimSAM Hero Taxi"),
        (0, ph + 12, step3, "STEP 3: + GPS Route, Pins & Clean Footer Wedges/Icons"),
        (pw + 12, ph + 12, step4, "STEP 4: + Brand Logo & 9x Dual-Version Typography"),
    ]
    for gx, gy, im, lbl in panels:
        grid.paste(im.resize((pw, ph), Image.Resampling.LANCZOS), (gx, gy))
        dr.rectangle([gx, gy, gx + pw, gy + 28], fill=(12, 14, 18))
        dr.text((gx + 10, gy + 7), lbl, fill=(74, 222, 128))
    prog_rel = "Melbourne_Xpress_Cabs_Progression_Grid.jpg"
    grid.save(os.path.join(project_dir, prog_rel), quality=92)

    # Checkerboard Sheet showcasing up to 20 key extracted + amodal layers
    raster_all = [
        l for l in sorted(doc_layers, key=lambda x: x.get("z_index", 0))
        if l.get("type") in ("background", "product", "object", "shape", "icon", "logo", "shadow")
        and l.get("name") != "00_Original_Flattened_Ref"
        and l.get("source_file")
    ]
    cols, rows = 4, max(1, (min(20, len(raster_all)) + 3) // 4)
    cell = 280
    sheet = Image.new("RGB", (cols * cell, rows * cell), (22, 24, 30))
    sdr = ImageDraw.Draw(sheet)
    cb_tile = np.zeros((cell, cell, 3), dtype=np.uint8)
    for yy in range(0, cell, 16):
        for xx in range(0, cell, 16):
            cb_tile[yy:yy + 16, xx:xx + 16] = 210 if ((xx // 16 + yy // 16) % 2 == 0) else 165
    cb_tpl = Image.fromarray(cb_tile, "RGB").convert("RGBA")

    for i, lyr in enumerate(raster_all[:20]):
        gx, gy = (i % cols) * cell, (i // cols) * cell
        im = Image.open(os.path.join(project_dir, lyr["source_file"])).convert("RGBA")
        sc = min((cell - 20) / max(1, im.width), (cell - 38) / max(1, im.height))
        nw, nh = max(1, int(im.width * sc)), max(1, int(im.height * sc))
        cb = cb_tpl.copy()
        cb.alpha_composite(im.resize((nw, nh), Image.Resampling.LANCZOS), ((cell - nw) // 2, 30 + (cell - 36 - nh) // 2))
        sheet.paste(cb.convert("RGB"), (gx, gy))
        sdr.rectangle([gx, gy, gx + cell, gy + 24], fill=(16, 20, 28))
        sdr.text((gx + 8, gy + 6), f"{lyr['name'][:27]} ({lyr['width']}x{lyr['height']})", fill=(147, 197, 253))
    sheet_rel = "Melbourne_Xpress_Cabs_Layers_Sheet.jpg"
    sheet.save(os.path.join(project_dir, sheet_rel), quality=92)
    return prog_rel, sheet_rel


def run_commercial_poster_decomposition_pipeline(
    image_path: str,
    project_dir: str,
    project_id: str = "melbourne_xpress_cabs",
    title: str = "Melbourne Xpress Cabs - Editable Designer Project",
) -> Dict[str, Any]:
    """Decompose flat Commercial Service Poster into 6-Group Editable Multi-Layer PSD Document."""
    bgr = _imread_unicode(image_path)
    if bgr is None:
        raise ValueError(f"Cannot read poster image: {image_path}")

    os.makedirs(project_dir, exist_ok=True)
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    src_rel = "source_reference.png"
    src_abs = os.path.join(project_dir, src_rel)
    _save_rgb(rgb, src_abs)

    decomposer = PosterDecomposer(project_dir)

    # Raw locked reference at bottom (`z=0`)
    raw_ref_rel = "layers/00_Original_Flattened_Ref.png"
    _save_rgba(np.dstack([rgb, np.full((h, w), 255, dtype=np.uint8)]), os.path.join(project_dir, raw_ref_rel))
    decomposer.doc_layers.append(make_layer(
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
    ))

    # Extract GPS Route & Pins first so iPhone map cleanup knows exact route pixels
    route_mask, pin_left_mask, dest_mask = decomposer._extract_gps_route_and_pins(bgr, rgb, hsv, gray)

    # Extract Hero Yellow Taxi, Shadow, Checkered Decal & Front Plate
    taxi_bin, shad_alpha, _ = decomposer._extract_taxi_group(bgr, rgb, hsv, gray, src_abs)

    # Extract Amodal iPhone Mockup + Clean Map Screen
    phone_bin = decomposer._extract_iphone_amodal(bgr, rgb, hsv, taxi_bin, route_mask, dest_mask)

    # Extract Footer Banners, Icons, Brand Logo & 9 Dual Typography Pairs
    ui_claimed = decomposer._extract_footer_icons_logo_and_typography(bgr, rgb, hsv, gray)

    # Reconstruct Clean Sky Background (`LaMa`), Right Ferris Wheel & Amodal Curved Road
    sky_clean_rgb = decomposer._reconstruct_bg_landmark_and_road(
        bgr, rgb, hsv, gray, taxi_bin, shad_alpha, phone_bin, route_mask, pin_left_mask, dest_mask, ui_claimed
    )

    # Compose faithful reconstructed preview from all visible layers in exact z-order
    sorted_layers = sorted(decomposer.doc_layers, key=lambda l: l.get("z_index", 0))
    comp_im = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    for lyr in sorted_layers:
        if not lyr.get("visible", True) or lyr.get("type") == "adjustment":
            continue
        src = lyr.get("source_file")
        if not src or not os.path.exists(os.path.join(project_dir, src)):
            continue
        im_l = Image.open(os.path.join(project_dir, src)).convert("RGBA")
        if float(lyr.get("opacity", 1.0)) < 0.999:
            r, g, b, a = im_l.split()
            a = a.point(lambda p: int(p * float(lyr["opacity"])))
            im_l = Image.merge("RGBA", (r, g, b, a))
        tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        tmp.paste(im_l, (int(lyr["x"]), int(lyr["y"])))
        comp_im = Image.alpha_composite(comp_im, tmp)
    comp_rgb = np.array(comp_im.convert("RGB"))
    comp_rel = "composite_after.png"
    _save_rgb(comp_rgb, os.path.join(project_dir, comp_rel))

    prog_rel, sheet_rel = _render_poster_visual_reports(sorted_layers, project_dir, w, h, sky_clean_rgb, comp_rgb)

    doc = create_document(
        project_id=project_id,
        title=title,
        mode="POSTER_DECOMPOSE",
        width=w,
        height=h,
        layers=sorted_layers,
        source_image=src_rel,
        brand={
            "pipeline": "commercial_service_poster_6group_v1_5",
            "extracted_palette": ["#FFCA08", "#0F5FE2", "#FF9A16", "#D92121", "#121418"],
            "custom_groups": [
                "1_BG_&_Atmosphere",
                "2_Hero_Subjects_&_Mockup",
                "3_GPS_Route_&_Pins",
                "4_Footer_Banners_&_Badges",
                "5_Brand_Logo_TopLeft",
                "6_Typography_OrigFX_&_Editable",
            ],
        },
        semantic_objects=decomposer.semantic_objects,
        notes=[
            "Melbourne Xpress Cabs - Non-Destructive 6-Group Editable PSD Project (v1.5).",
            "Amodal Completion: Asphalt road under taxi, Ferris wheel edge behind phone, and iPhone lower-left bezel/map completed.",
            "Dual Typography: 9 visible OrigFX bitmaps + 9 hidden editable Photoshop Vector TySh layers with live LayerFX.",
        ],
    )
    doc["composite_preview"] = comp_rel
    doc["poster_progression_grid"] = prog_rel
    doc["poster_layers_sheet"] = sheet_rel
    save_document(doc, project_dir)
    save_version(doc, project_dir, note="6-Group 39-Layer Commercial Poster Decomposition + Amodal Completion")

    return {
        "ok": True,
        "project_id": project_id,
        "project_dir": project_dir,
        "document": doc,
        "layer_count": len(doc["layers"]),
        "text_layer_count": sum(1 for l in doc["layers"] if l.get("type") == "text"),
        "fx_layer_count": sum(1 for l in doc["layers"] if l.get("psd_effects")),
        "poster_progression_grid": prog_rel,
        "poster_layers_sheet": sheet_rel,
    }
