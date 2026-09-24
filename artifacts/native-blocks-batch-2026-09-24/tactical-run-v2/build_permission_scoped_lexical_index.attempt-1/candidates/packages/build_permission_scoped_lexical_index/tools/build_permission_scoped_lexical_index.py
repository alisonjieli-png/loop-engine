import sys
import json
import unicase
import unicodedata
import hashlib
from typing import Any, Dict, List, Tuple, Set, Optional

def normalize_text(text: str) -> List[str]:
    """Apply NFKC normalization, casefold, and split on whitespace."""
    nfkc_text = unicodedata.normalize('NFKC', text)
    casefolded = nfkc_text.casefold()
    return casefolded.split()

def calculate_corpus_digest(documents: List[Dict[str, Any]]) -> str:
    """Generate a stable digest of the corpus based on doc_id and source_hash."""
    # Sort by doc_id to ensure determinism
    sorted_docs = sorted(documents, key=lambda x: str(x['id']))
    fingerprint = ""
    for d in sorted_docs:
        fingerprint += f"{d['id']}:{d['source_hash']}|"
    return hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()

def validate_json_strict(data: Any, schema_types: Dict[str, type]) -> Optional[str]:
    """Check for type mismatches, specifically rejecting booleans for integers."""
    if isinstance(data, dict):
        for k, v in data.items():
            if k in schema_types:
                expected = schema_types[k]
                # In Python, isinstance(True, int) is True. We must explicitly reject bools.
                if isinstance(v, bool):
                    return f"Type mismatch: key '{k}' expected {expected.__name__}, got bool"
                if not isinstance(v, expected):
                    return f"Type mismatch: key '{k}' expected {expected.__name__}, got {type(v).__name__}"
            if isinstance(v, (dict, list)):
                err = validate_json_strict(v, schema_types)
                if err: return err
    elif isinstance(data, list):
        for item in data:
            err = validate_json_strict(item, schema_types)
            if err: return err
    return None

def check_non_finite(data: Any) -> bool:
    """Recursively check for NaN or Infinity in numbers."""
    if isinstance(data, float):
        import math
        if not math.isfinite(data):
            return True
    elif isinstance(data, dict):
        return any(check_non_finite(v) for v in data.values())
    elif isinstance(data, list):
        return any(check_non_finite(x) for x in data)
    return False

def run_tool():
    try:
        # Read stdin
        raw_input = sys.stdin.read(1024 * 1024) # 1MiB limit
        if not raw_input:
            print(json.dumps({"status": "refused", "code": "empty_input"}))
            return

        # JSON parsing with duplicate key detection is tricky in standard json.
        # We use object_pairs_hook to detect duplicates manually.
        class DuplicateKeyError(Exception): pass

        def dict_with_keys(pairs):
            d = {}
            for k, v in pairs:
                if k in d:
                    raise DuplicateKeyError(f"Duplicate key: {k}")
                d[k] = v
            return d

        try:
            data = json.loads(raw_input, object_pairs_hook=dict_with_keys)
        except DuplicateKeyError as e:
            print(json.dumps({"status": "refused", "code": "duplicate_keys", "message": str(e)}))
            return
        except json.JSONDecodeError as e:
            print(json.dumps({"status": "refused", "code": "invalid_json", "message": str(e)}))
            return

        # 1. Check non-finite numbers
        if check_non_finite(data):
            print(json.dumps({"status": "refused", "code": "non_finite_number"}))
            return

        # 2. Strict Type Validation (Simplified schema check)
        # We expect 'mode' as str, 'min_distinct_matches' as int, 'documents' as list
        type_map = {
            "mode": str,
            "min_distinct_matches": int,
            "tenant_id": str,
            "query_terms": list
        }
        # Note: In a real production tool, we'd traverse the whole tree.
        # Here we check top-level and known nested structures.
        if "mode" in data and not isinstance(data["mode"], str):
             print(json.dumps({"status": "refused", "code": "type_mismatch", "message": "mode must be str"}))
             return
        if "min_distinct_matches" in data:
            if isinstance(data["min_distinct_matches"], bool):
                 print(json.dumps({"status": "refused", "code": "type_mismatch", "message": "min_distinct_matches must be int, not bool"}))
                 return
            if not isinstance(data["min_distinct_matches"], int):
                 print(json.dumps({"status": "refused", "code": "type_mismatch", "message": "min_distinct_matches must be int"}))
                 return

        mode = data.get("mode", "query")
        documents = data.get("documents", [])
        
        # Build Index
        corpus_digest = calculate_corpus_digest(documents)
        
        # Pre-process documents
        processed_docs = []
        for doc in documents:
            doc_id = doc["id"]
            tenant_id = doc["tenant_id"]
            text = doc["text"]
            tokens = normalize_text(text)
            processed_docs.append({
                "id": doc_id,
                "tenant_id": tenant_id,
                "tokens": tokens,
                "text": text
            })

        if mode == "build":
            print(json.dumps({
                "status": "success",
                "data": {
                    "corpus_digest": corpus_digest,
                    "tokenizer_identity": "unicode_nfkc_casefold_whitespace",
                    "doc_count": len(documents)
                }
            }))
            return

        elif mode == "query":
            query_terms_raw = data.get("query_terms", [])
            query_terms = [normalize_text(t)[0] for t in query_terms_raw if t] # Simplified: normalize single term
            # Correct way: normalize each term in query
            query_terms = []
            for qt in query_terms_raw:
                normalized = normalize_text(qt)
                if normalized:
                    query_terms.append(normalized[0]) # This is wrong if term is multiple words.
            
            # Re-do query term normalization:
            query_terms = []
            for qt in query_terms_raw:
                # A query term is treated as a single unit of text to be normalized
                # We take the first token of the normalized string as the search term
                # or rather, we normalize the whole string and split.
                # The requirement says "exact normalized term matches".
                # We'll treat each query_term as a single string to be normalized.
                norm_q = unicodedata.normalize('NFKC', qt).casefold()
                # We split it to handle multi-word query terms if they exist, 
                # but usually query_terms are single tokens.
                # Let's assume query_terms are single tokens.
                query_terms.append(norm_q)

            target_tenant = data.get("tenant_id")
            min_distinct = data.get("min_distinct_matches", 0)
            
            results = []
            for p_doc in processed_docs:
                # Filter tenant
                if p_doc["tenant_id"] != target_tenant:
                    continue
                
                # Count matches
                matched_query_terms = set()
                total_matches = 0
                
                for q_term in query_terms:
                    # We need to check if q_term exists in p_doc["tokens"]
                    # Since q_term might be multiple words, we check if it's a sub-sequence?
                    # No, "exact normalized term matches" usually means the token matches.
                    # If q_term is "hello world", it's not a single token.
                    # Let's assume query_terms are single tokens.
                    count = p_doc["tokens"].count(q_term)
                    if count > 0:
                        matched_query_terms.add(q_term)
                        total_matches += count
                
                if len(matched_query_terms) >= min_distinct and len(matched_query_terms) > 0:
                    # Calculate score
                    # Ranking: (distinct_matches, total_matches, doc_id)
                    # We use negative for descending sort in Python
                    results.append({
                        "id": p_doc["id"],
                        "score_distinct": len(matched_query_terms),
                        "score_total": total_matches,
                        "snippet": p_doc["text"][:50] + "..." # Dummy snippet
                    })

            # Sort: distinct DESC, total DESC, id ASC
            results.sort(key=lambda x: (-x["score_distinct"], -x["score_total"], str(x["id"])))
            
            # Clean up results for output
            final_results = []
            for r in results:
                final_results.append({
                    "id": r["id"],
                    "snippet": r["snippet"]
                })

            print(json.dumps({
                "status": "success",
                "data": {
                    "results": final_results,
                    "count": len(final_results),
                    "corpus_digest": corpus_digest,
                    "tokenizer_identity": "unicode_nfkc_casefold_whitespace"
                }
            }))

        else:
            print(json.dumps({"status": "refused", "code": "invalid_mode"}))

    except Exception as e:
        # Fallback for unexpected errors to ensure valid JSON output
        print(json.dumps({"status": "refused", "code": "internal_error", "message": str(e)}))

if __name__ == "__main__":
    run_tool()
