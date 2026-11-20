"""AI Design Studio v1.1 — Comprehensive Acceptance, Multi-Variant, Reference & Edge-Case Test Engine."""
import base64
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
import numpy as np
from PIL import Image, ImageDraw

STUDIO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STUDIO_ROOT not in sys.path:
    sys.path.insert(0, STUDIO_ROOT)

from core.design_document import create_document, load_document, make_layer, save_document
from core.generate_engine import _load_font, generate_layout_variants, render_text_layer_png
from core.image_analyzer import run_redesign
from core.knowledge_base import KnowledgeBase
from core.project_manager import (
    check_autosave_recovery,
    check_project_integrity,
    list_versions,
    restore_version,
    save_version,
    write_autosave,
)
from core.qa_engine import export_and_qa_all
from core.reference_analyzer import analyze_reference_image
from core.server import StudioHandler

FIXTURES = os.path.join(STUDIO_ROOT, "tests", "fixtures")
OUT_V11 = os.path.join(STUDIO_ROOT, "tests", "output", "v1_1_acceptance")


def _http_json(url: str, payload: dict = None, method: str = "GET"):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def run_all():
    if os.path.exists(OUT_V11):
        shutil.rmtree(OUT_V11)
    os.makedirs(OUT_V11, exist_ok=True)
    report = []

    srv = ThreadingHTTPServer(("127.0.0.1", 8797), StudioHandler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base_url = "http://127.0.0.1:8797"

    created_ephemeral_pids = []
    try:
        # ------------------------------------------------------------------
        # TEST 1: Layer Editor Full Workflow + Group CRUD + Multiple Exports + Binary Pixel PSD Verify
        # ------------------------------------------------------------------
        st, gen_res = _http_json(f"{base_url}/api/generate", {
            "title": "Editor Workflow Test",
            "canvas_preset": "square_1080",
            "layout": "tech_dark_glow",
            "headline": "BAN ĐẦU",
            "subheadline": "Phụ đề kiểm thử",
            "cta_text": "Hotline 1900",
            "product_rel_paths": ["assets/logos/✅ SAFE DRIVE.png"],
        }, method="POST")
        assert st == 200 and gen_res["ok"]
        pid = gen_res["document"]["project_id"]
        created_ephemeral_pids.append(pid)

        # Create Group -> Assign Layer -> Rename Group
        st, grp_res = _http_json(f"{base_url}/api/project/{pid}/group", {"action": "create", "group_name": "Promo_Group"}, "POST")
        assert st == 200 and grp_res["ok"]
        target_lyr = next(l for l in grp_res["document"]["layers"] if l["type"] == "text")
        st, grp_res2 = _http_json(f"{base_url}/api/project/{pid}/group", {"action": "assign_layer", "group_name": "Promo_Group", "layer_id": target_lyr["id"]}, "POST")
        assert st == 200 and grp_res2["ok"]

        # Edit move, scale, z-order, visibility, opacity, text content
        layers_ed = grp_res2["document"]["layers"]
        orig_x = target_lyr["x"]
        for l in layers_ed:
            if l["id"] == target_lyr["id"]:
                l["x"] += 40
                l["y"] += 25
                l["opacity"] = 0.75
                l["metadata"]["scale"] = 0.90
                l["text_data"]["text"] = "NỘI DUNG ĐÃ CHỈNH SỬA"
            if l["type"] == "shape":
                l["visible"] = False
        # Swap z_index of last two layers
        if len(layers_ed) >= 2:
            layers_ed[-1]["z_index"], layers_ed[-2]["z_index"] = layers_ed[-2]["z_index"], layers_ed[-1]["z_index"]

        # Save & Export PSD (Export #1)
        st, sv1 = _http_json(f"{base_url}/api/project/{pid}/save", {"layers": layers_ed, "note": "Edited text+move+scale"}, "POST")
        assert st == 200 and sv1["ok"] and sv1["qa"]["overall_passed"]

        # Delete Group & Export PSD again (Export #2)
        st, grp_del = _http_json(f"{base_url}/api/project/{pid}/group", {"action": "delete", "group_name": "Promo_Group"}, "POST")
        assert st == 200 and grp_del["ok"]
        st, exp2 = _http_json(f"{base_url}/api/project/{pid}/export_psd", {}, "POST")
        assert st == 200 and exp2["ok"] and exp2["qa"]["overall_passed"]

        # Verify PSD binary decoded text & pixels
        psd_path = exp2["qa"]["psd_path"]
        vr = subprocess.run(["node", os.path.join(STUDIO_ROOT, "core", "psd_bridge.js"), "verify", psd_path], capture_output=True, text=True, check=True)
        v_info = json.loads(vr.stdout)
        edited_found = any((l.get("textValue") or "").strip() == "NỘI DUNG ĐÃ CHỈNH SỬA" for l in v_info["layers"])
        moved_found = any(l["name"] == target_lyr["name"] and l["left"] == orig_x + 40 for l in v_info["layers"])
        hidden_found = any(l["hidden"] is True for l in v_info["layers"])

        report.append({
            "test": "T1_Editor_Groups_MultiExport_PSDBinaryVerify",
            "passed": bool(v_info["ok"] and v_info["composite_decoded"] and edited_found and moved_found and hidden_found),
            "decoded_pixel_layers": f"{v_info['decoded_pixel_layers']}/{v_info['layer_count']}",
            "edited_text_verified": edited_found,
            "moved_coords_verified": moved_found,
            "hidden_state_verified": hidden_found,
        })

        # ------------------------------------------------------------------
        # TEST 2: MODE B Multi-Product + Logo + Reference + Vietnamese + 3 Distinct Variants
        # ------------------------------------------------------------------
        kb = KnowledgeBase(os.path.join(STUDIO_ROOT, "knowledge"))
        k_ctx = kb.query_for_brief("tech_automotive", "safedrive")
        var_dir = os.path.join(OUT_V11, "mode_b_variants")
        variants = generate_layout_variants(
            STUDIO_ROOT,
            var_dir,
            "safedrive_multi",
            {
                "title": "SafeDrive Multi-Product",
                "canvas_preset": "portrait_4x5",
                "headline": "BỘ ĐÔI AN TOÀN TOÀN DIỆN",
                "subheadline": "Cảnh báo AI sớm • Giám sát hành trình thông minh",
                "bullets": ["Cảnh báo va chạm AI", "Camera hành trình 24/7", "Dẫn đường GPS"],
                "cta_text": "Tải ngay trên App Store & Google Play",
                "product_paths": [
                    os.path.join(FIXTURES, "04_white_bg_product.png"),
                    os.path.join(FIXTURES, "03_multi_product.png"),
                ],
                "logo_path": os.path.join(FIXTURES, "05_transparent_png.png"),
                "reference_paths": [os.path.join(FIXTURES, "06_canva_design.jpg")],
            },
            k_ctx,
        )
        comp_arrays = []
        all_var_ok = len(variants) == 3
        for v in variants:
            qa_v = export_and_qa_all(STUDIO_ROOT, v["project_dir"])
            if not qa_v["overall_passed"]:
                all_var_ok = False
            comp_arrays.append(np.array(Image.open(os.path.join(v["project_dir"], "qa_composite.png")).convert("RGB"), dtype=np.float32))
            # Verify 2 products preserved
            prod_layers = [l for l in v["document"]["layers"] if l["type"] == "product"]
            if len(prod_layers) != 2:
                all_var_ok = False

        # Verify the 3 variants are genuinely visually distinct (mean pixel diff > 15)
        diff_12 = float(np.mean(np.abs(comp_arrays[0] - comp_arrays[1])))
        diff_13 = float(np.mean(np.abs(comp_arrays[0] - comp_arrays[2])))
        diff_23 = float(np.mean(np.abs(comp_arrays[1] - comp_arrays[2])))
        variants_distinct = min(diff_12, diff_13, diff_23) > 15.0

        report.append({
            "test": "T2_MODE_B_MultiProduct_Reference_3Variants",
            "passed": bool(all_var_ok and variants_distinct),
            "variants_count": len(variants),
            "diff_v1_v2": round(diff_12, 2),
            "diff_v1_v3": round(diff_13, 2),
            "diff_v2_v3": round(diff_23, 2),
        })

        # ------------------------------------------------------------------
        # TEST 3: Design Knowledge Reference Analyzer
        # ------------------------------------------------------------------
        ref1 = analyze_reference_image(os.path.join(FIXTURES, "06_canva_design.jpg"), "Canva_SafeDrive")
        ref2 = analyze_reference_image(os.path.join(FIXTURES, "07_overlapping.jpg"), "OneWay_Taxi")
        kb_tmp = KnowledgeBase(os.path.join(OUT_V11, "kb_test"))
        kb_tmp.save_reference_analysis(ref1)
        kb_tmp.save_reference_analysis(ref2)
        reloaded = kb_tmp.load().get("references_analyzed", [])
        ref_ok = (
            len(reloaded) == 2
            and ref1["visual_hierarchy"]["whitespace_pct"] > 0
            and ref1["palette"]["bg_hex"].startswith("#")
            and len(ref1["design_principles_extracted"]) >= 3
        )
        report.append({
            "test": "T3_DesignKnowledge_ReferenceAnalyzer",
            "passed": ref_ok,
            "canva_layout": ref1["visual_hierarchy"]["suggested_layout"],
            "canva_bg": ref1["palette"]["bg_hex"],
            "oneway_layout": ref2["visual_hierarchy"]["suggested_layout"],
            "oneway_bg": ref2["palette"]["bg_hex"],
        })

        # ------------------------------------------------------------------
        # TEST 4: Project Management (Autosave Recovery, Version Restore, Integrity Missing Asset)
        # ------------------------------------------------------------------
        pm_dir = os.path.join(OUT_V11, "pm_test")
        shutil.copytree(variants[0]["project_dir"], pm_dir)
        doc_v1 = load_document(pm_dir)
        orig_len = len(doc_v1["layers"])
        # Autosave draft with 1 deleted layer
        draft_doc = json.loads(json.dumps(doc_v1))
        draft_doc["layers"] = draft_doc["layers"][:-1]
        write_autosave(draft_doc, pm_dir)
        rec = check_autosave_recovery(pm_dir)
        # Save v002 with modified title, then restore v001
        doc_v1["title"] = "Modified_V2"
        save_version(doc_v1, pm_dir, note="v2 edit")
        restored = restore_version(pm_dir, "v001")
        # Integrity check: move 1 asset temporarily, verify detection, restore
        first_file = os.path.join(pm_dir, restored["layers"][0]["source_file"])
        tmp_bak = first_file + ".bak"
        os.rename(first_file, tmp_bak)
        int_bad = check_project_integrity(pm_dir)
        os.rename(tmp_bak, first_file)
        int_good = check_project_integrity(pm_dir)

        report.append({
            "test": "T4_ProjectManagement_Autosave_Restore_Integrity",
            "passed": bool(
                rec and rec["has_recovery"] and rec["unclean_shutdown"]
                and len(restored["layers"]) == orig_len
                and (not int_bad["ok"] and len(int_bad["missing_assets"]) == 1)
                and int_good["ok"]
            ),
            "versions_count": len(list_versions(pm_dir)),
            "missing_detected": len(int_bad["missing_assets"]),
        })

        # ------------------------------------------------------------------
        # TEST 5: Stress, Edge-Case & Negative Failure Handling
        # ------------------------------------------------------------------
        # 5a. Invalid image upload -> HTTP 400
        bad_b64 = base64.b64encode(b"NOT_A_REAL_PNG_FILE_12345").decode("ascii")
        st_bad, res_bad = _http_json(f"{base_url}/api/redesign", {"filename": "corrupt.png", "data_base64": bad_b64}, "POST")
        invalid_handled = (st_bad == 400 and res_bad.get("ok") is False)

        # 5b. High-res image (3600x2400) -> safely capped at max_dim=2048
        hi_path = os.path.join(OUT_V11, "huge_3600x2400.png")
        hi_im = Image.new("RGB", (3600, 2400), (245, 245, 250))
        ImageDraw.Draw(hi_im).rectangle([1200, 600, 2400, 1800], fill=(16, 185, 129))
        hi_im.save(hi_path)
        hi_dir = os.path.join(OUT_V11, "huge_proj")
        hi_doc = run_redesign(hi_path, hi_dir, "huge_proj", upscale_2x=True, max_dim=2048)
        hi_qa = export_and_qa_all(STUDIO_ROOT, hi_dir)
        highres_ok = (max(hi_doc["width"], hi_doc["height"]) <= 2048 and hi_qa["overall_passed"])

        # 5c. Stress: 32 layers across 6 groups
        stress_dir = os.path.join(OUT_V11, "stress_32_layers")
        os.makedirs(os.path.join(stress_dir, "layers"), exist_ok=True)
        s_layers = []
        bg_p = os.path.join(stress_dir, "layers", "bg.png")
        Image.new("RGBA", (640, 640), (20, 25, 35, 255)).save(bg_p)
        s_layers.append(make_layer("00_BG", "background", "layers/bg.png", 0, 0, 640, 640, z_index=0, group="Group_0_BG"))
        for i in range(1, 32):
            lp = os.path.join(stress_dir, "layers", f"l_{i:02d}.png")
            Image.new("RGBA", (60, 60), ((i * 37) % 255, (i * 73) % 255, 200, 255)).save(lp)
            s_layers.append(make_layer(f"Layer_{i:02d}", "object", f"layers/l_{i:02d}.png", (i % 8) * 70 + 20, (i // 8) * 110 + 20, 60, 60, z_index=i, group=f"Group_{(i % 5) + 1}"))
        s_doc = create_document("stress_32", "Stress 32 Layers", "GENERATE", 640, 640, s_layers)
        save_document(s_doc, stress_dir)
        s_qa = export_and_qa_all(STUDIO_ROOT, stress_dir)
        stress_ok = (s_qa["overall_passed"] and s_qa["qa3_psd"]["layer_count"] == 32 and s_qa["qa3_psd"]["group_count"] == 6 and s_qa["qa3_psd"]["decoded_pixel_layers"] == 32)

        # 5d. Non-existent font fallback -> renders non-empty Vietnamese text
        f_fb = _load_font(STUDIO_ROOT, 40, bold=True)
        t_im, tw, th = render_text_layer_png("KIỂM TRA FONT DỰ PHÒNG", f_fb, (255, 255, 255), 500)
        font_fb_ok = (tw > 40 and th > 20 and int(np.sum(np.array(t_im)[:, :, 3] > 0)) > 100)

        # 5e. Corrupt PSD file -> verify MUST reject (returncode != 0)
        corrupt_psd = os.path.join(OUT_V11, "corrupt.psd")
        with open(corrupt_psd, "wb") as f:
            f.write(b"8BPS_CORRUPTED_BYTES_0000")
        vr_bad = subprocess.run(["node", os.path.join(STUDIO_ROOT, "core", "psd_bridge.js"), "verify", corrupt_psd], capture_output=True, text=True, check=False)
        corrupt_rejected = (vr_bad.returncode != 0)

        # 5f. Low disk threshold check & malformed JSON API check
        low_disk_check = check_project_integrity(stress_dir, min_free_mb=999999999)
        low_disk_caught = (not low_disk_check["ok"] and len(low_disk_check["warnings"]) >= 1)

        req_mal = urllib.request.Request(f"{base_url}/api/generate", data=b"{bad json", headers={"Content-Type": "application/json"}, method="POST")
        try:
            urllib.request.urlopen(req_mal, timeout=5)
            malformed_status = 200
        except urllib.error.HTTPError as e:
            malformed_status = e.code

        report.append({
            "test": "T5_Negative_Stress_EdgeCases",
            "passed": bool(invalid_handled and highres_ok and stress_ok and font_fb_ok and corrupt_rejected and low_disk_caught and malformed_status == 400),
            "invalid_image_400": invalid_handled,
            "highres_capped_ok": highres_ok,
            "stress_32layers_6groups_ok": stress_ok,
            "font_fallback_ok": font_fb_ok,
            "corrupt_psd_rejected": corrupt_rejected,
            "low_disk_guard_ok": low_disk_caught,
            "malformed_json_400": (malformed_status == 400),
        })
    finally:
        srv.shutdown()
        srv.server_close()
        for ep in created_ephemeral_pids:
            ep_dir = os.path.join(STUDIO_ROOT, "projects", ep)
            if os.path.exists(ep_dir):
                shutil.rmtree(ep_dir, ignore_errors=True)

    summary_path = os.path.join(OUT_V11, "v1_1_acceptance_report.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    all_pass = all(r["passed"] for r in report)
    for r in report:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['test']} -> {json.dumps(r, ensure_ascii=False)}")
    print(f"\nV1.1 ACCEPTANCE SUITE: {'ALL PASSED' if all_pass else 'FAILED'} ({sum(1 for r in report if r['passed'])}/{len(report)})")
    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
