"""
Houdini side for Alembic Bridge v1.

Usage (shelf tool):
    import houdini_bridge as hb
    hb.export_selected_to_maya('/path/to/bridge_config.json')

    import houdini_bridge as hb
    hb.import_latest_from_maya('/path/to/bridge_config.json')
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import hou


@dataclass
class BridgeConfig:
    bridge_folder: Path
    scene_code: str
    abc_frame_range: tuple[int, int]
    force_path_attr: bool


def _load_config(config_path: str | Path) -> BridgeConfig:
    data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    hcfg = data.get("houdini", {})
    fr = hcfg.get("abc_frame_range", [1, 1])
    return BridgeConfig(
        bridge_folder=Path(data["bridge_folder"]),
        scene_code=data.get("scene_code", "scene"),
        abc_frame_range=(int(fr[0]), int(fr[1])),
        force_path_attr=bool(hcfg.get("force_path_attr", True)),
    )


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _sanitize_path_token(text: str) -> str:
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^0-9A-Za-z_\-/]", "_", text)
    return text


def _ensure_path_attr(node: hou.Node) -> None:
    """
    Normalizes primitive string `path` attribute for Alembic hierarchy export.
    """
    geo = node.geometry()
    path_attrib = geo.findPrimAttrib("path")
    if path_attrib is None:
        path_attrib = geo.addAttrib(hou.attribType.Prim, "path", "")

    for prim in geo.prims():
        current = prim.attribValue(path_attrib) or ""
        current = _sanitize_path_token(str(current))
        if not current.startswith("/"):
            current = f"/{current}" if current else f"/{node.name()}/prim_{prim.number()}"
        prim.setAttribValue(path_attrib, current)


def _selected_node() -> hou.Node:
    selected = hou.selectedNodes()
    if not selected:
        raise RuntimeError("Выбери SOP или OBJ ноду в Houdini.")
    return selected[0]


def export_selected_to_maya(config_path: str | Path) -> Path:
    cfg = _load_config(config_path)
    src = _selected_node()

    if src.type().category().name() == "Object":
        geo_node = src.displayNode()
        if geo_node is None:
            raise RuntimeError("У OBJ ноды нет display SOP для экспорта.")
        src = geo_node

    if cfg.force_path_attr:
        _ensure_path_attr(src)

    cfg.bridge_folder.mkdir(parents=True, exist_ok=True)
    stem = f"{cfg.scene_code}_houdini_{_timestamp()}"
    abc_path = cfg.bridge_folder / f"{stem}.abc"
    meta_path = cfg.bridge_folder / f"{stem}.json"

    rop = hou.node("/out").createNode("alembic")
    rop.parm("filename").set(str(abc_path))
    rop.parm("trange").set(1)
    rop.parm("f1").set(cfg.abc_frame_range[0])
    rop.parm("f2").set(cfg.abc_frame_range[1])
    rop.parm("root").set(src.path())
    rop.parm("buildfrompath").set(1)
    rop.parm("pathattrib").set("path")
    rop.render()
    rop.destroy()

    metadata = {
        "direction": "houdini_to_maya",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_node": src.path(),
        "abc_file": abc_path.name,
    }
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    hou.ui.displayMessage(f"Exported: {abc_path}")
    return abc_path


def import_latest_from_maya(config_path: str | Path) -> Path:
    cfg = _load_config(config_path)
    candidates = sorted(cfg.bridge_folder.glob(f"{cfg.scene_code}_maya_*.abc"))
    if not candidates:
        raise RuntimeError("Не найден Alembic из Maya.")

    latest = candidates[-1]
    container = hou.node("/obj").createNode("geo", node_name=f"abc_in_{_timestamp()}")
    for child in container.children():
        child.destroy()

    abc = container.createNode("alembic", "abc_in")
    abc.parm("fileName").set(str(latest))
    abc.setDisplayFlag(True)
    abc.setRenderFlag(True)
    container.layoutChildren()
    hou.ui.displayMessage(f"Imported: {latest}")
    return latest
