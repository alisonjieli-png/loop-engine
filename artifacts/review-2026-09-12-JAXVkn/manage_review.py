"""Build a disposable DuckDB review projection from existing saved evidence.

This is an audit artifact, not a Loop Engine runtime, catalog authority, or
managed-record writer. It runs no tasks, evaluators, models, or test suites.
JSON output is produced only by DuckDB COPY.
"""
from pathlib import Path
import hashlib
import json
import shutil

import duckdb

DEST = Path(__file__).parent
SOURCE = Path('/tmp/loop-engine-review-20260912-JAXVkn')
DB = DEST / 'review.duckdb'
con = duckdb.connect(str(DB))
con.execute("SET memory_limit='2GB'")
con.execute('SET threads=2')
con.execute('SET preserve_insertion_order=false')
con.execute('CREATE TABLE IF NOT EXISTS source_documents (name VARCHAR PRIMARY KEY, source_path VARCHAR, sha256 VARCHAR, payload JSON)')
names = (
    'inventory-summary.json', 'content-scan-summary.json',
    'tracked-file-manifest.json', 'session-summary.json',
    'session-index.json', 'supplemental-opencode-session-index.json',
    'codex-history-index.json', 'snapshot-drift.json',
    'focused-checks.json', 'harness-semantic-checks.json',
    'review-probes.json', 'gate-review.json',
    'timeout-and-reward-review.json', 'campaign-inventory.json',
    'saved-tactical-review.json', 'wheel-build-result.json',
    'clean-install-result.json', 'repository-conformance-result.json',
    'installed-conformance-result.json', 'installed-self-test-result.json',
    'unfiltered-check-disposition.json', 'user-request-stop.json',
)
for name in names:
    p = SOURCE / name
    if not p.is_file():
        continue
    raw = p.read_bytes()
    previous = con.execute('SELECT sha256 FROM source_documents WHERE name=?', [name]).fetchone()
    if previous and previous[0] != hashlib.sha256(raw).hexdigest():
        raise SystemExit('Source changed since the review snapshot: ' + name)
    con.execute('INSERT INTO source_documents VALUES (?, ?, ?, ?::JSON) ON CONFLICT DO NOTHING',
                [name, str(p), hashlib.sha256(raw).hexdigest(), raw.decode()])
con.execute('CREATE TABLE IF NOT EXISTS file_inventory AS SELECT * FROM read_json_auto(?, format=\'newline_delimited\', union_by_name=true)',
            [str(SOURCE / 'all-file-inventory.jsonl.gz')])
con.execute('CREATE TABLE IF NOT EXISTS source_file_index AS SELECT * FROM read_json_auto(?, format=\'array\', union_by_name=true)',
            [str(SOURCE / 'source-file-index.json')])
con.execute('CREATE TABLE IF NOT EXISTS tracked_files AS SELECT json_extract_string(value,\'$.path\') AS path, json_extract_string(value,\'$.sha256\') AS sha256, value AS record FROM (SELECT payload FROM source_documents WHERE name=\'tracked-file-manifest.json\'), json_each(payload,\'$.files\')')
con.execute('CREATE TABLE IF NOT EXISTS sessions AS SELECT json_extract_string(value,\'$.tool\') AS tool, json_extract_string(value,\'$.session_id\') AS session_id, json_extract_string(value,\'$.scope\') AS scope, value AS record FROM (SELECT payload FROM source_documents WHERE name IN (\'session-index.json\',\'supplemental-opencode-session-index.json\')), json_each(payload)')
con.execute('CREATE TABLE IF NOT EXISTS tactical_cells AS SELECT json_extract_string(value,\'$.campaign\') AS campaign, json_extract_string(value,\'$.task\') AS task, json_extract_string(value,\'$.arm\') AS arm, json_extract_string(value,\'$.solve_terminal\') AS solve_terminal, json_extract(value,\'$.gate_passed\')::BOOLEAN AS gate_passed, json_extract(value,\'$.model_calls\')::BIGINT AS model_calls, value AS record FROM (SELECT payload FROM source_documents WHERE name=\'saved-tactical-review.json\'), json_each(payload,\'$.cells\')')
con.execute('CREATE TABLE IF NOT EXISTS tactical_histories AS SELECT json_extract_string(value,\'$.run_id\') AS run_id, json_extract_string(value,\'$.path\') AS source_path, json_extract_string(value,\'$.sha256\') AS sha256, value AS record FROM (SELECT payload FROM source_documents WHERE name=\'saved-tactical-review.json\'), json_each(payload,\'$.histories\')')
con.execute('CREATE TABLE IF NOT EXISTS findings (finding_id VARCHAR PRIMARY KEY, importance VARCHAR, evidence_state VARCHAR, summary VARCHAR, source_document VARCHAR)')
findings = [
 ('F01','before performance claims','reproduced before review-only clarification','All eight adapted evaluators expose target labels to predict; both saved perfect-score solutions train on the same full CSV later sampled as holdout.','gate-review.json'),
 ('F02','before lifecycle qualification','reproduced before review-only clarification','Declared verifier timeout returns while a descendant continues writing; verifier and campaign gate launch on the host.','timeout-and-reward-review.json'),
 ('F03','before reuse and replay qualification','reproduced before review-only clarification','Current reader rejects an unchanged v1 LoopDefinition produced by the committed encoder because new output fields change its digest.','review-probes.json'),
 ('F04','before continued-output integration','observed source contract behavior','Consumer output multiplicity controls input connection compatibility; response schema, production lifetime and serving policy need distinct meanings.','review-probes.json'),
 ('F05','before training-data admission','reproduced before review-only clarification','Empty history earns completion credit; structural markers plus artifact-missing prose can earn the maximum trajectory reward.','timeout-and-reward-review.json'),
 ('F06','before causal comparisons','observed records and source','Campaign retries reuse and remove a task-arm directory; saved reports and surviving cell records disagree, and a gate pass is separate from engine completion.','saved-tactical-review.json'),
 ('F07','before a capacity claim','missing sufficient evidence','HTTP acceptance of a max_tokens parameter does not establish the exact model maximum; the fit-window helper uses a character estimate.','campaign-inventory.json'),
 ('F08','before describing the product path','observed source call graph','Qualified reuse, graph execution, reactive portfolios and pointer resolution exist, but their integration into per-step harness operation is incomplete.','tracked-file-manifest.json'),
]
con.executemany('INSERT INTO findings VALUES (?, ?, ?, ?, ?) ON CONFLICT DO NOTHING', findings)
con.execute('CREATE TABLE IF NOT EXISTS coverage AS SELECT ?::VARCHAR AS record_type, (SELECT count(*) FROM file_inventory) AS inventoried_file_entries, (SELECT count(*) FROM source_file_index) AS text_files_scanned, (SELECT count(*) FROM sessions) AS session_records, (SELECT count(*) FROM tactical_cells) AS tactical_cell_records, (SELECT count(*) FROM tactical_histories) AS tactical_history_files, FALSE AS exhaustive_line_by_line_semantic_review, FALSE AS new_provider_calls_authorized', ['loop_engine_review_coverage/v1'])

def export(query, filename, options='FORMAT JSON, ARRAY true'):
    # Both query and output filenames are fixed review code, never source text.
    target = str(DEST / filename).replace("'", "''")
    con.execute(f"COPY ({query}) TO '{target}' ({options})")

export('SELECT * FROM coverage', 'coverage.json')
export('SELECT * FROM findings ORDER BY finding_id', 'findings.json')
export('SELECT campaign, count(*) AS saved_cells, count(*) FILTER (WHERE gate_passed) AS reported_gate_passes, count(*) FILTER (WHERE model_calls IS NULL) AS unknown_call_counts, sum(model_calls) AS known_call_subtotal FROM tactical_cells GROUP BY campaign ORDER BY campaign', 'tactical-campaigns.json')
export('SELECT * FROM sessions ORDER BY tool, session_id', 'sessions.json')
export('SELECT * FROM source_documents ORDER BY name', 'evidence-documents.json')
export('SELECT * FROM file_inventory', 'file-inventory.jsonl.gz', "FORMAT JSON, ARRAY false, COMPRESSION GZIP")
export('SELECT * FROM source_file_index', 'source-file-index.jsonl.gz', "FORMAT JSON, ARRAY false, COMPRESSION GZIP")
con.execute('CHECKPOINT')
print(con.execute('SELECT * FROM coverage').fetchall())
print(con.execute('SELECT tool,scope,count(*) FROM sessions GROUP BY tool,scope ORDER BY tool,scope').fetchall())
con.close()

# Preserve existing explanatory logs and the already-used reproduction source.
# Do not execute these scripts during the present review-only phase.
for name in ('review_census.py','review_probes.py','gate_review.py',
             'timeout_review.py','saved_tactical_review.py',
             'installed-self-test.log','installed-conformance.log',
             'repository-conformance.log','wheel-build.log','clean-install.log'):
    p = SOURCE / name
    if p.is_file():
        target = DEST / 'prior-review-material' / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(p, target)
