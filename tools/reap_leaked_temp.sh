#!/usr/bin/env bash
# Reclaim the leaks that starve heavy runs: the RAM-backed temp filesystem and cold builder scratch.
# Idempotent and safe to run unattended. Reports what it removed to a dated record.
set -u
# The repository this copy lives in, so cron can run the auto-updated main checkout.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
[ -x "$PY" ] || PY=/home/username/loop-engine/.venv/bin/python
[ -x "$PY" ] || PY=python3
LOGDIR=/home/username/.le-ci-tmp/reaper
mkdir -p "$LOGDIR"
RECORD="$LOGDIR/reaper-$(date -u +%Y%m%dT%H%M%SZ).json"

# 1. The RAM disk: prune leaked temp entries. This is the single biggest lever, because
#    /tmp is tmpfs and every byte here is memory the machine cannot use for a gate run.
if [ -n "${REAPER_DRY_RUN:-}" ]; then
  "$PY" "$ROOT/tools/preflight_capacity.py" --json > "$RECORD" 2>/dev/null
else
  "$PY" "$ROOT/tools/preflight_capacity.py" --prune-tmp --json > "$RECORD" 2>/dev/null
fi

# 2. Old gate-run scratch folders under the CI temp area (pure run artifacts).
[ -n "${REAPER_DRY_RUN:-}" ] || find /home/username/.le-ci-tmp/pre-push -mindepth 1 -maxdepth 1 -type d -mmin +1440 -exec rm -rf {} + 2>/dev/null

# 3. The disk: report, and move cold scratch to the external disk when one is mounted.
REAPER_DRY_RUN="${REAPER_DRY_RUN:-}" "$PY" - "$RECORD" <<'PYEOF'
import json, os, shutil, subprocess, sys, time
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
    dry = bool(os.environ.get("REAPER_DRY_RUN"))
    if not dry:
        target.mkdir(parents=True, exist_ok=True)
    moved, kept = [], {}
    ci = Path("/home/username/.le-ci-tmp")
    # Folders a run depends on stay in place: the gate environments, the reserved
    # names, and anything marked .keep-in-place. Python environments are never cold scratch.
    reserved = {"pre-push", "tmp", "slots", "tools", "node_modules"}
    in_use = set()
    for proc in Path("/proc").glob("[0-9]*"):
        try:
            in_use.add(os.path.realpath(proc / "cwd"))
        except OSError:
            continue
    def newest_mtime(d):
        # The folder's own time changes only when entries are added or removed,
        # so a run that rewrites files inside it also counts.
        newest = d.stat().st_mtime
        with os.scandir(d) as entries:
            for i, entry in enumerate(entries):
                if i >= 2000:
                    break
                try:
                    newest = max(newest, entry.stat(follow_symlinks=False).st_mtime)
                except OSError:
                    continue
        return newest
    for d in sorted(ci.iterdir(), key=lambda x: x.stat().st_mtime if x.exists() else 0):
        if not d.is_dir():
            continue
        name = d.name.lower()
        if d.name in reserved or "venv" in name or name.startswith("env") or (d / ".keep-in-place").exists() \
                or (d / "pyvenv.cfg").exists():
            kept[d.name] = "protected"
            continue
        real = os.path.realpath(d)
        if any(cwd == real or cwd.startswith(real + os.sep) for cwd in in_use):
            kept[d.name] = "a running process works in it"
            continue
        try:
            if time.time() - newest_mtime(d) < 7200:
                continue  # recent: possibly in flight
            dest = target / d.name
            if dest.exists():
                kept[d.name] = "an older copy already sits on the external disk"
                continue
            if not dry:
                shutil.move(str(d), str(dest))
            moved.append(d.name)
        except Exception:
            continue
    data["moved_to_external" if not dry else "would_move_to_external"] = moved
    data["kept_in_place"] = kept
    data["disk_free_gb_after_move"] = free_gb("/")
record.write_text(json.dumps(data, indent=2))
PYEOF
echo "reaper done: $RECORD"
