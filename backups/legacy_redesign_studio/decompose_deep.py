import os
import json
import cv2
import numpy as np
from PIL import Image


def save_rgba_crop(rgb: np.ndarray, mask: np.ndarray, out_dir: str, fname: str, feather: int = 3):
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return None
    x1, y1, x2, y2 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    alpha = mask[y1:y2, x1:x2]
    if feather > 1:
        alpha = cv2.GaussianBlur(alpha, (feather, feather), 0)
    rgba = np.dstack([rgb[y1:y2, x1:x2], alpha])
    Image.fromarray(rgba, "RGBA").save(os.path.join(out_dir, fname))
    return {"file": fname, "x": x1, "y": y1, "width": x2 - x1, "height": y2 - y1}


def decompose_deep(img_path: str, out_dir: str):
    layers_dir = os.path.join(out_dir, "layers_deep")
    os.makedirs(layers_dir, exist_ok=True)
    for f in os.listdir(layers_dir):
        if f.endswith(".png"):
            os.remove(os.path.join(layers_dir, f))

    bgr = cv2.imread(img_path)
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # 1. Estimate smooth local background
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    is_yellow_bg = (hsv[:, :, 0] >= 14) & (hsv[:, :, 0] <= 34) & (hsv[:, :, 1] >= 110) & (hsv[:, :, 2] >= 140)
    flat_bg = is_yellow_bg & (grad_mag < 18)

    small_h, small_w = 92, 92
    bgr_small = cv2.resize(bgr, (small_w, small_h), interpolation=cv2.INTER_AREA)
    fg_approx_small = cv2.resize((~flat_bg).astype(np.uint8) * 255, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
    fg_approx_small = cv2.dilate(fg_approx_small, np.ones((3, 3), np.uint8), iterations=1)
    bg_est_small = cv2.inpaint(bgr_small, fg_approx_small, 5, cv2.INPAINT_TELEA)
    bg_est_small = cv2.GaussianBlur(bg_est_small, (9, 9), 0)
    bg_est = cv2.resize(bg_est_small, (w, h), interpolation=cv2.INTER_CUBIC)

    lab_est = cv2.cvtColor(bg_est, cv2.COLOR_BGR2LAB)
    diff = np.linalg.norm(lab.astype(np.float32) - lab_est.astype(np.float32), axis=2)
    edges = cv2.Canny(gray, 45, 130)
    edges_dil = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    fg = ((diff > 18) | (edges_dil > 0)).astype(np.uint8) * 255
    fg_closed = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

    flood = fg_closed.copy()
    mask_ff = np.zeros((h + 2, w + 2), np.uint8)
    seed_points = []
    for sx in range(0, w, 8):
        seed_points.extend([(sx, 2), (sx, h - 3)])
    for sy in range(0, h, 8):
        seed_points.extend([(2, sy), (w - 3, sy)])
    seed_points.extend([(155, 345), (385, 575), (415, 625)])
    for sx, sy in seed_points:
        if 0 <= sx < w and 0 <= sy < h and flood[sy, sx] == 0 and diff[sy, sx] < 14:
            cv2.floodFill(flood, mask_ff, (sx, sy), 128)
    fg_filled = np.where(flood == 128, 0, 255).astype(np.uint8)

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
    Image.fromarray(bg_final_rgba).save(os.path.join(layers_dir, "01_Background_Clean.png"))

    results = [{
        "name": "01_Background_Clean", "type": "background",
        "file": "layers_deep/01_Background_Clean.png", "x": 0, "y": 0, "width": w, "height": h
    }]

    # 2. Extract small/text regions cleanly by bounding zones
    def extract_zone(mask_src, x1, y1, x2, y2, name, ltype):
        m = np.zeros((h, w), np.uint8)
        m[y1:y2, x1:x2] = mask_src[y1:y2, x1:x2]
        info = save_rgba_crop(rgb, m, layers_dir, f"{name}.png")
        if info:
            info["name"] = name
            info["type"] = ltype
            info["file"] = f"layers_deep/{name}.png"
            results.append(info)
        return m

    m_pin = extract_zone(clean_fg, 630, 0, w, 125, "02_Decor_Pin_TopRight", "decor")
    m_emoji = extract_zone(clean_fg, 0, 410, 90, 505, "03_Decor_Emoji_Left", "decor")
    m_ar_top = extract_zone(clean_fg, 375, 15, 570, 95, "08_Text_Top_Arabic_Orig", "text_orig")
    m_oneway = extract_zone(clean_fg, 75, 80, 405, 205, "07_Logo_ONEWAY_Orig", "logo_orig")
    m_ar_mid = extract_zone(clean_fg, 15, 205, 340, 275, "09_Text_Mid_Arabic_Orig", "text_orig")
    m_ph_icon = extract_zone(clean_fg, 428, 675, 480, 730, "10_Icon_Phone_Bottom", "decor")
    m_ph_txt = extract_zone(clean_fg, 478, 650, 628, 730, "11_Text_Phone_Orig", "text_orig")

    # Remaining hero mask = Road + Taxi + Hand/Phone
    hero_mask = clean_fg.copy()
    for m in [m_pin, m_emoji, m_ar_top, m_oneway, m_ar_mid, m_ph_icon, m_ph_txt]:
        hero_mask = cv2.subtract(hero_mask, m)

    # 3. Separate Hand + iPhone using GrabCut + polygon of phone & hand
    # Phone + Hand polygon (tilted phone + hand holding it)
    hand_phone_poly = np.array([
        [528, 378], [625, 342], [735, 515], [735, 735],
        [625, 735], [552, 575], [532, 430]
    ], dtype=np.int32)
    gc_mask = np.full((h, w), cv2.GC_BGD, dtype=np.uint8)
    # Probable foreground inside hero_mask
    gc_mask[hero_mask > 0] = cv2.GC_PR_BGD
    # Inside polygon is probable FG
    poly_mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(poly_mask, [hand_phone_poly], 255)
    gc_mask[(poly_mask > 0) & (hero_mask > 0)] = cv2.GC_PR_FGD
    # Definite foreground: white iPhone screen & skin tone hand inside poly_mask
    is_white_screen = (rgb[:, :, 0] > 235) & (rgb[:, :, 1] > 235) & (rgb[:, :, 2] > 235)
    is_skin = (rgb[:, :, 0] > 165) & (rgb[:, :, 1] > 105) & (rgb[:, :, 1] < 200) & (rgb[:, :, 2] < 185) & (rgb[:, :, 0] > rgb[:, :, 2] + 15)
    gc_mask[(poly_mask > 0) & (is_white_screen | is_skin)] = cv2.GC_FGD
    # Definite background: left of x=520 or above y=340
    gc_mask[:, :520] = cv2.GC_BGD
    gc_mask[:340, :] = cv2.GC_BGD

    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, gc_mask, None, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_MASK)
    hand_phone_mask = np.where((gc_mask == cv2.GC_FGD) | (gc_mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    hand_phone_mask = cv2.bitwise_and(hand_phone_mask, hero_mask)
    # Clean small fragments
    hand_phone_mask = cv2.morphologyEx(hand_phone_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1)

    info_hp = save_rgba_crop(rgb, hand_phone_mask, layers_dir, "06_Object_Hand_Phone.png")
    if info_hp:
        info_hp.update({"name": "06_Object_Hand_Phone", "type": "object", "file": "layers_deep/06_Object_Hand_Phone.png"})
        results.append(info_hp)

    # 4. Separate Taxi Car from 3D Road
    taxi_road_mask = cv2.subtract(hero_mask, hand_phone_mask)
    # Taxi car + TAXI roof sign occupies y < 385 (plus front wheel down to y=475 in x=[405..545] and front bumper down to y=430 in x=[210..420])
    taxi_poly = np.array([
        [435, 198], [545, 202], [655, 285], [655, 360],
        [545, 425], [525, 472], [440, 472], [405, 438],
        [285, 428], [212, 405], [212, 330], [325, 245]
    ], dtype=np.int32)
    taxi_zone = np.zeros((h, w), np.uint8)
    cv2.fillPoly(taxi_zone, [taxi_poly], 255)
    taxi_mask = cv2.bitwise_and(taxi_road_mask, taxi_zone)

    info_taxi = save_rgba_crop(rgb, taxi_mask, layers_dir, "05_Object_Taxi_Car.png")
    if info_taxi:
        info_taxi.update({"name": "05_Object_Taxi_Car", "type": "object", "file": "layers_deep/05_Object_Taxi_Car.png"})
        results.append(info_taxi)

    # Road is the remaining part of taxi_road_mask
    road_mask = cv2.subtract(taxi_road_mask, taxi_mask)
    info_road = save_rgba_crop(rgb, road_mask, layers_dir, "04_Object_Road_3D.png")
    if info_road:
        info_road.update({"name": "04_Object_Road_3D", "type": "object", "file": "layers_deep/04_Object_Road_3D.png"})
        results.append(info_road)

    with open(os.path.join(out_dir, "manifest_deep.json"), "w", encoding="utf-8") as f:
        json.dump({"width": w, "height": h, "layers": results}, f, ensure_ascii=False, indent=2)

    print(f"DEEP DECOMPOSE DONE: {len(results)} layers")
    for r in results:
        print(f"  - {r['name']} ({r['type']}) [{r['x']},{r['y']} {r['width']}x{r['height']}]")


if __name__ == "__main__":
    decompose_deep(
        r"C:/Users/BUM/.gemini/antigravity/brain/7a3bd732-b5a7-4da2-8ae9-7603555447fd/.user_uploaded/media_1794885806500_463cbbd0.jpg",
        r"d:\AI\TESTER\redesign_studio"
    )
