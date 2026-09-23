"""Count signs that a step used its material, from the model's own responses.

    python runner/use_signals.py --bodies /path/to/run-folder/bodies

Loaded and used are separate facts. The proxy already proves that the item
text was loaded into every request of a material arm. This script looks for
words that only the items introduce, such as their reason names and
confidence values, in what the model itself wrote: its text and the
arguments of its tool calls. The same words are counted in the arms without
material as a baseline. A match is a sign of use, not proof of use, and it
says nothing about whether the use helped.

Writes `results/use-signals.json`. Only the Python standard library is used.
Derived from the same script of the data cleanup study, with terms for the
names and websites items added.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
TERMS = {
    "phones": ("digit_count_unexpected", "digit count", "national length", "national_length",
               "0.93", "0.35", "confidence"),
    "emails": ("unrecoverable_shape", "ambiguous_address", "symbol_word", "0.85", "0.92",
               "confidence"),
    "addresses": ("house_number_not_found", "city_or_region_ambiguous", "country_from_position",
                  "empty_address", "remainder"),
    "duplicates": ("blocking", "weakest", "0.92", "0.75", "sequencematcher", "difflib",
                   "initials"),
    "names": ("surname exception", "preserved token", "case information", "internal capital",
              "particle", "0.92", "0.97"),
    "websites": ("invalid_host", "whitespace_inside_url", "trailing_slash_removed",
                 "scheme_added", "0.95"),
}


def model_text(response_path):
    """Everything the model wrote in one streamed response."""
    parts = []
    for line in response_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("data:") or line.endswith("[DONE]"):
            continue
        try:
            payload = json.loads(line[5:])
        except json.JSONDecodeError:
            continue
        for choice in payload.get("choices") or []:
            delta = choice.get("delta") or choice.get("message") or {}
            parts.append(delta.get("content") or "")
            for call in delta.get("tool_calls") or []:
                parts.append((call.get("function") or {}).get("arguments") or "")
    return "".join(parts).lower()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bodies", required=True)
    args = parser.parse_args(argv)
    records = [json.loads(path.read_text(encoding="utf-8"))
               for path in sorted((STUDY / "trials" / "records").glob("*.json"))]
    cells = {}
    for record in records:
        if not record["counts_in_results"]:
            continue
        folder = Path(args.bodies) / record["trial_id"]
        text = "".join(model_text(path) for path in sorted(folder.glob("*-response.txt")))
        found = sorted(term for term in TERMS[record["family"]] if term in text)
        cell = cells.setdefault(f"{record['family']}|{record['arm']}",
                                {"steps": 0, "steps_with_any_term": 0, "terms_seen": {}})
        cell["steps"] += 1
        cell["steps_with_any_term"] += bool(found)
        for term in found:
            cell["terms_seen"][term] = cell["terms_seen"].get(term, 0) + 1
    result = {"record_type": "overnight_use_signals/v1", "terms": TERMS,
              "cells": dict(sorted(cells.items()))}
    out = STUDY / "results" / "use-signals.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    for key, cell in result["cells"].items():
        print(key, cell["steps_with_any_term"], "of", cell["steps"], cell["terms_seen"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
