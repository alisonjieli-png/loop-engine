# Handoff: website cut inventory, September 23, 2026

Kind: dated handoff record for the next session. Written by Claude Code
(Claude Opus 5.5), session `81df4e9e`, under the owner's wrap-up direction. It
is a snapshot, not new authority; the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md governs what happens next.

## Where the work is

- Worktree: `/home/username/.le-integration/site-inventory`, detached at a
  commit made on top of `243a8811` (main, Fly release 20). No branch was made,
  nothing was pushed, nothing was deployed.
- Deliverables:
  - [WEBSITE-CUT-INVENTORY-2026-09-23.md](WEBSITE-CUT-INVENTORY-2026-09-23.md):
    141 rows grouped by header, footer, pages and routes, homepage sections,
    page sections, hostname surfaces, never-merged pages and other features.
  - [cut-inventory.json](../../artifacts/website-audit-2026-09-23/cut-inventory.json):
    the same 141 rows as typed records (`website_cut_inventory/v1`).
  - This record, and `docs/RECORDS-INDEX.md` regenerated to list the two new
    dated records.

## What is done

- Every distinct version of the website page (36 blobs across all
  references) was split into units and compared with main; 499 lost units
  were traced to the commit that dropped them and grouped into rows.
- The consolidation line (`44a4b426`), `wave6/documentation-content`
  (`240c1270`), the port `ca62214d`, and the uncommitted page work in the
  model guidance, surface, overnight, status, machine fit and refusal wording
  worktrees were read without editing them.
- The live site was fetched once per hostname (eight GET requests to the
  root, plus GET requests to `/waitlist`, `/connect`, `/docs`, `/status`,
  `/for/coding-agents`, `/overnight`, `/context`, `/docs/what-baltor-is`,
  `/use-cases`, `/terms`, `/get-started`, `/machine-fit` and
  `/api/v1/capabilities` on baltor.ai). No form was sent, no account was
  used, no provider was called.
- Decisions: 2 restore as it was (header and footer Get started), 58 restore
  reworked, 81 superseded. The doc's section "Against the target site map"
  records six points where the placements differ from the integrating
  session's map, with reasons.

## What is left, in order

1. Run the hardcoding audit on this tree (the command is below). It scans
   Markdown and JSON. On the untouched tree it reported 632 high and no new
   high finding; it was not rerun with the two new files because of the
   wrap-up direction. If the new files add a high finding, adjust the wording
   or add an owned allowlist entry.
2. Run the offline link check and Vale (not installed here). The relative
   links and anchors were checked by a script and all resolve; the files have
   no em dash, no en dash and no URL.
3. Merge this commit to main through the usual review (documentation only;
   it touches no source file).
4. Build the restorations in the order of the doc's section "Items to
   restore": header and footer Get started first (HDR-01, FTR-01), then the
   homepage and Get started rows, then the consolidation line pages (merge
   plan step 2 of the branch triage), then the documentation view, then the
   hostname surfaces. Check each restored sentence against the source before
   publishing it; the rows name the known stale facts.
5. Ask the owner about the two items that need a privacy notice revision
   (UNM-05, UNM-10) and about publishing terms of service.

## Checks run, with results

| Check | Result |
|---|---|
| `npx --yes markdownlint-cli2@0.23.2` on the inventory | First run: 6 issues (MD033, angle-bracket placeholders); after the fix: 0 issues |
| `npx --yes markdownlint-cli2@0.23.2` on this handoff | 0 issues (run before the commit) |
| JSON parse of `cut-inventory.json` | Parses; 141 rows; every state and decision value is in its declared vocabulary; no cell contains a pipe or a dash character |
| Relative links and anchors in the inventory | 6 of 6 resolve |
| Hardcoding audit on the untouched worktree at `243a8811` | Exit 0; 2671 files; high 632; no new high finding (6 minutes) |
| Hardcoding audit with the new files | Not run |
| `python tools/build_records_index.py --check` after regeneration | Exit 0 (run before the commit) |

## Known failures

None observed. The unverified items are listed above and in the inventory's
"Limits" section.

## Commands to continue

```bash
cd /home/username/.le-integration/site-inventory
export TMPDIR=/home/username/.le-ci-tmp   # a temporary folder outside the repository
PYTHONPATH=devtools/src python -m loop_engine_devtools.cli --hardcoding-audit \
  --allowlist devtools/hardcoding-allowlist.yaml \
  --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high
npx --yes markdownlint-cli2@0.23.2 docs/verification/WEBSITE-CUT-INVENTORY-2026-09-23.md \
  docs/verification/HANDOFF-site-inventory-2026-09-23.md
python tools/build_records_index.py --check
python -m unittest tools.test_build_records_index
```

The scratch scripts that produced the rows (`extract.py`, `history.py`,
`removals.py`, `rows.py`, `generate.py`) are in this session's scratchpad and
are not part of the repository. To change a row, edit the Markdown table and
the JSON record together.

## Live or external effects

None. Only read-only GET requests to the live site, listed above.
