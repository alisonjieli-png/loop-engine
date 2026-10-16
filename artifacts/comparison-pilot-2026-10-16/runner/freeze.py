"""Record or check the SHA-256 digest of every frozen pilot file.

    python3 freeze.py          write design/design-freeze.json
    python3 freeze.py --check  exit 1 if any frozen file changed

The frozen set is the design, the task prompts, the Baltor treatment files, the
task manifest, the scorer controls, the source inventory and every runner file.
The runner refuses to start a trial when a digest differs. A later change is an
amendment with its reason, never a silent edit.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FREEZE = ROOT / "design" / "design-freeze.json"
PATTERNS = ("design/design.json", "design/tasks/*/prompt.txt", "design/treatment-baltor.txt",
            "design/baltor-connection-entry.json", "design/baltor-quickstart-bootstrap.sh",
            "design/task-manifest.json", "design/scorer-controls.json", "sources/*.json", "runner/*.py",
            "probe/*.json")


def frozen_files():
    files = {}
    for pattern in PATTERNS:
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file() and path != FREEZE:
                files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def main():
    files = frozen_files()
    if "--check" in sys.argv:
        recorded = json.loads(FREEZE.read_text(encoding="utf-8"))["files"]
        changed = sorted(name for name in set(recorded) | set(files) if recorded.get(name) != files.get(name))
        print("frozen files unchanged" if not changed else "changed: " + ", ".join(changed))
        return 1 if changed else 0
    FREEZE.write_text(json.dumps({"record_type": "comparison_pilot_design_freeze/v1", "files": files},
                                 indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"froze {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
