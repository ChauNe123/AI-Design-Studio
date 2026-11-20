"""AI Design Studio — Local Windows Backend Server (http://127.0.0.1:8788)."""
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

STUDIO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STUDIO_ROOT not in sys.path:
    sys.path.insert(0, STUDIO_ROOT)

from core.design_document import load_document, make_layer, save_document
from core.generate_engine import _load_font, render_text_layer_png, run_generate
from core.image_analyzer import run_redesign
from core.knowledge_base import KnowledgeBase
from core.qa_engine import export_and_qa_all

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
                "studio_root": STUDIO_ROOT,
                "os": platform.platform(),
                "python": sys.version.split()[0],
                "cpu_cores": os.cpu_count(),
                "disk_d_free_gb": round(free / (1024**3), 1),
                "photoshop_available": os.path.exists(cfg["photoshop_exe"]),
                "photosop_available": os.path.exists(cfg["photosop_exe"]),
                "projects_count": len(list_projects()),
            })
        elif clean == "/api/projects":
            self._send_json({"ok": True, "projects": list_projects()})
        elif clean.startswith("/api/project/"):
            pid = clean.split("/api/project/", 1)[1].strip("/")
            pdir = os.path.join(PROJECTS_DIR, pid)
            if not os.path.exists(os.path.join(pdir, "design_document.json")):
                self._send_json({"ok": False, "error": "Project not found"}, 404)
                return
            self._send_json({"ok": True, "document": load_document(pdir)})
        elif clean == "/api/assets":
            self._send_json({"ok": True, "assets": list_assets()})
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

                doc = run_redesign(
                    image_path=inp_path,
                    project_dir=pdir,
                    project_id=pid,
                    title=data.get("title") or os.path.splitext(fname)[0],
                    upscale_2x=bool(data.get("upscale_2x", cfg["upscale_2x"])),
                    max_dim=int(cfg.get("max_dim", 2048)),
                )
                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({"ok": True, "document": load_document(pdir), "qa": qa})

            elif clean == "/api/generate":
                data = self._read_json()
                pid = f"generate_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
                pdir = os.path.join(PROJECTS_DIR, pid)
                os.makedirs(pdir, exist_ok=True)

                prod_paths = []
                for rel in data.get("product_rel_paths", []):
                    ap = os.path.join(STUDIO_ROOT, rel.replace("/", os.sep))
                    if os.path.exists(ap):
                        prod_paths.append(ap)
                logo_rel = data.get("logo_rel_path", "")
                logo_abs = os.path.join(STUDIO_ROOT, logo_rel.replace("/", os.sep)) if logo_rel else ""

                k_ctx = kb.query_for_brief(
                    industry=data.get("industry", "tech_automotive"),
                    brand_id=data.get("brand_id", ""),
                )
                brief = {
                    "title": data.get("title") or data.get("headline") or "New Design",
                    "canvas_preset": data.get("canvas_preset", "square_1080"),
                    "layout": data.get("layout", "tech_dark_glow"),
                    "industry": data.get("industry", "tech_automotive"),
                    "headline": data.get("headline", "SẢN PHẨM THÔNG MINH"),
                    "subheadline": data.get("subheadline", "Giải pháp công nghệ chuyên nghiệp"),
                    "cta_text": data.get("cta_text", "Liên hệ ngay • safedrive.com"),
                    "bg_color": data.get("bg_color", ""),
                    "bg_alt_color": data.get("bg_alt_color", ""),
                    "accent_color": data.get("accent_color", ""),
                    "text_color": data.get("text_color", ""),
                    "product_paths": prod_paths,
                    "logo_path": logo_abs,
                    "remove_white_bg": bool(data.get("remove_white_bg", True)),
                }
                run_generate(STUDIO_ROOT, pdir, pid, brief, k_ctx)
                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({"ok": True, "document": load_document(pdir), "qa": qa})

            elif clean.startswith("/api/project/") and clean.endswith("/save"):
                pid = clean.split("/api/project/", 1)[1].rsplit("/save", 1)[0].strip("/")
                pdir = os.path.join(PROJECTS_DIR, pid)
                doc = load_document(pdir)
                incoming = self._read_json()

                # Merge layer edits & re-render edited text layers if text changed
                incoming_map = {l["id"]: l for l in incoming.get("layers", [])}
                updated_layers = []
                for lyr in doc.get("layers", []):
                    if lyr["id"] not in incoming_map:
                        continue  # Deleted by user
                    upd = incoming_map[lyr["id"]]
                    lyr["x"] = int(round(upd.get("x", lyr["x"])))
                    lyr["y"] = int(round(upd.get("y", lyr["y"])))
                    lyr["z_index"] = int(upd.get("z_index", lyr["z_index"]))
                    lyr["visible"] = bool(upd.get("visible", lyr["visible"]))
                    lyr["opacity"] = float(upd.get("opacity", lyr["opacity"]))
                    lyr["blend_mode"] = upd.get("blend_mode", lyr.get("blend_mode", "normal"))
                    meta = lyr.get("metadata") or {}
                    for k in ("scale", "hue", "sat", "bright"):
                        if k in (upd.get("metadata") or {}):
                            meta[k] = upd["metadata"][k]
                    lyr["metadata"] = meta

                    # If editable text changed, re-render PNG so preview and PSD stay synced
                    if lyr["type"] == "text" and upd.get("text_data") and lyr.get("text_data"):
                        new_td = upd["text_data"]
                        old_td = lyr["text_data"]
                        if (
                            new_td.get("text") != old_td.get("text")
                            or new_td.get("font_size") != old_td.get("font_size")
                            or new_td.get("color") != old_td.get("color")
                        ):
                            f_sz = int(new_td.get("font_size", 42))
                            col = tuple(new_td.get("color", [255, 255, 255]))
                            t_im, tw, th = render_text_layer_png(
                                new_td.get("text", ""),
                                _load_font(STUDIO_ROOT, f_sz, bold=True),
                                col,
                                max_width=int(doc["width"] * 0.85),
                            )
                            rel = lyr["source_file"] or f"layers/{lyr['id']}.png"
                            t_im.save(os.path.join(pdir, rel))
                            lyr["source_file"] = rel
                            lyr["width"] = tw
                            lyr["height"] = th
                            lyr["text_data"] = new_td

                    updated_layers.append(lyr)

                # Add any newly created user text layers
                existing_ids = {l["id"] for l in updated_layers}
                for upd in incoming.get("layers", []):
                    if upd["id"] not in existing_ids and upd.get("type") == "text":
                        td = upd.get("text_data") or {"text": "NEW TEXT", "font_size": 48, "color": [255, 255, 255]}
                        t_im, tw, th = render_text_layer_png(
                            td.get("text", "NEW TEXT"),
                            _load_font(STUDIO_ROOT, int(td.get("font_size", 48)), bold=True),
                            tuple(td.get("color", [255, 255, 255])),
                            max_width=int(doc["width"] * 0.85),
                        )
                        rel = f"layers/{upd['id']}.png"
                        t_im.save(os.path.join(pdir, rel))
                        updated_layers.append(make_layer(
                            layer_id=upd["id"],
                            name=upd.get("name", "Text_New"),
                            layer_type="text",
                            source_file=rel,
                            x=upd.get("x", 60),
                            y=upd.get("y", 60),
                            width=tw,
                            height=th,
                            z_index=upd.get("z_index", len(updated_layers)),
                            visible=upd.get("visible", True),
                            opacity=upd.get("opacity", 1.0),
                            group="3_Brand_&_Texts",
                            text_data=td,
                        ))

                doc["layers"] = updated_layers
                save_document(doc, pdir)
                qa = export_and_qa_all(STUDIO_ROOT, pdir)
                self._send_json({"ok": True, "document": load_document(pdir), "qa": qa})

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
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, 500)


def run_server(port: int = 8788):
    os.makedirs(PROJECTS_DIR, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", port), StudioHandler)
    print(f"AI Design Studio running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
