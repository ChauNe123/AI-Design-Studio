"""Unified Design Document schema — single source of truth for Preview, Editor, QA, and PSD Export."""
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

VALID_LAYER_TYPES = {
    "background",
    "shape",
    "product",
    "object",
    "logo",
    "icon",
    "text",
    "shadow",
    "light_effect",
    "decor",
    "reference",
}

VALID_BLEND_MODES = {
    "normal",
    "multiply",
    "screen",
    "overlay",
    "soft light",
    "hard light",
    "darken",
    "lighten",
}


def make_layer(
    name: str,
    layer_type: str,
    source_file: Optional[str],
    x: int,
    y: int,
    width: int,
    height: int,
    z_index: int = 0,
    opacity: float = 1.0,
    visible: bool = True,
    blend_mode: str = "normal",
    group: str = "Main",
    mask_file: Optional[str] = None,
    ai_reconstructed: bool = False,
    text_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    layer_id: Optional[str] = None,
) -> Dict[str, Any]:
    ltype = layer_type if layer_type in VALID_LAYER_TYPES else "object"
    bmode = blend_mode if blend_mode in VALID_BLEND_MODES else "normal"
    return {
        "id": layer_id or f"lyr_{uuid.uuid4().hex[:8]}",
        "name": name,
        "type": ltype,
        "source_file": source_file,
        "x": int(round(x)),
        "y": int(round(y)),
        "width": max(1, int(round(width))),
        "height": max(1, int(round(height))),
        "z_index": int(z_index),
        "opacity": max(0.0, min(1.0, float(opacity))),
        "visible": bool(visible),
        "blend_mode": bmode,
        "mask_file": mask_file,
        "ai_reconstructed": bool(ai_reconstructed),
        "text_data": text_data,
        "group": group or "Main",
        "metadata": metadata or {},
    }


def create_document(
    project_id: str,
    title: str,
    mode: str,
    width: int,
    height: int,
    layers: Optional[List[Dict[str, Any]]] = None,
    source_image: Optional[str] = None,
    brand: Optional[Dict[str, Any]] = None,
    notes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    doc = {
        "schema_version": "1.0.0",
        "project_id": project_id,
        "title": title,
        "mode": mode,  # "REDESIGN" or "GENERATE"
        "width": int(width),
        "height": int(height),
        "dpi": 72,
        "color_mode": "RGB",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source_image": source_image,
        "brand": brand or {},
        "notes": notes or [],
        "layers": [],
        "qa_status": None,
    }
    if layers:
        doc["layers"] = normalize_z_order(layers)
    return doc


def normalize_z_order(layers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sorted_layers = sorted(layers, key=lambda l: l.get("z_index", 0))
    for idx, lyr in enumerate(sorted_layers):
        lyr["z_index"] = idx
    return sorted_layers


def validate_document(doc: Dict[str, Any]) -> List[str]:
    errors = []
    for req in ("project_id", "mode", "width", "height", "layers"):
        if req not in doc:
            errors.append(f"Missing required document field: {req}")
    if doc.get("width", 0) <= 0 or doc.get("height", 0) <= 0:
        errors.append("Canvas width and height must be positive integers.")

    seen_ids = set()
    for idx, lyr in enumerate(doc.get("layers", [])):
        lid = lyr.get("id")
        if not lid:
            errors.append(f"Layer #{idx} missing id.")
        elif lid in seen_ids:
            errors.append(f"Duplicate layer id: {lid}")
        seen_ids.add(lid)

        if not lyr.get("name"):
            errors.append(f"Layer {lid} missing name.")
        if lyr.get("width", 0) <= 0 or lyr.get("height", 0) <= 0:
            errors.append(f"Layer {lid} has invalid dimensions.")
        if lyr.get("type") == "text" and not lyr.get("text_data") and not lyr.get("source_file"):
            errors.append(f"Text layer {lid} missing both text_data and source_file.")
        if lyr.get("type") != "text" and not lyr.get("source_file"):
            errors.append(f"Raster layer {lid} ({lyr.get('name')}) missing source_file.")
    return errors


def save_document(doc: Dict[str, Any], project_dir: str) -> str:
    os.makedirs(project_dir, exist_ok=True)
    doc["updated_at"] = datetime.now().isoformat(timespec="seconds")
    doc["layers"] = normalize_z_order(doc.get("layers", []))
    out_path = os.path.join(project_dir, "design_document.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return out_path


def load_document(project_dir: str) -> Dict[str, Any]:
    path = os.path.join(project_dir, "design_document.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
