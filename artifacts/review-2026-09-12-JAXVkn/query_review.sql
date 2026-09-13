-- Read-only examples for this derived review database.
SELECT * FROM coverage;

SELECT tool, scope, count(*) AS records
FROM sessions
GROUP BY tool, scope
ORDER BY tool, scope;

SELECT campaign, arm, count(*) AS saved_cells,
       count(*) FILTER (WHERE gate_passed) AS reported_gate_passes,
       count(*) FILTER (WHERE model_calls IS NULL) AS unknown_call_counts
FROM tactical_cells
GROUP BY campaign, arm
ORDER BY campaign, arm;

SELECT finding_id, importance, evidence_state, summary
FROM findings ORDER BY finding_id;

SELECT path, size, sha256
FROM source_file_index
WHERE path LIKE 'src/loop_engine/core/harness%'
ORDER BY path;
