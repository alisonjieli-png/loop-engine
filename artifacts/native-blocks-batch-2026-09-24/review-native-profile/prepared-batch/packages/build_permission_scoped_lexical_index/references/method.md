# Lexical Reference Engine Algorithm

## Overview
A deterministic, in-memory lexical indexer designed for tenant-scoped document retrieval. It uses exact term matching with Unicode normalization.

## Normalization Pipeline
1. **Unicode NFKC**: Normalizes compatibility characters (e.g., full-width Latin to standard Latin).
2. **Casefolding**: Converts all text to lowercase using Unicode casefolding rules.
3. **Tokenization**: Splits text on whitespace.

## Indexing & Querying
- **Indexing**: Maps normalized terms to document identifiers and tenant scopes.
- **Filtering**: Before ranking, all documents must match the `tenant_id` provided in the query.
- **Abstention**: If the number of distinct query terms found in a document is less than `min_distinct_matches`, the document is excluded.

## Ranking Criteria
Results are sorted by:
1. **Distinct Match Count** (Descending): Number of unique query terms present in the document.
2. **Total Term Frequency** (Descending): Total count of all query term occurrences in the document.
3. **Lexical ID** (Ascending): The `doc_id` as a string tie-breaker.

## Constraints & Refusals
- **Input Size**: Maximum 1MiB UTF-8.
- **Type Strictness**: Rejects booleans in integer fields (e.g., `min_distinct_matches`).
- **JSON Integrity**: Rejects inputs with duplicate keys or non-finite numbers (NaN, Inf).
- **Complexity**: $O(N \cdot L)$ where $N$ is number of docs and $L$ is avg doc length.

## Limitations
- No semantic/embedding-based similarity.
- No fuzzy/stemming support.
- In-memory only; no persistence.
