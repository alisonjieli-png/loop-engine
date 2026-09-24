# Build Permission-Scoped Lexical Index

## Task
Implement a deterministic, in-memory lexical indexer that supports tenant-scoped querying, text normalization (NFKC + casefold), and specific ranking criteria.

## First Action
1. Define the JSON input schema to enforce strict types (rejecting booleans where integers are expected).
2. Implement the normalization pipeline: `unicodedata.normalize('NFKC', text).casefold()`.
3. Implement the indexing logic: map normalized terms to `(doc_id, position)` or frequency counts.
4. Implement the query logic: filter by `tenant_id`, calculate distinct term matches, total term frequency, and tie-break with `doc_id`.

## Helper Invocation
The tool is a standalone Python script. It reads a JSON object from `stdin` and writes a JSON object to `stdout`.

## Contract & Refusal Rules
- **Input Size**: Max 1MiB UTF-8.
- **Refusals**: 
    - Duplicate keys in JSON (manual check required as `json.load` picks last).
    - Non-finite numbers (NaN/Inf).
    - Boolean values in integer fields (e.g., `min_distinct_matches: true` is a refusal).
    - Mismatched `source_hash` for a document in the corpus.
- **Ranking**: 
    1. Count of distinct query terms found in doc.
    2. Total occurrences of all query terms in doc.
    3. Lexical `doc_id` (ascending).
- **Scope**: Only documents matching the query's `tenant_id` are considered.

## Constraints
- Python 3.10+ standard library only.
- No `eval`, `exec`, `importlib`, `network`, `os.system`, or `subprocess` inside the tool.
- No semantic similarity; exact term matching only.
