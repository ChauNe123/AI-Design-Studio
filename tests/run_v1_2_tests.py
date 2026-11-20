"""AI Design Studio v1.2 Comprehensive Acceptance & Integration Test Suite."""
import base64
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request

STUDIO_ROOT = r"D:\AI_Design_Studio"
sys.path.insert(0, STUDIO_ROOT)

from core import (
    credential_store,
    design_document,
    effects_engine,
    ai_providers,
)
from core.server import StudioHandler
from http.server import ThreadingHTTPServer

GRAB_IMG = r"C:/Users/BUM/.gemini/antigravity/brain/7a3bd732-b5a7-4da2-8ae9-7603555447fd/.user_uploaded/media_1794977150476_12e90368.jpg"
OUT_DIR = os.path.join(STUDIO_ROOT, "tests", "output", "v1_2_results")
os.makedirs(OUT_DIR, exist_ok=True)


def http_req(base_url: str, path: str, payload=None, timeout: int = 180):
    url = base_url + path
    if payload is None:
        req = urllib.request.Request(url, method="GET")
    else:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def test_unit_schema_credentials_privacy_limits():
    results = {}

    # 1. Credential Manager store / retrieve / delete + no plaintext leak
    svc = "TestTempKey_" + str(int(time.time()))
    secret_val = "sk-test-secret-9876543210-DO-NOT-LEAK"
    assert credential_store.save_api_key(svc, secret_val), "Credential write failed"
    assert credential_store.read_api_key(svc) == secret_val, "Credential read mismatch"
    assert credential_store.has_api_key(svc), "Credential has_api_key false"
    assert credential_store.delete_api_key(svc), "Credential delete failed"
    assert not credential_store.has_api_key(svc), "Credential still present after delete"
    results["credential_manager"] = "PASS"

    # 2. Hybrid AI Privacy & Cost Gates (must stay LOCAL_ONLY and refuse unconfirmed cloud calls)
    mgr = ai_providers.AIProviderManager(STUDIO_ROOT)
    st = mgr.get_public_status()
    assert st["mode"] == "LOCAL_ONLY", f"Expected LOCAL_ONLY default, got {st['mode']}"

    # Attempt unconfirmed call in LOCAL_ONLY
    blocked1 = mgr.execute_cloud_inpaint(
        "openai_image", GRAB_IMG, GRAB_IMG, "clean", user_confirmed=False
    )
    assert not blocked1["ok"] and blocked1.get("fallback_to_local") and "LOCAL_ONLY" in blocked1["error"], f"Blocked check failed: {blocked1}"

    # Temporarily simulate HYBRID call without user_confirmed
    cfg = mgr._load_cfg()
    orig_mode = cfg["mode"]
    orig_en = cfg["providers"]["openai_image"]["enabled"]
    try:
        mgr.update_provider("openai_image", enabled=True, mode="HYBRID")
        blocked2 = mgr.execute_cloud_inpaint(
            "openai_image", GRAB_IMG, GRAB_IMG, "clean", user_confirmed=False
        )
        assert not blocked2["ok"] and blocked2.get("fallback_to_local") and "permission" in blocked2["error"].lower(), f"Confirm check failed: {blocked2}"

        # With confirmation but NO API key -> safe failure, does not crash
        blocked3 = mgr.execute_cloud_inpaint(
            "openai_image", GRAB_IMG, GRAB_IMG, "clean", user_confirmed=True
        )
        assert not blocked3["ok"] and blocked3.get("fallback_to_local") and ("API key" in blocked3["error"] or "budget" in blocked3["error"]), blocked3

        # Ensure public status NEVER contains plaintext secrets
        pub_dump = json.dumps(mgr.get_public_status())
        assert "sk-" not in pub_dump
    finally:
        mgr.update_provider("openai_image", enabled=orig_en, mode=orig_mode)
    results["hybrid_ai_privacy_gates"] = "PASS"

    # 3. Migration from v1.1 document -> v1.2.0
    v1_sample = {
        "project_id": "v1_mig_test",
        "title": "Legacy v1.1 Doc",
        "mode": "REDESIGN",
        "width": 1000,
        "height": 1000,
        "layers": [
            {"id": "l1", "name": "bg", "type": "background", "source_file": "layers/bg.png", "x": 0, "y": 0, "width": 1000, "height": 1000, "z_index": 0, "opacity": 1.0, "visible": True}
        ],
    }
    mig = design_document.migrate_document_v1_to_v1_2(v1_sample)
    assert mig["schema_version"] == "1.2.0"
    assert "adjustments" in mig["layers"][0] and "effects" in mig["layers"][0] and "locked" in mig["layers"][0]
    assert design_document.validate_document(mig) == []
    results["schema_v1_1_to_v1_2_migration"] = "PASS"

    # 4. Corrupt / Unreadable image error handling + 30-layer stress benchmark
    results["stress_30_layers"] = _benchmark_30_layers()
    return results


def _benchmark_30_layers():
    from PIL import Image
    tmp_proj = os.path.join(OUT_DIR, "stress_30")
    if os.path.exists(tmp_proj):
        shutil.rmtree(tmp_proj)
    os.makedirs(os.path.join(tmp_proj, "layers"), exist_ok=True)
    im = Image.new("RGBA", (600, 600), (20, 140, 80, 220))
    bg_im = Image.new("RGBA", (2048, 2048), (10, 24, 20, 255))
    bg_rel = "layers/s_00_bg.png"
    bg_im.save(os.path.join(tmp_proj, bg_rel))
    layers = [design_document.make_layer(
        layer_id="s_00", name="Stress_BG", layer_type="background", source_file=bg_rel,
        x=0, y=0, width=2048, height=2048, z_index=0, group="1_Background"
    )]
    for i in range(1, 30):
        rel = f"layers/s_{i:02d}.png"
        im.save(os.path.join(tmp_proj, rel))
        layers.append(design_document.make_layer(
            layer_id=f"s_{i:02d}",
            name=f"Stress_{i:02d}",
            layer_type="object",
            source_file=rel,
            x=(i * 30) % 1400,
            y=(i * 25) % 1400,
            width=600,
            height=600,
            z_index=i,
            adjustments={"hue": (i * 5) % 60, "sat": 110, "bright": 105, "contrast": 100, "exposure": 0.0, "temperature": 0, "shadow": 0, "highlight": 0},
        ))
    doc = design_document.create_document("stress_30", "Stress 30 Layers 2K", "GENERATE", 2048, 2048, layers)
    design_document.save_document(doc, tmp_proj)

    t0 = time.time()
    from core.qa_engine import export_and_qa_all
    qa = export_and_qa_all(STUDIO_ROOT, tmp_proj)
    elapsed = round(time.time() - t0, 2)
    assert qa["overall_passed"], f"30-layer 2K stress QA failed: {qa}"
    psd_mb = round(os.path.getsize(os.path.join(tmp_proj, qa["psd_file"])) / (1024 * 1024), 2)
    return {"passed": True, "layers": 30, "canvas": "2048x2048", "elapsed_sec": elapsed, "psd_mb": psd_mb}


def test_live_server_grab_e2e():
    assert os.path.exists(GRAB_IMG), f"Missing Grab test poster: {GRAB_IMG}"
    server = ThreadingHTTPServer(("127.0.0.1", 8792), StudioHandler)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    base = "http://127.0.0.1:8792"
    report = {}

    try:
        # 1. Check /api/system, /api/fonts, /api/providers
        sc, sys_info = http_req(base, "/api/system")
        assert sc == 200 and sys_info["ok"] and sys_info["version"] == "1.2.0"
        sc, fonts_res = http_req(base, "/api/fonts")
        assert sc == 200 and len(fonts_res["fonts"]) >= 5
        sc, prov_res = http_req(base, "/api/providers")
        assert sc == 200 and prov_res["providers_state"]["mode"] == "LOCAL_ONLY"
        report["system_endpoints"] = {"fonts_count": len(fonts_res["fonts"]), "ai_mode": prov_res["providers_state"]["mode"]}

        # 2. Invalid image upload safety check
        bad_b64 = base64.b64encode(b"not-a-valid-image-bytes").decode("ascii")
        sc, bad_res = http_req(base, "/api/redesign", {"title": "Bad", "filename": "bad.jpg", "data_base64": bad_b64})
        assert sc == 400 and not bad_res["ok"]
        report["corrupt_input_handling"] = "PASS"

        # 3. Upload real Grab poster -> Semantic Redesign v1.2
        with open(GRAB_IMG, "rb") as f:
            grab_b64 = base64.b64encode(f.read()).decode("ascii")
        t0 = time.time()
        sc, rd = http_req(
            base,
            "/api/redesign",
            {
                "title": "Grab_V12_Semantic_Test",
                "filename": "grab_poster.jpg",
                "semantic_mode": True,
                "use_rmbg": True,
                "use_ocr": True,
                "upscale_2x": False,
                "data_base64": grab_b64,
            },
            timeout=240,
        )
        assert sc == 200 and rd["ok"], f"Grab redesign failed: {rd}"
        doc = rd["document"]
        pid = doc["project_id"]
        pdir = os.path.join(STUDIO_ROOT, "projects", pid)
        initial_layer_count = len(doc["layers"])
        sem_objs = doc.get("semantic_objects", [])
        text_layers = [l for l in doc["layers"] if l["type"] == "text"]
        assert len(sem_objs) >= 3, f"Expected >=3 semantic objects, got {len(sem_objs)}"
        assert len(text_layers) >= 1, "Expected >=1 OCR text layer on Grab poster"

        shutil.copy2(os.path.join(pdir, "qa_composite.png"), os.path.join(OUT_DIR, "grab_01_initial_composite.png"))
        shutil.copy2(os.path.join(pdir, "qa_layers_sheet.png"), os.path.join(OUT_DIR, "grab_01_initial_layers.png"))

        # Find largest Foreground layer (Hero/Person/Remaining)
        fg_cands = [l for l in doc["layers"] if l["group"].startswith("3_Foreground") or l["group"].startswith("4_Foreground")]
        hero_lyr = max(fg_cands, key=lambda x: x["width"] * x["height"], default=None)
        assert hero_lyr is not None, "Expected Foreground Hero layer"

        report["grab_semantic_initial"] = {
            "project_id": pid,
            "elapsed_sec": round(time.time() - t0, 2),
            "layer_count": initial_layer_count,
            "semantic_object_count": len(sem_objs),
            "ocr_text_layers": [l["text_data"]["text"] for l in text_layers],
            "warnings": doc.get("warnings", []),
            "qa_passed": rd["qa"]["overall_passed"],
        }

        # 4. Interactive SlimSAM Segmentation on Grab Poster:
        # 4a: Motorbike + rider front-left (carved cleanly off Foreground Hero)
        sc, seg_moto = http_req(base, f"/api/project/{pid}/segment", {
            "points": [[360, 860], [340, 930], [420, 770], [430, 850]],
            "labels": [1, 1, 1, 1],
            "mask_level": 2,
            "use_sam": True,
            "layer_name": "Motorbike_And_Rider_SlimSAM",
            "category": "vehicle",
            "group": "5_Interactive_Segmented",
            "carve_from_layer_id": hero_lyr["id"],
            "feather_px": 1,
        })
        assert sc == 200 and seg_moto["ok"], seg_moto
        moto_lyr = seg_moto["layer"]
        shutil.copy2(os.path.join(pdir, moto_lyr["source_file"]), os.path.join(OUT_DIR, "grab_02_slimsam_motorbike.png"))

        # 4b: Green Car on right curve (body + bumper + negative sky point)
        sc, seg_car = http_req(base, f"/api/project/{pid}/segment", {
            "points": [[815, 725], [855, 738], [795, 735], [830, 665]],
            "labels": [1, 1, 1, 0],
            "mask_level": 2,
            "use_sam": True,
            "layer_name": "Green_Car_SlimSAM",
            "category": "vehicle",
            "group": "5_Interactive_Segmented",
            "carve_from_layer_id": hero_lyr["id"],
        })
        assert sc == 200 and seg_car["ok"], seg_car
        car_lyr = seg_car["layer"]
        shutil.copy2(os.path.join(pdir, car_lyr["source_file"]), os.path.join(OUT_DIR, "grab_03_slimsam_car.png"))

        # 4c: Family of 3 at bottom-right
        sc, seg_fam = http_req(base, f"/api/project/{pid}/segment", {
            "points": [[685, 835], [730, 855], [775, 835]],
            "labels": [1, 1, 1],
            "mask_level": 2,
            "use_sam": True,
            "layer_name": "Family_Group_SlimSAM",
            "category": "character",
            "group": "5_Interactive_Segmented",
            "carve_from_layer_id": hero_lyr["id"],
        })
        assert sc == 200 and seg_fam["ok"], seg_fam

        report["interactive_slimsam"] = {
            "motorbike_engine": seg_moto["seg_result"]["engine"],
            "motorbike_iou": seg_moto["seg_result"].get("iou_score"),
            "car_engine": seg_car["seg_result"]["engine"],
            "family_engine": seg_fam["seg_result"]["engine"],
        }

        # 5. Reconstruction / Object Removal test (Remove small Green Car area on Background layer cleanly)
        bg_lyr = seg_fam["document"]["layers"][0]
        sc, rec_res = http_req(base, f"/api/project/{pid}/reconstruct", {
            "target_layer_id": bg_lyr["id"],
            "box": [car_lyr["x"], car_lyr["y"], car_lyr["width"], car_lyr["height"]],
            "mode": "algorithmic_inpaint",
            "provider_id": "local_engine",
        })
        assert sc == 200 and rec_res["ok"]
        assert rec_res["reconstruct"]["pixel_origin"] == "algorithmic_inpaint"
        doc = rec_res["document"]
        report["reconstruction"] = {
            "pixel_origin": rec_res["reconstruct"]["pixel_origin"],
            "target_layer": bg_lyr["name"],
            "qa_passed": rec_res["qa"]["overall_passed"],
        }

        # 6. Mandatory Real-World Editing Workflow (Edit text, change color/brightness, move motorbike, hide building, lock/duplicate, save, reopen, export PSD)
        layers_to_save = json.loads(json.dumps(doc["layers"]))

        # 6a. Edit top headline text layer (hide its OrigRaster if present, show & edit Editable text)
        t_edit = next(
            (l for l in layers_to_save if l["type"] == "text" and "LỰC" in l["text_data"]["text"].upper()),
            next((l for l in layers_to_save if l["type"] == "text"), None),
        )
        assert t_edit is not None
        raster_pair = next((l for l in layers_to_save if "Text_OrigRaster_" in l["name"] and l["name"].endswith(t_edit["name"][-2:])), None)
        if raster_pair:
            raster_pair["visible"] = False
        t_edit["visible"] = True
        t_edit["text_data"]["text"] = "AN TOÀN TRÊN MỌI"
        t_edit["text_data"]["font_size"] = min(68, int(t_edit["text_data"].get("font_size", 68)))
        t_edit["text_data"]["color"] = [236, 253, 245]
        t_edit["text_data"]["stroke_enabled"] = True
        t_edit["text_data"]["stroke_color"] = [6, 78, 59]
        t_edit["text_data"]["stroke_width"] = 4
        t_edit["text_data"]["shadow_enabled"] = True
        t_edit["text_reconstruction"]["user_confirmed"] = True
        t_edit["text_reconstruction"]["needs_user_confirmation"] = False
        t_edit["metadata"]["text_dirty"] = True

        # 6b. Adjust Hero jacket Hue + Brightness + Drop Shadow
        h_edit = next(l for l in layers_to_save if l["id"] == hero_lyr["id"])
        h_edit["adjustments"]["hue"] = -18
        h_edit["adjustments"]["bright"] = 112
        h_edit["adjustments"]["contrast"] = 108
        h_edit["effects"]["drop_shadow"]["enabled"] = True

        # 6c. Move motorbike layer cleanly (+45 px X, -18 px Y)
        m_edit = next(l for l in layers_to_save if l["id"] == moto_lyr["id"])
        orig_mx, orig_my = m_edit["x"], m_edit["y"]
        m_edit["x"] += 45
        m_edit["y"] -= 18

        # 6d. Hide Bitexco architecture layer (type == "architecture" on left side)
        mid_bldg = next((l for l in layers_to_save if l["type"] == "architecture" and l["x"] < 420), None)
        hidden_name = None
        if mid_bldg:
            mid_bldg["visible"] = False
            hidden_name = mid_bldg["name"]

        sc, save_res = http_req(base, f"/api/project/{pid}/save", {"layers": layers_to_save, "note": "Grab v1.2 Edited Campaign"})
        assert sc == 200 and save_res["ok"] and save_res["qa"]["overall_passed"], f"Save/QA failed: {save_res}"

        # 6e. Layer action checks: duplicate + lock + unlock on motorbike
        sc, dup_res = http_req(base, f"/api/project/{pid}/layer_action", {"action": "duplicate", "layer_id": moto_lyr["id"]})
        assert sc == 200 and dup_res["ok"]
        dup_id = dup_res["document"]["layers"][-1]["id"]
        sc, lock_res = http_req(base, f"/api/project/{pid}/layer_action", {"action": "lock", "layer_id": dup_id})
        assert sc == 200 and lock_res["document"]["layers"][-1]["locked"] is True
        sc, unlock_res = http_req(base, f"/api/project/{pid}/layer_action", {"action": "unlock", "layer_id": dup_id})
        assert sc == 200 and unlock_res["document"]["layers"][-1]["locked"] is False

        # Remove duplicate before final reopen check so clean edited canvas stands out, OR leave and re-save
        clean_layers = [l for l in unlock_res["document"]["layers"] if l["id"] != dup_id]
        sc, save2 = http_req(base, f"/api/project/{pid}/save", {"layers": clean_layers, "note": "Final Grab v1.2 Export"})
        assert sc == 200 and save2["ok"] and save2["qa"]["overall_passed"]

        # 7. Simulate Close & Reopen Project -> Verify persistence & PSD binary round-trip
        sc, reopened = http_req(base, f"/api/project/{pid}")
        assert sc == 200 and reopened["ok"]
        rdoc = reopened["document"]
        r_moto = next(l for l in rdoc["layers"] if l["id"] == moto_lyr["id"])
        r_hero = next(l for l in rdoc["layers"] if l["id"] == hero_lyr["id"])
        r_txt = next(l for l in rdoc["layers"] if l["id"] == t_edit["id"])
        assert r_moto["x"] == orig_mx + 45 and r_moto["y"] == orig_my - 18
        assert r_hero["adjustments"]["hue"] == -18 and r_hero["effects"]["drop_shadow"]["enabled"] is True
        assert r_txt["text_data"]["text"] == "AN TOÀN TRÊN MỌI"
        if mid_bldg:
            r_bldg = next(l for l in rdoc["layers"] if l["id"] == mid_bldg["id"])
            assert r_bldg["visible"] is False

        shutil.copy2(os.path.join(pdir, "qa_composite.png"), os.path.join(OUT_DIR, "grab_04_edited_final_composite.png"))
        shutil.copy2(os.path.join(pdir, "qa_layers_sheet.png"), os.path.join(OUT_DIR, "grab_04_edited_layers.png"))

        # Verify PSD via node bridge directly
        psd_path = os.path.join(pdir, rdoc["qa_status"]["psd_file"])
        vproc = subprocess.run(["node", os.path.join(STUDIO_ROOT, "core", "psd_bridge.js"), "verify", psd_path], capture_output=True, text=True, check=True)
        psd_info = json.loads(vproc.stdout.strip())
        assert psd_info["ok"] and psd_info["composite_decoded"] and psd_info["decoded_pixel_layers"] == psd_info["layer_count"]

        # 8. Remix / Import Idea from Old Project verification
        sc, cat_res = http_req(base, "/api/projects/remix_catalog")
        assert sc == 200 and cat_res["ok"] and len(cat_res["catalog"]) >= 2
        other = next((c for c in cat_res["catalog"] if c["project_id"] != pid and c["layers"]), None)
        assert other is not None, "Expected another project in remix_catalog with layers"
        sc, rmx_res = http_req(base, f"/api/project/{pid}/import_remix", {
            "src_project_id": other["project_id"],
            "layer_ids": [other["layers"][0]["id"]],
            "apply_palette_style": True,
        })
        assert sc == 200 and rmx_res["ok"] and rmx_res["imported_count"] == 1 and rmx_res["qa"]["overall_passed"]

        report["remix_from_old_project"] = {
            "source_project": other["project_id"],
            "imported_layer": other["layers"][0]["name"],
            "qa_passed": rmx_res["qa"]["overall_passed"],
        }
        report["grab_edited_reopen_psd"] = {
            "final_layers": len(rdoc["layers"]),
            "moved_motorbike_xy": [r_moto["x"], r_moto["y"]],
            "hero_hue_bright": [r_hero["adjustments"]["hue"], r_hero["adjustments"]["bright"]],
            "hidden_building": hidden_name,
            "edited_text": r_txt["text_data"]["text"],
            "psd_bytes": os.path.getsize(psd_path),
            "psd_groups": psd_info["group_count"],
            "psd_layers": psd_info["layer_count"],
            "psd_text_layers": psd_info["text_layer_count"],
            "psd_composite_decoded": psd_info["composite_decoded"],
            "versions_count": len(reopened["versions"]),
            "integrity_ok": reopened["integrity"]["ok"],
        }
        return report
    finally:
        server.shutdown()


if __name__ == "__main__":
    summary = {
        "unit_and_stress": test_unit_schema_credentials_privacy_limits(),
        "grab_e2e": test_live_server_grab_e2e(),
    }
    out_json = os.path.join(OUT_DIR, "v1_2_test_report.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
