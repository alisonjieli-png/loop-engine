"""Measure the step function rules on a reviewed catalogue folder, and draw a fixed sample for hand judgement.

The rules engine (``library_step_function_tagging``, engine ``step_function_rules``) tags an item with the kinds
of step it supports. No served release carries the tags yet, so this tool measures the rules directly on the
approved packages of one reviewed folder: it builds the same ``StepFunctionMaterial`` the reviewed catalogue
writer builds (``tools/write_reviewed_catalogue.py``, ``item_attributes``), tags every approved item, and writes

- ``distribution.json``: tags per item, items with no tag, the top words that drove each function;
- ``tags.jsonl``: one line per approved item with its tags, scores and evidence;
- ``sample-<n>.json``: a deterministic random sample of tagged items (``--seed``), with each item's headline,
  scores, evidence and the head of its entry text, so a person can judge every tag;
- ``sample-reading.txt``: the same sample laid out for reading, with a short quote around each evidence word.

Package bodies are read from the reviewed folder and never copied into this repository. The titles come from
the review export the folder was written from (``--export``), because the writer names each item by its export
title; without an export the identity stands in, as the writer does.

    PYTHONPATH=src:tools python tools/measure_step_function_tags.py \\
        --reviewed /home/username/baltor-library/reviewed-2026-09-26-10/imported \\
        --export /home/username/baltor-library/review-batches/2026-09-26-10 \\
        --output $HOME/.le-ci-tmp/tag-precision --sample 100 --seed 20260926
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
import re
import sys

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parent
for entry in (str(HERE), str(REPOSITORY / "src"), str(REPOSITORY)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from candidate_review.native import TEXT_MEDIA  # noqa: E402
from loop_engine.core.library_ingestion.step_functions import (  # noqa: E402
    STEP_FUNCTIONS, RulesStepFunctionTagger, StepFunctionMaterial, entry_text)
from loop_engine.core.service_runtime.catalogue_attributes import harness_kind_of  # noqa: E402

RECORD_TYPE = "step_function_tag_measurement/v1"
HEAD_CHARS = 1400
QUOTE_CHARS = 70


def read_titles(export: Path | None) -> dict:
    titles = {}
    if export is None:
        return titles
    for path in sorted(export.glob("specifications-[0-9][0-9][0-9].json")):
        for spec in json.loads(path.read_text(encoding="utf-8")).get("specifications", []):
            titles[spec["id"]] = str(spec.get("title") or "")
    return titles


def approved_identities(reviewed: Path) -> set:
    reviews = json.loads((reviewed / "reviews.json").read_text(encoding="utf-8"))
    return {row["identity"] for row in reviews["rows"] if row["outcome"] == "approved"}


def package_rows(reviewed: Path, item: dict) -> list:
    """(path, role, media type, text or None) for each package file, read from the reviewed folder."""
    rows = []
    for entry in item["package_files"]:
        source = reviewed / entry["source"]
        text = None
        if entry["media_type"] in TEXT_MEDIA:
            try:
                text = source.read_bytes().decode("utf-8")
            except UnicodeError:
                text = None
        rows.append((entry["path"], entry["role"], entry["media_type"], text))
    return rows


def material_for(item: dict, rows: list, title: str) -> StepFunctionMaterial:
    reference = item["reference"]
    roles = tuple(role for _path, role, _media, _text in rows)
    declared = str(item.get("provenance", {}).get("harness_kind") or "")
    kind = harness_kind_of(reference["kind"], tuple(reference.get("styles") or ()), roles, declared)
    return StepFunctionMaterial(reference["kind"], kind, title or reference["identity"], reference["purpose"],
                                entry_text(rows), roles)


def quote(text: str, word: str) -> str:
    match = re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text.lower())
    if match is None:
        return ""
    start, end = max(0, match.start() - QUOTE_CHARS), min(len(text), match.end() + QUOTE_CHARS)
    return " ".join(text[start:end].split())


def measure(reviewed: Path, export: Path | None, output: Path, sample_size: int, seed: int,
            identities=None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    tagger = RulesStepFunctionTagger()
    titles = read_titles(export)
    items = json.loads((reviewed / "items.json").read_text(encoding="utf-8"))["items"]
    approved = approved_identities(reviewed)
    per_function, drivers, tag_counts, untagged, kinds_untagged = Counter(), defaultdict(Counter), Counter(), [], Counter()
    lines, tagged, materials = [], {}, {}
    for item in sorted(items, key=lambda row: row["reference"]["identity"]):
        identity = item["reference"]["identity"]
        if identity not in approved:
            continue
        rows = package_rows(reviewed, item)
        material = material_for(item, rows, titles.get(identity, ""))
        tags = tagger.tag(material)
        scores = tagger.scores(material)
        line = {"identity": identity, "harness_kind": material.harness_kind, "kind": material.kind,
                "title": material.name, "functions": list(tags.functions),
                "scores": {function: score for function, (score, _evidence) in scores.items() if score},
                "evidence": [{"function": function, "basis": basis} for function, basis in tags.evidence]}
        lines.append(line)
        tag_counts[len(tags.functions)] += 1
        for function in tags.functions:
            per_function[function] += 1
        for function, basis in tags.evidence:
            drivers[function][basis] += 1
        materials[identity] = (item, material, tags, scores)
        if tags.functions:
            tagged[identity] = (item, material, tags, scores)
        else:
            untagged.append(identity)
            kinds_untagged[material.harness_kind] += 1
    with (output / "tags.jsonl").open("w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(json.dumps(line, sort_keys=True) + "\n")
    distribution = {
        "record_type": RECORD_TYPE, "reviewed_folder": str(reviewed), "export_folder": str(export or ""),
        "engine": {"engine_id": tagger.engine_id, "engine_version": tagger.engine_version},
        "approved_items": len(lines), "tagged_items": len(tagged), "untagged_items": len(untagged),
        "tags_per_item": {str(count): number for count, number in sorted(tag_counts.items())},
        "items_per_function": {function: per_function.get(function, 0) for function in STEP_FUNCTIONS},
        "untagged_by_harness_kind": dict(sorted(kinds_untagged.items())),
        "top_words_per_function": {function: [{"basis": basis, "items": number}
                                              for basis, number in drivers[function].most_common(15)]
                                   for function in STEP_FUNCTIONS},
        "untagged_identities": untagged,
    }
    (output / "distribution.json").write_text(json.dumps(distribution, indent=1, sort_keys=True) + "\n",
                                              encoding="utf-8")
    if identities is not None:
        # Re-measure an earlier sample: tag exactly those items, in that order, whatever they score now.
        chosen = [identity for identity in identities if identity in materials]
        missing = sorted(set(identities) - set(chosen))
        if missing:
            raise SystemExit(f"identities absent from the approved items: {missing[:5]}")
    else:
        chosen = random.Random(seed).sample(sorted(tagged), min(sample_size, len(tagged)))
    sample, reading = [], []
    for identity in chosen:
        item, material, tags, scores = materials[identity]
        text = material.text
        evidence = [{"function": function, "basis": basis,
                     "quote": quote(text if basis.startswith("text: ") else material.name + " " + material.purpose,
                                    basis.split(": ", 1)[1]) if ": " in basis and not basis.startswith(("file role", "harness kind")) else ""}
                    for function, basis in tags.evidence]
        sample.append({"identity": identity, "title": material.name, "harness_kind": material.harness_kind,
                       "kind": material.kind, "purpose": material.purpose, "file_roles": list(material.file_roles),
                       "functions": list(tags.functions),
                       "scores": {function: score for function, (score, _evidence) in scores.items() if score},
                       "evidence": evidence, "entry_text_head": text[:HEAD_CHARS], "entry_text_chars": len(text)})
        reading.append("=" * 100)
        reading.append(f"[{len(sample)}] {identity}  ({material.harness_kind}; roles {sorted(set(material.file_roles))})")
        reading.append(f"TITLE: {material.name}")
        reading.append(f"PURPOSE: {material.purpose}")
        reading.append(f"TAGS: {list(tags.functions)}   SCORES: {sample[-1]['scores']}")
        for row in evidence:
            reading.append(f"  - {row['function']} <- {row['basis']}" + (f"  | ...{row['quote']}..." if row["quote"] else ""))
        reading.append(f"TEXT ({len(text)} chars, head):")
        reading.append(text[:HEAD_CHARS])
    (output / f"sample-{len(chosen)}.json").write_text(
        json.dumps({"record_type": "step_function_tag_sample/v1", "seed": seed, "size": len(chosen),
                    "engine": distribution["engine"], "items": sample}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")
    (output / "sample-reading.txt").write_text("\n".join(reading) + "\n", encoding="utf-8")
    return distribution


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reviewed", required=True, type=Path, help="A reviewed catalogue folder (items.json, reviews.json, packages/).")
    parser.add_argument("--export", type=Path, default=None, help="The review export the folder was written from, for titles.")
    parser.add_argument("--output", required=True, type=Path, help="Where the distribution, tags and sample are written.")
    parser.add_argument("--sample", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260926)
    parser.add_argument("--identities", type=Path, default=None,
                        help="Re-measure these identities (one per line, an earlier sample) instead of drawing a sample.")
    options = parser.parse_args(argv)
    identities = None
    if options.identities is not None:
        identities = [line.strip() for line in options.identities.read_text(encoding="utf-8").splitlines() if line.strip()]
    distribution = measure(options.reviewed.resolve(), options.export.resolve() if options.export else None,
                           options.output.resolve(), options.sample, options.seed, identities)
    summary = {key: distribution[key] for key in ("approved_items", "tagged_items", "untagged_items", "tags_per_item",
                                                  "items_per_function")}
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
