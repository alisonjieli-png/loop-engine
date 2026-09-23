"""The native skill file a client would install, rendered exactly as the installer renders it.

A format check must read the rendered ``SKILL.md``, not only the stored body.
The installer (``tools/install_selected_material.py``) writes generated front
matter (the native name and the purpose as the description) and then the
served body byte for byte, so this module calls the installer's own functions
instead of restating its rules.
"""
from __future__ import annotations

from pathlib import Path

from install_selected_material import InstallRefusal, native_name, render_skill_header

from ..records import refuse

SKILL_FILE = "SKILL.md"


def rendered_skill(request) -> tuple:
    """Return (native name, rendered bytes, description truncated) or refuse with a stable code."""
    try:
        name = native_name(request.identity)
    except InstallRefusal as refusal:
        refuse("native_name_invalid", f"the identity has no native skill name ({refusal.code.value})")
    purpose = request.item.get("reference", {}).get("purpose", "")
    try:
        header, truncated = render_skill_header(name, str(purpose))
    except InstallRefusal as refusal:
        refuse("description_empty", f"the purpose renders to no description ({refusal.code.value})")
    return name, header + request.body, truncated


def write_rendered_skill(request, folder: Path) -> Path:
    """Write the rendered skill into ``folder/<native name>/SKILL.md`` and return its folder."""
    name, payload, _truncated = rendered_skill(request)
    skill_folder = Path(folder) / name
    skill_folder.mkdir(mode=0o700)
    with (skill_folder / SKILL_FILE).open("xb") as stream:
        stream.write(payload)
    return skill_folder
