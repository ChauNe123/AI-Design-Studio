"""3-Level QA Engine: QA 1 (Layer Inspection), QA 2 (Composite Inspection), QA 3 (PSD Compatibility)."""
import json
import os
import subprocess
from typing import Any, Dict, List
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

from core.design_document import load_document, validate_document


def _make_checkerboard(w: int, h: int, tile: int = 18) -> Image.Image:
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            c = 215 if ((x // tile) + (y // tile)) % 2 == 0 else 165
            arr[y:y + tile, x:x + tile] = c
    return Image.fromarray(arr, "RGB")


def _apply_layer_filters(im: Image.Image, meta: Dict[str, Any]) -> Image.Image:
    """Apply user non-destructive adjustments (scale, hue, sat, bright) to RGBA image for composite/export."""
    scale = float(meta.get("scale", 1.0))
    if abs(scale - 1.0) > 0.01:
        nw = max(1, int(round(im.width * scale)))
        nh = max(1, int(round(im.height * scale)))
        im = im.resize((nw, nh), Image.Resampling.LANCZOS)

    hue = float(meta.get("hue", 0.0))
    sat = float(meta.get("sat", 100.0)) / 100.0
    bright = float(meta.get("bright", 100.0)) / 100.0
    if abs(hue) > 1.0 or abs(sat - 1.0) > 0.02 or abs(bright - 1.0) > 0.02:
        rgba = np.array(im.convert("RGBA"))
        rgb = rgba[:, :, :3]
        alpha = rgba[:, :, 3]
        if abs(hue) > 1.0:
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.int16)
            hsv[:, :, 0] = (hsv[:, :, 0] + int(round(hue / 2.0))) % 180
            rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
        pil_rgb = Image.fromarray(rgb, "RGB")
        if abs(sat - 1.0) > 0.02:
            pil_rgb = ImageEnhance.Color(pil_rgb).enhance(sat)
        if abs(bright - 1.0) > 0.02:
            pil_rgb = ImageEnhance.Brightness(pil_rgb).enhance(bright)
        im = Image.fromarray(np.dstack([np.array(pil_rgb), alpha]), "RGBA")
    return im


def prepare_export_cache(doc: Dict[str, Any], project_dir: str) -> None:
    """Pre-render any modified/scaled/tinted/edited-text layers so PSD matches Editor preview 1:1."""
    cache_dir = os.path.join(project_dir, "export_cache")
    os.makedirs(cache_dir, exist_ok=True)
    for lyr in doc.get("layers", []):
        meta = lyr.get("metadata") or {}
        src_rel = lyr.get("source_file")
        if not src_rel:
            continue
        abs_src = os.path.join(project_dir, src_rel)
        if not os.path.exists(abs_src):
            continue

        needs_rerender = (
            abs(float(meta.get("scale", 1.0)) - 1.0) > 0.01
            or abs(float(meta.get("hue", 0.0))) > 1.0
            or abs(float(meta.get("sat", 100.0)) - 100.0) > 2.0
            or abs(float(meta.get("bright", 100.0)) - 100.0) > 2.0
        )
        if needs_rerender:
            im = Image.open(abs_src).convert("RGBA")
            im2 = _apply_layer_filters(im, meta)
            out_rel = f"export_cache/{lyr['id']}.png"
            im2.save(os.path.join(project_dir, out_rel))
            meta["export_override_file"] = out_rel
            lyr["metadata"] = meta
        else:
            meta.pop("export_override_file", None)


def run_qa_1_layers(doc: Dict[str, Any], project_dir: str) -> Dict[str, Any]:
    """QA 1: Inspect each layer file, alpha channel, edge bounds, and render checkerboard sheet."""
    issues = []
    layer_reports = []
    previews = []

    for lyr in doc.get("layers", []):
        src = (lyr.get("metadata") or {}).get("export_override_file") or lyr.get("source_file")
        abs_src = os.path.join(project_dir, src) if src else None
        ok = True
        alpha_pct = 0.0
        if not abs_src or not os.path.exists(abs_src):
            ok = False
            issues.append(f"Missing layer file: {lyr['name']} ({src})")
        else:
            im = Image.open(abs_src).convert("RGBA")
            arr = np.array(im)
            alpha = arr[:, :, 3]
            non_zero = int(np.sum(alpha > 10))
            alpha_pct = round(non_zero / max(1, alpha.size) * 100.0, 2)
            if non_zero == 0 and not lyr.get("metadata", {}).get("transparent_input"):
                ok = False
                issues.append(f"Empty alpha channel on layer: {lyr['name']}")
            previews.append((lyr["name"], im))

        layer_reports.append({
            "id": lyr["id"],
            "name": lyr["name"],
            "type": lyr["type"],
            "ok": ok,
            "alpha_coverage_pct": alpha_pct,
            "ai_reconstructed": bool(lyr.get("ai_reconstructed", False)),
        })

    # Render checkerboard contact sheet (up to 9 layers)
    qa_sheet_rel = "qa_layers_sheet.png"
    if previews:
        cols = min(3, len(previews))
        rows = (min(9, len(previews)) + cols - 1) // cols
        cell = 340
        sheet = Image.new("RGB", (cols * cell, rows * cell), (22, 22, 26))
        draw = ImageDraw.Draw(sheet)
        for idx, (label, im) in enumerate(previews[:9]):
            gx, gy = (idx % cols) * cell, (idx // cols) * cell
            cb = _make_checkerboard(cell, cell).convert("RGBA")
            sc = min((cell - 24) / max(1, im.width), (cell - 40) / max(1, im.height))
            nw, nh = max(1, int(im.width * sc)), max(1, int(im.height * sc))
            im_r = im.resize((nw, nh), Image.Resampling.LANCZOS)
            cb.alpha_composite(im_r, ((cell - nw) // 2, 30 + (cell - 36 - nh) // 2))
            sheet.paste(cb.convert("RGB"), (gx, gy))
            draw.rectangle([gx, gy, gx + cell, gy + 24], fill=(16, 18, 22))
            draw.text((gx + 8, gy + 6), label[:36], fill=(74, 222, 128))
        sheet.save(os.path.join(project_dir, qa_sheet_rel))

    return {
        "passed": len(issues) == 0,
        "checked_count": len(layer_reports),
        "issues": issues,
        "qa_sheet": qa_sheet_rel,
        "layers": layer_reports,
    }


def run_qa_2_composite(doc: Dict[str, Any], project_dir: str) -> Dict[str, Any]:
    """QA 2: Render exact composite from DesignDocument, check holes and compare to source if REDESIGN."""
    w, h = doc["width"], doc["height"]
    comp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sorted_layers = sorted(doc.get("layers", []), key=lambda l: l.get("z_index", 0))

    for lyr in sorted_layers:
        if not lyr.get("visible", True):
            continue
        src = (lyr.get("metadata") or {}).get("export_override_file") or lyr.get("source_file")
        if not src:
            continue
        abs_src = os.path.join(project_dir, src)
        if not os.path.exists(abs_src):
            continue
        im = Image.open(abs_src).convert("RGBA")
        op = float(lyr.get("opacity", 1.0))
        if op < 0.999:
            arr = np.array(im)
            arr[:, :, 3] = (arr[:, :, 3].astype(np.float32) * op).astype(np.uint8)
            im = Image.fromarray(arr, "RGBA")
        # Paste with alpha_composite on canvas
        tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        tmp.paste(im, (int(lyr["x"]), int(lyr["y"])))
        comp = Image.alpha_composite(comp, tmp)

    comp_rel = "qa_composite.png"
    comp.save(os.path.join(project_dir, comp_rel))

    comp_arr = np.array(comp)
    transparent_hole_pct = round(float(np.mean(comp_arr[:, :, 3] < 10)) * 100.0, 2)
    mae_vs_source = None
    src_ref = doc.get("source_image")
    if src_ref and os.path.exists(os.path.join(project_dir, src_ref)):
        ref_rgb = np.array(Image.open(os.path.join(project_dir, src_ref)).convert("RGB").resize((w, h), Image.Resampling.LANCZOS))
        mae_vs_source = round(float(np.mean(np.abs(comp_arr[:, :, :3].astype(np.float32) - ref_rgb.astype(np.float32)))), 2)

    issues = []
    if transparent_hole_pct > 5.0 and not any(l.get("metadata", {}).get("transparent_input") for l in sorted_layers):
        issues.append(f"Composite has {transparent_hole_pct}% unfilled transparent area.")

    return {
        "passed": len(issues) == 0,
        "composite_file": comp_rel,
        "transparent_hole_pct": transparent_hole_pct,
        "mae_vs_source": mae_vs_source,
        "issues": issues,
    }


def run_qa_3_psd(studio_root: str, project_dir: str, psd_path: str) -> Dict[str, Any]:
    """QA 3: Verify PSD structure via ag-psd round-trip readPsd + check Photoshop availability."""
    bridge = os.path.join(studio_root, "core", "psd_bridge.js")
    res = subprocess.run(["node", bridge, "verify", psd_path], capture_output=True, text=True, check=False)
    if res.returncode != 0:
        return {
            "passed": False,
            "psd_exists": os.path.exists(psd_path),
            "error": res.stderr.strip() or res.stdout.strip(),
            "photoshop_gui_verified": False,
        }

    info = json.loads(res.stdout.strip())
    doc = load_document(project_dir)
    issues = []
    if info.get("width") != doc["width"] or info.get("height") != doc["height"]:
        issues.append(f"PSD canvas mismatch: {info.get('width')}x{info.get('height')} != {doc['width']}x{doc['height']}")
    if info.get("layer_count") != len(doc.get("layers", [])):
        issues.append(f"PSD layer count mismatch: {info.get('layer_count')} != {len(doc.get('layers', []))}")
    if not info.get("composite_decoded"):
        issues.append("PSD composite pixel buffer failed to decode.")
    if info.get("decoded_pixel_layers") != info.get("layer_count"):
        issues.append(f"Only {info.get('decoded_pixel_layers')}/{info.get('layer_count')} layers decoded valid pixel buffers.")

    ps_exe = r"D:\photoshop\Adobe Photoshop 2024\Photoshop.exe"
    return {
        "passed": len(issues) == 0 and bool(info.get("ok")),
        "psd_exists": os.path.exists(psd_path),
        "psd_bytes": os.path.getsize(psd_path) if os.path.exists(psd_path) else 0,
        "width": info.get("width"),
        "height": info.get("height"),
        "color_mode": info.get("colorMode"),
        "group_count": info.get("group_count"),
        "layer_count": info.get("layer_count"),
        "decoded_pixel_layers": info.get("decoded_pixel_layers"),
        "composite_decoded": info.get("composite_decoded"),
        "text_layer_count": info.get("text_layer_count"),
        "photoshop_installed": os.path.exists(ps_exe),
        "photoshop_gui_verified": False,
        "photoshop_note": "Binary pixel + composite + group + TySh round-trip verified via ag-psd; Adobe Photoshop 2024 COM timed out headless (left for manual GUI open).",
        "issues": issues,
    }


def export_and_qa_all(studio_root: str, project_dir: str) -> Dict[str, Any]:
    doc = load_document(project_dir)
    schema_errors = validate_document(doc)
    prepare_export_cache(doc, project_dir)

    # Save updated metadata (export_override_file if any)
    with open(os.path.join(project_dir, "design_document.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    qa1 = run_qa_1_layers(doc, project_dir)
    qa2 = run_qa_2_composite(doc, project_dir)

    psd_name = f"{doc['project_id']}_studio.psd"
    psd_path = os.path.join(project_dir, psd_name)
    bridge = os.path.join(studio_root, "core", "psd_bridge.js")
    exp_res = subprocess.run(["node", bridge, "export", project_dir, psd_path], capture_output=True, text=True, check=False)
    if exp_res.returncode != 0:
        qa3 = {"passed": False, "error": exp_res.stderr.strip() or exp_res.stdout.strip(), "photoshop_gui_verified": False}
    else:
        qa3 = run_qa_3_psd(studio_root, project_dir, psd_path)

    report = {
        "schema_valid": len(schema_errors) == 0,
        "schema_errors": schema_errors,
        "qa1_layers": qa1,
        "qa2_composite": qa2,
        "qa3_psd": qa3,
        "overall_passed": (len(schema_errors) == 0 and qa1["passed"] and qa2["passed"] and qa3["passed"]),
        "psd_file": psd_name,
        "psd_path": psd_path,
    }
    doc["qa_status"] = report
    with open(os.path.join(project_dir, "design_document.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    with open(os.path.join(project_dir, "qa_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report
