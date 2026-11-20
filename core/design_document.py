"""Unified Design Document v1.2 Schema & v1.1->v1.2 Migration — single source of truth."""
import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.2.0"

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
    "character",
    "vehicle",
    "architecture",
    "adjustment",
    "group_marker",
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
    "pass through",
    "color dodge",
    "linear dodge (add)",
    "color",
    "luminosity",
}


def default_adjustments() -> Dict[str, Any]:
    return {
        "hue": 0.0,
        "sat": 100.0,
        "bright": 100.0,
        "contrast": 100.0,
        "exposure": 0.0,
        "temperature": 0.0,
        "shadow": 0.0,
        "highlight": 0.0,
    }


def default_effects() -> Dict[str, Any]:
    return {
        "feather": 0,
        "blur": 0.0,
        "glow": {"enabled": False, "color": [16, 185, 129], "radius": 14, "opacity": 0.75},
        "drop_shadow": {"enabled": False, "dx": 6, "dy": 8, "blur": 12, "color": [0, 0, 0], "opacity": 0.55},
        "color_overlay": {"enabled": False, "color": [255, 255, 255], "opacity": 0.5},
        "gradient_overlay": {"enabled": False, "c1": [16, 185, 129], "c2": [6, 95, 70], "angle": 90, "opacity": 0.6},
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
    original_source_file: Optional[str] = None,
    locked: bool = False,
    rotation: float = 0.0,
    crop: Optional[Dict[str, int]] = None,
    adjustments: Optional[Dict[str, Any]] = None,
    effects: Optional[Dict[str, Any]] = None,
    text_reconstruction: Optional[Dict[str, Any]] = None,
    reconstruction_history: Optional[List[Dict[str, Any]]] = None,
    confidence_score: float = 1.0,
    warnings: Optional[List[str]] = None,
    clipping: bool = False,
    mask_default_color: int = 0,
    adjustment_data: Optional[Dict[str, Any]] = None,
    psd_effects: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ltype = layer_type if layer_type in VALID_LAYER_TYPES else "object"
    bmode = blend_mode if blend_mode in VALID_BLEND_MODES else "normal"
    adj = {**default_adjustments(), **(adjustments or {})}
    eff = {**default_effects(), **(effects or {})}
    return {
        "id": layer_id or f"lyr_{uuid.uuid4().hex[:8]}",
        "name": name,
        "type": ltype,
        "source_file": source_file,
        "original_source_file": original_source_file or source_file,
        "x": int(round(x)),
        "y": int(round(y)),
        "width": max(1, int(round(width))),
        "height": max(1, int(round(height))),
        "z_index": int(z_index),
        "opacity": max(0.0, min(1.0, float(opacity))),
        "visible": bool(visible),
        "locked": bool(locked),
        "rotation": float(rotation),
        "crop": crop,
        "blend_mode": bmode,
        "clipping": bool(clipping),
        "mask_file": mask_file,
        "mask_default_color": int(mask_default_color),
        "adjustment_data": adjustment_data,
        "psd_effects": psd_effects,
        "ai_reconstructed": bool(ai_reconstructed),
        "adjustments": adj,
        "effects": eff,
        "text_data": text_data,
        "text_reconstruction": text_reconstruction,
        "reconstruction_history": reconstruction_history or [],
        "confidence_score": float(confidence_score),
        "warnings": warnings or [],
        "group": group or "Main",
        "metadata": metadata or {},
    }


def make_semantic_object(
    object_id: str,
    object_name: str,
    object_category: str,
    bounding_box: List[int],
    z_index: int,
    confidence_score: float = 0.8,
    segmentation_mask: Optional[str] = None,
    parent_object_id: Optional[str] = None,
    overlap_relationships: Optional[List[Dict[str, str]]] = None,
    source_asset: Optional[str] = None,
    reconstruction_status: str = "extracted",
    editability_status: str = "raster_editable",
    linked_layer_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "object_id": object_id,
        "object_name": object_name,
        "object_category": object_category,
        "bounding_box": [int(v) for v in bounding_box],  # [x, y, w, h]
        "segmentation_mask": segmentation_mask,
        "confidence_score": round(float(confidence_score), 3),
        "z_index": int(z_index),
        "parent_object_id": parent_object_id,
        "overlap_relationships": overlap_relationships or [],
        "source_asset": source_asset,
        "reconstruction_status": reconstruction_status,
        "editability_status": editability_status,
        "linked_layer_id": linked_layer_id,
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
    semantic_objects: Optional[List[Dict[str, Any]]] = None,
    api_tasks: Optional[List[Dict[str, Any]]] = None,
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    doc = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "title": title,
        "mode": mode,
        "width": int(width),
        "height": int(height),
        "dpi": 72,
        "color_mode": "RGB",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "source_image": source_image,
        "brand": brand or {},
        "notes": notes or [],
        "semantic_objects": semantic_objects or [],
        "layers": [],
        "api_tasks": api_tasks or [],
        "warnings": warnings or [],
        "qa_status": None,
    }
    if layers:
        doc["layers"] = normalize_z_order(layers)
    return doc


def migrate_document_v1_to_v1_2(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Safely upgrade v1.0/v1.1 DesignDocument to v1.2.0 without losing any existing fields."""
    if not doc:
        return doc
    ver = doc.get("schema_version", "1.0.0")
    doc.setdefault("semantic_objects", [])
    doc.setdefault("api_tasks", [])
    doc.setdefault("warnings", [])
    doc.setdefault("notes", [])
    doc.setdefault("brand", {})

    for lyr in doc.get("layers", []):
        meta = lyr.get("metadata") or {}
        lyr.setdefault("original_source_file", lyr.get("source_file"))
        lyr.setdefault("locked", False)
        lyr.setdefault("rotation", 0.0)
        lyr.setdefault("crop", None)
        lyr.setdefault("clipping", False)
        lyr.setdefault("mask_default_color", 0)
        lyr.setdefault("adjustment_data", None)
        lyr.setdefault("psd_effects", None)
        lyr.setdefault("text_reconstruction", None)
        lyr.setdefault("reconstruction_history", [])
        lyr.setdefault("confidence_score", 1.0)
        lyr.setdefault("warnings", [])

        # Migrate v1.1 metadata hue/sat/bright into structured adjustments
        adj = {**default_adjustments(), **(lyr.get("adjustments") or {})}
        for k in ("hue", "sat", "bright"):
            if k in meta and k not in (lyr.get("adjustments") or {}):
                adj[k] = float(meta[k])
        lyr["adjustments"] = adj
        lyr["effects"] = {**default_effects(), **(lyr.get("effects") or {})}

    if ver != SCHEMA_VERSION:
        doc["schema_version"] = SCHEMA_VERSION
        doc.setdefault("notes", []).append(f"Migrated safely from schema {ver} -> {SCHEMA_VERSION}")
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
        elif lyr.get("type") == "adjustment":
            if not lyr.get("adjustment_data"):
                errors.append(f"Adjustment layer {lid} ({lyr.get('name')}) missing adjustment_data.")
        elif lyr.get("type") not in ("text", "adjustment") and not lyr.get("source_file"):
            errors.append(f"Raster layer {lid} ({lyr.get('name')}) missing source_file.")
    return errors


def save_document(doc: Dict[str, Any], project_dir: str) -> str:
    os.makedirs(project_dir, exist_ok=True)
    doc = migrate_document_v1_to_v1_2(doc)
    doc["updated_at"] = datetime.now().isoformat(timespec="seconds")
    doc["layers"] = normalize_z_order(doc.get("layers", []))
    out_path = os.path.join(project_dir, "design_document.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    return out_path


def load_document(project_dir: str) -> Dict[str, Any]:
    path = os.path.join(project_dir, "design_document.json")
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return migrate_document_v1_to_v1_2(doc)
