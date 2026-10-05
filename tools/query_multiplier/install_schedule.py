"""Pin a reviewed revision and install the multiplier's systemd user timer; enabling it is a separate flag.

```text
install_schedule.py --revision <commit> [--minutes 40] [--on-calendar '*-*-* *:07:00'] [--enable]
├── ~/baltor-scheduled/query-multiplier/<commit12>/   src and tools of that commit (git archive), read-only,
│                                                      REVISION holds the full commit
├── ~/.config/systemd/user/baltor-query-multiplier.service
│       oneshot; runs tools/query_multiplier/scheduled-run.sh of the pinned checkout; MemoryMax=4G,
│       MemorySwapMax=256M, CPUQuota=50%, Nice=10, idle I/O; TimeoutStartSec above the pass length
└── ~/.config/systemd/user/baltor-query-multiplier.timer
        OnCalendar (hourly by default), Persistent, RandomizedDelaySec=120
```

Without --enable nothing is started: the operator runs one complete manual pass of the pinned checkout first
(`systemctl --user start baltor-query-multiplier.service`, or scheduled-run.sh by hand) and enables the timer
only after that pass ends with state complete. The pass writes its live status to
<root>/state/status.json; `systemctl --user status baltor-query-multiplier` shows the last exit.
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
UNIT = "baltor-query-multiplier"
PINNED = Path.home() / "baltor-scheduled" / "query-multiplier"
SYSTEMD = Path.home() / ".config" / "systemd" / "user"

SERVICE = """[Unit]
Description=Baltor query multiplier: research probes within every source's limits (pinned {short})
Documentation=file://{checkout}/tools/query_multiplier/README.md

[Service]
Type=oneshot
WorkingDirectory={checkout}
Environment=PATH={home}/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=TMPDIR={home}/.le-ci-tmp/tmp/querymult
Environment=QUERY_MULTIPLIER_ROOT={root}
Environment=QUERY_MULTIPLIER_MINUTES={minutes}
ExecStartPre=/usr/bin/mkdir -p {home}/.le-ci-tmp/tmp/querymult
ExecStart=/bin/bash {checkout}/tools/query_multiplier/scheduled-run.sh
Nice=10
IOSchedulingClass=idle
CPUQuota=50%
MemoryMax=4G
MemorySwapMax=256M
TimeoutStartSec={timeout}
NoNewPrivileges=true
UMask=0077
"""

TIMER = """[Unit]
Description=Run the Baltor query multiplier ({calendar})

[Timer]
OnCalendar={calendar}
RandomizedDelaySec=120
AccuracySec=1m
Persistent=true
Unit={unit}.service

[Install]
WantedBy=timers.target
"""


def pin(revision: str) -> Path:
    full = subprocess.run(["git", "-C", str(REPOSITORY), "rev-parse", "--verify", revision + "^{commit}"],
                          capture_output=True, text=True, check=True).stdout.strip()
    checkout = PINNED / full[:12]
    if not checkout.exists():
        checkout.mkdir(parents=True)
        archive = subprocess.run(["git", "-C", str(REPOSITORY), "archive", full, "src", "tools"], capture_output=True, check=True).stdout
        subprocess.run(["tar", "-x", "-C", str(checkout)], input=archive, check=True)
        (checkout / "REVISION").write_text(full + "\n", encoding="utf-8")
        for folder in (checkout / "src", checkout / "tools"):
            for path in [folder, *folder.rglob("*")]:
                mode = path.stat().st_mode
                path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
    if (checkout / "REVISION").read_text(encoding="utf-8").strip() != full:
        raise SystemExit("pinned checkout revision mismatch: " + str(checkout))
    return checkout


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--revision", default="HEAD")
    parser.add_argument("--minutes", type=int, default=40)
    parser.add_argument("--on-calendar", default="*-*-* *:07:00")
    parser.add_argument("--root", default=str(Path.home() / "baltor-library" / "query-runs"))
    parser.add_argument("--enable", action="store_true", help="enable and start the timer (after one complete manual pass)")
    options = parser.parse_args(argv)
    if not 5 <= options.minutes <= 55:
        raise SystemExit("a pass lasts 5 to 55 minutes, so an hourly timer never overlaps itself")
    checkout = pin(options.revision)
    SYSTEMD.mkdir(parents=True, exist_ok=True)
    home = str(Path.home())
    service = SERVICE.format(short=checkout.name, checkout=checkout, home=home, root=options.root,
                             minutes=options.minutes, timeout=(options.minutes + 15) * 60)
    (SYSTEMD / (UNIT + ".service")).write_text(service, encoding="utf-8")
    (SYSTEMD / (UNIT + ".timer")).write_text(TIMER.format(calendar=options.on_calendar, unit=UNIT), encoding="utf-8")
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    enabled = False
    if options.enable:
        subprocess.run(["systemctl", "--user", "enable", "--now", UNIT + ".timer"], check=True)
        enabled = True
    print(json.dumps({"checkout": str(checkout), "service": str(SYSTEMD / (UNIT + ".service")),
                      "timer": str(SYSTEMD / (UNIT + ".timer")), "enabled": enabled,
                      "status_file": os.path.join(options.root, "state", "status.json")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
