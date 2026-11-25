"""Module 1: Semantic Design Analyzer v1.3 — DETR Auto-Detection, Object-by-Object SlimSAM Split, LaMa Clean Background & Smart Fonts."""
import os
from typing import Any, Dict, List, Tuple
import cv2
import numpy as np
from PIL import Image

from core.design_document import create_document, make_layer, make_semantic_object, save_document
from core.image_analyzer import _estimate_local_background, inspect_input_quality, upscale_preserve_aspect_local
from core.project_manager import save_version
from core.reconstruction_engine import reconstruct_region
from core.segmentation_engine import (
    analyze_mask_quality,
    apply_mask_to_source,
    detect_objects,
    refine_mask,
    run_rmbg_salient,
    segment_interactive,
)
from core.typography_engine import extract_typography_objects, render_styled_text


def _imread_unicode(path: str):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)


def _boxes_iou_or_touch(a: List[int], b: List[int], pad: int = 8) -> bool:
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    return not (ax1 + aw + pad < bx1 or bx1 + bw + pad < ax1 or ay1 + ah + pad < by1 or by1 + bh + pad < ay1)


def _interior_seed_point(mask_u8: np.ndarray) -> Tuple[int, int]:
    """Return deepest interior (x, y) point inside a binary mask via distance transform."""
    bin_m = (mask_u8 > 127).astype(np.uint8)
    if not np.any(bin_m):
        h, w = mask_u8.shape[:2]
        return w // 2, h // 2
    dist = cv2.distanceTransform(bin_m, cv2.DIST_L2, 5)
    _, _, _, max_loc = cv2.minMaxLoc(dist)
    return int(max_loc[0]), int(max_loc[1])


def _extract_mask_layer(
    src_ref_path: str,
    project_dir: str,
    raw_mask: np.ndarray,
    layer_name: str,
    layer_type: str,
    group: str,
    z_index: int,
    cat: str,
    confidence: float,
    mask_tag: str,
    feather_px: int = 1,
    min_speck: int = 90,
) -> Tuple[Dict[str, Any], Dict[str, Any], np.ndarray]:
    """Refine mask cleanly, extract crisp 1:1 RGBA crop, and return (layer_dict, semantic_obj, binary_mask)."""
    nw, nh = raw_mask.shape[1], raw_mask.shape[0]
    mask_rel = f"masks/{mask_tag}.png"
    mask_abs = os.path.join(project_dir, mask_rel)
    Image.fromarray(raw_mask, "L").save(mask_abs)
    refine_mask(mask_abs, feather_px=feather_px, fill_holes=True, remove_specks_min_area=min_speck)

    refined_u8 = cv2.imdecode(np.fromfile(mask_abs, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
    if refined_u8 is None or int(np.sum(refined_u8 > 25)) < min_speck:
        return None, None, np.zeros((nh, nw), dtype=np.uint8)

    q_info = analyze_mask_quality(src_ref_path, mask_abs)
    rgba_rel = f"layers/{layer_name}.png"
    ex = apply_mask_to_source(src_ref_path, mask_abs, os.path.join(project_dir, rgba_rel), decontaminate_edges=True)

    lyr = make_layer(
        name=layer_name,
        layer_type=layer_type,
        source_file=rgba_rel,
        mask_file=mask_rel,
        x=ex["x"],
        y=ex["y"],
        width=ex["width"],
        height=ex["height"],
        z_index=z_index,
        group=group,
        confidence_score=confidence,
        warnings=q_info.get("warnings", []),
        metadata={"mask_quality": q_info},
    )
    sem = make_semantic_object(
        object_id=f"obj_{mask_tag}",
        object_name=layer_name,
        object_category=cat,
        bounding_box=[ex["x"], ex["y"], ex["width"], ex["height"]],
        z_index=z_index,
        confidence_score=confidence,
        segmentation_mask=mask_rel,
        source_asset=rgba_rel,
        reconstruction_status="extracted_clean_1to1",
        editability_status="mask_and_raster_editable",
        linked_layer_id=lyr["id"],
    )
    bin_out = (refined_u8 > 96).astype(np.uint8) * 255
    return lyr, sem, bin_out


def run_semantic_redesign(
    image_path: str,
    project_dir: str,
    project_id: str,
    title: str = "Semantic Redesign",
    upscale_2x: bool = True,
    max_dim: int = 2048,
    target_long_edge: int = 1920,
    use_rmbg: bool = True,
    use_ocr: bool = True,
    auto_object_split: bool = True,
    banner_mode: bool = False,
) -> Dict[str, Any]:
    """Full v1.3+ Auto Object-by-Object Semantic Reconstruction + LaMa Clean Background + Editable Typography."""
    if banner_mode:
        from core.banner_decomposer import run_banner_decomposition_pipeline
        return run_banner_decomposition_pipeline(
            image_path=image_path,
            project_dir=project_dir,
            project_id=project_id,
            title=title,
            max_dim=max_dim,
        )["document"]
    layers_dir = os.path.join(project_dir, "layers")
    masks_dir = os.path.join(project_dir, "masks")
    os.makedirs(layers_dir, exist_ok=True)
    os.makedirs(masks_dir, exist_ok=True)

    bgr_orig = _imread_unicode(image_path)
    if bgr_orig is None:
        raise ValueError(f"Could not read input image: {image_path}")
    oh, ow = bgr_orig.shape[:2]

    input_diag = inspect_input_quality(image_path, target_long_edge=target_long_edge if upscale_2x else max(ow, oh))
    warnings: List[str] = list(input_diag.get("warnings") or [])

    if upscale_2x and max(ow, oh) < min(target_long_edge, max_dim):
        up_tmp_name = f"input_upscaled_{min(target_long_edge, max_dim)}px.png"
        up_info = upscale_preserve_aspect_local(
            input_path=image_path,
            out_upscaled_path=os.path.join(project_dir, up_tmp_name),
            target_long_edge=target_long_edge,
            max_dim=max_dim,
        )
        nw, nh = up_info["output_size"]
        bgr = _imread_unicode(up_info["processed_path"])
        warnings.append(up_info["warning"])
    else:
        scale = (max_dim / max(ow, oh)) if max(ow, oh) > max_dim else 1.0
        nw, nh = int(round(ow * scale)), int(round(oh * scale))
        bgr = cv2.resize(bgr_orig, (nw, nh), interpolation=cv2.INTER_AREA) if scale != 1.0 else bgr_orig
        up_info = {
            "original_path": image_path,
            "processed_path": "source_reference.png",
            "input_size": [ow, oh],
            "output_size": [nw, nh],
            "scale_factor": round(nw / max(1.0, float(ow)), 4),
            "aspect_ratio_preserved": True,
            "upscaled": False,
            "method": "native_1to1_no_resize" if scale == 1.0 else "local_lanczos4_downscale_cap",
            "dedicated_sr_model_used": False,
            "quality_inspection": input_diag,
        }

    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)

    src_ref_path = os.path.join(project_dir, "source_reference.png")
    Image.fromarray(rgb, "RGB").save(src_ref_path)

    doc_layers: List[Dict[str, Any]] = []
    semantic_objects: List[Dict[str, Any]] = []

    # 1. Auto Object Discovery (DETR-ResNet-50) + RMBG-1.4 Salient Mask + OCR
    det_res = detect_objects(src_ref_path, threshold=0.62) if auto_object_split else {"ok": False, "objects": []}
    detr_objs = det_res.get("objects", []) if det_res.get("ok") else []

    rmbg_mask_path = os.path.join(masks_dir, "rmbg_salient.png")
    salient_mask = np.zeros((nh, nw), dtype=np.uint8)
    rmbg_used = False
    if use_rmbg:
        rmbg_res = run_rmbg_salient(src_ref_path, rmbg_mask_path)
        if rmbg_res.get("ok") and os.path.exists(rmbg_mask_path):
            m = cv2.imdecode(np.fromfile(rmbg_mask_path, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
            if m is not None:
                if m.shape[:2] != (nh, nw):
                    m = cv2.resize(m, (nw, nh), interpolation=cv2.INTER_LINEAR)
                salient_mask = (m > 120).astype(np.uint8) * 255
                rmbg_used = True

    raw_typo_items = extract_typography_objects(src_ref_path, project_dir) if use_ocr else []
    # Filter out obvious OCR false-positives inside sky/faces/buildings
    person_boxes = [o["bbox"] for o in detr_objs if o["label"] == "person"]
    typo_items = []
    for ti in raw_typo_items:
        tx, ty, tw, th = ti["bbox"]
        tcx, tcy = tx + tw / 2.0, ty + th / 2.0
        in_face_or_helmet = False
        for px, py, pw, ph in person_boxes:
            if px <= tcx <= px + pw and py <= tcy <= py + ph * 0.36:
                in_face_or_helmet = True
                break
        # Drop low-confidence OCR detections sitting on photo faces/helmets or blurry scenery
        if in_face_or_helmet and ti["confidence"] < 0.85:
            continue
        if len(ti["ocr_text"].strip()) <= 3 and ti["confidence"] < 0.80:
            continue
        typo_items.append(ti)

    text_mask_all = np.zeros((nh, nw), dtype=np.uint8)
    for ti in typo_items:
        tx, ty, tw, th = ti["bbox"]
        # Only add high-confidence non-overlapping bottom/banner text to background inpaint if NOT inside hero card
        text_mask_all[max(0, ty - 2):min(nh, ty + th + 2), max(0, tx - 2):min(nw, tx + tw + 2)] = 255

    # 2. Classify DETR objects: Background/Midground vehicles (outside salient_mask) vs Foreground Hero sub-objects
    bg_det_masks = np.zeros((nh, nw), dtype=np.uint8)
    extracted_bg_objs = []
    fg_det_candidates = []

    for idx_d, obj in enumerate(detr_objs):
        bx, by, bw, bh = obj["bbox"]
        bx2, by2 = min(nw, bx + bw), min(nh, by + bh)
        sub_sal = salient_mask[max(0, by):by2, max(0, bx):bx2]
        sal_overlap = float(np.mean(sub_sal > 0)) if sub_sal.size else 0.0

        # Distant cars on bridges/roads with low overlap against foreground hero -> Midground Vehicles
        if obj["label"] in ("car", "truck", "bus", "bicycle") and sal_overlap < 0.35:
            pts = [[bx + bw // 2, by + bh // 2]]
            lbls = [1]
            # Place exterior negative points cleanly outside padded bbox so car edges stay intact
            pad_neg = max(18, min(bw, bh) // 3)
            for nx, ny in [
                (max(2, bx - pad_neg), by + bh // 2),
                (min(nw - 3, bx2 + pad_neg), by + bh // 2),
                (bx + bw // 2, max(2, by - pad_neg)),
                (bx + bw // 2, min(nh - 3, by2 + pad_neg)),
            ]:
                pts.append([nx, ny])
                lbls.append(0)
            out_m = os.path.join(masks_dir, f"_tmp_bgobj_{idx_d}.png")
            segment_interactive(
                src_ref_path, out_m,
                points=pts, labels=lbls,
                box=[max(0, bx - 2), max(0, by - 2), min(nw, bx2 + 2), min(nh, by2 + 2)],
                mask_level=1,
                use_sam=True, tmp_dir=masks_dir,
            )
            if os.path.exists(out_m):
                m_u8 = cv2.imdecode(np.fromfile(out_m, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                if m_u8 is not None and int(np.sum(m_u8 > 100)) >= 120:
                    extracted_bg_objs.append((obj, m_u8))
                    # Dilate car hole mask by 9px for LaMa so zero green car rim ghosts on background
                    car_hole = cv2.dilate((m_u8 > 80).astype(np.uint8) * 255, np.ones((11, 11), np.uint8), iterations=1)
                    bg_det_masks = cv2.bitwise_or(bg_det_masks, car_hole)
        else:
            fg_det_candidates.append(obj)

    # 3. Extract compact isolated Midground silhouettes (e.g. Bitexco / Brand Logos) WITHOUT slicing large photo bridges
    bg_est, grad_mag = _estimate_local_background(bgr)
    diff = np.linalg.norm(lab.astype(np.float32) - cv2.cvtColor(bg_est, cv2.COLOR_BGR2LAB).astype(np.float32), axis=2)
    edges = cv2.dilate(cv2.Canny(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), 45, 130), np.ones((3, 3), np.uint8), iterations=1)
    fg_raw = (((diff > 22) & (grad_mag >= 10)) | (diff > 38) | (edges > 0)).astype(np.uint8) * 255
    fg_raw = cv2.morphologyEx(fg_raw, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1)

    midground_raw = cv2.subtract(fg_raw, cv2.dilate(salient_mask, np.ones((7, 7), np.uint8), iterations=1))
    midground_raw = cv2.subtract(midground_raw, cv2.dilate(bg_det_masks, np.ones((5, 5), np.uint8), iterations=1))
    midground_raw = cv2.subtract(midground_raw, text_mask_all)

    num_m, m_labels, m_stats, _ = cv2.connectedComponentsWithStats(midground_raw, 8)
    min_mid_area = max(400, int(nw * nh * 0.0015))
    max_mid_area = int(nw * nh * 0.14)
    valid_mid_indices = [
        i for i in range(1, num_m)
        if min_mid_area <= int(m_stats[i][4]) <= max_mid_area
        and int(m_stats[i][2]) < int(nw * 0.48)
        and int(m_stats[i][3]) < int(nh * 0.65)
        and not (int(m_stats[i][0]) == 0 and int(m_stats[i][1]) == 0 and int(m_stats[i][2]) > int(nw * 0.25))
    ]
    mid_clean_mask = np.isin(m_labels, valid_mid_indices).astype(np.uint8) * 255

    # 4. Build CLEAN LaMa Scene Background (preserve bottom logo/legal strip y > 0.87*nh from hero dilation scars)
    outside_text_mask = cv2.subtract(text_mask_all, cv2.dilate(salient_mask, np.ones((5, 5), np.uint8), iterations=1))
    total_bg_hole_mask = cv2.bitwise_or(salient_mask, cv2.bitwise_or(bg_det_masks, cv2.bitwise_or(mid_clean_mask, outside_text_mask)))
    # Protect crisp white bottom branding/legal band (y > 88% height) if it lies outside main subject silhouettes
    bottom_y = int(nh * 0.88)
    total_bg_hole_mask[bottom_y:, :] = cv2.bitwise_and(
        total_bg_hole_mask[bottom_y:, :],
        cv2.erode(salient_mask[bottom_y:, :], np.ones((5, 5), np.uint8), iterations=1),
    )
    bg_mask_path = os.path.join(masks_dir, "mask_clean_bg_holes.png")
    Image.fromarray(total_bg_hole_mask, "L").save(bg_mask_path)

    bg_out_rel = "layers/01_Background_Clean.png"
    recon = reconstruct_region(src_ref_path, bg_mask_path, os.path.join(project_dir, bg_out_rel), mode="auto")

    bg_lyr = make_layer(
        name="01_Background_Clean",
        layer_type="background",
        source_file=bg_out_rel,
        x=0, y=0, width=nw, height=nh, z_index=0,
        group="1_Background_&_Scene",
        ai_reconstructed=True,
        reconstruction_history=[recon["history_entry"]],
        confidence_score=0.92,
    )
    doc_layers.append(bg_lyr)
    semantic_objects.append(make_semantic_object(
        object_id="obj_background",
        object_name="Background Scene (Clean)",
        object_category="background",
        bounding_box=[0, 0, nw, nh],
        z_index=0,
        confidence_score=0.92,
        source_asset=bg_out_rel,
        reconstruction_status=f"reconstructed_{recon.get('engine', 'lama')}",
        editability_status="raster_editable",
        linked_layer_id=bg_lyr["id"],
    ))
    z = 1

    # 5a. Add Auto-Detected Midground Vehicles (e.g. GrabCars on Overpass!)
    for idx_v, (obj, m_u8) in enumerate(extracted_bg_objs, start=1):
        lbl_title = f"{obj['label'].capitalize()}_{idx_v:02d}"
        lyr_v, sem_v, _ = _extract_mask_layer(
            src_ref_path, project_dir, m_u8,
            layer_name=f"{z + 1:02d}_{lbl_title}",
            layer_type="vehicle" if obj["label"] in ("car", "truck", "motorcycle", "bicycle") else "object",
            group="2_Midground_Objects",
            z_index=z,
            cat=obj["label"],
            confidence=obj["score"],
            mask_tag=f"mid_det_{z:02d}",
            feather_px=1, min_speck=80,
        )
        if lyr_v:
            sem_v["overlap_relationships"] = [{"relation": "in_front_of", "target": "obj_background"}]
            doc_layers.append(lyr_v)
            semantic_objects.append(sem_v)
            z += 1

    # 5b. Add Compact Midground Architecture / Logos (if any)
    for i in valid_mid_indices:
        x, y, bw, bh, _ = [int(v) for v in m_stats[i]]
        m_i = np.where(m_labels == i, 255, 0).astype(np.uint8)
        if y < nh * 0.16 and bw < nw * 0.35:
            cat, lbl_name, grp = "logo", f"Logo_{z:02d}", "5_Logos_&_Typography"
        elif bh > bw * 1.15 and nh * 0.20 < y < nh * 0.85:
            cat, lbl_name, grp = "architecture", f"Architecture_{z:02d}", "2_Midground_Objects"
        else:
            cat, lbl_name, grp = "foreground_object", f"MidObject_{z:02d}", "2_Midground_Objects"

        lyr_m, sem_m, _ = _extract_mask_layer(
            src_ref_path, project_dir, m_i,
            layer_name=f"{z + 1:02d}_{lbl_name}",
            layer_type="architecture" if cat == "architecture" else ("logo" if cat == "logo" else "object"),
            group=grp, z_index=z, cat=cat, confidence=0.80,
            mask_tag=f"mid_{z:02d}", feather_px=1, min_speck=100,
        )
        if lyr_m:
            sem_m["overlap_relationships"] = [{"relation": "in_front_of", "target": "obj_background"}]
            doc_layers.append(lyr_m)
            semantic_objects.append(sem_m)
            z += 1

    # 6. Auto Object-by-Object Foreground Decomposition (SlimSAM-77 + Remaining Props inside RMBG-1.4)
    claimed_fg = np.zeros((nh, nw), dtype=np.uint8)
    if np.any(salient_mask > 0):
        # Extract non-person hero objects first (motorcycle, handheld items), then riders largest-last
        fg_sorted = sorted(
            fg_det_candidates,
            key=lambda o: (1 if o["label"] == "person" else 0, o["bbox"][2] * o["bbox"][3]),
        )
        for idx_f, obj in enumerate(fg_sorted):
            bx, by, bw, bh = obj["bbox"]
            bx2, by2 = min(nw, bx + bw), min(nh, by + bh)
            if bw * bh < 600:
                continue

            # Pick interior + points inside salient_mask MINUS overlapping other classes (so motorbike avoids rider's pants!)
            cand_region = np.zeros((nh, nw), dtype=np.uint8)
            cand_region[max(0, by):by2, max(0, bx):bx2] = salient_mask[max(0, by):by2, max(0, bx):bx2]
            cand_region = cv2.subtract(cand_region, claimed_fg)
            if obj["label"] in ("motorcycle", "bicycle"):
                pure_veh = cand_region.copy()
                for px, py, pw, ph in person_boxes:
                    pure_veh[max(0, py):min(nh, py + ph), max(0, px):min(nw, px + pw)] = 0
                if int(np.sum(pure_veh > 0)) >= 600:
                    cand_region = pure_veh
            if int(np.sum(cand_region > 0)) < 500:
                continue

            sx, sy = _interior_seed_point(cand_region)
            pts = [[sx, sy]]
            lbls = [1]
            # Add extra interior points on the un-occluded vehicle/object parts
            ys_c, xs_c = np.where(cand_region > 0)
            if len(xs_c) > 200:
                pts.append([int(np.percentile(xs_c, 22)), int(np.percentile(ys_c, 65))])
                lbls.append(1)

            # Negative points: centers of other non-overlapping foreground DETR objects (or rider torso when seeding bike)
            for j_f, other in enumerate(fg_sorted):
                if j_f == idx_f:
                    continue
                ox, oy, owb, ohb = other["bbox"]
                ocx, ocy = ox + owb // 2, oy + ohb // 3
                if obj["label"] in ("motorcycle", "bicycle") and other["label"] == "person":
                    pts.append([ocx, ocy])
                    lbls.append(0)
                elif not (bx <= ocx <= bx2 and by <= ocy <= by2):
                    pts.append([ocx, ocy])
                    lbls.append(0)

            out_m = os.path.join(masks_dir, f"_tmp_fg_{idx_f}.png")
            segment_interactive(
                src_ref_path, out_m,
                points=pts, labels=lbls,
                box=[bx, by, bx2, by2],
                mask_level=2 if (bw * bh > nw * nh * 0.05) else 1,
                use_sam=True, tmp_dir=masks_dir,
            )
            if os.path.exists(out_m):
                m_sam = cv2.imdecode(np.fromfile(out_m, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                if m_sam is not None:
                    # Keep cleanly inside dilated salient_mask & subtract already claimed objects so 0 duplicate pixels!
                    sal_clip = cv2.dilate(salient_mask, np.ones((5, 5), np.uint8), iterations=1)
                    m_obj = cv2.bitwise_and(m_sam, sal_clip)
                    # If single non-overlapping foreground candidate matches >60% of RMBG salient island, adopt full crisp RMBG island so vehicle/subject is never torn in half!
                    if len(fg_sorted) == 1:
                        sal_area = max(1, int(np.sum(salient_mask > 120)))
                        sam_in_sal = int(np.sum((m_obj > 90) & (salient_mask > 120)))
                        if sam_in_sal / sal_area >= 0.55:
                            m_obj = salient_mask.copy()
                    m_obj = cv2.subtract(m_obj, claimed_fg)
                    if int(np.sum(m_obj > 90)) >= 900:
                        cat_lbl = obj["label"].capitalize()
                        ltype = "vehicle" if obj["label"] in ("motorcycle", "car", "bicycle") else ("character" if obj["label"] == "person" else "object")
                        lyr_f, sem_f, bin_f = _extract_mask_layer(
                            src_ref_path, project_dir, m_obj,
                            layer_name=f"{z + 1:02d}_{cat_lbl}_{idx_f + 1:02d}",
                            layer_type=ltype,
                            group="3_Foreground_Objects",
                            z_index=z,
                            cat=obj["label"],
                            confidence=obj["score"],
                            mask_tag=f"fg_obj_{z:02d}",
                            feather_px=1, min_speck=140,
                        )
                        if lyr_f:
                            doc_layers.append(lyr_f)
                            semantic_objects.append(sem_f)
                            claimed_fg = cv2.bitwise_or(claimed_fg, bin_f)
                            z += 1

        # Extract any substantial un-claimed Hero / Prop regions using eroded subtraction to avoid semi-transparent hairline seams
        rem_sal = cv2.subtract(salient_mask, cv2.erode(claimed_fg, np.ones((3, 3), np.uint8), iterations=1))
        num_r, r_labels, r_stats, _ = cv2.connectedComponentsWithStats(rem_sal, 8)
        for i_r in range(1, num_r):
            rx, ry, rbw, rbh, rarea = [int(v) for v in r_stats[i_r]]
            if rarea < max(900, int(nw * nh * 0.004)):
                continue
            r_mask = np.where(r_labels == i_r, 255, 0).astype(np.uint8)
            # Check if region looks like a colorful held graphic board/badge or hero continuation
            lbl_suffix = "Held_Card_or_Prop" if (rx > nw * 0.35 and rbw > nw * 0.25 and rbh > nh * 0.18) else f"Foreground_Hero_{z:02d}"
            lyr_r, sem_r, _ = _extract_mask_layer(
                src_ref_path, project_dir, r_mask,
                layer_name=f"{z + 1:02d}_{lbl_suffix}",
                layer_type="character" if "Hero" in lbl_suffix else "foreground_object",
                group="4_Foreground_Hero_Parts",
                z_index=z,
                cat="sign_card" if "Card" in lbl_suffix else "foreground_object",
                confidence=0.86 if rmbg_used else 0.68,
                mask_tag=f"fg_rem_{z:02d}",
                feather_px=1, min_speck=140,
            )
            if lyr_r:
                doc_layers.append(lyr_r)
                semantic_objects.append(sem_r)
                z += 1

    # 7. Typography Layers (Keep Clean OrigRaster visible by default, Editable Text Layer paired cleanly with Vietnamese Font!)
    for ti in typo_items:
        tx, ty, tw, th = ti["bbox"]
        crop_rgb = rgb[ty:ty + th, tx:tx + tw]
        crop_bgr = bgr[ty:ty + th, tx:tx + tw]
        bg_c = bg_est[ty:ty + th, tx:tx + tw]
        d_txt = np.linalg.norm(cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2LAB).astype(np.float32) - cv2.cvtColor(bg_c, cv2.COLOR_BGR2LAB).astype(np.float32), axis=2)
        t_alpha = np.where(d_txt > 16, 255, 0).astype(np.uint8)
        t_alpha = cv2.GaussianBlur(t_alpha, (3, 3), 0)
        raster_rel = f"layers/{z + 1:02d}_TextRaster_{ti['index']:02d}.png"
        Image.fromarray(np.dstack([crop_rgb, t_alpha]), "RGBA").save(os.path.join(project_dir, raster_rel))

        fm = ti["font_match"]
        ed_im = render_styled_text(
            text=ti["ocr_text"],
            font_file=fm["font_file"],
            font_size=ti["font_size"],
            color=tuple(ti["fill_color"]),
            align=ti["alignment"],
            stroke_enabled=ti["has_stroke_or_3d"],
            stroke_color=(255, 255, 255) if sum(ti["fill_color"]) < 380 else (0, 0, 0),
            stroke_width=2,
            rotation=ti["rotation"],
        )
        ed_rel = f"layers/{z + 1:02d}_TextEditable_{ti['index']:02d}.png"
        ed_im.save(os.path.join(project_dir, ed_rel))

        lyr_r = make_layer(
            name=f"{z + 1:02d}_Text_OrigRaster_{ti['index']:02d}",
            layer_type="object",
            source_file=raster_rel,
            x=tx, y=ty, width=tw, height=th, z_index=z,
            visible=True,
            group="5_Original_Text_Raster",
            confidence_score=ti["confidence"],
            warnings=[ti["warning"]] if ti["warning"] else [],
        )
        doc_layers.append(lyr_r)
        z += 1

        lyr_e = make_layer(
            name=f"{z + 1:02d}_Text_Editable_{ti['index']:02d}",
            layer_type="text",
            source_file=ed_rel,
            x=max(0, tx - 24), y=max(0, ty - 24), width=ed_im.width, height=ed_im.height, z_index=z,
            visible=False,
            group="5_Logos_&_Typography",
            text_data={
                "text": ti["ocr_text"],
                "font": fm["font_name"],
                "font_file": fm["font_file"],
                "font_size": ti["font_size"],
                "color": ti["fill_color"],
                "align": ti["alignment"],
                "tracking": ti["letter_spacing"],
                "leading": 10,
                "stroke_enabled": ti["has_stroke_or_3d"],
                "stroke_color": [255, 255, 255] if sum(ti["fill_color"]) < 380 else [0, 0, 0],
                "stroke_width": 2,
                "shadow_enabled": False,
                "glow_enabled": False,
                "gradient_enabled": False,
                "extrude_3d_depth": 0,
            },
            text_reconstruction={
                "original_raster_file": ti["original_raster_file"],
                "ocr_text": ti["ocr_text"],
                "ocr_confidence": ti["confidence"],
                "baseline_y": ti["baseline_y"],
                "alignment": ti["alignment"],
                "rotation": ti["rotation"],
                "estimated_font": fm["font_name"],
                "matched_font_file": fm["font_file"],
                "is_exact_font_match": fm["is_exact_font_match"],
                "match_note": fm["match_note"],
                "needs_user_confirmation": True,
            },
            confidence_score=ti["confidence"],
            warnings=[fm["match_note"]] + ([ti["warning"]] if ti["warning"] else []),
        )
        doc_layers.append(lyr_e)
        semantic_objects.append(make_semantic_object(
            object_id=f"obj_text_{ti['index']:02d}",
            object_name=f"Text: {ti['ocr_text'][:24]}",
            object_category="typography",
            bounding_box=[tx, ty, tw, th],
            z_index=z,
            confidence_score=ti["confidence"],
            overlap_relationships=[{"relation": "in_front_of", "target": "obj_background"}],
            source_asset=ed_rel,
            reconstruction_status="needs_user_confirmation",
            editability_status="editable_text",
            linked_layer_id=lyr_e["id"],
        ))
        z += 1

    # Fallback: if no foreground object survived decomposition at all, preserve clean Foreground Hero from RMBG
    if not any(l["group"].startswith("3_Foreground") or l["group"].startswith("4_Foreground") for l in doc_layers) and np.any(salient_mask > 0):
        lyr_f, sem_f, _ = _extract_mask_layer(
            src_ref_path, project_dir, salient_mask,
            layer_name=f"{z + 1:02d}_Foreground_Hero",
            layer_type="character", group="3_Foreground_Objects",
            z_index=z, cat="character", confidence=0.85,
            mask_tag=f"fg_fallback_{z:02d}", feather_px=1, min_speck=120,
        )
        if lyr_f:
            doc_layers.append(lyr_f)
            semantic_objects.append(sem_f)

    # Extract dominant color palette for Remix/Reuse across future projects
    small_rgb = cv2.resize(rgb, (64, 64), interpolation=cv2.INTER_AREA).reshape(-1, 3)
    pal_samples = small_rgb[::max(1, len(small_rgb) // 6)][:5]
    palette_hex = ["#%02X%02X%02X" % tuple(int(c) for c in px) for px in pal_samples]

    doc = create_document(
        project_id=project_id,
        title=title,
        mode="REDESIGN",
        width=nw,
        height=nh,
        layers=doc_layers,
        source_image="source_reference.png",
        brand={
            "extracted_palette": palette_hex,
            "input_preprocess": up_info,
        },
        semantic_objects=semantic_objects,
        warnings=list(dict.fromkeys(warnings)),
        notes=[
            f"Semantic Redesign v1.3 ({ow}x{oh} -> {nw}x{nh}, method={up_info['method']}).",
            f"DETR Objects: {len(detr_objs)} | RMBG-1.4: {rmbg_used} | BG Engine: {recon.get('engine', 'lama')} | OCR lines: {len(typo_items)}.",
        ],
    )
    save_document(doc, project_dir)
    save_version(doc, project_dir, note="Initial v1.3 Auto Object-by-Object Semantic Redesign")
    return doc
