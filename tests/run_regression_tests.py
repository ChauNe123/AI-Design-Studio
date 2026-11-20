"""Full 7-Dataset + MODE A/B + Live HTTP API + QA 1/2/3 Regression Test Suite."""
import base64
import json
import os
import shutil
import sys
import threading
import time
import urllib.request
from PIL import Image, ImageDraw, ImageFont

STUDIO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STUDIO_ROOT not in sys.path:
    sys.path.insert(0, STUDIO_ROOT)

from core.design_document import load_document, validate_document
from core.generate_engine import run_generate
from core.image_analyzer import run_redesign
from core.knowledge_base import KnowledgeBase
from core.qa_engine import export_and_qa_all
from core.retouch_analyzer import run_product_retouch_pipeline
from core.server import StudioHandler
from http.server import ThreadingHTTPServer

FIXTURES = os.path.join(STUDIO_ROOT, "tests", "fixtures")
TEST_OUT = os.path.join(STUDIO_ROOT, "tests", "output")


def prepare_fixtures():
    os.makedirs(FIXTURES, exist_ok=True)
    # 1. Simple background + 1 shape
    im1 = Image.new("RGB", (600, 600), (240, 245, 255))
    d1 = ImageDraw.Draw(im1)
    d1.ellipse([180, 180, 420, 420], fill=(37, 99, 235))
    im1.save(os.path.join(FIXTURES, "01_simple_bg.png"))

    # 2. Multi-text poster
    im2 = Image.new("RGB", (700, 500), (15, 23, 42))
    d2 = ImageDraw.Draw(im2)
    f_lg = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 44)
    f_sm = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 24)
    d2.text((50, 60), "SAFE DRIVE PRO", fill=(16, 185, 129), font=f_lg)
    d2.text((50, 140), "AI COLLISION WARNING", fill=(255, 255, 255), font=f_sm)
    d2.text((50, 200), "LANE DEPARTURE ALERT", fill=(250, 204, 21), font=f_sm)
    im2.save(os.path.join(FIXTURES, "02_multi_text.png"))

    # 3. Multi-product on clean background
    im3 = Image.new("RGB", (800, 500), (245, 245, 245))
    d3 = ImageDraw.Draw(im3)
    d3.rounded_rectangle([60, 120, 280, 380], radius=20, fill=(220, 38, 38))
    d3.rounded_rectangle([320, 100, 520, 400], radius=20, fill=(16, 185, 129))
    d3.ellipse([560, 150, 740, 330], fill=(245, 158, 11))
    im3.save(os.path.join(FIXTURES, "03_multi_product.png"))

    # 4. White-background product with white interior detail
    im4 = Image.new("RGB", (600, 600), (255, 255, 255))
    d4 = ImageDraw.Draw(im4)
    d4.rounded_rectangle([180, 120, 420, 480], radius=30, fill=(20, 20, 25))
    d4.rounded_rectangle([200, 150, 400, 450], radius=20, fill=(255, 255, 255))
    d4.ellipse([260, 260, 340, 340], fill=(16, 185, 129))
    im4.save(os.path.join(FIXTURES, "04_white_bg_product.png"))

    # 5. Transparent PNG product
    trans_src = r"D:\CanvaSafeDrive\✅ SAFE DRIVE.png"
    if os.path.exists(trans_src):
        shutil.copyfile(trans_src, os.path.join(FIXTURES, "05_transparent_png.png"))
    else:
        im5 = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
        d5 = ImageDraw.Draw(im5)
        d5.ellipse([80, 80, 420, 420], fill=(16, 185, 129, 255))
        im5.save(os.path.join(FIXTURES, "05_transparent_png.png"))

    # 6. Real Canva design
    canva_src = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\.user_uploaded\media_1794903847507_0b7fa85b.jpg"
    if os.path.exists(canva_src):
        shutil.copyfile(canva_src, os.path.join(FIXTURES, "06_canva_design.jpg"))
    else:
        shutil.copyfile(os.path.join(FIXTURES, "02_multi_text.png"), os.path.join(FIXTURES, "06_canva_design.jpg"))

    # 7. Overlapping elements poster
    ov_src = r"C:\Users\BUM\.gemini\antigravity\brain\7a3bd732-b5a7-4da2-8ae9-7603555447fd\.user_uploaded\media_1794885806500_463cbbd0.jpg"
    if os.path.exists(ov_src):
        shutil.copyfile(ov_src, os.path.join(FIXTURES, "07_overlapping.jpg"))
    else:
        im7 = Image.new("RGB", (600, 600), (255, 180, 0))
        d7 = ImageDraw.Draw(im7)
        d7.rectangle([100, 200, 450, 450], fill=(30, 30, 30))
        d7.ellipse([250, 120, 520, 390], fill=(220, 38, 38))
        im7.save(os.path.join(FIXTURES, "07_overlapping.jpg"))


def run_all_tests():
    if os.path.exists(TEST_OUT):
        shutil.rmtree(TEST_OUT)
    os.makedirs(TEST_OUT, exist_ok=True)
    prepare_fixtures()

    results = []

    # Test MODE A across all 7 datasets
    cases = [
        ("01_simple_bg", "01_simple_bg.png", False),
        ("02_multi_text", "02_multi_text.png", False),
        ("03_multi_product", "03_multi_product.png", False),
        ("04_white_bg_product", "04_white_bg_product.png", False),
        ("05_transparent_png", "05_transparent_png.png", False),
        ("06_canva_design", "06_canva_design.jpg", True),
        ("07_overlapping", "07_overlapping.jpg", True),
    ]

    for pid, fname, up2x in cases:
        t0 = time.time()
        pdir = os.path.join(TEST_OUT, pid)
        doc = run_redesign(os.path.join(FIXTURES, fname), pdir, pid, title=pid, upscale_2x=up2x)
        errs = validate_document(doc)
        qa = export_and_qa_all(STUDIO_ROOT, pdir)
        dt = round(time.time() - t0, 2)
        results.append({
            "test": f"MODE_A::{pid}",
            "passed": qa["overall_passed"] and len(errs) == 0,
            "layers": len(doc["layers"]),
            "size": f"{doc['width']}x{doc['height']}",
            "psd_bytes": qa["qa3_psd"].get("psd_bytes", 0),
            "psd_layers_readback": qa["qa3_psd"].get("layer_count", 0),
            "mae": qa["qa2_composite"].get("mae_vs_source"),
            "time_s": dt,
            "issues": errs + qa["qa1_layers"]["issues"] + qa["qa2_composite"]["issues"] + qa["qa3_psd"].get("issues", []),
        })

    # Test MODE B (GENERATE)
    t0 = time.time()
    kb = KnowledgeBase(os.path.join(STUDIO_ROOT, "knowledge"))
    k_ctx = kb.query_for_brief("tech_automotive", "safedrive")
    g_dir = os.path.join(TEST_OUT, "08_mode_b_generate")
    g_doc = run_generate(
        STUDIO_ROOT,
        g_dir,
        "08_mode_b_generate",
        {
            "title": "Regression Generate Test",
            "canvas_preset": "portrait_4x5",
            "layout": "tech_dark_glow",
            "headline": "LÁI XE AN TOÀN HƠN",
            "subheadline": "Cảnh báo AI sớm • Theo dõi khoảng cách chuẩn xác",
            "cta_text": "Tải ngay SafeDrive • safedrive.com",
            "product_paths": [os.path.join(FIXTURES, "04_white_bg_product.png")],
            "logo_path": os.path.join(FIXTURES, "05_transparent_png.png"),
        },
        k_ctx,
    )
    g_qa = export_and_qa_all(STUDIO_ROOT, g_dir)
    results.append({
        "test": "MODE_B::generate_portrait_4x5",
        "passed": g_qa["overall_passed"],
        "layers": len(g_doc["layers"]),
        "size": f"{g_doc['width']}x{g_doc['height']}",
        "psd_bytes": g_qa["qa3_psd"].get("psd_bytes", 0),
        "psd_layers_readback": g_qa["qa3_psd"].get("layer_count", 0),
        "text_layers_in_psd": g_qa["qa3_psd"].get("text_layer_count", 0),
        "time_s": round(time.time() - t0, 2),
        "issues": g_qa["qa1_layers"]["issues"] + g_qa["qa2_composite"]["issues"] + g_qa["qa3_psd"].get("issues", []),
    })

    # Test MODE B Art Movement Presets (Bauhaus & Pop Art) + DVF Aesthetic QA Checks
    t0 = time.time()
    am_passed = True
    am_issues = []
    am_psd_bytes = 0
    am_layers = 0
    for style_key, style_title in [("bauhaus", "Bauhaus Minimalist Poster"), ("pop_art", "Pop Art Neon Promo")]:
        am_dir = os.path.join(STUDIO_ROOT, "projects", f"09_mode_b_{style_key}")
        if os.path.exists(am_dir):
            shutil.rmtree(am_dir)
        os.makedirs(am_dir, exist_ok=True)
        am_doc = run_generate(
            STUDIO_ROOT,
            am_dir,
            f"09_mode_b_{style_key}",
            {
                "title": style_title,
                "canvas_preset": "square_1080",
                "art_movement": style_key,
                "headline": "THIẾT KẾ CHUẨN MỸ THUẬT",
                "subheadline": f"Phong cách {style_key.upper()} • Tỷ lệ phân cấp chuẩn DVF",
                "cta_text": "Khám phá ngay • AI Design Studio",
                "product_paths": [os.path.join(FIXTURES, "04_white_bg_product.png")],
            },
            k_ctx,
        )
        am_qa = export_and_qa_all(STUDIO_ROOT, am_dir)
        aes = am_qa["qa2_composite"].get("aesthetic_checks", {})
        h_ratio = (aes.get("hierarchy_ratio") or {}).get("ratio") or 0
        if not am_qa["overall_passed"] or h_ratio < 2.0:
            am_passed = False
            am_issues.append(f"{style_key}: qa={am_qa['overall_passed']}, ratio={h_ratio}")
        am_psd_bytes += am_qa["qa3_psd"].get("psd_bytes", 0)
        am_layers = len(am_doc["layers"])

    results.append({
        "test": "MODE_B::test_art_movement_presets",
        "passed": am_passed,
        "layers": am_layers,
        "size": "1080x1080 (bauhaus+pop_art)",
        "psd_bytes": am_psd_bytes,
        "time_s": round(time.time() - t0, 2),
        "issues": am_issues,
    })

    # Test Pro Product Retouching & Intrinsic Lighting 4-Block Pipeline (RETOUCH)
    t0 = time.time()
    retouch_src = r"D:\AI\TESTER\scratch_psd\preview_before_real.jpg"
    if not os.path.exists(retouch_src):
        retouch_src = os.path.join(FIXTURES, "04_white_bg_product.png")
    rt_dir = os.path.join(TEST_OUT, "10_mode_retouch_18layer")
    rt_res = run_product_retouch_pipeline(
        image_path=retouch_src,
        project_dir=rt_dir,
        project_id="10_mode_retouch_18layer",
        title="Retouch Live Adjustment Test",
        max_dim=1200,
    )
    rt_errs = validate_document(rt_res["document"])
    rt_qa = export_and_qa_all(STUDIO_ROOT, rt_dir)
    rt_qa3 = rt_qa.get("qa3_psd", {})
    rt_issues = list(rt_errs) + list(rt_qa["qa1_layers"]["issues"]) + list(rt_qa["qa2_composite"]["issues"]) + list(rt_qa3.get("issues", []))
    rt_passed = (
        len(rt_errs) == 0
        and bool(rt_qa["overall_passed"])
        and rt_qa3.get("adjustment_layer_count", 0) == 13
        and rt_qa3.get("masked_layer_count", 0) >= 8
        and rt_qa3.get("clipped_layer_count", 0) == 6
        and bool(rt_qa3.get("composite_decoded"))
        and os.path.exists(os.path.join(rt_dir, rt_res["before_after_comparison"]))
        and os.path.exists(os.path.join(rt_dir, rt_res["masks_contact_sheet"]))
    )
    results.append({
        "test": "RETOUCH::test_18_layer_product_retouch_psd",
        "passed": rt_passed,
        "layers": len(rt_res["document"]["layers"]),
        "adjustment_layers": rt_qa3.get("adjustment_layer_count", 0),
        "masks": rt_qa3.get("masked_layer_count", 0),
        "clipping": rt_qa3.get("clipped_layer_count", 0),
        "size": f"{rt_res['document']['width']}x{rt_res['document']['height']}",
        "psd_bytes": rt_qa3.get("psd_bytes", 0),
        "time_s": round(time.time() - t0, 2),
        "issues": rt_issues,
    })

    # Test Live HTTP API Integration (real server on ephemeral port 8799)
    srv = ThreadingHTTPServer(("127.0.0.1", 8799), StudioHandler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        with urllib.request.urlopen("http://127.0.0.1:8799/api/system", timeout=5) as r:
            sys_resp = json.loads(r.read().decode("utf-8"))
        with open(os.path.join(FIXTURES, "01_simple_bg.png"), "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        req = urllib.request.Request(
            "http://127.0.0.1:8799/api/redesign",
            data=json.dumps({"title": "API Test", "filename": "01_simple_bg.png", "upscale_2x": False, "data_base64": b64}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as r:
            rd_resp = json.loads(r.read().decode("utf-8"))
        api_pid = rd_resp["document"]["project_id"]
        # Test saving an edit (move layer + change opacity) via /api/project/<id>/save
        layers_edit = rd_resp["document"]["layers"]
        if len(layers_edit) > 1:
            layers_edit[1]["x"] += 15
            layers_edit[1]["opacity"] = 0.85
        req2 = urllib.request.Request(
            f"http://127.0.0.1:8799/api/project/{api_pid}/save",
            data=json.dumps({"layers": layers_edit}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req2, timeout=45) as r:
            sv_resp = json.loads(r.read().decode("utf-8"))
        # Test /api/retouch HTTP endpoint as well
        req_rt = urllib.request.Request(
            "http://127.0.0.1:8799/api/retouch",
            data=json.dumps({"title": "API Retouch Test", "filename": "01_simple_bg.png", "max_dim": 600, "data_base64": b64}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_rt, timeout=90) as r:
            rt_api_resp = json.loads(r.read().decode("utf-8"))
        rt_api_pid = (rt_api_resp.get("document") or {}).get("project_id", "")
        if rt_api_pid and os.path.exists(os.path.join(STUDIO_ROOT, "projects", rt_api_pid)):
            shutil.rmtree(os.path.join(STUDIO_ROOT, "projects", rt_api_pid))

        # Cleanup ephemeral test project inside studio/projects
        api_pdir = os.path.join(STUDIO_ROOT, "projects", api_pid)
        if os.path.exists(api_pdir):
            shutil.rmtree(api_pdir)
        results.append({
            "test": "API::system_redesign_save_export",
            "passed": bool(
                sys_resp.get("ok")
                and rd_resp.get("ok")
                and sv_resp.get("ok")
                and sv_resp["qa"]["overall_passed"]
                and rt_api_resp.get("ok")
                and rt_api_resp["qa"]["overall_passed"]
                and rt_api_resp["qa"]["qa3_psd"].get("adjustment_layer_count") == 13
            ),
            "layers": len(sv_resp["document"]["layers"]),
            "psd_bytes": sv_resp["qa"]["qa3_psd"].get("psd_bytes", 0),
            "issues": [],
        })
    finally:
        srv.shutdown()
        srv.server_close()

    report_path = os.path.join(TEST_OUT, "regression_summary.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    passed_all = all(r["passed"] for r in results)
    for r in results:
        print(f"[{'PASS' if r['passed'] else 'FAIL'}] {r['test']} | layers={r.get('layers')} | psd={r.get('psd_bytes')}B | issues={r.get('issues')}")
    print(f"\nOVERALL REGRESSION: {'ALL PASSED' if passed_all else 'SOME FAILED'} ({sum(1 for r in results if r['passed'])}/{len(results)})")
    if not passed_all:
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
