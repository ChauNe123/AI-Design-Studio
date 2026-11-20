import os
import json
import math
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ORIG_PATH = r"C:\Users\BUM/.gemini/antigravity/brain/7a3bd732-b5a7-4da2-8ae9-7603555447fd/.user_uploaded/media_1794901983917_6d6af116.jpg"
OUT_DIR = r"d:\AI\TESTER\redesign_studio\canva_fullhd"
LAYERS_DIR = os.path.join(OUT_DIR, "layers")
os.makedirs(LAYERS_DIR, exist_ok=True)

TARGET_W, TARGET_H = 2048, 2048  # 2x Full HD Square


def sharpen_fullhd(pil_img: Image.Image, radius=1.3, percent=130, threshold=2) -> Image.Image:
    if pil_img.mode == "RGBA":
        r, g, b, a = pil_img.split()
        rgb = Image.merge("RGB", (r, g, b)).filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))
        r2, g2, b2 = rgb.split()
        return Image.merge("RGBA", (r2, g2, b2, a))
    return pil_img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def save_crop(rgb: np.ndarray, mask: np.ndarray, fname: str, feather=3, pure_black_fill=False):
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    alpha = cv2.GaussianBlur(mask[y1:y2, x1:x2], (feather, feather), 0) if feather > 1 else mask[y1:y2, x1:x2]
    interior = cv2.erode(mask[y1:y2, x1:x2], np.ones((3, 3), np.uint8), iterations=1)
    alpha = np.maximum(alpha, interior)
    if pure_black_fill:
        sub = mask[y1:y2, x1:x2]
        sh, sw = sub.shape
        up = cv2.resize(sub, (sw * 4, sh * 4), interpolation=cv2.INTER_CUBIC)
        up_blur = cv2.GaussianBlur(up, (9, 9), 0)
        _, up_sharp = cv2.threshold(up_blur, 127, 255, cv2.THRESH_BINARY)
        smooth_alpha = cv2.resize(up_sharp, (sw, sh), interpolation=cv2.INTER_AREA)
        crop_rgb = np.zeros((y2 - y1, x2 - x1, 3), dtype=np.uint8)
        rgba = np.dstack([crop_rgb, smooth_alpha])
        pil_im = Image.fromarray(rgba, "RGBA")
    else:
        rgba = np.dstack([rgb[y1:y2, x1:x2], alpha])
        pil_im = sharpen_fullhd(Image.fromarray(rgba, "RGBA"))
    pil_im.save(os.path.join(LAYERS_DIR, fname))
    return {"file": f"layers/{fname}", "x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}


def draw_vector_camera(size=72):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sw = int(S * 0.055)
    # Main body rounded rect
    d.rounded_rectangle([int(S*0.08), int(S*0.24), int(S*0.92), int(S*0.86)], radius=int(S*0.09), outline=(0, 0, 0, 255), width=sw)
    # Top viewfinder bump
    d.polygon([(int(S*0.32), int(S*0.24)), (int(S*0.39), int(S*0.13)), (int(S*0.61), int(S*0.13)), (int(S*0.68), int(S*0.24))], fill=(0, 0, 0, 0), outline=(0, 0, 0, 255), width=sw)
    # Erase bottom edge of trapezoid so it merges cleanly
    d.rectangle([int(S*0.34), int(S*0.24) - sw, int(S*0.66), int(S*0.24) + sw], fill=(0, 0, 0, 0))
    # Lens outer circle & inner filled dot
    cx, cy = int(S * 0.5), int(S * 0.55)
    r1, r2 = int(S * 0.18), int(S * 0.09)
    d.ellipse([cx - r1, cy - r1, cx + r1, cy + r1], outline=(0, 0, 0, 255), width=sw)
    d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(0, 0, 0, 255))
    # Flash dot
    fx, fy, fr = int(S * 0.22), int(S * 0.37), int(S * 0.04)
    d.ellipse([fx - fr, fy - fr, fx + fr, fy + fr], outline=(0, 0, 0, 255), width=int(sw * 0.8))
    return im.resize((size, size), Image.Resampling.LANCZOS)


def draw_vector_speed(size=72):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sw = int(S * 0.06)
    cx, cy, r = int(S * 0.58), int(S * 0.56), int(S * 0.32)
    d.arc([cx - r, cy - r, cx + r, cy + r], start=135, end=405, fill=(0, 0, 0, 255), width=sw)
    # Top button
    d.line([(cx, cy - r - int(S*0.09)), (cx, cy - r)], fill=(0, 0, 0, 255), width=sw)
    d.line([(cx - int(S*0.08), cy - r - int(S*0.09)), (cx + int(S*0.08), cy - r - int(S*0.09))], fill=(0, 0, 0, 255), width=sw)
    # Needle
    d.ellipse([cx - int(S*0.05), cy - int(S*0.05), cx + int(S*0.05), cy + int(S*0.05)], fill=(0, 0, 0, 255))
    d.line([(cx, cy), (cx + int(S*0.18), cy - int(S*0.16))], fill=(0, 0, 0, 255), width=sw)
    # Speed lines on left
    for idx, y_off in enumerate([-0.12, 0.0, 0.12]):
        yy = int(cy + S * y_off)
        x_start = int(S * (0.08 + idx * 0.04))
        d.line([(x_start, yy), (int(S * 0.24), yy)], fill=(0, 0, 0, 255), width=int(sw * 0.85))
    return im.resize((size, size), Image.Resampling.LANCZOS)


def draw_pin(d, cx, cy, r, sw):
    # Teardrop pin: circle top + triangle bottom
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 0, 0, 255), width=sw)
    pts = [(cx - int(r * 0.88), cy + int(r * 0.45)), (cx, cy + int(r * 1.85)), (cx + int(r * 0.88), cy + int(r * 0.45))]
    d.line([pts[0], pts[1]], fill=(0, 0, 0, 255), width=sw)
    d.line([pts[1], pts[2]], fill=(0, 0, 0, 255), width=sw)
    ir = int(r * 0.42)
    d.ellipse([cx - ir, cy - ir, cx + ir, cy + ir], fill=(0, 0, 0, 255))


def draw_vector_distance(size=72):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sw = int(S * 0.05)
    draw_pin(d, int(S * 0.24), int(S * 0.26), int(S * 0.14), sw)
    draw_pin(d, int(S * 0.78), int(S * 0.68), int(S * 0.14), sw)
    # Smooth cubic Bezier S-curve connecting the two pins
    p0 = (int(S * 0.36), int(S * 0.50))
    p1 = (int(S * 0.80), int(S * 0.48))
    p2 = (int(S * 0.06), int(S * 0.88))
    p3 = (int(S * 0.64), int(S * 0.92))
    curve = []
    for i in range(65):
        t = i / 64.0
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        curve.append((x, y))
    d.line(curve, fill=(0, 0, 0, 255), width=int(sw * 0.9), joint="curve")
    return im.resize((size, size), Image.Resampling.LANCZOS)


def draw_vector_gps(size=72):
    S = size * 4
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    sw = int(S * 0.055)
    draw_pin(d, int(S * 0.50), int(S * 0.34), int(S * 0.22), sw)
    d.arc([int(S*0.20), int(S*0.68), int(S*0.80), int(S*0.90)], start=-20, end=200, fill=(0, 0, 0, 255), width=sw)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def make_checkerboard(w, h, tile=24):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            c = 215 if ((x // tile) + (y // tile)) % 2 == 0 else 165
            arr[y:y + tile, x:x + tile] = c
    return Image.fromarray(arr, "RGB")


def main():
    bgr_1x = cv2.imread(ORIG_PATH)
    bgr_clean = cv2.bilateralFilter(bgr_1x, 5, 25, 25)
    bgr = cv2.resize(bgr_clean, (TARGET_W, TARGET_H), interpolation=cv2.INTER_LANCZOS4)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    is_green = ((hsv[:, :, 0] >= 55) & (hsv[:, :, 0] <= 90) & (hsv[:, :, 1] >= 120) & (hsv[:, :, 2] >= 120)).astype(np.uint8) * 255

    # 1. Black Corner Shape
    is_black = ((bgr[:, :, 0] < 28) & (bgr[:, :, 1] < 28) & (bgr[:, :, 2] < 28)).astype(np.uint8) * 255
    black_zone = np.zeros((TARGET_H, TARGET_W), np.uint8)
    black_zone[:1120, :1420] = is_black[:1120, :1420]
    black_closed = cv2.morphologyEx(black_zone, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8), iterations=2)
    num_l, labels, stats, _ = cv2.connectedComponentsWithStats(black_closed, 8)
    best_i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    blob_mask = np.where(labels == best_i, 255, 0).astype(np.uint8)
    ff = blob_mask.copy()
    ff_m = np.zeros((TARGET_H + 2, TARGET_W + 2), np.uint8)
    cv2.floodFill(ff, ff_m, (TARGET_W - 5, TARGET_H - 5), 128)
    blob_solid = np.where(ff == 128, 0, 255).astype(np.uint8)
    ys_b, xs_b = np.where(blob_solid > 0)
    bx1, by1, bx2, by2 = int(xs_b.min()), int(ys_b.min()), int(xs_b.max()) + 1, int(ys_b.max()) + 1
    blob_alpha = cv2.GaussianBlur(blob_solid[by1:by2, bx1:bx2], (5, 5), 0)
    blob_rgba = np.zeros((by2 - by1, bx2 - bx1, 4), dtype=np.uint8)
    blob_rgba[:, :, 3] = blob_alpha
    Image.fromarray(blob_rgba, "RGBA").save(os.path.join(LAYERS_DIR, "02_Shape_Black_Corner.png"))

    # 2. Driver Photo (protect driver's grey/greenish shirt at bottom-left x>=936, y>=1450!)
    is_vivid_green = ((hsv[:, :, 0] >= 55) & (hsv[:, :, 0] <= 90) & (hsv[:, :, 1] >= 150) & (hsv[:, :, 2] >= 140)).astype(np.uint8) * 255
    is_vivid_green[1450:TARGET_H, 945:TARGET_W] = 0
    non_green = cv2.bitwise_not(is_vivid_green)
    non_green = cv2.bitwise_and(non_green, cv2.bitwise_not(blob_solid))
    photo_zone = np.zeros((TARGET_H, TARGET_W), np.uint8)
    photo_zone[380:TARGET_H, 920:TARGET_W] = non_green[380:TARGET_H, 920:TARGET_W]
    photo_zone = cv2.morphologyEx(photo_zone, cv2.MORPH_CLOSE, np.ones((11, 11), np.uint8), iterations=2)
    num_p, p_lbl, p_stats, _ = cv2.connectedComponentsWithStats(photo_zone, 8)
    best_p = 1 + int(np.argmax(p_stats[1:, cv2.CC_STAT_AREA]))
    photo_mask = np.where(p_lbl == best_p, 255, 0).astype(np.uint8)
    ff_p = photo_mask.copy()
    ff_pm = np.zeros((TARGET_H + 2, TARGET_W + 2), np.uint8)
    cv2.floodFill(ff_p, ff_pm, (10, 10), 128)
    photo_mask = np.where(ff_p == 128, 0, 255).astype(np.uint8)
    photo_mask = cv2.erode(photo_mask, np.ones((3, 3), np.uint8), iterations=1)
    info_photo = save_crop(rgb, photo_mask, "03_Photo_Driver_Car.png", feather=3)

    # 3. Clean Green Background
    bg_inpaint_mask = cv2.bitwise_not(is_green)
    bg_inpaint_mask = cv2.dilate(bg_inpaint_mask, np.ones((15, 15), np.uint8), iterations=2)
    sm_bgr = cv2.resize(bgr, (256, 256), interpolation=cv2.INTER_AREA)
    sm_mask = cv2.resize(bg_inpaint_mask, (256, 256), interpolation=cv2.INTER_NEAREST)
    sm_inpainted = cv2.GaussianBlur(cv2.inpaint(sm_bgr, sm_mask, 9, cv2.INPAINT_TELEA), (15, 15), 0)
    bg_full = cv2.resize(sm_inpainted, (TARGET_W, TARGET_H), interpolation=cv2.INTER_CUBIC)
    keep_orig = (bg_inpaint_mask == 0)[:, :, None]
    bg_final_bgr = np.where(keep_orig, bgr, bg_full)
    bg_final_rgb = cv2.cvtColor(bg_final_bgr, cv2.COLOR_BGR2RGB)
    Image.fromarray(bg_final_rgb, "RGB").save(os.path.join(LAYERS_DIR, "01_Background_Green_Clean.png"))

    manifest = [
        {"name": "01_Background_Green_Clean", "group": "1_Background", "file": "layers/01_Background_Green_Clean.png", "x": 0, "y": 0, "width": TARGET_W, "height": TARGET_H, "hidden": False},
        {"name": "02_Shape_Black_Corner", "group": "1_Background", "file": "layers/02_Shape_Black_Corner.png", "x": bx1, "y": by1, "width": bx2 - bx1, "height": by2 - by1, "hidden": False},
        {"name": "03_Photo_Driver_Car", "group": "2_Photo_&_Logo", **info_photo, "hidden": False},
    ]

    # 4. Logo SafeDrive
    dark_on_green = cv2.bitwise_and(cv2.bitwise_not(is_green), (cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) < 130).astype(np.uint8) * 255)
    m_logo = np.zeros((TARGET_H, TARGET_W), np.uint8)
    m_logo[100:220, 1600:1920] = dark_on_green[100:220, 1600:1920]
    info_logo = save_crop(rgb, m_logo, "04_Logo_SafeDrive.png", feather=3, pure_black_fill=True)
    if info_logo:
        manifest.append({"name": "04_Logo_SafeDrive", "group": "2_Photo_&_Logo", **info_logo, "hidden": False})

    # 5. Crisp Procedural Vector-Quality Icons (4x supersampled!)
    vec_icons = [
        ("05_Icon_Camera", draw_vector_camera(72), 95, 1285),
        ("06_Icon_Speed", draw_vector_speed(72), 95, 1392),
        ("07_Icon_Distance", draw_vector_distance(72), 95, 1500),
        ("08_Icon_GPS", draw_vector_gps(72), 95, 1608),
    ]
    for name, im, ix, iy in vec_icons:
        fname = f"{name}.png"
        im.save(os.path.join(LAYERS_DIR, fname))
        manifest.append({"name": name, "group": "3_Feature_Icons", "file": f"layers/{fname}", "x": ix, "y": iy, "width": im.width, "height": im.height, "hidden": False})

    # 6. Original Texts (VISIBLE by default so PSD matches 100% visually!)
    for name, (x1, y1, x2, y2) in [
        ("09_Text_Feat1_Orig", (175, 1290, 960, 1350)),
        ("10_Text_Feat2_Orig", (175, 1400, 960, 1455)),
        ("11_Text_Feat3_Orig", (175, 1510, 960, 1565)),
        ("12_Text_Feat4_Orig", (175, 1615, 960, 1675)),
    ]:
        m = np.zeros((TARGET_H, TARGET_W), np.uint8)
        m[y1:y2, x1:x2] = dark_on_green[y1:y2, x1:x2]
        info = save_crop(rgb, m, f"{name}.png", feather=3, pure_black_fill=True)
        if info:
            manifest.append({"name": name, "group": "4_Texts_Visible_Sharp", **info, "hidden": False})

    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    for name, (x1, y1, x2, y2), is_green_txt in [
        ("13_Text_Headline1_Orig", (70, 265, 1140, 390), True),
        ("14_Text_Headline2_Orig", (70, 395, 1220, 560), False),
        ("15_Text_Subtitle_Orig", (70, 580, 1080, 720), False),
    ]:
        m = np.zeros((TARGET_H, TARGET_W), np.uint8)
        m[y1:y2, x1:x2] = is_green[y1:y2, x1:x2] if is_green_txt else (gray[y1:y2, x1:x2] > 140).astype(np.uint8) * 255
        info = save_crop(rgb, m, f"{name}.png", feather=3)
        if info:
            manifest.append({"name": name, "group": "4_Texts_Visible_Sharp", **info, "hidden": False})

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"width": TARGET_W, "height": TARGET_H, "layers": manifest}, f, ensure_ascii=False, indent=2)

    # Render QA Sheet
    cell = 460
    qa_items = [
        ("01_Background_Green_Clean", Image.fromarray(bg_final_rgb).convert("RGBA")),
        ("02_Shape_Black_Corner", Image.open(os.path.join(LAYERS_DIR, "02_Shape_Black_Corner.png"))),
        ("03_Photo_Driver_Car", Image.open(os.path.join(LAYERS_DIR, "03_Photo_Driver_Car.png"))),
        ("04_Logo_SafeDrive", Image.open(os.path.join(LAYERS_DIR, "04_Logo_SafeDrive.png"))),
        ("05_Icon_Camera", Image.open(os.path.join(LAYERS_DIR, "05_Icon_Camera.png"))),
        ("07_Icon_Distance", Image.open(os.path.join(LAYERS_DIR, "07_Icon_Distance.png"))),
    ]
    sheet = Image.new("RGB", (cell * 3, cell * 2), (24, 24, 28))
    draw = ImageDraw.Draw(sheet)
    for idx, (label, im) in enumerate(qa_items):
        gx, gy = (idx % 3) * cell, (idx // 3) * cell
        cb = make_checkerboard(cell, cell).convert("RGBA")
        scale = min((cell - 30) / im.width, (cell - 45) / im.height)
        nw, nh = int(im.width * scale), int(im.height * scale)
        im_r = im.resize((nw, nh), Image.Resampling.LANCZOS)
        cb.alpha_composite(im_r, ((cell - nw) // 2, 34 + (cell - 40 - nh) // 2))
        sheet.paste(cb.convert("RGB"), (gx, gy))
        draw.rectangle([gx, gy, gx + cell, gy + 28], fill=(18, 18, 22))
        draw.text((gx + 10, gy + 7), label, fill=(74, 222, 128))

    qa_path = os.path.join(OUT_DIR, "canva_qa_sheet.png")
    sheet.save(qa_path)
    print(f"CANVA FULL HD ({TARGET_W}x{TARGET_H}): {len(manifest)} layers -> {qa_path}")


if __name__ == "__main__":
    main()
