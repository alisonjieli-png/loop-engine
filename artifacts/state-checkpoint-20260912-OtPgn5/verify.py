"""Check the checkpoint's citations, numbers, and retained source identities.

This is a documentation check, not a task benchmark or runtime self-test.
The output is a separate DuckDB-managed validation projection.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

import duckdb


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REPORT = ROOT / "docs/research/COGNITIVE-STEP-ARCHITECTURE-AND-STATE-2026-09-12.md"


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main() -> None:
    for name in ("validation.duckdb", "validation.json"):
        if (OUT / name).exists():
            raise SystemExit(f"Refusing to overwrite validation: {name}")
    checks: list[tuple[str, bool, str]] = []
    links = 0
    for path in (REPORT, OUT / "README.md"):
        text = path.read_text()
        for target in re.findall(r"\[[^\]\n]+\]\(([^)\n]+)\)", text):
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            links += 1
            checks.append(("local_link", resolved.exists(), f"{path.name}: {target}"))
        checks.append(("no_em_or_en_dashes", not bool(re.search("[\u2013\u2014]", text)), path.name))
        retired = re.compile(
            r"\bchronicles?\b|\breceipts?\b|\bchild(?:ren)?\b|"
            r"\broot[ _-]+(?:loop|practitioner|intelligence|solution)\b|"
            r"\bloop[ _-]intelligence\b|\bintelligence pillars?\b|"
            r"\bString Intelligence\b|\bstop conditions?\b", re.I
        )
        checks.append(("current_public_vocabulary", not bool(retired.search(text)), path.name))
    text = REPORT.read_text()
    definitions = re.findall(r"^\[\^(\d+)\]:", text, re.M)
    uses = re.findall(r"\[\^(\d+)\](?!:)", text)
    checks.append(("footnote_definitions_unique", len(definitions) == len(set(definitions)), str(len(definitions))))
    checks.append(("all_footnotes_resolve", set(uses) == set(definitions), str(sorted(set(uses), key=int))))
    entry = (ROOT / "docs/context/CODEX-START-HERE.md").read_text()
    checks.append(("session_entry_link", REPORT.name in entry, "CODEX-START-HERE.md"))
    saved = duckdb.connect(str(OUT / "checkpoint.duckdb"), read_only=True)
    facts = saved.execute("""SELECT
        (SELECT count(*) FROM legacy_cells),
        (SELECT count(DISTINCT task) FROM legacy_cells),
        (SELECT count(*) FROM cognitive_cells),
        (SELECT sum(model_calls_known_subtotal) FROM cognitive_cells),
        (SELECT sum(recovery_rounds) FROM cognitive_cells),
        (SELECT sum(reusable_candidates) FROM cognitive_cells),
        (SELECT count(*) FILTER (WHERE heldout_passed) FROM cognitive_cells),
        (SELECT count(*) FILTER (WHERE model_call_accounting_complete) FROM cognitive_cells)
    """).fetchone()
    checks.append(("reported_run_denominators", facts == (80, 8, 6, 202, 9, 0, 0, 3), str(facts)))
    checks.append(("installed_full_suite", saved.execute("SELECT passed=3839 AND total=3839 AND all_passed FROM qa_full").fetchone()[0], "saved suite, not rerun"))
    checks.append(("installed_conformance", saved.execute("SELECT all_gates_pass AND len(json_keys(to_json(zero_tolerance_gates)))=27 FROM qa_conformance").fetchone()[0], "saved gates, not rerun"))
    for relative, expected in saved.execute("SELECT path, sha256 FROM source_manifest").fetchall():
        path = ROOT / relative
        checks.append(("principal_source_unchanged", path.is_file() and sha256(path) == expected, relative))
    current = ROOT / "src/loop_engine"
    runtime = saved.execute("SELECT path,current_sha256,checked_sha256,matches FROM runtime_sources").fetchall()
    checks.append(("runtime_file_set", {str(p.relative_to(current)) for p in current.rglob('*.py')} == {row[0] for row in runtime}, "472-file package source set"))
    for relative, expected, checked, matched in runtime:
        path = current / relative
        checks.append(("runtime_still_matches_checked_source", matched and path.is_file() and sha256(path) == expected == checked, relative))
    saved.close()
    db = duckdb.connect(str(OUT / "validation.duckdb"))
    db.execute("CREATE TABLE checks(name VARCHAR, passed BOOLEAN, detail VARCHAR)")
    db.executemany("INSERT INTO checks VALUES (?, ?, ?)", checks)
    db.execute("CREATE TABLE deliverables(path VARCHAR, sha256 VARCHAR)")
    for path in (REPORT, OUT / "README.md", OUT / "snapshot.py", OUT / "verify.py", ROOT / "docs/context/CODEX-START-HERE.md"):
        db.execute("INSERT INTO deliverables VALUES (?, ?)", [str(path.relative_to(ROOT)), sha256(path)])
    target = str(OUT / "validation.json").replace("'", "''")
    db.execute(f"""COPY (SELECT
        'documentation_checkpoint_validation/v1' AS record_type,
        current_timestamp AS verified_at,
        count(*) AS checks,
        count(*) FILTER (WHERE passed) AS passed,
        bool_and(passed) AS all_passed,
        (SELECT list(t ORDER BY path) FROM deliverables t) AS deliverables,
        (SELECT list(t) FROM checks t WHERE NOT passed) AS failures
        FROM checks) TO '{target}' (FORMAT JSON, ARRAY false)""")
    result = db.execute("SELECT count(*), count(*) FILTER (WHERE passed), bool_and(passed) FROM checks").fetchone()
    print('documentation checks', result, 'local links', links, 'sources', len(definitions))
    for failure in db.execute("SELECT * FROM checks WHERE NOT passed").fetchall():
        print(failure)
    db.close()
    if not result[2]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
