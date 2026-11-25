"""3-Level QA Engine: QA 1 (Layer Inspection), QA 2 (Composite Inspection), QA 3 (PSD Compatibility)."""
import json
import os
import subprocess
from typing import Any, Dict, List
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

from core.design_document import load_document, validate_document
from core.effects_engine import render_layer_non_destructive


def _make_checkerboard(w: int, h: int, tile: int = 18) -> Image.Image:
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            c = 215 if ((x // tile) + (y // tile)) % 2 == 0 else 165
            arr[y:y + tile, x:x + tile] = c
    return Image.fromarray(arr, "RGB")


def prepare_export_cache(doc: Dict[str, Any], project_dir: str) -> None:
    """Pre-render any modified/scaled/rotated/cropped/adjusted/effect layers using non-destructive engine."""
    cache_dir = os.path.join(project_dir, "export_cache")
    os.makedirs(cache_dir, exist_ok=True)
    for lyr in doc.get("layers", []):
        meta = lyr.get("metadata") or {}
        src_rel = lyr.get("original_source_file") or lyr.get("source_file")
        if not src_rel:
            continue
        abs_src = os.path.join(project_dir, src_rel)
        if not os.path.exists(abs_src):
            continue

        adj = lyr.get("adjustments") or {}
        eff = lyr.get("effects") or {}
        scale = float(meta.get("scale", 1.0))
        rotation = float(lyr.get("rotation", 0.0))
        crop_rect = lyr.get("crop")
        mask_rel = lyr.get("mask_file")
        mask_abs = os.path.join(project_dir, mask_rel) if mask_rel and os.path.exists(os.path.join(project_dir, mask_rel)) else None

        has_adj = (
            abs(float(adj.get("hue", meta.get("hue", 0.0)))) > 1.0
            or abs(float(adj.get("sat", meta.get("sat", 100.0))) - 100.0) > 2.0
            or abs(float(adj.get("bright", meta.get("bright", 100.0))) - 100.0) > 2.0
            or abs(float(adj.get("contrast", 100.0)) - 100.0) > 2.0
            or abs(float(adj.get("exposure", 0.0))) > 0.01
            or abs(float(adj.get("temperature", 0.0))) > 1.0
            or abs(float(adj.get("shadow", 0.0))) > 1.0
            or abs(float(adj.get("highlight", 0.0))) > 1.0
        )
        has_eff = (
            int(eff.get("feather", 0)) > 0
            or float(eff.get("blur", 0.0)) > 0.2
            or (eff.get("glow") or {}).get("enabled")
            or (eff.get("drop_shadow") or {}).get("enabled")
            or (eff.get("color_overlay") or {}).get("enabled")
            or (eff.get("gradient_overlay") or {}).get("enabled")
        )
        # If source_file is already freshly extracted/edited, use it when no extra non-destructive overrides exist
        active_src = os.path.join(project_dir, lyr.get("source_file") or src_rel)
        needs_rerender = (
            abs(scale - 1.0) > 0.01
            or abs(rotation) > 0.1
            or crop_rect is not None
            or has_adj
            or has_eff
        )
        if needs_rerender and os.path.exists(active_src):
            merged_adj = dict(adj)
            for k in ("hue", "sat", "bright"):
                if k in meta and abs(float(merged_adj.get(k, 0 if k == "hue" else 100)) - (0 if k == "hue" else 100)) < 0.1:
                    merged_adj[k] = meta[k]
            im2, (pad_x, pad_y) = render_layer_non_destructive(
                active_src,
                adjustments=merged_adj,
                effects=eff,
                scale=scale,
                rotation=rotation,
                crop_rect=crop_rect,
                mask_path=None,  # active_src already carries extracted alpha
            )
            out_rel = f"export_cache/{lyr['id']}.png"
            im2.save(os.path.join(project_dir, out_rel))
            meta["export_override_file"] = out_rel
            meta["export_offset"] = [int(pad_x), int(pad_y)]
            lyr["metadata"] = meta
        else:
            meta.pop("export_override_file", None)
            meta.pop("export_offset", None)


def run_qa_1_layers(doc: Dict[str, Any], project_dir: str) -> Dict[str, Any]:
    """QA 1: Inspect each layer file, alpha channel, edge bounds, and render checkerboard sheet."""
    issues = []
    layer_reports = []
    previews = []

    for lyr in doc.get("layers", []):
        if lyr.get("type") == "adjustment":
            has_adj = bool(lyr.get("adjustment_data"))
            ok = has_adj
            alpha_pct = 100.0
            if not has_adj:
                issues.append(f"Adjustment layer missing adjustment_data: {lyr['name']}")
            m_rel = lyr.get("mask_file")
            m_abs = os.path.join(project_dir, m_rel) if m_rel else None
            if m_rel and (not m_abs or not os.path.exists(m_abs)):
                ok = False
                issues.append(f"Missing mask file on adjustment layer {lyr['name']}: {m_rel}")
            elif m_abs and os.path.exists(m_abs):
                m_im = Image.open(m_abs).convert("L")
                m_arr = np.array(m_im)
                alpha_pct = round(float(np.mean(m_arr > 10)) * 100.0, 2)
                previews.append((f"[ADJ] {lyr['name']}", m_im.convert("RGBA")))
            layer_reports.append({
                "id": lyr["id"],
                "name": lyr["name"],
                "type": lyr["type"],
                "adjustment_type": (lyr.get("adjustment_data") or {}).get("type"),
                "has_mask": bool(m_rel),
                "clipping": bool(lyr.get("clipping", False)),
                "ok": ok,
                "alpha_coverage_pct": alpha_pct,
                "ai_reconstructed": bool(lyr.get("ai_reconstructed", False)),
            })
            continue

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

    # Render checkerboard contact sheet (all layers, up to 36 cells so multi-layer projects are fully visible)
    qa_sheet_rel = "qa_layers_sheet.png"
    if previews:
        shown = previews[:36]
        cols = min(4 if len(shown) > 9 else 3, len(shown))
        rows = (len(shown) + cols - 1) // cols
        cell = 320
        sheet = Image.new("RGB", (cols * cell, rows * cell), (22, 22, 26))
        draw = ImageDraw.Draw(sheet)
        for idx, (label, im) in enumerate(shown):
            gx, gy = (idx % cols) * cell, (idx // cols) * cell
            cb = _make_checkerboard(cell, cell).convert("RGBA")
            sc = min((cell - 20) / max(1, im.width), (cell - 38) / max(1, im.height))
            nw, nh = max(1, int(im.width * sc)), max(1, int(im.height * sc))
            im_r = im.resize((nw, nh), Image.Resampling.LANCZOS)
            cb.alpha_composite(im_r, ((cell - nw) // 2, 28 + (cell - 34 - nh) // 2))
            sheet.paste(cb.convert("RGB"), (gx, gy))
            draw.rectangle([gx, gy, gx + cell, gy + 24], fill=(16, 18, 22))
            draw.text((gx + 8, gy + 6), f"#{idx+1:02d} {label}"[:40], fill=(74, 222, 128))
        sheet.save(os.path.join(project_dir, qa_sheet_rel))

    return {
        "passed": len(issues) == 0,
        "checked_count": len(layer_reports),
        "issues": issues,
        "qa_sheet": qa_sheet_rel,
        "layers": layer_reports,
    }


def _wcag_luminance(rgb) -> float:
    vals = []
    for c in rgb[:3]:
        s = float(c) / 255.0
        vals.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]


def check_hierarchy_ratio(doc: Dict[str, Any]) -> Dict[str, Any]:
    """DVF Check: Verify Headline / Subheadline font size ratio >= 2.0x."""
    sizes = []
    for lyr in doc.get("layers", []):
        if lyr.get("type") == "text" and lyr.get("visible", True) and lyr.get("text_data"):
            sz = float(lyr["text_data"].get("font_size", 0))
            if sz > 0:
                sizes.append((sz, lyr.get("name", "")))
    if len(sizes) < 2:
        return {"checked": False, "ratio": None, "passed": True, "warning": ""}
    sizes.sort(key=lambda x: x[0], reverse=True)
    head_sz, sub_sz = sizes[0][0], sizes[1][0]
    ratio = round(head_sz / max(1.0, sub_sz), 2)
    passed = ratio >= 2.0
    warn = "" if passed else f"DVF Hierarchy Warning: Headline/Subheadline ratio {ratio}x < 2.0x ({head_sz}px vs {sub_sz}px)."
    return {"checked": True, "headline_px": head_sz, "subheadline_px": sub_sz, "ratio": ratio, "passed": passed, "warning": warn}


def check_negative_space_ratio(doc: Dict[str, Any]) -> Dict[str, Any]:
    """DVF Check: Estimate total non-background object+text area; warn if > 80% canvas (negative space < 20%)."""
    w, h = max(1, int(doc.get("width", 1))), max(1, int(doc.get("height", 1)))
    occ = np.zeros((h, w), dtype=np.uint8)
    for lyr in doc.get("layers", []):
        if not lyr.get("visible", True):
            continue
        if lyr.get("type") in ("background", "light_effect", "shape", "shadow"):
            continue
        x1 = max(0, int(lyr.get("x", 0)))
        y1 = max(0, int(lyr.get("y", 0)))
        x2 = min(w, x1 + max(0, int(lyr.get("width", 0))))
        y2 = min(h, y1 + max(0, int(lyr.get("height", 0))))
        if x2 > x1 and y2 > y1:
            occ[y1:y2, x1:x2] = 1
    occupied_pct = round(float(np.mean(occ > 0)) * 100.0, 2)
    neg_pct = round(100.0 - occupied_pct, 2)
    passed = occupied_pct <= 80.0
    warn = "" if passed else f"DVF Negative Space Warning: Objects/Text occupy {occupied_pct}% (>80% canvas; negative space={neg_pct}%)."
    return {"occupied_pct": occupied_pct, "negative_space_pct": neg_pct, "passed": passed, "warning": warn}


def check_text_contrast(doc: Dict[str, Any], bg_arr: np.ndarray) -> Dict[str, Any]:
    """DVF Check: Measure WCAG contrast ratio between each visible text layer color and underlying background."""
    h, w = bg_arr.shape[:2]
    checked = []
    warnings = []
    for lyr in doc.get("layers", []):
        if lyr.get("type") != "text" or not lyr.get("visible", True) or not lyr.get("text_data"):
            continue
        t_col = lyr["text_data"].get("color") or [255, 255, 255]
        x1 = max(0, int(lyr.get("x", 0)))
        y1 = max(0, int(lyr.get("y", 0)))
        x2 = min(w, x1 + max(1, int(lyr.get("width", 1))))
        y2 = min(h, y1 + max(1, int(lyr.get("height", 1))))
        if x2 <= x1 or y2 <= y1:
            continue
        patch = bg_arr[y1:y2, x1:x2, :3]
        bg_med = np.median(patch.reshape(-1, 3), axis=0)
        l1 = _wcag_luminance(t_col)
        l2 = _wcag_luminance(bg_med)
        hi, lo = max(l1, l2), min(l1, l2)
        cr = round((hi + 0.05) / (lo + 0.05), 2)
        ok = cr >= 3.0
        checked.append({"layer": lyr.get("name", lyr["id"]), "contrast_ratio": cr, "passed": ok})
        if not ok:
            warnings.append(f"DVF Contrast Warning: '{lyr.get('name')}' contrast {cr}:1 (<3.0:1).")
    return {"passed": len(warnings) == 0, "checked_layers": checked, "warnings": warnings}


def run_qa_2_composite(doc: Dict[str, Any], project_dir: str) -> Dict[str, Any]:
    """QA 2: Render exact composite from DesignDocument, check holes and compare to source if REDESIGN."""
    w, h = doc["width"], doc["height"]
    sorted_layers = sorted(doc.get("layers", []), key=lambda l: l.get("z_index", 0))
    has_live_adjustments = any(l.get("type") == "adjustment" for l in sorted_layers)

    if has_live_adjustments:
        from core.retouch_analyzer import evaluate_adjustment_stack
        base_rgb = np.zeros((h, w, 3), dtype=np.uint8)
        comp_rgb = evaluate_adjustment_stack(base_rgb, sorted_layers, project_dir)
        comp = Image.fromarray(comp_rgb, "RGB").convert("RGBA")
    else:
        comp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
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
            # Paste with alpha_composite on canvas (honoring export_offset from effects padding)
            exp_off = (lyr.get("metadata") or {}).get("export_offset") or [0, 0]
            px = int(lyr["x"]) - int(exp_off[0] or 0)
            py = int(lyr["y"]) - int(exp_off[1] or 0)
            tmp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            tmp.paste(im, (px, py))
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

    # DVF Visual Aesthetic Checks (Hierarchy >= 2.0x, Negative Space >= 20%, Text Contrast >= 3.0:1)
    bg_only = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    for lyr in sorted_layers:
        if not lyr.get("visible", True) or lyr.get("type") not in ("background", "shape", "light_effect"):
            continue
        src = (lyr.get("metadata") or {}).get("export_override_file") or lyr.get("source_file")
        if src and os.path.exists(os.path.join(project_dir, src)):
            im_b = Image.open(os.path.join(project_dir, src)).convert("RGBA")
            tmp_b = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            tmp_b.paste(im_b, (int(lyr["x"]), int(lyr["y"])))
            bg_only = Image.alpha_composite(bg_only, tmp_b)

    hier_chk = check_hierarchy_ratio(doc)
    neg_chk = check_negative_space_ratio(doc)
    con_chk = check_text_contrast(doc, np.array(bg_only))
    aes_warnings = [w_msg for w_msg in ([hier_chk.get("warning"), neg_chk.get("warning")] + con_chk.get("warnings", [])) if w_msg]

    issues = []
    if transparent_hole_pct > 5.0 and not any(l.get("metadata", {}).get("transparent_input") for l in sorted_layers):
        issues.append(f"Composite has {transparent_hole_pct}% unfilled transparent area.")

    return {
        "passed": len(issues) == 0,
        "composite_file": comp_rel,
        "transparent_hole_pct": transparent_hole_pct,
        "mae_vs_source": mae_vs_source,
        "aesthetic_checks": {
            "hierarchy_ratio": hier_chk,
            "negative_space": neg_chk,
            "text_contrast": con_chk,
            "warnings": aes_warnings,
        },
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
    valid_readback = info.get("decoded_pixel_layers", 0) + info.get("adjustment_layer_count", 0)
    if valid_readback != info.get("layer_count"):
        issues.append(f"Only {valid_readback}/{info.get('layer_count')} layers decoded valid pixel or adjustment blocks.")

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
        "adjustment_layer_count": info.get("adjustment_layer_count", 0),
        "masked_layer_count": info.get("masked_layer_count", 0),
        "clipped_layer_count": info.get("clipped_layer_count", 0),
        "fx_layer_count": info.get("fx_layer_count", 0),
        "composite_decoded": info.get("composite_decoded"),
        "text_layer_count": info.get("text_layer_count"),
        "photoshop_installed": os.path.exists(ps_exe),
        "photoshop_gui_verified": False,
        "photoshop_note": "Binary pixel + adjustment + mask + composite + group + TySh round-trip verified via ag-psd; Adobe Photoshop 2024 COM left for interactive GUI open.",
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
        "technical_checks_passed": (len(schema_errors) == 0 and qa1["passed"] and qa2["passed"] and qa3["passed"]),
        "overall_passed": (len(schema_errors) == 0 and qa1["passed"] and qa2["passed"] and qa3["passed"]),
        "visual_qc_status": "PENDING_USER_PHOTOSHOP_REVIEW",
        "visual_qc_note": "Automated checks verify binary PSD integrity, mask alignment, and non-empty layer buffers ONLY. Visual cleanliness and editability require human QC in Adobe Photoshop.",
        "psd_file": psd_name,
        "psd_path": psd_path,
    }
    doc["qa_status"] = report
    with open(os.path.join(project_dir, "design_document.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    with open(os.path.join(project_dir, "qa_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report
