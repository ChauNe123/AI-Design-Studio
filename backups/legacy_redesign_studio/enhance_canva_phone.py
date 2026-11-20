import os
import json
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

DIR = r"d:\AI\TESTER\redesign_studio\canva_fullhd"
LAYERS_DIR = os.path.join(DIR, "layers")
PHONE_SRC = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\safedrive_phone_isolated_1794887977458.jpg"


def enhance_photo_clarity(pil_im: Image.Image) -> Image.Image:
    """Apply subtle CLAHE micro-contrast + 2-stage UnsharpMask for crisp Full HD detail."""
    rgba = np.array(pil_im)
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3]

    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    l2 = clahe.apply(l)
    enhanced_rgb = cv2.cvtColor(cv2.merge([l2, a, b]), cv2.COLOR_LAB2RGB)
    # Blend 55% original + 45% CLAHE so skin/colors stay natural
    blended = (rgb.astype(np.float32) * 0.55 + enhanced_rgb.astype(np.float32) * 0.45).astype(np.uint8)

    pil_rgb = Image.fromarray(blended, "RGB").filter(ImageFilter.UnsharpMask(radius=1.6, percent=145, threshold=2))
    out = np.dstack([np.array(pil_rgb), alpha])
    return Image.fromarray(out, "RGBA")


def main():
    # 1. Load 03_Photo_Driver_Car.png and manifest
    with open(os.path.join(DIR, "manifest.json"), "r", encoding="utf-8") as f:
        manifest = json.load(f)

    photo_item = next(l for l in manifest["layers"] if l["name"] == "03_Photo_Driver_Car")
    px, py = photo_item["x"], photo_item["y"]
    photo_pil = Image.open(os.path.join(DIR, photo_item["file"])).convert("RGBA")

    # Save before-zoom for comparison
    # Dashboard phone on 2048x2048 canvas is at x=1690..1950, y=1215..1420
    local_x1, local_y1 = 1690 - px, 1215 - py
    local_x2, local_y2 = min(photo_pil.width, 1955 - px), min(photo_pil.height, 1425 - py)
    before_crop = photo_pil.crop((local_x1, local_y1, local_x2, local_y2)).convert("RGB")

    # 2. Enhance clarity of the entire driver & car interior photo
    photo_sharp = enhance_photo_clarity(photo_pil)

    # 3. Extract the ultra-sharp SafeDrive AR screen from safedrive_phone_isolated_1794887977458.jpg
    src_bgr = cv2.imread(PHONE_SRC)
    sh, sw = src_bgr.shape[:2]
    # Approximate inner screen corners of safedrive_phone_isolated (tilted slightly)
    # Let's warp the full screen area cleanly into the dashboard phone's rectangular screen
    src_pts = np.float32([
        [sw * 0.225, sh * 0.235],
        [sw * 0.815, sh * 0.195],
        [sw * 0.775, sh * 0.775],
        [sw * 0.180, sh * 0.735],
    ])
    # Destination screen rectangle inside photo_sharp (local coordinates)
    dst_pts = np.float32([
        [1712 - px, 1244 - py],
        [1938 - px, 1246 - py],
        [1938 - px, 1384 - py],
        [1712 - px, 1384 - py],
    ])
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    src_rgb = cv2.cvtColor(src_bgr, cv2.COLOR_BGR2RGB)
    warped_screen = cv2.warpPerspective(src_rgb, M, (photo_sharp.width, photo_sharp.height), flags=cv2.INTER_LANCZOS4)

    # Create smooth rounded-rectangle mask for the screen (keeping the top/bottom mount clips & bezel!)
    screen_mask = Image.new("L", (photo_sharp.width, photo_sharp.height), 0)
    d = ImageDraw.Draw(screen_mask)
    d.rounded_rectangle([1716 - px, 1246 - py, 1936 - px, 1382 - py], radius=10, fill=255)
    # Keep the left notch dark
    d.rounded_rectangle([1714 - px, 1288 - py, 1726 - px, 1340 - py], radius=4, fill=0)
    screen_mask_arr = (cv2.GaussianBlur(np.array(screen_mask), (3, 3), 0).astype(np.float32) / 255.0)[:, :, None]

    base_arr = np.array(photo_sharp)
    comp_rgb = (base_arr[:, :, :3].astype(np.float32) * (1 - screen_mask_arr) + warped_screen.astype(np.float32) * screen_mask_arr).astype(np.uint8)
    photo_enhanced = Image.fromarray(np.dstack([comp_rgb, base_arr[:, :, 3]]), "RGBA")
    photo_enhanced.save(os.path.join(LAYERS_DIR, "03_Photo_Driver_Car.png"))

    # 4. Also extract the sharp dashboard phone + mount as its own standalone layer `03b_Dashboard_Phone_Sharp.png`
    phone_only = photo_enhanced.crop((local_x1, local_y1, local_x2, local_y2))
    # Feather outer border slightly for seamless overlay
    p_arr = np.array(phone_only)
    p_mask = np.ones((phone_only.height, phone_only.width), dtype=np.uint8) * 255
    # Mask out bright windshield sky above the phone (left & top-left of phone)
    is_sky = (p_arr[:, :, 0] > 180) & (p_arr[:, :, 1] > 185) & (p_arr[:, :, 2] > 180)
    # Only floodfill sky from top-left (0,0)
    sky_u8 = is_sky.astype(np.uint8) * 255
    ff_m = np.zeros((sky_u8.shape[0] + 2, sky_u8.shape[1] + 2), np.uint8)
    cv2.floodFill(sky_u8, ff_m, (2, 2), 128)
    p_mask = np.where(sky_u8 == 128, 0, p_arr[:, :, 3]).astype(np.uint8)
    p_mask = cv2.GaussianBlur(p_mask, (3, 3), 0)
    phone_layer = Image.fromarray(np.dstack([p_arr[:, :, :3], p_mask]), "RGBA")
    phone_layer.save(os.path.join(LAYERS_DIR, "03b_Dashboard_Phone_Sharp.png"))

    # Update manifest if 03b not already present
    if not any(l["name"] == "03b_Dashboard_Phone_Sharp" for l in manifest["layers"]):
        idx_photo = next(i for i, l in enumerate(manifest["layers"]) if l["name"] == "03_Photo_Driver_Car")
        manifest["layers"].insert(idx_photo + 1, {
            "name": "03b_Dashboard_Phone_Sharp",
            "group": "2_Photo_&_Logo",
            "file": "layers/03b_Dashboard_Phone_Sharp.png",
            "x": px + local_x1,
            "y": py + local_y1,
            "width": phone_layer.width,
            "height": phone_layer.height,
            "hidden": False
        })
        with open(os.path.join(DIR, "manifest.json"), "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

    # Save Before vs After comparison
    after_crop = photo_enhanced.crop((local_x1, local_y1, local_x2, local_y2)).convert("RGB")
    comp = Image.new("RGB", (before_crop.width * 2 + 20, before_crop.height + 40), (20, 20, 24))
    comp.paste(before_crop, (0, 35))
    comp.paste(after_crop, (before_crop.width + 20, 35))
    d2 = ImageDraw.Draw(comp)
    d2.text((10, 10), "BEFORE (1024px Blurry)", fill=(248, 113, 113))
    d2.text((before_crop.width + 30, 10), "AFTER (Full HD Sharp Phone + Screen)", fill=(74, 222, 128))
    comp.save(os.path.join(DIR, "phone_enhanced_compare.png"))
    print("DONE: Enhanced driver photo + sharp dashboard phone layer!")


if __name__ == "__main__":
    main()
