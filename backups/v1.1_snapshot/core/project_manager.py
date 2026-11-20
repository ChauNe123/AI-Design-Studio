"""Project Management Engine — Autosave, Version History, Restore, Group CRUD, Integrity Check."""
import json
import os
import shutil
from datetime import datetime
from typing import Any, Dict, List, Optional
from PIL import Image

from core.design_document import load_document, normalize_z_order, save_document, validate_document


def _versions_dir(project_dir: str) -> str:
    d = os.path.join(project_dir, "versions")
    os.makedirs(d, exist_ok=True)
    return d


def _versions_index_path(project_dir: str) -> str:
    return os.path.join(_versions_dir(project_dir), "index.json")


def list_versions(project_dir: str) -> List[Dict[str, Any]]:
    idx_path = _versions_index_path(project_dir)
    if not os.path.exists(idx_path):
        return []
    with open(idx_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_version(doc: Dict[str, Any], project_dir: str, note: str = "Manual save", max_versions: int = 25) -> Dict[str, Any]:
    vdir = _versions_dir(project_dir)
    index = list_versions(project_dir)
    next_num = (index[-1]["seq"] + 1) if index else 1
    vid = f"v{next_num:03d}"
    vfile = f"{vid}.json"
    vpath = os.path.join(vdir, vfile)

    snap = json.loads(json.dumps(doc, ensure_ascii=False))
    snap["layers"] = normalize_z_order(snap.get("layers", []))
    with open(vpath, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)

    entry = {
        "version_id": vid,
        "seq": next_num,
        "file": vfile,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "note": note,
        "layer_count": len(snap.get("layers", [])),
        "groups": sorted({l.get("group", "Main") for l in snap.get("layers", [])}),
    }
    index.append(entry)
    while len(index) > max_versions:
        old = index.pop(0)
        old_p = os.path.join(vdir, old["file"])
        if os.path.exists(old_p):
            os.remove(old_p)

    with open(_versions_index_path(project_dir), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    return entry


def restore_version(project_dir: str, version_id: str) -> Dict[str, Any]:
    vdir = _versions_dir(project_dir)
    vpath = os.path.join(vdir, f"{version_id}.json")
    if not os.path.exists(vpath):
        raise FileNotFoundError(f"Version {version_id} not found in {vdir}")

    # Backup current state before restoring
    if os.path.exists(os.path.join(project_dir, "design_document.json")):
        cur_doc = load_document(project_dir)
        save_version(cur_doc, project_dir, note=f"Auto-backup before restore -> {version_id}")

    with open(vpath, "r", encoding="utf-8") as f:
        restored = json.load(f)

    # Verify referenced assets exist before committing
    save_document(restored, project_dir)
    clear_autosave(project_dir)
    return restored


def write_autosave(doc: Dict[str, Any], project_dir: str) -> str:
    os.makedirs(project_dir, exist_ok=True)
    draft_path = os.path.join(project_dir, "autosave_draft.json")
    payload = {
        "autosaved_at": datetime.now().isoformat(timespec="seconds"),
        "document": doc,
    }
    with open(draft_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    lock_path = os.path.join(project_dir, ".session_active")
    with open(lock_path, "w", encoding="utf-8") as f:
        f.write(payload["autosaved_at"])
    return draft_path


def check_autosave_recovery(project_dir: str) -> Optional[Dict[str, Any]]:
    draft_path = os.path.join(project_dir, "autosave_draft.json")
    doc_path = os.path.join(project_dir, "design_document.json")
    if not os.path.exists(draft_path):
        return None
    with open(draft_path, "r", encoding="utf-8") as f:
        draft = json.load(f)
    doc_mtime = os.path.getmtime(doc_path) if os.path.exists(doc_path) else 0
    draft_mtime = os.path.getmtime(draft_path)
    return {
        "has_recovery": draft_mtime >= doc_mtime - 0.5,
        "autosaved_at": draft.get("autosaved_at"),
        "unclean_shutdown": os.path.exists(os.path.join(project_dir, ".session_active")),
        "document": draft.get("document"),
    }


def clear_autosave(project_dir: str) -> None:
    for fn in ("autosave_draft.json", ".session_active"):
        p = os.path.join(project_dir, fn)
        if os.path.exists(p):
            os.remove(p)


def apply_group_operation(doc: Dict[str, Any], action: str, group_name: str, new_name: str = "", layer_id: str = "") -> Dict[str, Any]:
    """Create, rename, delete group, or move a layer into a group."""
    groups_meta = list(doc.get("brand", {}).get("custom_groups", []))
    existing = sorted({l.get("group", "Main") for l in doc.get("layers", [])} | set(groups_meta))

    if action == "create":
        g = group_name.strip()
        if not g:
            raise ValueError("Group name cannot be empty.")
        if g not in groups_meta:
            groups_meta.append(g)
        doc.setdefault("brand", {})["custom_groups"] = groups_meta
    elif action == "rename":
        old_g, new_g = group_name.strip(), new_name.strip()
        if not old_g or not new_g:
            raise ValueError("Old and new group names are required.")
        for lyr in doc.get("layers", []):
            if lyr.get("group") == old_g:
                lyr["group"] = new_g
        groups_meta = [new_g if g == old_g else g for g in groups_meta]
        doc.setdefault("brand", {})["custom_groups"] = groups_meta
    elif action == "delete":
        g = group_name.strip()
        if g == "Main" and len(existing) <= 1:
            raise ValueError("Cannot delete the sole Main group.")
        fallback = "Main" if g != "Main" else next((x for x in existing if x != g), "Default")
        for lyr in doc.get("layers", []):
            if lyr.get("group") == g:
                lyr["group"] = fallback
        groups_meta = [x for x in groups_meta if x != g]
        doc.setdefault("brand", {})["custom_groups"] = groups_meta
    elif action == "assign_layer":
        g = group_name.strip() or "Main"
        found = False
        for lyr in doc.get("layers", []):
            if lyr["id"] == layer_id:
                lyr["group"] = g
                found = True
        if not found:
            raise ValueError(f"Layer {layer_id} not found.")
        if g not in groups_meta:
            groups_meta.append(g)
            doc.setdefault("brand", {})["custom_groups"] = groups_meta
    else:
        raise ValueError(f"Unknown group action: {action}")
    return doc


def check_project_integrity(project_dir: str, min_free_mb: int = 50) -> Dict[str, Any]:
    """Verify design_document.json, all referenced layer/mask images, dimensions, and disk space."""
    doc_path = os.path.join(project_dir, "design_document.json")
    if not os.path.exists(doc_path):
        return {"ok": False, "error": "Missing design_document.json", "missing_assets": [], "corrupt_files": []}

    doc = load_document(project_dir)
    schema_errors = validate_document(doc)
    missing_assets = []
    corrupt_files = []
    warnings = []

    for lyr in doc.get("layers", []):
        for field in ("source_file", "mask_file"):
            rel = lyr.get(field)
            if not rel:
                continue
            abs_p = os.path.join(project_dir, rel)
            if not os.path.exists(abs_p):
                missing_assets.append({"layer_id": lyr["id"], "layer_name": lyr["name"], "field": field, "path": rel})
            else:
                try:
                    with Image.open(abs_p) as im:
                        im.verify()
                except Exception as exc:
                    corrupt_files.append({"layer_id": lyr["id"], "path": rel, "error": str(exc)})

    drive = os.path.splitdrive(os.path.abspath(project_dir))[0] or "D:"
    _, _, free_bytes = shutil.disk_usage(drive + os.sep)
    free_mb = round(free_bytes / (1024 * 1024), 1)
    if free_mb < min_free_mb:
        warnings.append(f"Low disk space on {drive}: {free_mb} MB free (< {min_free_mb} MB).")

    ok = len(schema_errors) == 0 and len(missing_assets) == 0 and len(corrupt_files) == 0 and free_mb >= min_free_mb
    return {
        "ok": ok,
        "schema_errors": schema_errors,
        "missing_assets": missing_assets,
        "corrupt_files": corrupt_files,
        "free_disk_mb": free_mb,
        "warnings": warnings,
    }
