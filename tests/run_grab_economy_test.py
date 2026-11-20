"""Run AI Design Studio v1.2 on user's GrabBike/GrabCar Economy poster."""
import base64
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer

STUDIO_ROOT = r"D:\AI_Design_Studio"
sys.path.insert(0, STUDIO_ROOT)

from core.server import StudioHandler

INPUT_IMG = r"C:/Users/BUM/.gemini/antigravity/brain/7a3bd732-b5a7-4da2-8ae9-7603555447fd/.user_uploaded/media_1794983303791_da7944ff.jpg"
OUT_DIR = os.path.join(STUDIO_ROOT, "tests", "output", "grab_economy_v12")
os.makedirs(OUT_DIR, exist_ok=True)


def http_req(base_url: str, path: str, payload=None, timeout: int = 240):
    url = base_url + path
    if payload is None:
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json; charset=utf-8"}, method="POST"
        )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main():
    from PIL import Image
    with Image.open(INPUT_IMG) as im0:
        w0, h0 = im0.size

    server = ThreadingHTTPServer(("127.0.0.1", 8793), StudioHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:8793"

    try:
        with open(INPUT_IMG, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")

        # 1. Semantic Redesign (MODE A v1.2)
        sc, rd = http_req(base, "/api/redesign", {
            "title": "GrabBike_GrabCar_Economy",
            "filename": "grab_economy.jpg",
            "semantic_mode": True,
            "use_rmbg": True,
            "use_ocr": True,
            "upscale_2x": False,
            "data_base64": b64,
        })
        assert sc == 200 and rd["ok"], rd
        doc = rd["document"]
        pid = doc["project_id"]
        pdir = os.path.join(STUDIO_ROOT, "projects", pid)

        shutil.copy2(os.path.join(pdir, "qa_composite.png"), os.path.join(OUT_DIR, "01_initial_composite.png"))
        shutil.copy2(os.path.join(pdir, "qa_layers_sheet.png"), os.path.join(OUT_DIR, "01_initial_layers.png"))

        hero = next((l for l in doc["layers"] if "Foreground_Hero" in l["name"]), None)

        # 2. Interactive SlimSAM sub-object segmentation:
        # 2a. Green Card (inside card +, fingers -)
        _, seg_card = http_req(base, f"/api/project/{pid}/segment", {
            "points": [[540, 480], [740, 560], [890, 520], [560, 640], [700, 405], [640, 725]],
            "labels": [1, 1, 1, 1, 0, 0],
            "mask_level": 2,
            "use_sam": True,
            "layer_name": "Green_Economy_Card",
            "category": "object",
            "group": "5_Interactive_Segmented",
            "carve_from_layer_id": hero["id"] if hero else None,
            "feather_px": 1,
        })
        shutil.copy2(os.path.join(pdir, seg_card["layer"]["source_file"]), os.path.join(OUT_DIR, "02_seg_green_card.png"))

        # 2b. Upper-center Green GrabCar (exact car body center ~[575, 138])
        _, seg_car1 = http_req(base, f"/api/project/{pid}/segment", {
            "points": [[565, 138], [595, 132], [575, 100], [575, 178]],
            "labels": [1, 1, 0, 0],
            "mask_level": 1,
            "use_sam": True,
            "layer_name": "GrabCar_TopCenter",
            "category": "vehicle",
            "group": "5_Interactive_Segmented",
        })
        shutil.copy2(os.path.join(pdir, seg_car1["layer"]["source_file"]), os.path.join(OUT_DIR, "03_seg_car1.png"))

        # 2c. Upper-right Green GrabCar (exact car body ~[888, 205], negative on asphalt/rail)
        _, seg_car2 = http_req(base, f"/api/project/{pid}/segment", {
            "points": [[875, 205], [905, 212], [835, 210], [945, 215], [888, 168], [888, 250]],
            "labels": [1, 1, 0, 0, 0, 0],
            "mask_level": 1,
            "use_sam": True,
            "layer_name": "GrabCar_TopRight",
            "category": "vehicle",
            "group": "5_Interactive_Segmented",
        })
        shutil.copy2(os.path.join(pdir, seg_car2["layer"]["source_file"]), os.path.join(OUT_DIR, "04_seg_car2.png"))

        # 2d. White Motorbike front+wheel (excluding green rider jacket)
        _, seg_moto = http_req(base, f"/api/project/{pid}/segment", {
            "points": [[185, 580], [230, 445], [85, 760], [320, 480], [415, 360]],
            "labels": [1, 1, 1, 0, 0],
            "mask_level": 2,
            "use_sam": True,
            "layer_name": "White_Motorbike",
            "category": "vehicle",
            "group": "5_Interactive_Segmented",
            "carve_from_layer_id": hero["id"] if hero else None,
        })
        shutil.copy2(os.path.join(pdir, seg_moto["layer"]["source_file"]), os.path.join(OUT_DIR, "05_seg_motorbike.png"))

        # Reload latest doc + inspect layers & OCR
        _, latest = http_req(base, f"/api/project/{pid}")
        cur_doc = latest["document"]

        # Copy largest Foreground_Hero layer for inspection
        hero_cands = [l for l in cur_doc["layers"] if "Foreground_Hero" in l["name"]]
        cur_hero = max(hero_cands, key=lambda x: x["width"] * x["height"], default=None)
        if cur_hero:
            shutil.copy2(os.path.join(pdir, cur_hero["source_file"]), os.path.join(OUT_DIR, "06_hero_remaining.png"))

        bg_lyr = cur_doc["layers"][0]
        shutil.copy2(os.path.join(pdir, bg_lyr["source_file"]), os.path.join(OUT_DIR, "07_bg_reconstructed.png"))

        psd_path = os.path.join(pdir, cur_doc["qa_status"]["psd_file"]) if cur_doc.get("qa_status") else os.path.join(pdir, f"{pid}_studio.psd")
        # Save once to refresh QA & PSD with newly segmented layers!
        _, saved = http_req(base, f"/api/project/{pid}/save", {"layers": cur_doc["layers"], "note": "Grab Economy + SlimSAM Segmented"})
        sdoc = saved["document"]
        psd_path = os.path.join(pdir, sdoc["qa_status"]["psd_file"])
        vproc = subprocess.run(["node", os.path.join(STUDIO_ROOT, "core", "psd_bridge.js"), "verify", psd_path], capture_output=True, text=True, check=True)
        psd_info = json.loads(vproc.stdout.strip())

        shutil.copy2(os.path.join(pdir, "qa_composite.png"), os.path.join(OUT_DIR, "08_final_composite.png"))
        shutil.copy2(os.path.join(pdir, "qa_layers_sheet.png"), os.path.join(OUT_DIR, "08_final_layers.png"))

        report = {
            "input_size": [w0, h0],
            "project_id": pid,
            "psd_path": psd_path,
            "psd_mb": round(os.path.getsize(psd_path) / (1024 * 1024), 2),
            "layer_count": len(sdoc["layers"]),
            "semantic_object_count": len(sdoc.get("semantic_objects", [])),
            "ocr_texts": [
                {"name": l["name"], "text": (l.get("text_data") or {}).get("text"), "visible": l["visible"], "conf": l.get("confidence_score")}
                for l in sdoc["layers"] if l["type"] == "text"
            ],
            "layers_summary": [
                {"z": l["z_index"], "name": l["name"], "type": l["type"], "group": l["group"], "box": [l["x"], l["y"], l["width"], l["height"]], "visible": l["visible"]}
                for l in sdoc["layers"]
            ],
            "seg_engines": {
                "card": seg_card["seg_result"],
                "car1": seg_car1["seg_result"],
                "car2": seg_car2["seg_result"],
                "motorbike": seg_moto["seg_result"],
            },
            "qa_overall": saved["qa"]["overall_passed"],
            "psd_verify": {
                "ok": psd_info["ok"],
                "groups": psd_info["group_count"],
                "layers": psd_info["layer_count"],
                "decoded_pixel_layers": psd_info["decoded_pixel_layers"],
                "text_layers": psd_info["text_layer_count"],
                "composite_decoded": psd_info["composite_decoded"],
            },
            "warnings": sdoc.get("warnings", []),
        }
        with open(os.path.join(OUT_DIR, "report.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
