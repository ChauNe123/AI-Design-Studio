import os
import json
import struct
import cv2
import numpy as np
from PIL import Image


def packbits_encode(data: bytes) -> bytes:
    """RLE PackBits compression for PSD channels."""
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        # Check for run of identical bytes
        run_len = 1
        while i + run_len < n and run_len < 128 and data[i + run_len] == data[i]:
            run_len += 1
        if run_len >= 3:
            out.append(257 - run_len)
            out.append(data[i])
            i += run_len
        else:
            # Literal run
            lit_start = i
            lit_len = 0
            while i < n and lit_len < 128:
                if i + 2 < n and data[i] == data[i + 1] == data[i + 2]:
                    break
                i += 1
                lit_len += 1
            out.append(lit_len - 1)
            out.extend(data[lit_start:lit_start + lit_len])
    return bytes(out)


def write_psd(width: int, height: int, layers: list, out_path: str):
    """
    Write a standard RGB 8-bit multi-layer PSD file (readable by Photoshop / Photopea / PhoToSop).
    Each item in `layers` is dict: {name, left, top, right, bottom, rgba (H,W,4 uint8), opacity (0-255), visible (bool)}.
    """
    buf = bytearray()

    # 1. File Header (26 bytes)
    buf.extend(b"8BPS")
    buf.extend(struct.pack(">H", 1))          # Version 1 (PSD)
    buf.extend(b"\x00" * 6)                   # Reserved
    buf.extend(struct.pack(">H", 4))          # Channels: RGBA (4)
    buf.extend(struct.pack(">II", height, width))
    buf.extend(struct.pack(">H", 8))          # Depth: 8 bits
    buf.extend(struct.pack(">H", 3))          # Color Mode: RGB (3)

    # 2. Color Mode Data (empty)
    buf.extend(struct.pack(">I", 0))

    # 3. Image Resources (empty)
    buf.extend(struct.pack(">I", 0))

    # 4. Layer and Mask Information Section
    layer_info = bytearray()
    layer_info.extend(struct.pack(">h", len(layers)))

    channel_datas = []
    for lyr in layers:
        top, left, bottom, right = lyr["top"], lyr["left"], lyr["bottom"], lyr["right"]
        rgba = lyr["rgba"]
        lh, lw = rgba.shape[:2]

        # Channel order in PSD: -1 (Alpha), 0 (R), 1 (G), 2 (B)
        ch_indices = [-1, 0, 1, 2]
        arr_indices = [3, 0, 1, 2]
        lyr_ch_blobs = []
        for c_idx, a_idx in zip(ch_indices, arr_indices):
            ch_plane = rgba[:, :, a_idx]
            rows_packed = bytearray()
            row_counts = []
            for r in range(lh):
                packed = packbits_encode(ch_plane[r].tobytes())
                row_counts.append(len(packed))
                rows_packed.extend(packed)
            blob = bytearray()
            blob.extend(struct.pack(">H", 1))  # Compression: 1 = RLE PackBits
            for rc in row_counts:
                blob.extend(struct.pack(">H", rc))
            blob.extend(rows_packed)
            lyr_ch_blobs.append((c_idx, bytes(blob)))

        channel_datas.append(lyr_ch_blobs)

        # Layer Record
        layer_info.extend(struct.pack(">iiii", top, left, bottom, right))
        layer_info.extend(struct.pack(">H", 4))  # 4 channels
        for c_idx, blob in lyr_ch_blobs:
            layer_info.extend(struct.pack(">hI", c_idx, len(blob)))

        layer_info.extend(b"8BIM")
        layer_info.extend(b"norm")  # Normal blend mode
        layer_info.extend(struct.pack(">B", lyr.get("opacity", 255)))
        layer_info.extend(struct.pack(">B", 0))  # Clipping: base
        flags = 0 if lyr.get("visible", True) else 2
        layer_info.extend(struct.pack(">B", flags))
        layer_info.extend(struct.pack(">B", 0))  # Filler

        # Extra Data Field
        extra = bytearray()
        extra.extend(struct.pack(">I", 0))  # Layer mask data (0)
        extra.extend(struct.pack(">I", 0))  # Blending ranges (0)
        name_bytes = lyr["name"].encode("latin-1", errors="replace")[:255]
        name_len = len(name_bytes)
        padded_len = ((1 + name_len + 3) // 4) * 4
        extra.append(name_len)
        extra.extend(name_bytes)
        extra.extend(b"\x00" * (padded_len - 1 - name_len))

        layer_info.extend(struct.pack(">I", len(extra)))
        layer_info.extend(extra)

    # Append channel pixel data
    for lyr_ch_blobs in channel_datas:
        for _, blob in lyr_ch_blobs:
            layer_info.extend(blob)

    if len(layer_info) % 2 == 1:
        layer_info.append(0)

    layer_mask_sec = bytearray()
    layer_mask_sec.extend(struct.pack(">I", len(layer_info)))
    layer_mask_sec.extend(layer_info)
    layer_mask_sec.extend(struct.pack(">I", 0))  # Global layer mask info

    buf.extend(struct.pack(">I", len(layer_mask_sec)))
    buf.extend(layer_mask_sec)

    # 5. Merged Image Data (Composite)
    composite = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for lyr in layers:
        if not lyr.get("visible", True):
            continue
        pil_lyr = Image.fromarray(lyr["rgba"], "RGBA")
        composite.alpha_composite(pil_lyr, (lyr["left"], lyr["top"]))
    comp_arr = np.array(composite)

    buf.extend(struct.pack(">H", 1))  # RLE PackBits
    all_row_counts = bytearray()
    all_rows_data = bytearray()
    for c in range(4):
        plane = comp_arr[:, :, c]
        for r in range(height):
            packed = packbits_encode(plane[r].tobytes())
            all_row_counts.extend(struct.pack(">H", len(packed)))
            all_rows_data.extend(packed)
    buf.extend(all_row_counts)
    buf.extend(all_rows_data)

    with open(out_path, "wb") as f:
        f.write(buf)


def decompose_poster(img_path: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    layers_dir = os.path.join(out_dir, "layers")
    os.makedirs(layers_dir, exist_ok=True)

    bgr = cv2.imread(img_path)
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)

    # Estimate smooth local background using a heavily blurred version of background-like pixels
    # First, find pixels with low local gradient (flat areas)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    # Known background hue/saturation range (yellow-orange: H in [15, 32], S > 120, low gradient)
    is_yellow_bg = (hsv[:, :, 0] >= 14) & (hsv[:, :, 0] <= 34) & (hsv[:, :, 1] >= 110) & (hsv[:, :, 2] >= 140)
    flat_bg = is_yellow_bg & (grad_mag < 18)

    # Interpolate smooth background surface from flat_bg pixels via downscaled inpainting
    small_h, small_w = 92, 92
    bgr_small = cv2.resize(bgr, (small_w, small_h), interpolation=cv2.INTER_AREA)
    fg_approx_small = cv2.resize((~flat_bg).astype(np.uint8) * 255, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
    fg_approx_small = cv2.dilate(fg_approx_small, np.ones((3, 3), np.uint8), iterations=1)
    bg_est_small = cv2.inpaint(bgr_small, fg_approx_small, 5, cv2.INPAINT_TELEA)
    bg_est_small = cv2.GaussianBlur(bg_est_small, (9, 9), 0)
    bg_est = cv2.resize(bg_est_small, (w, h), interpolation=cv2.INTER_CUBIC)

    # Compare image to local estimated background in LAB
    lab_est = cv2.cvtColor(bg_est, cv2.COLOR_BGR2LAB)
    diff = np.linalg.norm(lab.astype(np.float32) - lab_est.astype(np.float32), axis=2)

    edges = cv2.Canny(gray, 45, 130)
    edges_dil = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    # Foreground mask: either far from local background OR strong edges
    fg = ((diff > 18) | (edges_dil > 0)).astype(np.uint8) * 255

    # Close tiny gaps inside outlines without merging separate text/objects
    fg_closed = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

    # Flood-fill ONLY from outer border + known interior road loop centers (avoiding car hood!)
    flood = fg_closed.copy()
    mask_ff = np.zeros((h + 2, w + 2), np.uint8)
    seed_points = []
    # Outer borders
    for sx in range(0, w, 8):
        seed_points.append((sx, 2))
        seed_points.append((sx, h - 3))
    for sy in range(0, h, 8):
        seed_points.append((2, sy))
        seed_points.append((w - 3, sy))
    # Known road interior loops (left loop & bottom-center loop)
    seed_points.extend([(155, 345), (385, 575), (415, 625)])
    for sx, sy in seed_points:
        if 0 <= sx < w and 0 <= sy < h and flood[sy, sx] == 0 and diff[sy, sx] < 14:
            cv2.floodFill(flood, mask_ff, (sx, sy), 128)
    fg_filled = np.where(flood == 128, 0, 255).astype(np.uint8)

    # Remove tiny noise specks
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg_filled, connectivity=8)
    clean_fg = np.zeros_like(fg_filled)
    for idx in range(1, num_labels):
        if stats[idx, cv2.CC_STAT_AREA] >= 60:
            clean_fg[labels == idx] = 255

    # Clean inpainted background
    inpaint_mask = cv2.dilate(clean_fg, np.ones((9, 9), np.uint8), iterations=1)
    bg_clean_bgr = cv2.inpaint(bgr, inpaint_mask, 9, cv2.INPAINT_TELEA)
    bg_blur = cv2.GaussianBlur(bg_clean_bgr, (25, 25), 0)
    alpha_blend = (cv2.GaussianBlur(inpaint_mask.astype(np.float32), (17, 17), 0) / 255.0)[:, :, None]
    bg_final_bgr = (bg_clean_bgr * (1 - alpha_blend * 0.75) + bg_blur * (alpha_blend * 0.75)).astype(np.uint8)
    bg_final_rgba = cv2.cvtColor(bg_final_bgr, cv2.COLOR_BGR2RGBA)

    bg_path = os.path.join(layers_dir, "01_Background_Clean.png")
    Image.fromarray(bg_final_rgba).save(bg_path)

    # Extract connected components as candidate object/text layers
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(clean_fg, connectivity=8)
    boxes = []
    for idx in range(1, num_labels):
        x, y, bw, bh, area = stats[idx]
        if area < 150:
            continue
        boxes.append((idx, x, y, bw, bh, area))

    # Group nearby boxes into semantic design layers based on spatial regions
    # Region definitions tailored for layered poster decomposition (auto-grouped by proximity)
    def classify_box(x, y, bw, bh):
        cx, cy = x + bw / 2, y + bh / 2
        if cy < 95 and cx > 340:
            return "Text_Top_Arabic"
        if 80 <= cy <= 215 and cx < 420:
            return "Logo_ONEWAY"
        if 200 <= cy <= 290 and cx < 370:
            return "Text_Mid_Arabic"
        if cy > 640 and cx > 420:
            return "Text_Phone_Number"
        if cy < 120 and cx > 620:
            return "Decor_Pin_TopRight"
        if 390 <= cy <= 490 and cx < 90:
            return "Decor_Emoji_Left"
        return "Main_Visual_Hero"

    grouped_masks = {}
    for idx, x, y, bw, bh, area in boxes:
        grp = classify_box(x, y, bw, bh)
        if grp not in grouped_masks:
            grouped_masks[grp] = np.zeros((h, w), np.uint8)
        grouped_masks[grp][labels == idx] = 255

    # Separate Phone Number (bottom-right: x >= 432, y >= 655) from Taxi/Road before hero grouping
    phone_num_mask = np.zeros((h, w), np.uint8)
    phone_num_mask[655:h, 432:626] = clean_fg[655:h, 432:626]
    if np.sum(phone_num_mask > 0) > 100:
        grouped_masks["Text_Phone_Number"] = phone_num_mask
        if "Main_Visual_Hero" in grouped_masks:
            grouped_masks["Main_Visual_Hero"] = cv2.subtract(grouped_masks["Main_Visual_Hero"], phone_num_mask)

    # Keep Taxi + Road + Hand/Phone as clean foreground hero (or split cleanly if non-overlapping)
    if "Main_Visual_Hero" in grouped_masks:
        grouped_masks["Object_Taxi_Road"] = grouped_masks.pop("Main_Visual_Hero")

    layer_order = [
        ("01_Background_Clean", None),
        ("Decor_Pin_TopRight", "02_Decor_Pin"),
        ("Decor_Emoji_Left", "03_Decor_Emoji"),
        ("Object_Taxi_Road", "04_Object_Taxi_Road"),
        ("Object_Hand_Phone", "05_Object_Hand_Phone"),
        ("Main_Visual_Hero", "04_Main_Visual_Hero"),
        ("Text_Top_Arabic", "06_Text_Top_Arabic"),
        ("Logo_ONEWAY", "07_Logo_ONEWAY"),
        ("Text_Mid_Arabic", "08_Text_Mid_Arabic"),
        ("Text_Phone_Number", "09_Text_Phone_Number"),
    ]

    psd_layers = [{
        "name": "01_Background_Clean",
        "left": 0, "top": 0, "right": w, "bottom": h,
        "rgba": bg_final_rgba,
        "opacity": 255,
        "visible": True,
    }]

    manifest_layers = [{
        "id": "layer_01",
        "name": "01_Background_Clean",
        "type": "background",
        "file": "layers/01_Background_Clean.png",
        "x": 0, "y": 0, "width": w, "height": h,
        "visible": True, "opacity": 1.0,
    }]

    idx_counter = 2
    for key, out_name in layer_order:
        if key == "01_Background_Clean" or key not in grouped_masks:
            continue
        m = grouped_masks[key]
        ys, xs = np.where(m > 0)
        if len(xs) == 0:
            continue
        x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
        # Soften edges slightly (1px feather)
        alpha = cv2.GaussianBlur(m[y1:y2, x1:x2], (3, 3), 0)
        crop_rgb = rgb[y1:y2, x1:x2]
        rgba_crop = np.dstack([crop_rgb, alpha])

        fname = f"{out_name}.png"
        fpath = os.path.join(layers_dir, fname)
        Image.fromarray(rgba_crop, "RGBA").save(fpath)

        psd_layers.append({
            "name": out_name,
            "left": x1, "top": y1, "right": x2, "bottom": y2,
            "rgba": rgba_crop,
            "opacity": 255,
            "visible": True,
        })

        ltype = "text" if ("Text_" in out_name or "Logo_" in out_name) else "object"
        manifest_layers.append({
            "id": f"layer_{idx_counter:02d}",
            "name": out_name,
            "type": ltype,
            "file": f"layers/{fname}",
            "x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1,
            "visible": True, "opacity": 1.0,
        })
        idx_counter += 1

    psd_path = os.path.join(out_dir, "output_layers.psd")
    write_psd(w, h, psd_layers, psd_path)

    manifest = {
        "width": w,
        "height": h,
        "source": os.path.basename(img_path),
        "psd_file": "output_layers.psd",
        "layers": manifest_layers,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"DONE: {len(manifest_layers)} layers extracted -> {psd_path}")
    for l in manifest_layers:
        print(f"  - {l['name']} ({l['type']}) [{l['x']},{l['y']} {l['width']}x{l['height']}]")


if __name__ == "__main__":
    decompose_poster(
        r"C:/Users/BUM/.gemini/antigravity/brain/7a3bd732-b5a7-4da2-8ae9-7603555447fd/.user_uploaded/media_1794885806500_463cbbd0.jpg",
        r"d:\AI\TESTER\redesign_studio"
    )
