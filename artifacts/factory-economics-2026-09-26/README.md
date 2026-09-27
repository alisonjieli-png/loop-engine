# Factory economics records of September 26, 2026

Kind: measurement records. Written by `tools/factory_report.py` and
`tools/factory_schedule.py` over the daily library job's journals, ledgers,
counts, export reports and the overnight generation batch. They hold counts,
times and paths only; no library body and no credential.

The first report and its two plans were written at 17:10 UTC while the
16 UTC slot was still running. The second report was written at 21:40 UTC,
after that slot finished its publish at 21:38 UTC, with the corrected report
tool (restarted stages kept out of the means, gaps without a stage note
attributed to no stage, the review lane read from the ledger, the projection
base counting written approvals, and the back-to-back rate taken from the
clean stage means). Both are kept; the decision record cites the second.

| File | What it is |
|---|---|
| `factory-report-2026-09-26T171000Z.json` | First `factory_report/v1` record, 6,398 served, declared serving capacity 25,000; kept as the earlier attempt |
| `factory-report-2026-09-26T171000Z.md` | The same record as a plain table |
| `plan-volume-gate-10000.json` | First `factory_schedule_plan/v1`, from 18:30 UTC with 7,988 served and a capacity of 10,000 |
| `plan-memory-gate-25000.json` | The same plan with a capacity of 25,000 |
| `factory-report-2026-09-26T214010Z.json` | Second `factory_report/v1` record, 7,806 served (the 16 UTC slot's checked publish), declared serving capacity 10,000 |
| `factory-report-2026-09-26T214010Z.md` | The same record as a plain table |
| `plan-volume-gate-10000-from-7806.json` | Plan from the second report, as if the queue replaced the 22:17 UTC cron slot, capacity 10,000 |
| `plan-memory-gate-25000-from-7806.json` | The same plan with a capacity of 25,000 |
| `factory_mutants.py` | Mutant controls: each of 18 mutants removes one guard of the two tools and runs the check named for it |
| `mutants-1.txt` | Its run on the final tools: every mutant caught, the unmutated copies passing |

Commands of the second set, run from the worktree at base revision
`43b421f8`:

```text
PYTHONPATH=src:tools python tools/factory_report.py --library /home/username/baltor-library \
  --overnight-batch /home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch \
  --served 7806 --serving-capacity 10000 --output OUT
PYTHONPATH=src:tools python tools/factory_schedule.py plan --report factory-report-2026-09-26T214010Z.json \
  --stock 47796 --served 7806 --serving-capacity 10000 --slots 6 --start 2026-09-26T22:17:00Z \
  --library /home/username/baltor-library --output plan-volume-gate-10000-from-7806.json
PYTHONPATH=src:tools python tools/factory_schedule.py run --report factory-report-2026-09-26T214010Z.json \
  --stock 47796 --served 7806 --serving-capacity 10000 --slots 6 --start 2026-09-26T22:17:00Z \
  --library /home/username/baltor-library --daily-job /home/username/baltor-private/tools/daily_library_release.sh \
  --repository /home/username/.le-library-job --run-folder /home/username/.le-library/import-2026-09-24/run-1 \
  --journal SCRATCH/dry-run-journal-2.jsonl --dry-run
```

The dry run printed two `would_start` events with the cron line's settings
and started nothing; the library's daily folder still held the same four
slots afterwards.

The decision record that reads them is
[Factory scheduling and economics](../../docs/research/FACTORY-SCHEDULING-AND-ECONOMICS-2026-09-26.md).
