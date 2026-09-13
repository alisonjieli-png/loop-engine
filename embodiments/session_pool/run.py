"""Independent entry point for pooled_sessions; no implicit model or network authority."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "devtools")]
from embodiment_lab.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main(fixed_variant="pooled_sessions"))
