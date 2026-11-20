"""Generic MODE A (REDESIGN) Engine — dynamic image decomposition, upscaling, and background reconstruction."""
import os
import cv2
import numpy as np
from PIL import Image, ImageFilter

from core.design_document import create_document, make_layer, save_document


def sharpen_fullhd(pil_img: Image.Image, radius: float = 1.2, percent: int = 125, threshold: int = 2) -> Image.Image:
    if pil_img.mode == "RGBA":
        r, g, b, a = pil_img.split()
        rgb = Image.merge("RGB", (r, g, b)).filter(
            ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold)
        )
        r2, g2, b2 = rgb.split()
        return Image.merge("RGBA", (r2, g2, b2, a))
    return pil_img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def _imread_unicode(img_path: str):
    data = np.fromfile(img_path, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def extract_product_rgba(img_path: str, remove_white_bg: bool = True) -> Image.Image:
    """Load product/logo image preserving original pixels. Flood-fills outer white only if requested."""
    pil_in = Image.open(img_path)
    if pil_in.mode == "RGBA":
        arr = np.array(pil_in)
        # If image already has meaningful transparency, keep it untouched
        if np.any(arr[:, :, 3] < 250):
            return pil_in

    bgr = _imread_unicode(img_path)
    if bgr is None:
        raise ValueError(f"Cannot read image: {img_path}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = bgr.shape[:2]

    if not remove_white_bg:
        return Image.fromarray(np.dstack([rgb, np.full((h, w), 255, dtype=np.uint8)]), "RGBA")

    # Check if borders are predominantly white/near-white
    border_pixels = np.vstack([bgr[0, :], bgr[-1, :], bgr[:, 0], bgr[:, -1]])
    if np.median(border_pixels) < 230:
        return Image.fromarray(np.dstack([rgb, np.full((h, w), 255, dtype=np.uint8)]), "RGBA")

    is_white = ((bgr[:, :, 0] > 238) & (bgr[:, :, 1] > 238) & (bgr[:, :, 2] > 238)).astype(np.uint8) * 255
    bg_mask = is_white.copy()
    flood = np.zeros((h + 2, w + 2), np.uint8)
    for sx in range(0, w, max(1, w // 40)):
        if bg_mask[0, sx] == 255:
            cv2.floodFill(bg_mask, flood, (sx, 0), 128)
        if bg_mask[h - 1, sx] == 255:
            cv2.floodFill(bg_mask, flood, (sx, h - 1), 128)
    for sy in range(0, h, max(1, h // 40)):
        if bg_mask[sy, 0] == 255:
            cv2.floodFill(bg_mask, flood, (0, sy), 128)
        if bg_mask[sy, w - 1] == 255:
            cv2.floodFill(bg_mask, flood, (w - 1, sy), 128)

    fg_mask = np.where(bg_mask == 128, 0, 255).astype(np.uint8)
    # Remove tiny outer specks
    num_l, labels, stats, _ = cv2.connectedComponentsWithStats(fg_mask, 8)
    clean_fg = np.zeros_like(fg_mask)
    for idx in range(1, num_l):
        if stats[idx, cv2.CC_STAT_AREA] >= 64:
            clean_fg[labels == idx] = 255

    eroded = cv2.erode(clean_fg, np.ones((3, 3), np.uint8), iterations=1)
    alpha = cv2.GaussianBlur(eroded, (3, 3), 0)
    interior = cv2.erode(eroded, np.ones((3, 3), np.uint8), iterations=1)
    alpha = np.maximum(alpha, interior)
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


def _estimate_local_background(bgr: np.ndarray) -> tuple:
    """Estimate smooth local background surface across arbitrary flat or gradient posters."""
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(gx * gx + gy * gy)

    # Sample border colors to identify likely background color family
    border = np.vstack([
        lab[0:6, :, :].reshape(-1, 3),
        lab[-6:, :, :].reshape(-1, 3),
        lab[:, 0:6, :].reshape(-1, 3),
        lab[:, -6:, :].reshape(-1, 3),
    ])
    border_med = np.median(border, axis=0)
    dist_border = np.linalg.norm(lab.astype(np.float32) - border_med.astype(np.float32), axis=2)

    flat_bg = (grad_mag < 16) & (dist_border < 36)
    # If border had mixed shapes (like black top-left + green), relax to low-gradient pixels near dominant border cluster
    if np.mean(flat_bg) < 0.08:
        flat_bg = grad_mag < 12

    sm_w, sm_h = max(64, min(160, w // 6)), max(64, min(160, h // 6))
    bgr_sm = cv2.resize(bgr, (sm_w, sm_h), interpolation=cv2.INTER_AREA)
    fg_sm = cv2.resize((~flat_bg).astype(np.uint8) * 255, (sm_w, sm_h), interpolation=cv2.INTER_NEAREST)
    fg_sm = cv2.dilate(fg_sm, np.ones((3, 3), np.uint8), iterations=1)
    bg_sm = cv2.inpaint(bgr_sm, fg_sm, 5, cv2.INPAINT_TELEA)
    bg_sm = cv2.GaussianBlur(bg_sm, (9, 9), 0)
    bg_est = cv2.resize(bg_sm, (w, h), interpolation=cv2.INTER_CUBIC)
    return bg_est, grad_mag


def _classify_component(crop_rgb: np.ndarray, mask_crop: np.ndarray, x: int, y: int, bw: int, bh: int, w: int, h: int) -> tuple:
    """Heuristically classify extracted layer into (layer_type, group_name, label_prefix)."""
    area = int(np.sum(mask_crop > 0))
    bbox_area = max(1, bw * bh)
    fill_ratio = area / bbox_area
    aspect = bw / max(1, bh)

    gray = cv2.cvtColor(crop_rgb, cv2.COLOR_RGB2GRAY)
    masked_vals = gray[mask_crop > 0]
    std_lum = float(np.std(masked_vals)) if len(masked_vals) > 0 else 0.0

    # Large solid or low-texture region covering >12% of canvas -> shape
    if (bw * bh) > (w * h * 0.10) and std_lum < 25 and fill_ratio > 0.55:
        return "shape", "1_Background_&_Shapes", "Shape"

    # Small compact elements -> icon or logo
    if bw <= int(w * 0.14) and bh <= int(h * 0.14) and area < (w * h * 0.015):
        return "icon", "3_Icons_&_Decor", "Icon"

    # Wide horizontal strip with medium-low fill ratio & crisp stroke contrast -> text block
    if aspect >= 2.2 and bh <= int(h * 0.18) and fill_ratio < 0.72:
        return "text", "4_Texts_Extracted", "Text"

    # Rich photographic variance or large hero region -> product/object
    if std_lum > 32 or (bw * bh) > (w * h * 0.04):
        return "product", "2_Products_&_Objects", "Object"

    if bw <= int(w * 0.35) and bh <= int(h * 0.14):
        return "logo", "2_Products_&_Objects", "Logo"

    return "object", "2_Products_&_Objects", "Element"


def _merge_nearby_text_boxes(boxes: list, w: int, h: int) -> list:
    """Merge horizontally close small glyphs/words on the same line into coherent text/element groups."""
    merged = []
    used = [False] * len(boxes)
    max_x_gap = max(14, int(w * 0.025))
    max_y_diff = max(10, int(h * 0.018))

    # Only merge small/medium boxes (likely glyphs/words); keep large hero objects untouched
    for i, b in enumerate(boxes):
        if used[i]:
            continue
        x1, y1, bw, bh, lbl_ids = b[0], b[1], b[2], b[3], [b[4]]
        x2, y2 = x1 + bw, y1 + bh
        used[i] = True
        if bw < w * 0.30 and bh < h * 0.12:
            changed = True
            while changed:
                changed = False
                for j, o in enumerate(boxes):
                    if used[j]:
                        continue
                    ox1, oy1, obw, obh, olbl = o
                    if obw >= w * 0.30 or obh >= h * 0.12:
                        continue
                    ox2, oy2 = ox1 + obw, oy1 + obh
                    # Same horizontal band and close X gap
                    v_overlap = min(y2, oy2) - max(y1, oy1)
                    h_gap = max(0, max(x1, ox1) - min(x2, ox2))
                    if v_overlap >= min(bh, obh) * 0.35 and abs((y1 + y2) / 2 - (oy1 + oy2) / 2) <= max_y_diff and h_gap <= max_x_gap:
                        x1, y1 = min(x1, ox1), min(y1, oy1)
                        x2, y2 = max(x2, ox2), max(y2, oy2)
                        lbl_ids.append(olbl)
                        used[j] = True
                        changed = True
        merged.append((x1, y1, x2 - x1, y2 - y1, lbl_ids))
    return merged


def run_redesign(
    image_path: str,
    project_dir: str,
    project_id: str,
    title: str = "Redesign Project",
    upscale_2x: bool = True,
    max_dim: int = 2048,
) -> dict:
    """Decompose any flat PNG/JPG/WEBP into independent RGBA layers + unified DesignDocument."""
    layers_dir = os.path.join(project_dir, "layers")
    os.makedirs(layers_dir, exist_ok=True)

    pil_src = Image.open(image_path)
    src_has_alpha = pil_src.mode == "RGBA" and np.any(np.array(pil_src)[:, :, 3] < 250)

    bgr_orig = _imread_unicode(image_path)
    if bgr_orig is None:
        raise ValueError(f"Could not read input image: {image_path}")

    oh, ow = bgr_orig.shape[:2]
    if max(ow, oh) > max_dim:
        scale = max_dim / max(ow, oh)
    elif upscale_2x and max(ow, oh) * 2 <= max_dim:
        scale = 2.0
    elif upscale_2x and max(ow, oh) < max_dim:
        scale = max_dim / max(ow, oh)
    else:
        scale = 1.0
    nw, nh = int(round(ow * scale)), int(round(oh * scale))

    # Denoise compression artifacts gently before resizing
    bgr_clean = cv2.bilateralFilter(bgr_orig, 5, 22, 22)
    bgr = cv2.resize(bgr_clean, (nw, nh), interpolation=cv2.INTER_LANCZOS4) if scale != 1.0 else bgr_clean
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)

    # Save copy of source reference
    ref_path = os.path.join(project_dir, "source_reference.png")
    Image.fromarray(rgb).save(ref_path)

    doc_layers = []

    if src_has_alpha:
        # Transparent PNG input: keep clean transparent background + exact alpha product layer
        rgba_arr = np.array(pil_src.resize((nw, nh), Image.Resampling.LANCZOS))
        bg_rgba = Image.new("RGBA", (nw, nh), (255, 255, 255, 0))
        bg_file = "layers/01_Background_Transparent.png"
        bg_rgba.save(os.path.join(project_dir, bg_file))
        doc_layers.append(make_layer(
            name="01_Background_Transparent",
            layer_type="background",
            source_file=bg_file,
            x=0, y=0, width=nw, height=nh, z_index=0,
            group="1_Background_&_Shapes",
            metadata={"transparent_input": True},
        ))

        alpha = rgba_arr[:, :, 3]
        ys, xs = np.where(alpha > 5)
        if len(xs) > 0:
            x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
            prod_pil = sharpen_fullhd(Image.fromarray(rgba_arr[y1:y2, x1:x2], "RGBA"))
            prod_file = "layers/02_Product_Extracted.png"
            prod_pil.save(os.path.join(project_dir, prod_file))
            doc_layers.append(make_layer(
                name="02_Product_Extracted",
                layer_type="product",
                source_file=prod_file,
                x=x1, y=y1, width=x2 - x1, height=y2 - y1, z_index=1,
                group="2_Products_&_Objects",
                metadata={"preserved_alpha": True},
            ))
    else:
        bg_est, grad_mag = _estimate_local_background(bgr)
        lab_est = cv2.cvtColor(bg_est, cv2.COLOR_BGR2LAB)
        diff = np.linalg.norm(lab.astype(np.float32) - lab_est.astype(np.float32), axis=2)

        edges = cv2.Canny(gray, 42, 125)
        edges_dil = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
        # Soft glows / clouds (low gradient) require stronger LAB difference so they don't glue text & subjects together
        fg_raw = (((diff > 18) & (grad_mag >= 8)) | (diff > 34) | (edges_dil > 0)).astype(np.uint8) * 255
        fg_closed = cv2.morphologyEx(fg_raw, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

        # Flood-fill from outer borders ONLY where pixel matches dominant background family (prevents leaking into photo sky/highlights)
        border_pts = np.vstack([
            lab[0:4, :, :].reshape(-1, 3),
            lab[-4:, :, :].reshape(-1, 3),
            lab[:, 0:4, :].reshape(-1, 3),
            lab[:, -4:, :].reshape(-1, 3),
        ])
        dom_bg_lab = np.median(border_pts, axis=0).astype(np.float32)
        dist_dom = np.linalg.norm(lab.astype(np.float32) - dom_bg_lab, axis=2)

        flood = fg_closed.copy()
        mask_ff = np.zeros((nh + 2, nw + 2), np.uint8)
        for sx in range(0, nw, max(4, nw // 80)):
            if flood[2, sx] == 0 and diff[2, sx] < 16 and dist_dom[2, sx] < 38:
                cv2.floodFill(flood, mask_ff, (sx, 2), 128)
            if flood[nh - 3, sx] == 0 and diff[nh - 3, sx] < 16 and dist_dom[nh - 3, sx] < 38:
                cv2.floodFill(flood, mask_ff, (sx, nh - 3), 128)
        for sy in range(0, nh, max(4, nh // 80)):
            if flood[sy, 2] == 0 and diff[sy, 2] < 16 and dist_dom[sy, 2] < 38:
                cv2.floodFill(flood, mask_ff, (2, sy), 128)
            if flood[sy, nw - 3] == 0 and diff[sy, nw - 3] < 16 and dist_dom[sy, nw - 3] < 38:
                cv2.floodFill(flood, mask_ff, (nw - 3, sy), 128)

        fg_filled = np.where(flood == 128, 0, 255).astype(np.uint8)

        # Remove tiny specks & faint atmospheric streaks (rain/cloud artifacts)
        min_area = max(60, int((nw * nh) * 0.00012))
        num_l, labels, stats, _ = cv2.connectedComponentsWithStats(fg_filled, 8)
        clean_fg = np.zeros_like(fg_filled)
        raw_boxes = []
        for idx in range(1, num_l):
            x, y, bw, bh, area = stats[idx]
            if area >= min_area:
                # Skip tiny faint atmospheric wisps (very small area AND very low LAB diff from background)
                if area < int((nw * nh) * 0.0015):
                    patch_diff = diff[y:y + bh, x:x + bw][labels[y:y + bh, x:x + bw] == idx]
                    if len(patch_diff) > 0 and float(np.percentile(patch_diff, 90)) < 26.0:
                        continue
                clean_fg[labels == idx] = 255
                raw_boxes.append((int(x), int(y), int(bw), int(bh), idx))

        # Reconstruct clean background (multi-scale inpaint + seam feathering)
        inpaint_mask = cv2.dilate(clean_fg, np.ones((9, 9), np.uint8), iterations=1)
        reconstructed_pct = round(float(np.mean(inpaint_mask > 0)) * 100.0, 2)
        sm_scale = min(1.0, 480.0 / max(nw, nh))
        sm_w, sm_h = max(64, int(nw * sm_scale)), max(64, int(nh * sm_scale))
        bg_inp_sm = cv2.inpaint(
            cv2.resize(bgr, (sm_w, sm_h), interpolation=cv2.INTER_AREA),
            cv2.resize(inpaint_mask, (sm_w, sm_h), interpolation=cv2.INTER_NEAREST),
            7,
            cv2.INPAINT_TELEA,
        )
        bg_inp = cv2.resize(bg_inp_sm, (nw, nh), interpolation=cv2.INTER_CUBIC)
        bg_blur = cv2.GaussianBlur(bg_inp, (21, 21), 0)
        blend_w = (cv2.GaussianBlur(inpaint_mask.astype(np.float32), (15, 15), 0) / 255.0)[:, :, None]
        bg_final_bgr = np.where(inpaint_mask[:, :, None] == 0, bgr, (bg_inp * (1 - blend_w * 0.65) + bg_blur * (blend_w * 0.65)).astype(np.uint8))
        bg_final_rgba = cv2.cvtColor(bg_final_bgr, cv2.COLOR_BGR2RGBA)

        bg_file = "layers/01_Background_Clean.png"
        Image.fromarray(bg_final_rgba, "RGBA").save(os.path.join(project_dir, bg_file))
        doc_layers.append(make_layer(
            name="01_Background_Clean",
            layer_type="background",
            source_file=bg_file,
            x=0, y=0, width=nw, height=nh, z_index=0,
            group="1_Background_&_Shapes",
            ai_reconstructed=reconstructed_pct > 1.0,
            metadata={"reconstructed_coverage_pct": reconstructed_pct, "upscale_factor": scale},
        ))

        # Group nearby text/glyph boxes & extract each layer cleanly
        merged_groups = _merge_nearby_text_boxes(raw_boxes, nw, nh)
        # Sort shapes first, then products/objects, then icons/logos, then text on top
        type_order = {"shape": 1, "product": 2, "object": 3, "logo": 4, "icon": 5, "text": 6}
        extracted_items = []
        for idx, (gx, gy, gw, gh, lbl_ids) in enumerate(merged_groups, start=2):
            m = np.zeros((nh, nw), np.uint8)
            for lid in lbl_ids:
                m[labels == lid] = 255
            crop_mask = m[gy:gy + gh, gx:gx + gw]
            crop_rgb = rgb[gy:gy + gh, gx:gx + gw]
            ltype, grp, prefix = _classify_component(crop_rgb, crop_mask, gx, gy, gw, gh, nw, nh)
            extracted_items.append((type_order.get(ltype, 3), gy, gx, ltype, grp, prefix, crop_rgb, crop_mask, gw, gh))

        extracted_items.sort(key=lambda t: (t[0], t[1], t[2]))
        for z_idx, (_, gy, gx, ltype, grp, prefix, crop_rgb, crop_mask, gw, gh) in enumerate(extracted_items, start=1):
            eroded = cv2.erode(crop_mask, np.ones((3, 3), np.uint8), iterations=1) if min(gw, gh) > 8 else crop_mask
            alpha = cv2.GaussianBlur(eroded, (3, 3), 0)
            alpha = np.maximum(alpha, eroded)
            rgba_crop = np.dstack([crop_rgb, alpha])
            pil_layer = sharpen_fullhd(Image.fromarray(rgba_crop, "RGBA"), radius=1.2, percent=120)
            fname = f"{z_idx + 1:02d}_{prefix}_{gx}_{gy}.png"
            rel_path = f"layers/{fname}"
            pil_layer.save(os.path.join(project_dir, rel_path))
            doc_layers.append(make_layer(
                name=f"{z_idx + 1:02d}_{prefix}_{gx}_{gy}",
                layer_type=ltype,
                source_file=rel_path,
                x=gx, y=gy, width=gw, height=gh, z_index=z_idx,
                group=grp,
                ai_reconstructed=False,
                metadata={"extracted_from_source": True, "area_px": int(np.sum(crop_mask > 0))},
            ))

    doc = create_document(
        project_id=project_id,
        title=title,
        mode="REDESIGN",
        width=nw,
        height=nh,
        layers=doc_layers,
        source_image="source_reference.png",
        notes=[
            f"Source resolution: {ow}x{oh} -> Working resolution: {nw}x{nh} (scale {scale}x)",
            "Background layer marked ai_reconstructed where occluded objects were removed via LAB-guided Telea inpainting.",
        ],
    )
    save_document(doc, project_dir)
    return doc
