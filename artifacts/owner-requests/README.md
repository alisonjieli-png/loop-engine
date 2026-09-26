# Owner requests reports

Kind: dated records written by
[`tools/owner_requests_ledger.py`](../../tools/owner_requests_ledger.py)
from the [owner requests ledger](../../docs/context/OWNER-REQUESTS-LEDGER-2026-09.md)
and the [roadmap](../../docs/roadmap/roadmap.yaml). Each file is
`owner-requests-report-YYYY-MM-DD.json` (record type
`owner_requests_report/v1`); a second run on the same day gets a `-2`
suffix, so no record is ever overwritten. A record lists every request whose
named steps are not live, every request whose ledger state is not live, every
request without a step, every roadmap step that no request names, and every
step identifier the roadmap does not know. It grants nothing; the roadmap
stays the only task authority.

## Current behaviour

A session runs, from the repository root:

```bash
PYTHONPATH=src:tools python tools/owner_requests_ledger.py
```

It writes the day's record here, prints the plain table, and exits 1 when
the ledger names a step the roadmap lacks. `--summary PATH` also writes a
Markdown summary; `--check` writes nothing and only validates;
`--output-dir` moves the record elsewhere.

Records of September 26, 2026, both kept:

- `owner-requests-report-2026-09-26.json`, the first pass, written at 12:57
  UTC from `main` at `76e14faa` with the 96-row ledger of that hour.
- `owner-requests-report-2026-09-26-2.json`, the second pass, written from
  `main` at `43b421f8` with the 110-row ledger, after a sweep of every quoted
  owner passage in the sources found fourteen requests the first pass had not
  listed.

## Proposed cron entry (not installed)

Proposed on September 26, 2026 and not installed: a daily run at 06:30 UTC.
The machine's cron keeps America/New_York time and has no `CRON_TZ`, so the
entry fires at 01:30 and 02:30 local time and only the run that lands in the
06 UTC hour proceeds, the same guard the weekly number and quickstart entries
use. The run reads the shared checkout `/home/username/loop-engine` once the
tool is committed there, and the worktree that wrote it until then. It writes
nothing into any checkout: the record goes under
`$HOME/.le-ci-tmp/owner-requests/records/`, and because the artifact board
that a session publishes to is never reachable from cron, the Markdown summary
is always written to `$HOME/.le-ci-tmp/owner-requests/latest.md`, which a
later session may publish as a page. A session copies a record it wants to
keep into this folder under its dated name, as every report is kept. The run
makes no model call and no network call, reads two files and writes at most
one record and one summary a day; that one record is its ceiling. Its log is
`$HOME/.le-ci-tmp/owner-requests/cron.log`.

```text
# BEGIN OWNER REQUESTS LEDGER (proposed 2026-09-26, not installed)
# 06:30 UTC daily (roadmap S-6.76). This cron keeps America/New_York time and has no CRON_TZ, so the line fires at 01:30 and 02:30
# local time and only the run that lands in the 06 UTC hour proceeds. No model call, no network call; one record and one summary a day.
30 1,2 * * * DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus TMPDIR=/home/username/.le-ci-tmp/owner-requests bash -lc '[ "$(date -u +\%H)" = "06" ] || exit 0; R=/home/username/loop-engine; [ -f "$R/tools/owner_requests_ledger.py" ] || R=/home/username/.le-agent-request-tracker; mkdir -p /home/username/.le-ci-tmp/owner-requests/records; cd "$R" && echo "$(date -u +\%FT\%TZ) $R" && PYTHONPATH=src:tools /home/username/loop-engine/.venv/bin/python tools/owner_requests_ledger.py --output-dir /home/username/.le-ci-tmp/owner-requests/records --summary /home/username/.le-ci-tmp/owner-requests/latest.md --quiet' >> /home/username/.le-ci-tmp/owner-requests/cron.log 2>&1
# END OWNER REQUESTS LEDGER
```

## Limits

- The ledger is written by hand from the dated handoffs, the decision table
  and the roadmap's evidence fields. A request that no document records is
  not in it, and the tool cannot find one.
- The tool compares the ledger's state column with the roadmap's status. It
  does not probe the live service, so "live" in a record means the ledger
  said so on the day it was judged.
