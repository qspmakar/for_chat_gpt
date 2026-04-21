"""
Maya side for Alembic Bridge v1.

Usage (shelf button):
    import maya_bridge as mb
    mb.export_selected_to_houdini('C:/path/to/bridge_config.json')

    import maya_bridge as mb
    mb.import_latest_from_houdini('C:/path/to/bridge_config.json')
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import maya.cmds as cmds


@dataclass
class BridgeConfig:
    bridge_folder: Path
    scene_code: str
    attr_whitelist: list[str]


def _load_config(config_path: str | Path) -> BridgeConfig:
    data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    mcfg = data.get("maya", {})
    return BridgeConfig(
        bridge_folder=Path(data["bridge_folder"]),
        scene_code=data.get("scene_code", "scene"),
        attr_whitelist=list(mcfg.get("attr_whitelist", [])),
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _selected_roots() -> list[str]:
    sel = cmds.ls(selection=True, long=True) or []
    if not sel:
        raise RuntimeError("Выдели хотя бы один объект в Maya.")
    return sel


def _job_string(roots: list[str], abc_path: Path, attrs: list[str]) -> str:
    parts = ["-uvWrite", "-worldSpace", "-writeVisibility"]
    for r in roots:
        parts.extend(["-root", r])
    for attr in attrs:
        parts.extend(["-attr", attr])
    parts.extend(["-file", str(abc_path)])
    return " ".join(parts)


def export_selected_to_houdini(config_path: str | Path) -> Path:
    cfg = _load_config(config_path)
    roots = _selected_roots()
    cfg.bridge_folder.mkdir(parents=True, exist_ok=True)

    stem = f"{cfg.scene_code}_maya_{_timestamp()}"
    abc_path = cfg.bridge_folder / f"{stem}.abc"
    meta_path = cfg.bridge_folder / f"{stem}.json"

    job = _job_string(roots, abc_path, cfg.attr_whitelist)
    cmds.AbcExport(j=job)

    metadata = {
        "direction": "maya_to_houdini",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "roots": roots,
        "dag_paths": roots,
        "abc_file": abc_path.name,
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    cmds.inViewMessage(amg=f"Exported: {abc_path}", pos="botLeft", fade=True)
    return abc_path


def import_latest_from_houdini(config_path: str | Path) -> Path:
    cfg = _load_config(config_path)
    candidates = sorted(cfg.bridge_folder.glob(f"{cfg.scene_code}_houdini_*.abc"))
    if not candidates:
        raise RuntimeError("Не найден Alembic из Houdini.")

    latest = candidates[-1]
    cmds.AbcImport(str(latest), mode="import")
    cmds.inViewMessage(amg=f"Imported: {latest}", pos="botLeft", fade=True)
    return latest
