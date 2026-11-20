import os
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw

OUT_DIR = r"d:\AI\TESTER\redesign_studio"
LAYERS_DIR = os.path.join(OUT_DIR, "layers_ai")
os.makedirs(LAYERS_DIR, exist_ok=True)

TAXI_SRC = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\ai_taxi_full_clean_1794887216495.jpg"
ROAD_SRC = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\ai_road_full_v2_1794887217811.jpg"
PHONE_SRC = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\hand_iphone_final_white_1794887306066.jpg"


def extract_from_white_bg(img_path: str, target_box: tuple, canvas_size=(736, 736), white_thresh=242):
    """Flood-fill outer white background from borders, keep interior whites (phone screen, headlights) intact."""
    bgr = cv2.imread(img_path)
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Outer white mask via floodfill from all 4 borders
    is_white = ((bgr[:, :, 0] > white_thresh) & (bgr[:, :, 1] > white_thresh) & (bgr[:, :, 2] > white_thresh)).astype(np.uint8) * 255
    flood = np.zeros((h + 2, w + 2), np.uint8)
    bg_mask = is_white.copy()
    for sx in range(0, w, 10):
        if bg_mask[2, sx] == 255:
            cv2.floodFill(bg_mask, flood, (sx, 2), 128)
        if bg_mask[h - 3, sx] == 255:
            cv2.floodFill(bg_mask, flood, (sx, h - 3), 128)
    for sy in range(0, h, 10):
        if bg_mask[sy, 2] == 255:
            cv2.floodFill(bg_mask, flood, (2, sy), 128)
        if bg_mask[sy, w - 3] == 255:
            cv2.floodFill(bg_mask, flood, (w - 3, sy), 128)

    fg_mask = np.where(bg_mask == 128, 0, 255).astype(np.uint8)
    # Remove tiny specks
    num_l, labels, stats, _ = cv2.connectedComponentsWithStats(fg_mask, 8)
    clean_fg = np.zeros_like(fg_mask)
    for i in range(1, num_l):
        if stats[i, cv2.CC_STAT_AREA] > 200:
            clean_fg[labels == i] = 255

    # Erode 1px to remove white fringe, then 3px feather
    clean_fg = cv2.erode(clean_fg, np.ones((3, 3), np.uint8), iterations=1)
    alpha = cv2.GaussianBlur(clean_fg, (3, 3), 0)

    ys, xs = np.where(clean_fg > 0)
    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    crop_rgba = np.dstack([rgb[y1:y2, x1:x2], alpha[y1:y2, x1:x2]])

    # Fit into target_box (tx, ty, tw, th) preserving aspect ratio
    tx, ty, tw, th = target_box
    pil_crop = Image.fromarray(crop_rgba, "RGBA")
    cw, ch = pil_crop.size
    scale = min(tw / cw, th / ch)
    nw, nh = int(round(cw * scale)), int(round(ch * scale))
    pil_resized = pil_crop.resize((nw, nh), Image.Resampling.LANCZOS)
    return pil_resized, tx, ty, nw, nh


def extract_road_from_yellow_bg(img_path: str, target_size=(736, 736)):
    bgr = cv2.imread(img_path)
    bgr = cv2.resize(bgr, target_size, interpolation=cv2.INTER_AREA)
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    is_yellow = (hsv[:, :, 0] >= 14) & (hsv[:, :, 0] <= 34) & (hsv[:, :, 1] >= 110) & (hsv[:, :, 2] >= 140)
    flat_bg = is_yellow & (grad_mag < 18)

    small = cv2.resize(bgr, (92, 92), interpolation=cv2.INTER_AREA)
    fg_s = cv2.resize((~flat_bg).astype(np.uint8) * 255, (92, 92), interpolation=cv2.INTER_NEAREST)
    fg_s = cv2.dilate(fg_s, np.ones((3, 3), np.uint8), iterations=1)
    bg_s = cv2.GaussianBlur(cv2.inpaint(small, fg_s, 5, cv2.INPAINT_TELEA), (9, 9), 0)
    bg_est = cv2.resize(bg_s, (w, h), interpolation=cv2.INTER_CUBIC)

    diff = np.linalg.norm(lab.astype(np.float32) - cv2.cvtColor(bg_est, cv2.COLOR_BGR2LAB).astype(np.float32), axis=2)
    edges = cv2.dilate(cv2.Canny(gray, 40, 120), np.ones((3, 3), np.uint8), iterations=1)
    fg = ((diff > 16) | (edges > 0)).astype(np.uint8) * 255
    fg_closed = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

    flood = fg_closed.copy()
    mask_ff = np.zeros((h + 2, w + 2), np.uint8)
    seeds = []
    for sx in range(0, w, 8):
        seeds.extend([(sx, 2), (sx, h - 3)])
    for sy in range(0, h, 8):
        seeds.extend([(2, sy), (w - 3, sy)])
    # Automatically detect all flat yellow-bg pockets (including enclosed road loops!)
    flat_bg_pockets = (is_yellow & (diff < 15) & (grad_mag < 12)).astype(np.uint8) * 255
    n_p, p_lbl, p_stats, p_cent = cv2.connectedComponentsWithStats(flat_bg_pockets, 8)
    for i in range(1, n_p):
        if p_stats[i, cv2.CC_STAT_AREA] >= 60:
            cx, cy = int(p_cent[i][0]), int(p_cent[i][1])
            seeds.append((cx, cy))
    for sx, sy in seeds:
        if 0 <= sx < w and 0 <= sy < h and flood[sy, sx] == 0 and diff[sy, sx] < 16:
            cv2.floodFill(flood, mask_ff, (sx, sy), 128)
    fg_filled = np.where(flood == 128, 0, 255).astype(np.uint8)

    num_l, labels, stats, _ = cv2.connectedComponentsWithStats(fg_filled, 8)
    clean_fg = np.zeros_like(fg_filled)
    for i in range(1, num_l):
        if stats[i, cv2.CC_STAT_AREA] > 250:
            clean_fg[labels == i] = 255

    # Erode 2px to eliminate yellow background halo, then 3px soft feather
    clean_fg = cv2.erode(clean_fg, np.ones((3, 3), np.uint8), iterations=1)
    alpha = cv2.GaussianBlur(clean_fg, (3, 3), 0)
    # Keep interior 100% opaque
    interior = cv2.erode(clean_fg, np.ones((5, 5), np.uint8), iterations=1)
    alpha = np.maximum(alpha, interior)

    # Also build silky-smooth clean background from bg_est (zero seams!)
    bg_smooth = cv2.GaussianBlur(bg_est, (101, 101), 0)
    bg_smooth_rgba = cv2.cvtColor(bg_smooth, cv2.COLOR_BGR2RGBA)
    Image.fromarray(bg_smooth_rgba, "RGBA").save(os.path.join(LAYERS_DIR, "01_Background_Clean.png"))

    ys, xs = np.where(clean_fg > 0)
    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    crop_rgba = np.dstack([rgb[y1:y2, x1:x2], alpha[y1:y2, x1:x2]])
    return Image.fromarray(crop_rgba, "RGBA"), x1, y1, x2 - x1, y2 - y1


def make_checkerboard(w, h, tile=16):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            c = 210 if ((x // tile) + (y // tile)) % 2 == 0 else 160
            arr[y:y + tile, x:x + tile] = c
    return Image.fromarray(arr, "RGB")


def main():
    # 1. Extract Road
    road_img, rx, ry, rw, rh = extract_road_from_yellow_bg(ROAD_SRC)
    road_img.save(os.path.join(LAYERS_DIR, "04_Object_Road_3D.png"))

    # 2. Extract Taxi (placed at original poster coordinates x=212, y=202, width~445, height~275)
    taxi_img, tx, ty, tw, th = extract_from_white_bg(TAXI_SRC, (212, 202, 445, 275))
    taxi_img.save(os.path.join(LAYERS_DIR, "05_Object_Taxi_Car.png"))

    # 3. Extract Hand + iPhone (placed at bottom-right x=520, y=340, width~216, height~396)
    phone_img, px, py, pw, ph = extract_from_white_bg(PHONE_SRC, (520, 340, 216, 396))
    phone_img.save(os.path.join(LAYERS_DIR, "06_Object_Hand_Phone.png"))

    # Update manifest_ai.json combining clean deep layers + AI-reconstructed objects
    with open(os.path.join(OUT_DIR, "manifest_deep.json"), "r", encoding="utf-8") as f:
        deep = json.load(f)

    new_layers = []
    for l in deep["layers"]:
        if l["name"] == "01_Background_Clean":
            new_layers.append({"name": l["name"], "type": "background", "file": "layers_ai/01_Background_Clean.png", "x": 0, "y": 0, "width": 736, "height": 736})
        elif l["name"] == "04_Object_Road_3D":
            new_layers.append({"name": l["name"], "type": "object", "file": "layers_ai/04_Object_Road_3D.png", "x": rx, "y": ry, "width": rw, "height": rh})
        elif l["name"] == "05_Object_Taxi_Car":
            new_layers.append({"name": l["name"], "type": "object", "file": "layers_ai/05_Object_Taxi_Car.png", "x": tx, "y": ty, "width": tw, "height": th})
        elif l["name"] == "06_Object_Hand_Phone":
            new_layers.append({"name": l["name"], "type": "object", "file": "layers_ai/06_Object_Hand_Phone.png", "x": px, "y": py, "width": pw, "height": ph})
        else:
            new_layers.append(l)

    with open(os.path.join(OUT_DIR, "manifest_ai.json"), "w", encoding="utf-8") as f:
        json.dump({"width": 736, "height": 736, "layers": new_layers}, f, ensure_ascii=False, indent=2)

    # Render QA Contact Sheet (2x2 grid on checkerboard)
    cell = 420
    sheet = Image.new("RGB", (cell * 2, cell * 2), (30, 30, 35))
    items = [
        ("01_Background_Clean", Image.open(os.path.join(LAYERS_DIR, "01_Background_Clean.png")).convert("RGBA")),
        ("04_Object_Road_3D", road_img),
        ("05_Object_Taxi_Car", taxi_img),
        ("06_Object_Hand_Phone", phone_img),
    ]
    draw = ImageDraw.Draw(sheet)
    for idx, (label, im) in enumerate(items):
        gx, gy = (idx % 2) * cell, (idx // 2) * cell
        cb = make_checkerboard(cell, cell).convert("RGBA")
        scale = min((cell - 40) / im.width, (cell - 50) / im.height)
        nw, nh = int(im.width * scale), int(im.height * scale)
        im_r = im.resize((nw, nh), Image.Resampling.LANCZOS)
        cb.alpha_composite(im_r, ((cell - nw) // 2, 35 + (cell - 40 - nh) // 2))
        sheet.paste(cb.convert("RGB"), (gx, gy))
        draw.rectangle([gx, gy, gx + cell, gy + 30], fill=(20, 20, 25))
        draw.text((gx + 10, gy + 8), label, fill=(250, 204, 21))

    qa_path = os.path.join(OUT_DIR, "qa_preview_sheet.png")
    sheet.save(qa_path)
    print("EXTRACTED AI LAYERS & QA SHEET:", qa_path)


if __name__ == "__main__":
    main()
