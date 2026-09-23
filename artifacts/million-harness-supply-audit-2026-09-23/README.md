# Offline harness supply inventory

This September 23, 2026 artifact measures repository supply without changing
the catalogue, reviewing candidates, fetching outside code, calling a model or
publishing a release. It is a companion to
[S-6.40, S-6.45, S-6.62 and S-6.63](../../docs/roadmap/roadmap.yaml), not a
second task list or authority store. The
[research readout](../../docs/research/MILLION-HARNESS-SUPPLY-NEXT-STEPS-2026-09-23.md)
interprets the result and the scale limits.

```text
Read-only audit
├── Committed starter catalogue, exact review record and packaged host manifest
├── Four first-party skill candidate manifests
├── Two mixed-format candidate manifests and their native layout bindings
├── Optional unmerged ingestion, historical review and panel records
└── Optional release bundle item lines, counted as prospective metadata only
```

Run against a checkout:

```bash
python3 -B artifacts/million-harness-supply-audit-2026-09-23/audit_supply.py \
  --repo . --out-dir artifacts/million-harness-supply-audit-2026-09-23/new-receipt
python3 -B -m unittest discover \
  -s artifacts/million-harness-supply-audit-2026-09-23 -p 'test_*.py'
```

The output folder must be new. `report.json` names every read input and its
SHA-256 digest; `review-queue.jsonl` gives one row per nonapproved local
package. The report separates logical package records, physical payload paths,
unique payload body digests, client layout variants, recorded approvals,
packaged host items and prospective bundle rows. The queue never labels an
unmerged panel verdict as approval ready. Opposing review outcomes on one
identity trigger an adjudication hold even when body digests differ.

Optional inputs can be repeated:

```bash
  --panel-record PATH_TO_starter_catalogue_panel_review_v1.json \
  --panel-record PATH_TO_historical_starter_review_v1.json \
  --ingestion-report PATH_TO_library_ingestion_run_report_v1.json \
  --bundle-dir PATH_TO_canonical_bundle_folder
```

The outside ingestion run report contributes discovered and staged counts,
with zero approval credit. A panel or historical review record contributes
outcomes, with zero approval credit until integrated through the authoritative
review path. When the exact reviewed body is still present, the tool checks
its recorded digest and compares a second digest after replacing only the
literal closing catalogue revision line. A matching normalized body with
opposing decisions is an adjudication finding, never a carried approval.
A bundle folder contributes bounded `items.jsonl` metadata, with zero active
release credit. The tool verifies the header's line count, byte count and
digest, but does not read blobs, validate a publisher's rights or inspect the
live release pointer. Use the repository's release reader for publication.

The audit uses a temporary SQLite database for exact digest grouping and a
streamed queue output. No database survives the run. It reads each package
body in chunks and keeps only small summaries in memory. `report.json` is
evidence for the checked revision and input digests, not a fresh approval or a
live service check. Exact duplicate bytes may still implement different
methods, and different bytes may be near duplicates; neither case is merged
automatically.

## Saved observations

The [current local receipt](receipt-historical-panel-dispute-2026-09-23/report.json)
is for detached revision `abcad4f8`. It includes the committed checkout plus
the unmerged library ingestion second run, the historical review record and
the later panel pilot as external evidence. It identifies 29 opposing review
outcomes on bodies equal after only the closing revision line changes. Those
external paths may not exist in another checkout; omit them to repeat the
committed-only inventory, or supply their reviewed successors. The saved
[initial receipt](receipt-initial-2026-09-23/report.json) and
[earlier panel receipt](receipt-panel-initial-2026-09-23/report.json) remain
beside the final streamed-queue result.

The reproducible [million-row synthetic metadata probe](receipt-synthetic-million-after-dispute-2026-09-23/scale-probe.json)
used [probe_streaming.py](probe_streaming.py) to pass five prospective
200,000-item bundle files through this offline tool under a 768 MiB
address-space ceiling. Its peak child resident memory was 43,532 KiB and audit
time was 19.898 seconds on this workstation. The disposable input had one
repeated synthetic file digest
and no body blobs. It proves only that this audit can count a million bounded
metadata lines without giving a million copies or proposals approval credit.
It does not measure production indexing, review, retrieval, native loading or
customer benefit. The [50,000-row predecessor](scale-probe-50000-2026-09-23.json)
is retained as a smaller comparison.

## Checks and limits

`test_audit_supply.py` plants changed body bytes, an ancestor symbolic link,
the same file bound to two client layouts, conflicting historical and panel
outcomes over bodies that differ only by a closing revision line, a prospective
bundle with repeated file bytes, an outside
ingestion report that tries to claim approval, and duplicate JSON fields.
These cases must refuse or preserve the separate denominators. Input manifests
are recognized only by their current exact record types. The bundle line path
is intentionally a metadata audit, not the host's complete bundle validation.
