"""Build the website's own procedural reference previews from their exact constructor."""
from __future__ import annotations

from pathlib import Path

from tools.procedural_assets.catalogue import FAMILIES, construct
from tools.procedural_assets.geometry import preview


def build(root):
    folder = Path(root) / "src/loop_engine/core/service_runtime/web_assets"
    for family, filename in (("bear", "procedural-bear-preview.svg"), ("conifer", "procedural-tree-preview.svg")):
        title, dimensions, _kind = FAMILIES[family]
        body = preview(construct(family, *dimensions), title, "isometric")
        (folder / filename).write_text(body + "\n", encoding="utf-8")


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
