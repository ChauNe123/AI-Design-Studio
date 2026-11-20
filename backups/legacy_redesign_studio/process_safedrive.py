import os
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ORIG_PATH = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\.user_uploaded\media_1794887864929_1ce955d2.webp"
BG_AI_PATH = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\clean_green_poster_background_v2_1794887996985.jpg"
DRIVER_AI_PATH = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\driver_circle_badge_clean_1794887988299.jpg"
PHONE_AI_PATH = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\safedrive_phone_isolated_1794887977458.jpg"

OUT_DIR = r"d:\AI\TESTER\redesign_studio\safedrive_fullhd"
LAYERS_DIR = os.path.join(OUT_DIR, "layers")
os.makedirs(LAYERS_DIR, exist_ok=True)

TARGET_W, TARGET_H = 1530, 2048  # 2x Full HD Portrait


def sharpen_fullhd(pil_img: Image.Image, radius=1.4, percent=135, threshold=2) -> Image.Image:
    """Enhance sharpness & clarity for Full HD export."""
    if pil_img.mode == "RGBA":
        r, g, b, a = pil_img.split()
        rgb = Image.merge("RGB", (r, g, b)).filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))
        r2, g2, b2 = rgb.split()
        return Image.merge("RGBA", (r2, g2, b2, a))
    return pil_img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def extract_from_white_bg(img_path: str, target_box: tuple, white_thresh=240):
    bgr = cv2.imread(img_path)
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
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
    num_l, labels, stats, _ = cv2.connectedComponentsWithStats(fg_mask, 8)
    clean_fg = np.zeros_like(fg_mask)
    for i in range(1, num_l):
        if stats[i, cv2.CC_STAT_AREA] > 300:
            clean_fg[labels == i] = 255

    clean_fg = cv2.erode(clean_fg, np.ones((3, 3), np.uint8), iterations=1)
    alpha = cv2.GaussianBlur(clean_fg, (3, 3), 0)
    interior = cv2.erode(clean_fg, np.ones((5, 5), np.uint8), iterations=1)
    alpha = np.maximum(alpha, interior)

    ys, xs = np.where(clean_fg > 0)
    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    crop_rgba = np.dstack([rgb[y1:y2, x1:x2], alpha[y1:y2, x1:x2]])
    pil_crop = Image.fromarray(crop_rgba, "RGBA")

    tx, ty, tw, th = target_box
    cw, ch = pil_crop.size
    scale = min(tw / cw, th / ch)
    nw, nh = int(round(cw * scale)), int(round(ch * scale))
    pil_resized = pil_crop.resize((nw, nh), Image.Resampling.LANCZOS)
    pil_sharp = sharpen_fullhd(pil_resized, radius=1.2, percent=125)
    return pil_sharp, tx, ty, nw, nh


def extract_region_2x(orig_2x_bgr: np.ndarray, box_1x: tuple, bg_2x_bgr: np.ndarray, threshold=20, keep_white_card=False):
    """Extract a sharp 2x layer by comparing against clean background (or local white/dark)."""
    x1, y1, x2, y2 = [v * 2 for v in box_1x]
    crop_bgr = orig_2x_bgr[y1:y2, x1:x2]
    crop_rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
    if keep_white_card:
        # Clean rounded-rectangle mask at exact 2x card bounds (zero holes, zero background slivers)
        cw_2x, ch_2x = x2 - x1, y2 - y1
        pil_mask = Image.new("L", (cw_2x, ch_2x), 0)
        d = ImageDraw.Draw(pil_mask)
        d.rounded_rectangle([2, 2, cw_2x - 3, ch_2x - 3], radius=24, fill=255)
        rgba = np.dstack([crop_rgb, np.array(pil_mask)])
        pil_im = sharpen_fullhd(Image.fromarray(rgba, "RGBA"), radius=1.3, percent=135)
        return pil_im, x1, y1, cw_2x, ch_2x
    else:
        bg_crop = bg_2x_bgr[y1:y2, x1:x2]
        diff = np.linalg.norm(crop_bgr.astype(np.float32) - bg_crop.astype(np.float32), axis=2)
        mask = (diff > threshold).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)
        mask = cv2.erode(mask, np.ones((3, 3), np.uint8), iterations=1)

    alpha = cv2.GaussianBlur(mask, (3, 3), 0)
    interior = cv2.erode(mask, np.ones((3, 3), np.uint8), iterations=1)
    alpha = np.maximum(alpha, interior)
    rgba = np.dstack([crop_rgb, alpha])
    pil_im = sharpen_fullhd(Image.fromarray(rgba, "RGBA"), radius=1.3, percent=135)
    return pil_im, x1, y1, x2 - x1, y2 - y1


def make_checkerboard(w, h, tile=20):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            c = 215 if ((x // tile) + (y // tile)) % 2 == 0 else 165
            arr[y:y + tile, x:x + tile] = c
    return Image.fromarray(arr, "RGB")


def main():
    # 1. Prepare Full HD Clean Background (1530x2048)
    bg_pil = Image.open(BG_AI_PATH).convert("RGB").resize((TARGET_W, TARGET_H), Image.Resampling.LANCZOS)
    bg_pil = sharpen_fullhd(bg_pil, radius=1.0, percent=110)
    bg_pil.save(os.path.join(LAYERS_DIR, "01_Background_Clean.png"))
    bg_2x_bgr = cv2.cvtColor(np.array(bg_pil), cv2.COLOR_RGB2BGR)

    # 2. Upscale original poster to 2x (1530x2048) with bilateral denoise + Lanczos + sharpen
    orig_bgr = cv2.imread(ORIG_PATH)
    orig_denoise = cv2.bilateralFilter(orig_bgr, 5, 25, 25)
    orig_2x_bgr = cv2.resize(orig_denoise, (TARGET_W, TARGET_H), interpolation=cv2.INTER_LANCZOS4)

    manifest = []
    manifest.append({
        "name": "01_Background_Clean", "group": "1_Background", "file": "layers/01_Background_Clean.png",
        "x": 0, "y": 0, "width": TARGET_W, "height": TARGET_H, "hidden": False
    })

    # 3. Extract AI-isolated Full HD Objects
    driver_im, dx, dy, dw, dh = extract_from_white_bg(DRIVER_AI_PATH, (124, 720, 488, 488))
    driver_im.save(os.path.join(LAYERS_DIR, "03_Circle_Driver_Photo.png"))
    manifest.append({
        "name": "03_Circle_Driver_Photo", "group": "2_Objects_&_Cards", "file": "layers/03_Circle_Driver_Photo.png",
        "x": dx, "y": dy, "width": dw, "height": dh, "hidden": False
    })

    phone_im, px, py, pw, ph = extract_from_white_bg(PHONE_AI_PATH, (600, 748, 846, 560))
    phone_im.save(os.path.join(LAYERS_DIR, "04_Phone_Mockup.png"))
    manifest.append({
        "name": "04_Phone_Mockup", "group": "2_Objects_&_Cards", "file": "layers/04_Phone_Mockup.png",
        "x": px, "y": py, "width": pw, "height": ph, "hidden": False
    })

    # 4. Extract Logo, 4 Feature Cards, and Footer Store Icons at 2x Full HD
    extractions = [
        ("02_Logo_SafeDrive", "2_Objects_&_Cards", (65, 72, 360, 152), 42, False, False),
        ("05_Card_CanhBaoVaCham", "2_Objects_&_Cards", (213, 344, 424, 423), 18, True, False),
        ("06_Card_CameraHanhTrinh", "2_Objects_&_Cards", (483, 336, 692, 406), 18, True, False),
        ("07_Card_DanDuongGPS", "2_Objects_&_Cards", (155, 748, 372, 824), 22, True, False),
        ("08_Card_CanhBaoTocDo", "2_Objects_&_Cards", (472, 748, 682, 824), 22, True, False),
        ("09_Icons_Store_Footer", "2_Objects_&_Cards", (296, 945, 365, 982), 35, False, False),
        # Original texts (kept hidden for reference)
        ("10_Text_TopRight_Orig", "3_Original_Texts_Hidden", (450, 75, 705, 145), 22, False, True),
        ("11_Text_Hero_SafeDrive_Orig", "3_Original_Texts_Hidden", (185, 165, 585, 225), 20, False, True),
        ("12_Text_Hero_Sub_Orig", "3_Original_Texts_Hidden", (90, 222, 680, 305), 22, False, True),
        ("13_Text_Footer_Left_Orig", "3_Original_Texts_Hidden", (85, 928, 298, 982), 30, False, True),
        ("14_Text_Footer_Right_Orig", "3_Original_Texts_Hidden", (405, 950, 685, 982), 30, False, True),
    ]

    for name, grp, box, thr, keep_card, hidden in extractions:
        im, lx, ly, lw, lh = extract_region_2x(orig_2x_bgr, box, bg_2x_bgr, threshold=thr, keep_white_card=keep_card)
        fname = f"{name}.png"
        im.save(os.path.join(LAYERS_DIR, fname))
        manifest.append({
            "name": name, "group": grp, "file": f"layers/{fname}",
            "x": lx, "y": ly, "width": lw, "height": lh, "hidden": hidden
        })

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"width": TARGET_W, "height": TARGET_H, "layers": manifest}, f, ensure_ascii=False, indent=2)

    # 5. Render QA Checkerboard Sheet (2x3 grid)
    cell_w, cell_h = 460, 460
    qa_items = [
        ("01_Background_Clean", bg_pil.convert("RGBA")),
        ("02_Logo_SafeDrive", Image.open(os.path.join(LAYERS_DIR, "02_Logo_SafeDrive.png"))),
        ("03_Circle_Driver_Photo", driver_im),
        ("04_Phone_Mockup", phone_im),
        ("05_Card_CanhBaoVaCham", Image.open(os.path.join(LAYERS_DIR, "05_Card_CanhBaoVaCham.png"))),
        ("07_Card_DanDuongGPS", Image.open(os.path.join(LAYERS_DIR, "07_Card_DanDuongGPS.png"))),
    ]
    sheet = Image.new("RGB", (cell_w * 3, cell_h * 2), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, (label, im) in enumerate(qa_items):
        gx, gy = (idx % 3) * cell_w, (idx // 3) * cell_h
        cb = make_checkerboard(cell_w, cell_h).convert("RGBA")
        scale = min((cell_w - 30) / im.width, (cell_h - 45) / im.height)
        nw, nh = int(im.width * scale), int(im.height * scale)
        im_r = im.resize((nw, nh), Image.Resampling.LANCZOS)
        cb.alpha_composite(im_r, ((cell_w - nw) // 2, 34 + (cell_h - 40 - nh) // 2))
        sheet.paste(cb.convert("RGB"), (gx, gy))
        draw.rectangle([gx, gy, gx + cell_w, gy + 28], fill=(18, 18, 22))
        draw.text((gx + 10, gy + 7), label, fill=(74, 222, 128))

    qa_path = os.path.join(OUT_DIR, "safedrive_qa_sheet.png")
    sheet.save(qa_path)
    print(f"SAFEDRIVE FULL HD ({TARGET_W}x{TARGET_H}): {len(manifest)} layers -> {qa_path}")


if __name__ == "__main__":
    main()
