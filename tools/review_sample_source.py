"""The sample source file the candidate review tests cite, and the revision they pin it at.

The native review reader accepts a catalogue only while every file it cites still has, in the working tree, the bytes
pinned for it at the catalogue's source revision. The review tests cited the production module
src/loop_engine/core/service_runtime/catalogue_packages.py at revision 9c57c9a4 until September 27, 2026, so every
change to that module broke them. They cite a dedicated file instead, which exists only to be a sample, pinned at the
newest commit that changed it or LICENSE (the two files every such test catalogue cites). At that commit both files
hold their current committed bytes, an unrelated commit never moves the pin, and a cherry-picked copy of the file
resolves to its own commit.

It reads git history and nothing else; it writes nothing and grants no authority.
"""
from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
#: The dedicated sample: a text file that exists only to be cited by the review tests.
SOURCE = "tools/candidate_review/resources/test-sample/cited-source.md"
#: The licence every original catalogue cites beside its sources.
LICENCE = "LICENSE"


def pinned_revision(root: Path = ROOT) -> str:
    """The newest commit that changed the sample or the licence; a checkout whose history holds neither is refused."""
    completed = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%H", "--", SOURCE, LICENCE],
                               capture_output=True, text=True, timeout=60, check=False)
    revision = completed.stdout.strip()
    if completed.returncode != 0 or len(revision) != 40:
        raise RuntimeError(f"no commit of this checkout holds {SOURCE}; commit it before running the review tests")
    return revision


REVISION = pinned_revision()
