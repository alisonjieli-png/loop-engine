import sys
import json
import unicodedata
import hashlib
from typing import Any, Dict, List, Tuple, Set

def normalize_text(text: str) -> List[str]:
    """NFKC normalization followed by casefolding and whitespace splitting."""
    normalized = unicodedata.normalize('NFKC', text).casefold()
    return normalized.split()

def calculate_corpus_digest(documents: List[Dict[str, Any]]) -> str:
    """Creates a stable digest of the document set based on content and order."""
    hasher = hashlib.sha256()
    for doc in documents:
        # Sort keys to ensure stability
        serialized = json.dumps(doc, sort_keys=True)
        hasher.update(serialized.encode('utf-8'))
    return hasher.hexdigest()

def validate_json_strict(raw_data: str) -> Dict[str, Any]:
    """
    Validates JSON for duplicate keys and non-finite numbers.
    Note: Standard json.load handles duplicates by taking the last one.
    To detect duplicates, we use a custom decoder.
    """
    class DuplicateKeyDetector(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            self.keys = set()
            super().__init__(*args, **kwargs)

        def decode(self, s, **kwargs):
            # This is a simplified way to detect duplicates in a single pass
            # by checking the object_pairs_hook
            return super().decode(s, **kwargs)

    def dict_with_dup_check(pairs):
        seen = set()
        for k, v in pairs:
            if k in seen:
                raise ValueError(f"Duplicate key detected: {k}")
            seen.add(k)
        return dict(pairs)

    # Check for non-finite numbers first
    # A simple way is to parse and then check values
    data = json.loads(raw_data, object_pairs_hook=dict_with_dup_check)
    
    def check_finite(obj):
        if isinstance(obj, float):
            if not (float('-inf') < obj < float('inf')):
                raise ValueError("Non-finite number detected")
        elif isinstance(obj, dict):
            for v in obj.values(): check_finite(v)
        elif isinstance(obj, list):
            for v in obj: check_finite(v)
            
    check_finite(data)
    return data

def run_tool():
    try:
        raw_input = sys.stdin.read(1048576) # 1MiB limit
        if not raw_input:
            print(json.dumps({"status": "refused", "code": "EMPTY_INPUT", "message": "Input is empty"}))
            return

        data = validate_json_strict(raw_input)
        
        # 1. Validate structure and types
        # Requirement: Reject booleans where integers are required.
        if "mode" not in data:
            print(json.dumps({"status": "refused", "code": "MISSING_MODE", "message": "Missing 'mode'"}))
            return
        
        mode = data["mode"]
        
        if mode == "build":
            documents = data.get("documents", [])
            if not isinstance(documents, list):
                print(json.dumps({"status": "refused", "code": "INVALID_DOCS", "message": "Documents must be a list"}))
                return
            
            # Verify document structure
            for doc in documents:
                for field in ["id", "text", "tenant_id", "source_hash"]:
                    if field not in doc:
                        print(json.dumps({"status": "refused", "code": "INVALID_DOC", "message": f"Doc missing {field}"}))
                        return
                    if not isinstance(doc[field], (str, int)): # id can be int or str
                        print(json.dumps({"status": "refused", "code": "INVALID_TYPE", "message": f"{field} type error"}))
                        return

            corpus_digest = calculate_corpus_digest(documents)
            
            # Build Index
            # term -> list of (doc_id, tenant_id, doc_index_in_list)
            index: Dict[str, List[Tuple[Any, str, int]]] = {}
            for idx, doc in enumerate(documents):
                terms = normalize_text(doc["text"])
                for term in terms:
                    if term not in index:
                        index[term] = []
                    index[term].append((doc["id"], doc["tenant_id"], idx))

            print(json.dumps({
                "status": "success",
                "data": {
                    "corpus_digest": corpus_digest,
                    "tokenizer": "NFKC_CASEFOLD_WHITESPACE",
                    "doc_count": len(documents)
                }
            }))

        elif mode == "query":
            # For query, we need the corpus to be provided or assumed.
            # The contract implies the tool is stateless per call, so corpus must be in input.
            corpus = data.get("corpus", [])
            query_terms_raw = data.get("query_terms", [])
            target_tenant = data.get("tenant_id")
            min_distinct = data.get("min_distinct_matches", 0)

            # Type check min_distinct (must be int, not bool)
            if not isinstance(min_distinct, int) or isinstance(min_distinct, bool):
                print(json.dumps({"status": "refused", "code": "INVALID_MIN_DISTINCT", "message": "min_distinct_matches must be integer"}))
                return

            if not isinstance(query_terms_raw, list):
                print(json.dumps({"status": "refused", "code": "INVALID_QUERY", "message": "query_terms must be list"}))
                return

            normalized_queries = [normalize_text(t)[0] if t else "" for t in query_terms_raw]
            # Note: normalize_text returns a list. If we want the whole string normalized:
            normalized_queries = []
            for qt in query_terms_raw:
                norm_list = normalize_text(qt)
                if norm_list:
                    normalized_queries.append(norm_list)
                else:
                    normalized_queries.append("")

            # We need to re-index the provided corpus for this query
            # In a real system this is pre-built, but here it's a bounded in-memory tool.
            term_map: Dict[str, List[int]] = {} # term -> list of doc indices
            for idx, doc in enumerate(corpus):
                terms = normalize_text(doc["text"])
                for t in terms:
                    if t not in term_map:
                        term_map[t] = []
                    term_map[t].append(idx)

            results = []
            for idx, doc in enumerate(corpus):
                # Filter tenant
                if doc.get("tenant_id") != target_tenant:
                    continue
                
                doc_terms = set(normalize_text(doc["text"]))
                matched_query_terms = [q for q in normalized_queries if q in doc_terms]
                
                distinct_matches = len(set(matched_query_terms))
                
                if distinct_matches >= min_distinct and distinct_matches > 0:
                    # Total occurrences of matched terms
                    total_occurrences = 0
                    doc_text_terms = normalize_text(doc["text"])
                    for dt in doc_text_terms:
                        if dt in normalized_queries:
                            total_occurrences += 1
                    
                    results.append({
                        "doc_id": doc["id"],
                        "distinct_matches": distinct_matches,
                        "total_occurrences": total_occurrences
                    })

            # Ranking: 1. distinct_matches DESC, 2. total_occurrences DESC, 3. doc_id ASC
            # Python sort is stable. To do multi-key:
            # We want descending for 1 and 2, ascending for 3.
            # We can use a key that returns a tuple.
            # For descending, we can negate numbers if they are ints.
            results.sort(key=lambda x: (-x["distinct_matches"], -x["total_occurrences"], str(x["doc_id"])))

            # Prepare snippets (just the doc_id and a small slice of text for this lexical engine)
            final_output = []
            for r in results:
                # Find the doc in corpus to get text
                doc_obj = next(d for d in corpus if d["id"] == r["doc_id"])
                final_output.append({
                    "id": r["doc_id"],
                    "score_distinct": r["distinct_matches"],
                    "score_total": r["total_occurrences"],
                    "snippet": doc_obj["text"][:50] + "..." if len(doc_obj["text"]) > 50 else doc_obj["text"]
                })

            print(json.dumps({
                "status": "success",
                "data": {
                    "results": final_output,
                    "count": len(final_output)
                }
            }))

        else:
            print(json.dumps({"status": "refused", "code": "INVALID_MODE", "message": f"Unknown mode: {mode}"}))

    except ValueError as ve:
        # Catch duplicate keys or non-finite numbers
        print(json.dumps({"status": "refused", "code": "PARSE_ERROR", "message": str(ve)}))
    except Exception as e:
        print(json.dumps({"status": "refused", "code": "INTERNAL_ERROR", "message": str(e)}))

if __name__ == "__main__":
    run_tool()
