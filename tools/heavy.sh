#!/usr/bin/env bash
# heavy.sh COMMAND...: run a heavy check (test module, gate subset, browser check) only when the machine can take it.
# Written on September 28, 2026 after parallel gate runs from five builders exhausted memory and swap the night before
# (34 Python processes, about 47 GB, at the 23:26 kill). Takes one of three machine-wide slots and waits until at least
# MIN_FREE_GB (default 12) of memory is available, then runs COMMAND under nice. The integrator's full gate runs take
# every slot with FULL=1. Exit status is COMMAND's.
set -u
SLOTS=/home/username/.le-ci-tmp/slots
MIN_FREE_GB="${MIN_FREE_GB:-12}"
avail_gb() { awk '/MemAvailable/ {printf "%d", $2/1048576}' /proc/meminfo; }
if [ "${INTEGRATOR:-0}" = 1 ]; then
  # The integrator's train gates use their own slot, so the release path never queues behind builders;
  # the memory check below still applies to them.
  exec 6>"$SLOTS/0"; flock 6; got=integrator
elif [ "${FULL:-0}" = 1 ]; then
  exec 7>"$SLOTS/1" 8>"$SLOTS/2" 9>"$SLOTS/3"
  flock 7; flock 8; flock 9
else
  while :; do
    for n in 1 2 3; do
      exec {fd}>"$SLOTS/$n"
      if flock -n "$fd"; then got=$n; break 2; fi
      exec {fd}>&-
    done
    sleep 20
  done
fi
# Temporary files go to the NVMe disk, not /tmp: /tmp here is a tmpfs, so every file in it uses memory and swap, and its
# per-user quota filled on September 28, 2026 (EDQUOT). One folder per slot; leftovers older than a day are removed.
export TMPDIR="${HEAVY_TMPDIR:-/home/username/.le-ci-tmp/tmp}/slot-${got:-full}"
mkdir -p "$TMPDIR" && find "$TMPDIR" -mindepth 1 -maxdepth 1 -mmin +1440 -exec rm -rf {} + 2>/dev/null
export TEMP="$TMPDIR" TMP="$TMPDIR"
# Preflight: refuse a run this machine cannot carry, and reclaim the RAM-disk leak that
# starved the runs of September 28, 2026 (17 GB across 36,088 /tmp entries, disk at 96%).
# Pruning is offered before a wait, so a leak is cleared rather than waited on.
PREFLIGHT=/home/username/loop-engine/tools/preflight_capacity.py
if [ -f "$PREFLIGHT" ]; then
  PYBIN=/home/username/loop-engine/.venv/bin/python
  [ -x "$PYBIN" ] || PYBIN=python3
  "$PYBIN" "$PREFLIGHT" --prune-tmp >&2 || true
  if ! "$PYBIN" "$PREFLIGHT" --strict >/dev/null 2>&1; then
    echo "heavy.sh: the machine cannot carry this run; reclaiming and waiting" >&2
    "$PYBIN" "$PREFLIGHT" >&2 || true
  fi
fi
while [ "$(avail_gb)" -lt "$MIN_FREE_GB" ]; do echo "heavy.sh: waiting, $(avail_gb) GB available" >&2; sleep 30; done
nice -n 10 "$@"
