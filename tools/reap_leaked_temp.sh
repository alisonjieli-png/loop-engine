#!/usr/bin/env bash
# Reclaim the leaks that starve heavy runs: the RAM-backed temp filesystem and cold builder scratch.
# Idempotent and safe to run unattended. Reports what it removed to a dated record.
set -u
PY=/home/username/loop-engine/.venv/bin/python
[ -x "$PY" ] || PY=python3
LOGDIR=/home/username/.le-ci-tmp/reaper
mkdir -p "$LOGDIR"
RECORD="$LOGDIR/reaper-$(date -u +%Y%m%dT%H%M%SZ).json"

# 1. The RAM disk: prune leaked temp entries. This is the single biggest lever, because
#    /tmp is tmpfs and every byte here is memory the machine cannot use for a gate run.
"$PY" /home/username/loop-engine/tools/preflight_capacity.py --prune-tmp --json > "$RECORD" 2>/dev/null

# 2. Old gate-run scratch folders under the CI temp area (pure run artifacts).
find /home/username/.le-ci-tmp/pre-push -mindepth 1 -maxdepth 1 -type d -mmin +1440 -exec rm -rf {} + 2>/dev/null

# 3. The disk: report, and move cold scratch to the external disk when one is mounted.
"$PY" - "$RECORD" <<'PYEOF'
import json, shutil, subprocess, sys, time
from pathlib import Path
record = Path(sys.argv[1])
try:
    data = json.loads(record.read_text())
except Exception:
    data = {}
def free_gb(path):
    u = shutil.disk_usage(path); return u.free // (1024**3)
offload = None
for c in ("/run/media/username/baltor-offload/loop-engine-scratch", "/run/media/username/baltor-offload"):
    p = Path(c)
    if p.is_dir(): offload = str(p); break
data["disk_free_gb_after_prune"] = free_gb("/")
if data.get("disk", {}).get("percent", 0) >= 92 and offload:
    # Move the oldest cold scratch to the external disk; keep the newest to protect in-flight work.
    target = Path(offload) / "reaped"
    target.mkdir(parents=True, exist_ok=True)
    moved = []
    ci = Path("/home/username/.le-ci-tmp")
    for d in sorted(ci.iterdir(), key=lambda x: x.stat().st_mtime if x.exists() else 0):
        if not d.is_dir() or d.name in ("pre-push", "tmp", "slots", "tools"): continue
        try:
            if time.time() - d.stat().st_mtime < 7200: continue  # recent: possibly in flight
            dest = target / d.name
            if dest.exists(): continue
            shutil.move(str(d), str(dest)); moved.append(d.name)
        except Exception:
            continue
    data["moved_to_external"] = moved
    data["disk_free_gb_after_move"] = free_gb("/")
record.write_text(json.dumps(data, indent=2))
PYEOF
echo "reaper done: $RECORD"
