# Lexical Reference Engine Algorithm

## Overview
A deterministic, in-memory lexical indexer designed for tenant-scoped document retrieval. It uses exact term matching after Unicode normalization.

## Normalization Pipeline
1. **Unicode NFKC**: Ensures compatibility of different character representations (e.g., combining characters).
2. **Casefolding**: A more aggressive version of lowercasing suitable for caseless matching.
3. **Whitespace Splitting**: Tokens are separated by any whitespace character.

## Query Ranking Heuristics
Results are returned in a strictly defined order to ensure stability:
1. **Primary**: Number of distinct query terms found in the document (Descending).
2. **Secondary**: Total number of occurrences of all query terms in the document (Descending).
3. **Tertiary**: Lexical document ID (Ascending).

## Constraints & Refusals
- **Tenant Isolation**: A document is only a candidate if `doc.tenant_id == query.tenant_id`.
- **Abstention**: If the number of distinct query terms matched is less than `min_distinct_matches`, the document is omitted.
- **Type Strictness**: The engine rejects JSON where a boolean is provided for a field expecting an integer (e.g., `min_distinct_matches: true`).
- **Input Integrity**: Rejects JSON with duplicate keys or non-finite numbers (NaN, Infinity).

## Complexity
- **Build**: $O(N \cdot L)$ where $N$ is doc count and $L$ is avg text length.
- **Query**: $O(N \cdot T)$ where $T$ is number of query terms.
- **Memory**: $O(N \cdot L)$ to store the in-memory index.

## Limitations
- No semantic or fuzzy matching.
- No stemming or lemmatization.
- Purely lexical.
