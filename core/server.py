"""AI Design Studio v1.2 — Local Windows Backend Server (http://127.0.0.1:8788)."""
import base64
import json
import os
import platform
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote
import cv2
import numpy as np
from PIL import Image, ImageDraw

STUDIO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STUDIO_ROOT not in sys.path:
    sys.path.insert(0, STUDIO_ROOT)

from core.ai_providers import AIProviderManager
from core.design_document import (
    default_adjustments,
    default_effects,
    load_document,
    make_layer,
    make_semantic_object,
    save_document,
)
from core.effects_engine import render_layer_non_destructive
from core.generate_engine import _load_font, generate_layout_variants, render_text_layer_png, run_generate
from core.image_analyzer import run_redesign
from core.knowledge_base import KnowledgeBase
from core.project_manager import (
    apply_group_operation,
    check_autosave_recovery,
    check_project_integrity,
    clear_autosave,
    list_versions,
    restore_version,
    save_version,
    write_autosave,
)
from core.banner_decomposer import run_banner_decomposition_pipeline
from core.qa_engine import export_and_qa_all
from core.reconstruction_engine import reconstruct_region
from core.reference_analyzer import analyze_reference_image
from core.retouch_analyzer import run_product_retouch_pipeline
from core.segmentation_engine import analyze_mask_quality, apply_mask_to_source, refine_mask, segment_interactive
from core.semantic_analyzer import run_semantic_redesign
from core.typography_engine import list_local_fonts, render_styled_text

UI_DIR = os.path.join(STUDIO_ROOT, "ui")
PROJECTS_DIR = os.path.join(STUDIO_ROOT, "projects")
ASSETS_DIR = os.path.join(STUDIO_ROOT, "assets")
SETTINGS_PATH = os.path.join(STUDIO_ROOT, "settings.json")

DEFAULT_SETTINGS = {
    "upscale_2x": True,
    "max_dim": 2048,
    "photoshop_exe": r"D:\photoshop\Adobe Photoshop 2024\Photoshop.exe",
    "photosop_exe": r"D:\KBDobe_Hub_Windows_x64\KBDobe_Hub\Apps\PhoToSop\PhoToSop.exe",
    "default_canvas": "square_1080",
}

kb = KnowledgeBase(os.path.join(STUDIO_ROOT, "knowledge"))
provider_mgr = AIProviderManager(STUDIO_ROOT)


def get_settings() -> dict:
    if not os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_SETTINGS, f, ensure_ascii=False, indent=2)
        return dict(DEFAULT_SETTINGS)
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return {**DEFAULT_SETTINGS, **json.load(f)}


def save_settings(new_cfg: dict) -> dict:
    merged = {**get_settings(), **new_cfg}
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    return merged


def list_assets() -> dict:
    out = {"products": [], "logos": [], "fonts": [], "references": []}
    for cat in out:
        d = os.path.join(ASSETS_DIR, cat)
        if not os.path.exists(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.startswith("."):
                continue
            full = os.path.join(d, fn)
            if os.path.isfile(full):
                out[cat].append({
                    "name": fn,
                    "rel_path": f"assets/{cat}/{fn}",
                    "abs_path": full,
                    "size": os.path.getsize(full),
                })
    return out


def list_projects() -> list:
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    items = []
    for pid in sorted(os.listdir(PROJECTS_DIR), reverse=True):
        pdir = os.path.join(PROJECTS_DIR, pid)
        doc_path = os.path.join(pdir, "design_document.json")
        if os.path.isfile(doc_path):
            try:
                doc = load_document(pdir)
                qa = doc.get("qa_status") or {}
                items.append({
                    "project_id": doc["project_id"],
                    "title": doc.get("title", pid),
                    "mode": doc.get("mode", "REDESIGN"),
                    "schema_version": doc.get("schema_version", "1.0.0"),
                    "width": doc.get("width"),
                    "height": doc.get("height"),
                    "layer_count": len(doc.get("layers", [])),
                    "updated_at": doc.get("updated_at"),
                    "qa_passed": bool(qa.get("overall_passed")),
                    "psd_file": qa.get("psd_file"),
                    "composite_preview": f"/projects/{pid}/qa_composite.png" if os.path.exists(os.path.join(pdir, "qa_composite.png")) else None,
                })
            except Exception:
                continue
    return items


def _resolve_rel_paths(rel_list: list) -> list:
    out = []
    for rel in (rel_list or []):
        if not rel:
            continue
        ap = os.path.join(STUDIO_ROOT, rel.replace("/", os.sep))
        if os.path.exists(ap):
            out.append(ap)
    return out


def _render_text_from_dict(td: dict, default_font_file: str = "") -> Image.Image:
    col = tuple(int(c) for c in td.get("color", [255, 255, 255])[:3])
    s_col = tuple(int(c) for c in td.get("stroke_color", [0, 0, 0])[:3])
    sh_col = tuple(int(c) for c in td.get("shadow_color", [0, 0, 0])[:3])
    gl_col = tuple(int(c) for c in td.get("glow_color", [16, 185, 129])[:3])
    gr_c2 = tuple(int(c) for c in td.get("gradient_c2", [16, 185, 129])[:3])
    ff = td.get("font_file") or default_font_file
    if not ff or not os.path.exists(ff):
        # Match by font name in local fonts
        lf = list_local_fonts()
        want = (td.get("font") or "").lower()
        found = next((f["file"] for f in lf if want and want in f["name"].lower()), None)
        ff = found or (lf[0]["file"] if lf else "")

    return render_styled_text(
        text=td.get("text", "TEXT"),
        font_file=ff,
        font_size=int(td.get("font_size", 42)),
        color=col,
        align=td.get("align", "left"),
        tracking=int(td.get("tracking", 0)),
        leading=int(td.get("leading", 10)),
        stroke_enabled=bool(td.get("stroke_enabled", False)),
        stroke_color=s_col,
        stroke_width=int(td.get("stroke_width", 3)),
        shadow_enabled=bool(td.get("shadow_enabled", False)),
        shadow_color=sh_col,
        shadow_offset=(int(td.get("shadow_dx", 4)), int(td.get("shadow_dy", 6))),
        shadow_blur=int(td.get("shadow_blur", 6)),
        glow_enabled=bool(td.get("glow_enabled", False)),
        glow_color=gl_col,
        glow_radius=int(td.get("glow_radius", 10)),
        gradient_enabled=bool(td.get("gradient_enabled", False)),
        gradient_c2=gr_c2,
        extrude_3d_depth=int(td.get("extrude_3d_depth", 0)),
        rotation=float(td.get("rotation", 0.0)),
    )


class StudioHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        return json.loads(raw.decode("utf-8"))

    def translate_path(self, path):
        clean = unquote(path.split("?", 1)[0])
        if clean.startswith("/projects/") or clean.startswith("/assets/"):
            rel = clean.lstrip("/").replace("/", os.sep)
            return os.path.join(STUDIO_ROOT, rel)
        if clean == "/" or clean == "":
            return os.path.join(UI_DIR, "index.html")
        return os.path.join(UI_DIR, clean.lstrip("/").replace("/", os.sep))

    def do_GET(self):
        clean = unquote(self.path.split("?", 1)[0])
        if clean == "/api/system":
            cfg = get_settings()
            total, used, free = shutil.disk_usage("D:/")
            self._send_json({
                "ok": True,
                "version": "1.5.0",
                "studio_root": STUDIO_ROOT,
                "os": platform.platform(),
                "python": sys.version.split()[0],
                "cpu_cores": os.cpu_count(),
                "disk_d_free_gb": round(free / (1024**3), 1),
                "photoshop_available": os.path.exists(cfg["photoshop_exe"]),
                "photosop_available": os.path.exists(cfg["photosop_exe"]),
                "projects_count": len(list_projects()),
                "ai_mode": provider_mgr.get_public_status().get("mode", "LOCAL_ONLY"),
            })
        elif clean == "/api/projects":
            self._send_json({"ok": True, "projects": list_projects()})
        elif clean == "/api/projects/remix_catalog":
            catalog = []
            for p in list_projects():
                pdir = os.path.join(PROJECTS_DIR, p["project_id"])
                try:
                    d = load_document(pdir)
                    pal = list((d.get("brand") or {}).get("extracted_palette") or [])
                    fonts_used = []
                    importable_layers = []
                    for lyr in d.get("layers", []):
                        if lyr["type"] == "text" and lyr.get("text_data"):
                            f = lyr["text_data"].get("font")
                            if f and f not in fonts_used:
                                fonts_used.append(f)
                        if lyr["type"] != "background" and lyr.get("source_file"):
                            importable_layers.append({
                                "id": lyr["id"],
                                "name": lyr["name"],
                                "type": lyr["type"],
                                "group": lyr.get("group", "Main"),
                                "thumb": f"/projects/{p['project_id']}/{lyr['source_file']}",
                                "width": lyr.get("width", 0),
                                "height": lyr.get("height", 0),
                            })
                    catalog.append({
                        "project_id": p["project_id"],
                        "title": d.get("title", p["project_id"]),
                        "mode": d.get("mode", "REDESIGN"),
                        "preview": p.get("composite_preview"),
                        "palette": pal,
                        "fonts": fonts_used[:5],
                        "layers": importable_layers[:20],
                    })
                except Exception:
                    continue
            self._send_json({"ok": True, "catalog": catalog})
        elif clean.startswith("/api/project/"):
            pid = clean.split("/api/project/", 1)[1].strip("/")
            pdir = os.path.join(PROJECTS_DIR, pid)
            if not os.path.exists(os.path.join(pdir, "design_document.json")):
                self._send_json({"ok": False, "error": "Project not found"}, 404)
                return
            self._send_json({
                "ok": True,
                "document": load_document(pdir),
                "versions": list_versions(pdir),
                "integrity": check_project_integrity(pdir),
                "autosave_recovery": check_autosave_recovery(pdir),
            })
        elif clean == "/api/assets":
            self._send_json({"ok": True, "assets": list_assets()})
        elif clean == "/api/fonts":
            self._send_json({"ok": True, "fonts": list_local_fonts()})
        elif clean == "/api/providers":
            self._send_json({"ok": True, "providers_state": provider_mgr.get_public_status()})
        elif clean == "/api/knowledge":
            self._send_json({"ok": True, "knowledge": kb.load()})
        elif clean == "/api/settings":
            self._send_json({"ok": True, "settings": get_settings()})
        else:
            super().do_GET()

    def do_POST(self):
        clean = unquote(self.path.split("?", 1)[0])
        try:
            if clean == "/api/settings":
                data = self._read_json()
                self._send_json({"ok": True, "settings": save_settings(data)})

            elif clean == "/api/providers/update":
                data = self._read_json()
                st = provider_mgr.update_provider(
                    provider_id=data.get("provider_id", ""),
                    enabled=data.get("enabled"),
                    model_name=data.get("model_name"),
                    api_key=data.get("api_key"),
                    monthly_budget_usd=data.get("monthly_budget_usd"),
                    mode=data.get("mode"),
                )
                self._send_json({"ok": True, "providers_state": st})

            elif clean == "/api/providers/test":
                data = self._read_json()
                self._send_json(provider_mgr.test_connection(data.get("provider_id", "local_engine")))

            elif clean == "/api/providers/preview_permission":
                data = self._read_json()
                prev = provider_mgr.prepare_cloud_permission_preview(
                    provider_id=data.get("provider_id", "local_engine"),
                    task_name=data.get("task", "inpaint"),
                    image_desc=data.get("image_desc", "Selected mask region"),
                    region_box=data.get("region_box"),
                )
                self._send_json({"ok": True, "preview": prev})

            elif clean == "/api/assets/upload":
                data = self._read_json()
                cat = data.get("category", "products")
                if cat not in ("products", "logos", "references"):
                    cat = "products"
                fname = os.path.basename(data.get("filename", f"asset_{uuid.uuid4().hex[:6]}.png"))
                b64 = data["data_base64"].split(",")[-1]
                out_path = os.path.join(ASSETS_DIR, cat, fname)
                with open(out_path, "wb") as f:
                    f.write(base64.b64decode(b64))
                self._send_json({"ok": True, "asset": {"name": fname, "rel_path": f"assets/{cat}/{fname}", "abs_path": out_path}})

            elif clean == "/api/knowledge/lesson":
                data = self._read_json()
                db = kb.add_lesson(
                    lesson_id=f"lesson_{uuid.uuid4().hex[:6]}",
                    status=data.get("status", "NOTE"),
                    issue=data.get("issue", ""),
                    fix=data.get("fix", ""),
                )
                self._send_json({"ok": True, "knowledge": db})

            elif clean == "/api/knowledge/analyze_reference":
                data = self._read_json()
                fname = os.path.basename(data.get("filename", f"ref_{uuid.uuid4().hex[:6]}.png"))
                b64 = data["data_base64"].split(",")[-1]
                ref_path = os.path.join(ASSETS_DIR, "references", fname)
                with open(ref_path, "wb") as f:
                    f.write(base64.b64decode(b64))
                analysis = analyze_reference_image(ref_path, ref_name=data.get("name") or fname)
                db = kb.save_reference_analysis(analysis)
                self._send_json({"ok": True, "analysis": analysis, "knowledge": db})

            elif clean == "/api/redesign":
                data = self._read_json()
                cfg = get_settings()
                pid = f"redesign_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
                pdir = os.path.join(PROJECTS_DIR, pid)
                os.makedirs(pdir, exist_ok=True)

                fname = os.path.basename(data.get("filename", "input.png"))
                inp_path = os.path.join(pdir, f"input_{fname}")
                b64 = data["data_base64"].split(",")[-1]
                with open(inp_path, "wb") as f:
                    f.write(base64.b64decode(b64))

                semantic_mode = bool(data.get("semantic_mode", True))
                try:
                    if semantic_mode:
                        doc = run_semantic_redesign(
                            image_path=inp_path,
                            project_dir=pdir,
                            project_id=pid,
                            title=data.get("title") or os.path.splitext(fname)[0],
                            upscale_2x=bool(data.get("upscale_2x", cfg["upscale_2x"])),
                            max_dim=int(cfg.get("max_dim", 2048)),
                            use_rmbg=bool(data.get("use_rmbg", True)),
                            use_ocr=bool(data.get("use_ocr", True)),
                            banner_mode=bool(data.get("banner_mode", False)),
                        )
                    else:
                        doc = run_redesign(
                            image_path=inp_path,
                            project_dir=pdir,
                            project_id=pid,
                            title=data.get("title") or os.path.splitext(fname)[0],
                            upscale_2x=bool(data.get("upscale_2x", cfg["upscale_2x"])),
                            max_dim=int(cfg.get("max_dim", 2048)),
                        )
                        save_version(doc, pdir, note="Initial MODE A decomposition")
                except Exception as exc:
                    shutil.rmtree(pdir, ignore_errors=True)
                    self._send_json({"ok": False, "error": f"Invalid or unreadable image: {exc}"}, 400)
                    return

                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({"ok": True, "document": load_document(pdir), "qa": qa, "versions": list_versions(pdir)})

            elif clean == "/api/retouch":
                data = self._read_json()
                cfg = get_settings()
                pid = f"retouch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
                pdir = os.path.join(PROJECTS_DIR, pid)
                os.makedirs(pdir, exist_ok=True)

                inp_path = data.get("image_path")
                fname = os.path.basename(data.get("filename", "product.png"))
                if not inp_path or not os.path.exists(inp_path):
                    if not data.get("data_base64"):
                        shutil.rmtree(pdir, ignore_errors=True)
                        self._send_json({"ok": False, "error": "Missing image payload or valid image_path"}, 400)
                        return
                    inp_path = os.path.join(pdir, f"input_{fname}")
                    b64 = data["data_base64"].split(",")[-1]
                    with open(inp_path, "wb") as f:
                        f.write(base64.b64decode(b64))

                cutout_path = data.get("cutout_path")
                try:
                    rt_res = run_product_retouch_pipeline(
                        image_path=inp_path,
                        project_dir=pdir,
                        project_id=pid,
                        title=data.get("title") or f"Retouch - {os.path.splitext(fname)[0]}",
                        cutout_path=cutout_path if (cutout_path and os.path.exists(cutout_path)) else None,
                        max_dim=int(data.get("max_dim") or cfg.get("max_dim", 2048)),
                    )
                except Exception as exc:
                    shutil.rmtree(pdir, ignore_errors=True)
                    self._send_json({"ok": False, "error": f"Retouch pipeline failed: {exc}"}, 400)
                    return

                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({
                    "ok": True,
                    "document": load_document(pdir),
                    "qa": qa,
                    "versions": list_versions(pdir),
                    "before_after_url": f"/projects/{pid}/{rt_res['before_after_comparison']}",
                    "masks_sheet_url": f"/projects/{pid}/{rt_res['masks_contact_sheet']}",
                    "psd_url": f"/projects/{pid}/{qa['psd_file']}",
                })

            elif clean == "/api/banner_decompose":
                data = self._read_json()
                cfg = get_settings()
                pid = f"banner_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
                pdir = os.path.join(PROJECTS_DIR, pid)
                os.makedirs(pdir, exist_ok=True)

                inp_path = data.get("image_path")
                fname = os.path.basename(data.get("filename", "banner.jpg"))
                if not inp_path or not os.path.exists(inp_path):
                    if not data.get("data_base64"):
                        shutil.rmtree(pdir, ignore_errors=True)
                        self._send_json({"ok": False, "error": "Missing image payload or valid image_path"}, 400)
                        return
                    inp_path = os.path.join(pdir, f"input_{fname}")
                    b64 = data["data_base64"].split(",")[-1]
                    with open(inp_path, "wb") as f:
                        f.write(base64.b64decode(b64))

                try:
                    bn_res = run_banner_decomposition_pipeline(
                        image_path=inp_path,
                        project_dir=pdir,
                        project_id=pid,
                        title=data.get("title") or f"Banner - {os.path.splitext(fname)[0]}",
                        max_dim=int(data.get("max_dim") or cfg.get("max_dim", 2048)),
                    )
                except Exception as exc:
                    shutil.rmtree(pdir, ignore_errors=True)
                    self._send_json({"ok": False, "error": f"Banner decomposition failed: {exc}"}, 400)
                    return

                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({
                    "ok": True,
                    "document": load_document(pdir),
                    "qa": qa,
                    "versions": list_versions(pdir),
                    "progression_url": f"/projects/{pid}/{bn_res['banner_progression_grid']}",
                    "layers_sheet_url": f"/projects/{pid}/{bn_res['banner_layers_sheet']}",
                    "psd_url": f"/projects/{pid}/{qa['psd_file']}",
                })

            elif clean == "/api/generate":
                data = self._read_json()
                pid = f"generate_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
                pdir = os.path.join(PROJECTS_DIR, pid)
                os.makedirs(pdir, exist_ok=True)
                k_ctx = kb.query_for_brief(industry=data.get("industry", "tech_automotive"), brand_id=data.get("brand_id", ""))
                brief = {
                    "title": data.get("title") or data.get("headline") or "New Design",
                    "canvas_preset": data.get("canvas_preset", "square_1080"),
                    "layout": data.get("layout", "tech_dark_glow"),
                    "art_movement": data.get("art_movement", "none"),
                    "color_harmony": data.get("color_harmony", "none"),
                    "industry": data.get("industry", "tech_automotive"),
                    "headline": data.get("headline", "SẢN PHẨM THÔNG MINH"),
                    "subheadline": data.get("subheadline", "Giải pháp công nghệ chuyên nghiệp"),
                    "cta_text": data.get("cta_text", "Liên hệ ngay • safedrive.com"),
                    "bullets": data.get("bullets") or [],
                    "bg_color": data.get("bg_color", ""),
                    "bg_alt_color": data.get("bg_alt_color", ""),
                    "accent_color": data.get("accent_color", ""),
                    "text_color": data.get("text_color", ""),
                    "product_paths": _resolve_rel_paths(data.get("product_rel_paths")),
                    "logo_path": (_resolve_rel_paths([data.get("logo_rel_path")]) or [""])[0],
                    "reference_paths": _resolve_rel_paths(data.get("reference_rel_paths")),
                    "remove_white_bg": bool(data.get("remove_white_bg", True)),
                }
                run_generate(STUDIO_ROOT, pdir, pid, brief, k_ctx)
                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({"ok": True, "document": load_document(pdir), "qa": qa, "versions": list_versions(pdir)})

            elif clean == "/api/generate_variants":
                data = self._read_json()
                base_id = f"var_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
                k_ctx = kb.query_for_brief(industry=data.get("industry", "tech_automotive"), brand_id=data.get("brand_id", ""))
                brief = {
                    "title": data.get("title") or data.get("headline") or "Concept",
                    "canvas_preset": data.get("canvas_preset", "square_1080"),
                    "art_movement": data.get("art_movement", "none"),
                    "color_harmony": data.get("color_harmony", "none"),
                    "industry": data.get("industry", "tech_automotive"),
                    "headline": data.get("headline", "SẢN PHẨM THÔNG MINH"),
                    "subheadline": data.get("subheadline", "Giải pháp công nghệ chuyên nghiệp"),
                    "cta_text": data.get("cta_text", "Liên hệ ngay • safedrive.com"),
                    "bullets": data.get("bullets") or [],
                    "bg_color": data.get("bg_color", ""),
                    "accent_color": data.get("accent_color", ""),
                    "text_color": data.get("text_color", ""),
                    "product_paths": _resolve_rel_paths(data.get("product_rel_paths")),
                    "logo_path": (_resolve_rel_paths([data.get("logo_rel_path")]) or [""])[0],
                    "reference_paths": _resolve_rel_paths(data.get("reference_rel_paths")),
                    "remove_white_bg": bool(data.get("remove_white_bg", True)),
                }
                variants = generate_layout_variants(STUDIO_ROOT, PROJECTS_DIR, base_id, brief, k_ctx)
                out_vars = []
                for v in variants:
                    qa = export_and_qa_all(STUDIO_ROOT, v["project_dir"])
                    out_vars.append({
                        "variant_label": v["variant_label"],
                        "layout": v["layout"],
                        "project_id": v["project_id"],
                        "composite_preview": f"/projects/{v['project_id']}/qa_composite.png",
                        "qa_passed": qa["overall_passed"],
                    })
                self._send_json({"ok": True, "variants": out_vars})

            elif clean.startswith("/api/project/") and clean.endswith("/segment"):
                # Interactive SlimSAM / GrabCut segmentation + non-destructive extraction
                pid = clean.split("/api/project/", 1)[1].rsplit("/segment", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                doc = load_document(pdir)
                data = self._read_json()

                src_path = os.path.join(pdir, doc.get("source_image") or "source_reference.png")
                if not os.path.exists(src_path):
                    self._send_json({"ok": False, "error": "Source reference image not found"}, 404)
                    return

                seg_id = uuid.uuid4().hex[:6]
                mask_rel = f"masks/seg_{seg_id}.png"
                mask_abs = os.path.join(pdir, mask_rel)
                raw_box = data.get("box")
                sam_box = None
                if raw_box and len(raw_box) == 4:
                    bx, by, bw, bh = [int(v) for v in raw_box]
                    sam_box = [bx, by, bx + bw, by + bh]
                seg_res = segment_interactive(
                    image_path=src_path,
                    out_mask_path=mask_abs,
                    points=data.get("points"),
                    labels=data.get("labels"),
                    box=sam_box,
                    mask_level=data.get("mask_level"),
                    use_sam=bool(data.get("use_sam", True)),
                    tmp_dir=os.path.join(pdir, "masks"),
                )
                refine_mask(
                    mask_abs,
                    expand_px=int(data.get("expand_px", 0)),
                    feather_px=int(data.get("feather_px", 1)),
                    fill_holes=bool(data.get("fill_holes", True)),
                    remove_specks_min_area=int(data.get("min_speck_area", 60)),
                )
                q_info = analyze_mask_quality(src_path, mask_abs)

                layer_name = data.get("layer_name") or f"Segmented_{seg_id}"
                rgba_rel = f"layers/{layer_name}_{seg_id}.png"
                rgba_abs = os.path.join(pdir, rgba_rel)
                ex = apply_mask_to_source(src_path, mask_abs, rgba_abs, decontaminate_edges=bool(data.get("decontaminate", True)))

                max_z = max([l.get("z_index", 0) for l in doc["layers"]] or [0])
                new_lyr = make_layer(
                    name=layer_name,
                    layer_type=data.get("category", "object"),
                    source_file=rgba_rel,
                    mask_file=mask_rel,
                    x=ex["x"], y=ex["y"], width=ex["width"], height=ex["height"],
                    z_index=max_z + 1,
                    group=data.get("group", "4_Foreground_Segmented"),
                    confidence_score=float(seg_res.get("iou_score", 0.8)),
                    warnings=q_info.get("warnings", []),
                    metadata={"seg_engine": seg_res.get("engine"), "mask_quality": q_info},
                )
                doc["layers"].append(new_lyr)
                doc.setdefault("semantic_objects", []).append(make_semantic_object(
                    object_id=f"obj_seg_{seg_id}",
                    object_name=layer_name,
                    object_category=data.get("category", "foreground_object"),
                    bounding_box=[ex["x"], ex["y"], ex["width"], ex["height"]],
                    z_index=max_z + 1,
                    confidence_score=float(seg_res.get("iou_score", 0.8)),
                    segmentation_mask=mask_rel,
                    source_asset=rgba_rel,
                    linked_layer_id=new_lyr["id"],
                ))

                # Optionally punch out / inpaint the segmented object from parent layer (e.g. moving motorbike off driver!)
                parent_id = data.get("carve_from_layer_id")
                if parent_id:
                    for plyr in doc["layers"]:
                        if plyr["id"] == parent_id and plyr.get("source_file"):
                            p_abs = os.path.join(pdir, plyr["source_file"])
                            if os.path.exists(p_abs):
                                p_im = Image.open(p_abs).convert("RGBA")
                                p_arr = np.array(p_im)
                                m_full = cv2.imdecode(np.fromfile(mask_abs, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                                px0, py0 = plyr["x"], plyr["y"]
                                ph0, pw0 = p_arr.shape[:2]
                                sub_m = m_full[py0:py0 + ph0, px0:px0 + pw0]
                                if sub_m.shape[:2] == p_arr.shape[:2]:
                                    # Carve alpha cleanly so extracted sub-object doesn't duplicate
                                    p_arr[:, :, 3] = np.where(sub_m > 127, 0, p_arr[:, :, 3])
                                    Image.fromarray(p_arr, "RGBA").save(p_abs)
                                    plyr.setdefault("reconstruction_history", []).append({
                                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                                        "pixel_origin": "user_edited",
                                        "note": f"Carved out {layer_name} non-destructively.",
                                    })

                save_document(doc, pdir)
                save_version(doc, pdir, note=f"Segmented {layer_name} ({seg_res.get('engine')})")
                self._send_json({
                    "ok": True,
                    "layer": new_lyr,
                    "seg_result": seg_res,
                    "mask_quality": q_info,
                    "document": load_document(pdir),
                    "versions": list_versions(pdir),
                })

            elif clean.startswith("/api/project/") and clean.endswith("/reconstruct"):
                # Remove object / inpaint occluded region on target layer (default: Background)
                pid = clean.split("/api/project/", 1)[1].rsplit("/reconstruct", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                doc = load_document(pdir)
                data = self._read_json()

                target_id = data.get("target_layer_id") or doc["layers"][0]["id"]
                target_lyr = next((l for l in doc["layers"] if l["id"] == target_id), None)
                if not target_lyr or not target_lyr.get("source_file"):
                    self._send_json({"ok": False, "error": "Target layer not found"}, 404)
                    return

                t_abs = os.path.join(pdir, target_lyr["source_file"])
                t_im = Image.open(t_abs).convert("RGB")
                tw, th = t_im.size

                # Build mask from either mask_layer_id, box [x,y,w,h], or existing mask_file
                rec_id = uuid.uuid4().hex[:6]
                mask_abs = os.path.join(pdir, "masks", f"recon_{rec_id}.png")
                os.makedirs(os.path.dirname(mask_abs), exist_ok=True)
                m_canvas = Image.new("L", (tw, th), 0)
                if data.get("box"):
                    bx, by, bw, bh = [int(v) for v in data["box"]]
                    lx, ly = bx - target_lyr["x"], by - target_lyr["y"]
                    ImageDraw.Draw(m_canvas).rectangle([lx, ly, lx + bw, ly + bh], fill=255)
                elif data.get("mask_layer_id"):
                    m_lyr = next((l for l in doc["layers"] if l["id"] == data["mask_layer_id"]), None)
                    if m_lyr and m_lyr.get("source_file"):
                        ml_im = Image.open(os.path.join(pdir, m_lyr["source_file"])).convert("RGBA")
                        ml_a = ml_im.split()[3]
                        m_canvas.paste(ml_a, (m_lyr["x"] - target_lyr["x"], m_lyr["y"] - target_lyr["y"]))
                m_canvas.save(mask_abs)

                out_rel = f"layers/{target_lyr['id']}_recon_{rec_id}.png"
                out_abs = os.path.join(pdir, out_rel)
                rec_res = reconstruct_region(
                    image_path=t_abs,
                    mask_path=mask_abs,
                    out_image_path=out_abs,
                    mode=data.get("mode", "auto"),
                    provider_mgr=provider_mgr,
                    provider_id=data.get("provider_id", "local_engine"),
                    user_confirmed=bool(data.get("user_confirmed", False)),
                    prompt=data.get("prompt", ""),
                )
                target_lyr["source_file"] = out_rel
                target_lyr["ai_reconstructed"] = True
                target_lyr.setdefault("reconstruction_history", []).append(rec_res["history_entry"])
                if data.get("provider_id", "local_engine") != "local_engine":
                    doc.setdefault("api_tasks", []).append({
                        "provider_id": data.get("provider_id"),
                        "pixel_origin": rec_res["pixel_origin"],
                        "timestamp": rec_res["history_entry"]["timestamp"],
                    })

                save_document(doc, pdir)
                save_version(doc, pdir, note=f"Reconstructed {target_lyr['name']} ({rec_res['pixel_origin']})")
                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({"ok": True, "reconstruct": rec_res, "document": load_document(pdir), "qa": qa})

            elif clean.startswith("/api/project/") and clean.endswith("/layer_action"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/layer_action", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                doc = load_document(pdir)
                data = self._read_json()
                action = data.get("action")
                lid = data.get("layer_id")
                lyr = next((l for l in doc["layers"] if l["id"] == lid), None)
                if not lyr:
                    self._send_json({"ok": False, "error": "Layer not found"}, 404)
                    return

                if action == "duplicate":
                    copy_l = json.loads(json.dumps(lyr))
                    copy_l["id"] = f"lyr_{uuid.uuid4().hex[:8]}"
                    copy_l["name"] = f"{lyr['name']}_copy"
                    copy_l["x"] += 20
                    copy_l["y"] += 20
                    copy_l["z_index"] = max(x["z_index"] for x in doc["layers"]) + 1
                    doc["layers"].append(copy_l)
                elif action == "rename":
                    lyr["name"] = (data.get("new_name") or lyr["name"]).strip()
                elif action in ("lock", "unlock"):
                    lyr["locked"] = (action == "lock")
                elif action == "restore_original":
                    if lyr.get("original_source_file") and os.path.exists(os.path.join(pdir, lyr["original_source_file"])):
                        lyr["source_file"] = lyr["original_source_file"]
                        with Image.open(os.path.join(pdir, lyr["source_file"])) as orig_im:
                            lyr["width"], lyr["height"] = orig_im.size
                    lyr["adjustments"] = default_adjustments()
                    lyr["effects"] = default_effects()
                    lyr["rotation"] = 0.0
                    lyr["crop"] = None
                    lyr.setdefault("metadata", {})["scale"] = 1.0
                    lyr["metadata"].pop("export_override_file", None)
                elif action == "replace_asset":
                    b64 = data["data_base64"].split(",")[-1]
                    rep_rel = f"layers/replaced_{lid}_{uuid.uuid4().hex[:4]}.png"
                    with open(os.path.join(pdir, rep_rel), "wb") as f:
                        f.write(base64.b64decode(b64))
                    with Image.open(os.path.join(pdir, rep_rel)) as rim:
                        lyr["width"], lyr["height"] = rim.size
                    lyr["source_file"] = rep_rel
                else:
                    self._send_json({"ok": False, "error": f"Unknown layer_action: {action}"}, 400)
                    return

                save_document(doc, pdir)
                save_version(doc, pdir, note=f"Layer {action}: {lyr['name']}")
                self._send_json({"ok": True, "document": load_document(pdir), "versions": list_versions(pdir)})

            elif clean.startswith("/api/project/") and clean.endswith("/autosave"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/autosave", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                doc = load_document(pdir)
                incoming = self._read_json()
                doc["layers"] = incoming.get("layers", doc["layers"])
                write_autosave(doc, pdir)
                self._send_json({"ok": True, "autosaved_at": datetime.now().isoformat(timespec="seconds")})

            elif clean.startswith("/api/project/") and clean.endswith("/group"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/group", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                doc = load_document(pdir)
                data = self._read_json()
                doc = apply_group_operation(
                    doc,
                    action=data.get("action", ""),
                    group_name=data.get("group_name", ""),
                    new_name=data.get("new_name", ""),
                    layer_id=data.get("layer_id", ""),
                )
                save_document(doc, pdir)
                save_version(doc, pdir, note=f"Group {data.get('action')}: {data.get('group_name')}")
                self._send_json({"ok": True, "document": load_document(pdir), "versions": list_versions(pdir)})

            elif clean.startswith("/api/project/") and clean.endswith("/import_remix"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/import_remix", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                doc = load_document(pdir)
                data = self._read_json()
                src_pid = data.get("src_project_id", "")
                src_pdir = os.path.join(PROJECTS_DIR, src_pid)
                if not src_pid or not os.path.exists(os.path.join(src_pdir, "design_document.json")):
                    self._send_json({"ok": False, "error": "Source project not found"}, 404)
                    return

                src_doc = load_document(src_pdir)
                req_ids = set(data.get("layer_ids") or [])
                off_x = int(data.get("offset_x", 0))
                off_y = int(data.get("offset_y", 0))
                max_z = max([l.get("z_index", 0) for l in doc["layers"]] or [0])

                imported_count = 0
                os.makedirs(os.path.join(pdir, "layers"), exist_ok=True)
                for slyr in src_doc.get("layers", []):
                    if req_ids and slyr["id"] not in req_ids:
                        continue
                    if not req_ids and slyr["type"] == "background":
                        continue
                    new_l = json.loads(json.dumps(slyr))
                    nid = f"lyr_rmx_{uuid.uuid4().hex[:6]}"
                    new_l["id"] = nid
                    new_l["name"] = f"Remix_{slyr['name']}"
                    new_l["group"] = "6_Remixed_From_Old_Project"
                    new_l["x"] = int(slyr.get("x", 0)) + off_x
                    new_l["y"] = int(slyr.get("y", 0)) + off_y
                    max_z += 1
                    new_l["z_index"] = max_z
                    new_l["visible"] = True
                    new_l["locked"] = False
                    if slyr.get("source_file") and os.path.exists(os.path.join(src_pdir, slyr["source_file"])):
                        rel_copy = f"layers/{nid}.png"
                        shutil.copy2(os.path.join(src_pdir, slyr["source_file"]), os.path.join(pdir, rel_copy))
                        new_l["source_file"] = rel_copy
                        new_l["original_source_file"] = rel_copy
                    new_l.pop("mask_file", None)
                    doc["layers"].append(new_l)
                    imported_count += 1

                if data.get("apply_palette_style"):
                    src_pal = (src_doc.get("brand") or {}).get("extracted_palette") or []
                    src_txt = next((l for l in src_doc.get("layers", []) if l["type"] == "text" and l.get("text_data")), None)
                    for lyr in doc["layers"]:
                        if lyr["type"] == "text" and lyr.get("text_data") and src_txt:
                            std = src_txt["text_data"]
                            lyr["text_data"]["font"] = std.get("font", lyr["text_data"].get("font"))
                            if std.get("font_file"):
                                lyr["text_data"]["font_file"] = std["font_file"]
                            lyr["text_data"]["color"] = std.get("color", lyr["text_data"].get("color"))
                            lyr["text_data"]["stroke_enabled"] = bool(std.get("stroke_enabled", False))
                            if std.get("stroke_color"):
                                lyr["text_data"]["stroke_color"] = std["stroke_color"]
                            t_im = _render_text_from_dict(lyr["text_data"])
                            t_rel = lyr.get("source_file") or f"layers/{lyr['id']}.png"
                            t_im.save(os.path.join(pdir, t_rel))
                            lyr["source_file"] = t_rel
                            lyr["width"], lyr["height"] = t_im.width, t_im.height
                    doc.setdefault("brand", {})["remixed_from"] = src_pid
                    if src_pal:
                        doc["brand"]["remixed_palette"] = src_pal

                save_document(doc, pdir)
                save_version(doc, pdir, note=f"Remixed {imported_count} layer(s) from {src_pid}")
                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({
                    "ok": True,
                    "imported_count": imported_count,
                    "document": load_document(pdir),
                    "qa": qa,
                    "versions": list_versions(pdir),
                })

            elif clean.startswith("/api/project/") and clean.endswith("/restore"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/restore", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                data = self._read_json()
                if data.get("from_autosave"):
                    rec = check_autosave_recovery(pdir)
                    if not rec or not rec.get("document"):
                        self._send_json({"ok": False, "error": "No autosave draft available"}, 404)
                        return
                    save_document(rec["document"], pdir)
                    clear_autosave(pdir)
                else:
                    restore_version(pdir, data.get("version_id", ""))
                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({"ok": True, "document": load_document(pdir), "qa": qa, "versions": list_versions(pdir)})

            elif clean.startswith("/api/project/") and clean.endswith("/save"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/save", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                doc = load_document(pdir)
                incoming = self._read_json()

                incoming_map = {l["id"]: l for l in incoming.get("layers", [])}
                updated_layers = []
                for lyr in doc.get("layers", []):
                    if lyr["id"] not in incoming_map:
                        continue
                    upd = incoming_map[lyr["id"]]
                    if lyr.get("locked") and upd.get("locked", True):
                        # Respect lock except allowing unlock toggle
                        updated_layers.append(lyr)
                        continue
                    lyr["name"] = upd.get("name", lyr["name"])
                    lyr["x"] = int(round(upd.get("x", lyr["x"])))
                    lyr["y"] = int(round(upd.get("y", lyr["y"])))
                    lyr["z_index"] = int(upd.get("z_index", lyr["z_index"]))
                    lyr["visible"] = bool(upd.get("visible", lyr["visible"]))
                    lyr["locked"] = bool(upd.get("locked", lyr.get("locked", False)))
                    lyr["rotation"] = float(upd.get("rotation", lyr.get("rotation", 0.0)))
                    lyr["crop"] = upd.get("crop", lyr.get("crop"))
                    lyr["opacity"] = float(upd.get("opacity", lyr["opacity"]))
                    lyr["blend_mode"] = upd.get("blend_mode", lyr.get("blend_mode", "normal"))
                    lyr["group"] = upd.get("group", lyr.get("group", "Main"))
                    if "clipping" in upd:
                        lyr["clipping"] = bool(upd["clipping"])
                    if isinstance(upd.get("adjustment_data"), dict):
                        lyr["adjustment_data"] = upd["adjustment_data"]
                    lyr["adjustments"] = {**(lyr.get("adjustments") or default_adjustments()), **(upd.get("adjustments") or {})}
                    lyr["effects"] = {**(lyr.get("effects") or default_effects()), **(upd.get("effects") or {})}
                    if upd.get("text_reconstruction"):
                        lyr["text_reconstruction"] = {**(lyr.get("text_reconstruction") or {}), **upd["text_reconstruction"]}
                    meta = lyr.get("metadata") or {}
                    for k in ("scale", "hue", "sat", "bright"):
                        if k in (upd.get("metadata") or {}):
                            meta[k] = upd["metadata"][k]
                    meta.pop("text_dirty", None)
                    lyr["metadata"] = meta

                    if lyr["type"] == "text" and upd.get("text_data"):
                        new_td = upd["text_data"]
                        old_td = lyr.get("text_data") or {}
                        if new_td != old_td or upd.get("metadata", {}).get("text_dirty"):
                            t_im = _render_text_from_dict(new_td)
                            rel = lyr.get("source_file") or f"layers/{lyr['id']}.png"
                            t_im.save(os.path.join(pdir, rel))
                            lyr["source_file"] = rel
                            lyr["width"] = t_im.width
                            lyr["height"] = t_im.height
                            lyr["text_data"] = new_td

                    updated_layers.append(lyr)

                existing_ids = {l["id"] for l in updated_layers}
                for upd in incoming.get("layers", []):
                    if upd["id"] not in existing_ids and upd.get("type") == "text":
                        td = upd.get("text_data") or {"text": "NEW TEXT", "font_size": 48, "color": [255, 255, 255]}
                        t_im = _render_text_from_dict(td)
                        rel = f"layers/{upd['id']}.png"
                        t_im.save(os.path.join(pdir, rel))
                        updated_layers.append(make_layer(
                            layer_id=upd["id"],
                            name=upd.get("name", "Text_New"),
                            layer_type="text",
                            source_file=rel,
                            x=upd.get("x", 60),
                            y=upd.get("y", 60),
                            width=t_im.width,
                            height=t_im.height,
                            z_index=upd.get("z_index", len(updated_layers)),
                            visible=upd.get("visible", True),
                            opacity=upd.get("opacity", 1.0),
                            group=upd.get("group", "3_Logos_&_Typography"),
                            text_data=td,
                        ))

                doc["layers"] = updated_layers
                save_document(doc, pdir)
                clear_autosave(pdir)
                save_version(doc, pdir, note=incoming.get("note", "Editor save"))
                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({
                    "ok": True,
                    "document": load_document(pdir),
                    "qa": qa,
                    "versions": list_versions(pdir),
                    "integrity": check_project_integrity(pdir),
                })

            elif clean.startswith("/api/project/") and clean.endswith("/export_psd"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/export_psd", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({"ok": True, "qa": qa, "download_url": f"/projects/{pid}/{qa['psd_file']}"})

            elif clean.startswith("/api/project/") and clean.endswith("/open_folder"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/open_folder", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                if os.path.exists(pdir):
                    subprocess.Popen(["explorer", pdir])
                    self._send_json({"ok": True})
                else:
                    self._send_json({"ok": False, "error": "Not found"}, 404)

            elif clean.startswith("/api/project/") and clean.endswith("/open_photoshop"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/open_photoshop", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                doc = load_document(pdir)
                psd_file = (doc.get("qa_status") or {}).get("psd_file") or f"{pid}_studio.psd"
                psd_path = os.path.join(pdir, psd_file)
                cfg = get_settings()
                exe = cfg.get("photoshop_exe")
                if os.path.exists(exe) and os.path.exists(psd_path):
                    subprocess.Popen([exe, psd_path])
                    self._send_json({"ok": True, "launched": exe})
                else:
                    self._send_json({"ok": False, "error": "Photoshop exe or PSD not found"}, 404)
            else:
                self._send_json({"ok": False, "error": "Unknown endpoint"}, 404)
        except json.JSONDecodeError as exc:
            self._send_json({"ok": False, "error": f"Malformed JSON: {exc}"}, 400)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, 500)


def run_server(port: int = 8788):
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", port), StudioHandler)
    print(f"AI Design Studio v1.2 running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
