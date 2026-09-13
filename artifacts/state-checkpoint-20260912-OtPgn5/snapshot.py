"""Build a body-free, derived checkpoint with DuckDB-managed JSON exports.

Reads saved evidence and source identities. It does not import Loop Engine,
call providers, execute candidate code, or alter canonical records.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess

import duckdb


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STUDY = ROOT / ".loop-engine-dev/cognitive-act-20260912-lRaw69"
SYSTEMATIC = ROOT / ".loop-engine-dev/systematic-20260912-Ly6MoT"
SOURCES = (
    "AGENTS.md",
    "README.md",
    "architecture.yaml",
    "terminology.yaml",
    "humanizer-context.md",
    "docs/architecture/CONSTITUTION.md",
    "docs/architecture/WORK-APPROACH-INSTRUMENTATION.md",
    "docs/contracts/README.md",
    "docs/components/README.md",
    "docs/components/self-improvement/README.md",
    "docs/components/core-architecture/HARNESS-FALLBACK.md",
    "docs/components/practitioner/COGNITIVE-ACT-RECOVERY.md",
    "docs/components/intelligence-layers/REUSABLE-CAPABILITY-FLYWHEEL.md",
    "docs/context/REFERENCE-SOURCES.md",
    "docs/research/COGNITIVE-STEP-HARNESS-DIRECTION-2026-09-12.md",
    "docs/verification/HARNESS-STEP-RECOVERY-2026-09-12.md",
    "docs/verification/COGNITIVE-ACT-RECOVERY-2026-09-12.md",
    "docs/verification/UNSEEN-NOVEL-TASK-CAMPAIGN-2026-09-06.md",
    "artifacts/review-2026-09-12-JAXVkn/REVIEW.md",
    "artifacts/review-2026-09-12-JAXVkn/review.duckdb",
    "artifacts/cognitive-act-recovery-20260912-05JQhk/summary.json",
    "artifacts/cognitive-act-recovery-20260912-05JQhk/summarize.py",
    "embodiments/HARNESS-GUIDE.md",
    "devtools/embodiment_lab/systematic_runtime.py",
    "tools/task_campaign.py",
    ".loop-engine-dev/systematic-20260912-Ly6MoT/campaign.duckdb",
    ".loop-engine-dev/systematic-20260912-Ly6MoT/campaign-manifest.json",
    ".loop-engine-dev/cognitive-act-20260912-lRaw69/focused-checks.json",
    ".loop-engine-dev/cognitive-act-20260912-lRaw69/qa/self-test.json",
    ".loop-engine-dev/cognitive-act-20260912-lRaw69/qa/conformance.json",
    ".loop-engine-dev/cognitive-act-20260912-lRaw69/qa/wheels/loop_engine-0.1.0-py3-none-any.whl",
)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True
    ).strip()


def main() -> None:
    for name in ("checkpoint.duckdb", "checkpoint.json", "source-manifest.json"):
        if (OUT / name).exists():
            raise SystemExit(f"Refusing to overwrite existing checkpoint: {name}")
    db = duckdb.connect(str(OUT / "checkpoint.duckdb"))
    db.execute("SET threads=2")
    db.execute("CREATE TABLE metadata(key VARCHAR PRIMARY KEY, value VARCHAR)")
    db.executemany("INSERT INTO metadata VALUES (?, ?)", [
        ("record_type", "local_state_checkpoint/v1"),
        ("repository", str(ROOT)),
        ("branch", git("branch", "--show-current")),
        ("head", git("rev-parse", "HEAD")),
        ("scope", "saved evidence and source identities; no new model calls"),
        ("authority", "derived report projection, not a product store or managed record"),
        ("history_verification", "six chains verified by cited recovery summary; not re-executed here"),
    ])
    db.execute("CREATE TABLE dirty_paths(status VARCHAR, path VARCHAR)")
    status = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain=v1", "-z"]
    ).decode().split("\0")
    # There are no renames in this checkpoint. Refuse ambiguous parsing.
    entries = [entry for entry in status if entry]
    if any(len(entry) < 4 or entry[2] != " " or "R" in entry[:2]
           or "C" in entry[:2] for entry in entries):
        raise SystemExit("Unexpected Git status record; inspect before importing")
    db.executemany("INSERT INTO dirty_paths VALUES (?, ?)",
                   [(entry[:2], entry[3:]) for entry in entries])
    db.execute("CREATE TABLE source_manifest(path VARCHAR PRIMARY KEY, bytes BIGINT, sha256 VARCHAR)")
    for relative in SOURCES:
        path = ROOT / relative
        db.execute("INSERT INTO source_manifest VALUES (?, ?, ?)",
                   [relative, path.stat().st_size, digest(path)])
    db.execute("CREATE TABLE runtime_sources(path VARCHAR PRIMARY KEY, current_sha256 VARCHAR, checked_sha256 VARCHAR, matches BOOLEAN)")
    current = ROOT / "src/loop_engine"
    checked = STUDY / "qa/package-source/src/loop_engine"
    paths = {p.relative_to(current) for p in current.rglob("*.py")}
    paths |= {p.relative_to(checked) for p in checked.rglob("*.py")}
    for relative in sorted(paths):
        a, b = current / relative, checked / relative
        da = digest(a) if a.is_file() else None
        dbb = digest(b) if b.is_file() else None
        db.execute("INSERT INTO runtime_sources VALUES (?, ?, ?, ?)",
                   [str(relative), da, dbb, da is not None and da == dbb])
    legacy = sorted(str(p) for p in Path("/home/username/task-campaign-runs").glob("*/cells/*/cell.json"))
    db.execute("""CREATE TABLE legacy_cells AS
        SELECT filename AS source_path, task, arm, status, solve_terminal,
               gate_passed, gate_score, model_calls, elapsed_seconds
        FROM read_json_auto(?, filename=true, union_by_name=true)""", [legacy])
    summary = ROOT / "artifacts/cognitive-act-recovery-20260912-05JQhk/summary.json"
    db.execute("""CREATE TABLE cognitive_cells AS
        WITH records AS (SELECT unnest(cells) AS cell FROM read_json_auto(?))
        SELECT cell.* FROM records""", [str(summary)])
    campaign = str(SYSTEMATIC / "campaign.duckdb").replace("'", "''")
    db.execute(f"ATTACH '{campaign}' AS campaign (READ_ONLY)")
    db.execute("CREATE TABLE factor_counts AS SELECT factor, count(*) AS levels, list(DISTINCT maturity) AS maturity FROM campaign.factor_levels GROUP BY factor ORDER BY factor")
    db.execute("CREATE TABLE task_admission_counts AS SELECT admission_status, count(*) AS tasks FROM campaign.task_catalog GROUP BY admission_status ORDER BY admission_status")
    configurations = db.execute("SELECT count(*) FROM campaign.configurations").fetchone()[0]
    db.execute("INSERT INTO metadata VALUES ('catalogued_configurations_per_task', ?)", [str(configurations)])
    db.execute("DETACH campaign")
    db.execute("CREATE TABLE qa_full AS SELECT record_type, passed, total, all_passed, missing_dependencies, optional_adapters_not_tested, strict_summary FROM read_json_auto(?)", [str(STUDY / "qa/self-test.json")])
    db.execute("CREATE TABLE qa_conformance AS SELECT record_type, files_scanned, all_gates_pass, zero_tolerance_gates FROM read_json_auto(?)", [str(STUDY / "qa/conformance.json")])
    db.execute("CREATE TABLE scoped_processes(pid INTEGER, command VARCHAR, category VARCHAR)")
    markers = (b"embodiment_lab.systematic", b"tools/task_campaign.py", b"cognitive-act-20260912-")
    for path in Path("/proc").iterdir():
        if not path.name.isdigit() or int(path.name) == os.getpid():
            continue
        try:
            argv = (path / "cmdline").read_bytes().split(b"\0")
            command = (path / "comm").read_text().strip()
        except (OSError, PermissionError):
            continue
        # Compare argument tokens only. Never retain arguments or environment.
        matched = any(any(marker in arg for marker in markers) for arg in argv[1:])
        if matched and command not in {"bash", "timeout", "codex", "codex-code-mode", "node"}:
            db.execute("INSERT INTO scoped_processes VALUES (?, ?, ?)",
                       [int(path.name), command, "campaign_marker_match_not_ownership_proof"])
    target = str(OUT / "checkpoint.json").replace("'", "''")
    db.execute(f"""COPY (SELECT
        'local_state_checkpoint/v1' AS record_type,
        current_timestamp AS observed_at,
        (SELECT list(t ORDER BY key) FROM metadata t) AS metadata,
        (SELECT count(*) FROM dirty_paths) AS dirty_status_entries,
        (SELECT count(*) FROM runtime_sources) AS runtime_python_files,
        (SELECT bool_and(matches) FROM runtime_sources) AS runtime_matches_checked_source,
        (SELECT count(*) FROM legacy_cells) AS legacy_cell_records,
        (SELECT count(DISTINCT task) FROM legacy_cells) AS legacy_distinct_tasks,
        (SELECT list(t ORDER BY factor) FROM factor_counts t) AS factor_counts,
        (SELECT list(t ORDER BY admission_status) FROM task_admission_counts t) AS task_admission_counts,
        (SELECT count(*) FROM cognitive_cells) AS cognitive_runs,
        (SELECT sum(model_calls_known_subtotal) FROM cognitive_cells) AS cognitive_known_calls,
        (SELECT count(*) FILTER (WHERE model_call_accounting_complete) FROM cognitive_cells) AS cognitive_complete_call_totals,
        (SELECT count(*) FILTER (WHERE heldout_passed) FROM cognitive_cells) AS cognitive_heldout_passes,
        (SELECT sum(recovery_rounds) FROM cognitive_cells) AS recovery_rounds,
        (SELECT sum(reusable_candidates) FROM cognitive_cells) AS reusable_candidates,
        (SELECT list(t) FROM qa_full t) AS installed_full_suite,
        (SELECT list(t) FROM qa_conformance t) AS installed_conformance,
        (SELECT count(*) FROM scoped_processes) AS campaign_process_marker_matches
    ) TO '{target}' (FORMAT JSON, ARRAY false)""")
    target = str(OUT / "source-manifest.json").replace("'", "''")
    db.execute(f"COPY (SELECT * FROM source_manifest ORDER BY path) TO '{target}' (FORMAT JSON, ARRAY true)")
    print(db.execute("SELECT count(*), bool_and(matches) FROM runtime_sources").fetchone())
    print(db.execute("SELECT count(*), count(DISTINCT task) FROM legacy_cells").fetchone())
    print(db.execute("SELECT count(*), sum(model_calls_known_subtotal), sum(recovery_rounds), sum(reusable_candidates) FROM cognitive_cells").fetchone())
    print('campaign process matches', db.execute("SELECT * FROM scoped_processes").fetchall())
    db.close()


if __name__ == "__main__":
    main()
