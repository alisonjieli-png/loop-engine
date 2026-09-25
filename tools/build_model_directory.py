"""Build the public model and endpoint directory from its sources, restartably.

Kind: development command. It reads the public sources named in `tools/model_directory/SOURCES.md`
through a cached, bounded, read-only reader, assembles one row per model and per endpoint, refuses
every row that does not keep its sources, and writes the packaged files under
`src/loop_engine/core/service_runtime/web_assets/model-directory/`.

Use:

    PYTHONPATH=src:tools python tools/build_model_directory.py --state ~/.cache/baltor-model-directory

A run that stops, for a crash or a reached request ceiling, continues where it stopped: every answer
is kept in the state folder with the moment it was read, and an answer younger than its maximum age
is reused. `--offline` builds from the state folder alone. The command exits 1 when it refused any
row, so a scheduled refresh that would publish an unsourced row fails instead.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from loop_engine.core.service_runtime import model_directory as records
from loop_engine.core.service_runtime import model_directory_fit as fit
from model_directory import encode, sources
from model_directory.endpoints import assemble_endpoints, harness_records
from model_directory.fetch import CachedReader
from model_directory.models import assemble_models
from model_directory.rows import slug_of, unique_slugs

ROOT = Path(__file__).resolve().parents[1]
REVIEWED = ROOT / "tools" / "model_directory"
OUTPUT = ROOT / "src" / "loop_engine" / "core" / "service_runtime" / "web_assets" / records.DATA_FOLDER


def packaged_hardware(reviewed: dict) -> dict:
    """The reviewed hardware presets as the packaged record, refusing a preset without its numbers."""
    names = sorted(reviewed["sources"])
    index = {name: position for position, name in enumerate(names)}
    presets = []
    for preset in reviewed["presets"]:
        if preset["kind"] not in fit.DEVICE_KINDS or not preset["memory_gib"] > 0:
            raise records.ModelDirectoryError(f"hardware preset {preset['id']} has no kind or memory")
        bandwidth = preset.get("bandwidth_gbps")
        if bandwidth is not None and not bandwidth > 0:
            raise records.ModelDirectoryError(f"hardware preset {preset['id']} has a bandwidth that is not positive")
        if preset.get("source") and preset["source"] not in index:
            raise records.ModelDirectoryError(f"hardware preset {preset['id']} names an unknown source")
        if not preset.get("source") and not preset.get("bandwidth_basis"):
            raise records.ModelDirectoryError(f"hardware preset {preset['id']} names no source and no basis")
        presets.append({**preset, "source": index.get(preset.get("source"), -1),
                        "usable_fraction": fit.default_usable_fraction(preset["kind"], preset["memory_gib"])})
    return {"record_type": records.HARDWARE_RECORD_TYPE, "reviewed_on": reviewed["reviewed_on"],
            "sources": [{"id": name, "address": reviewed["sources"][name][0], "read": reviewed["sources"][name][1]} for name in names],
            "presets": presets, "system_memory_default": reviewed["system_memory_default"],
            "formula": {"kv_bytes_per_value": fit.KV_BYTES_PER_VALUE, "overhead_fixed_bytes": fit.OVERHEAD_FIXED_BYTES,
                        "overhead_weight_fraction": fit.OVERHEAD_WEIGHT_FRACTION, "speed_low_fraction": fit.SPEED_LOW_FRACTION,
                        "speed_high_fraction": fit.SPEED_HIGH_FRACTION, "context_steps": list(fit.CONTEXT_STEPS),
                        "cpu_usable_fraction": fit.CPU_USABLE_FRACTION}}


def _primary(row: dict) -> str:
    ids = row["ids"]
    return ids.get("huggingface") or (ids.get("openrouter") or "").split(":", 1)[0] or ids.get("modelsdev") or row["name"]


def finish_models(pairs: list, baltor: list, report: dict, documentation: dict) -> list:
    """Give each row its slug and sources, add Baltor's own output records, and refuse unsourced rows."""
    slugs = unique_slugs([_primary(row) for row, _ in pairs])
    reviewed = {slug_of(entry["modelsdev"]): entry["slug"] for entry in documentation.get("hosted") or () if entry.get("modelsdev")}
    finished = []
    for row, sources_of in pairs:
        row["slug"] = slugs[_primary(row)]
        for price in row["prices"]:
            if price["route"] == records.ROUTE_DIRECT:
                price["provider_slug"] = reviewed.get(price["provider_slug"], price["provider_slug"])
        for item in baltor:
            model_id = item["provider"] + "/" + item["model"]
            if model_id in (row["ids"].get("openrouter"), row["ids"].get("modelsdev")):
                source = sources_of.add("baltor_records", "github.com/alisonjieli-png/loop-engine/blob/main/" + item["path"], item["observed_at"])
                row["facts"].setdefault("max_output", []).append({"value": item["maximum_output_tokens"], "source": source,
                                                                  "basis": "Baltor's provider client declares this limit: " + item["basis"]})
        row["sources"] = sources_of.items
        try:
            finished.append(records.validate_model_row(row))
        except records.ModelDirectoryError as error:
            report["refused"].append({"row": row.get("slug") or _primary(row), "reason": str(error)[:300]})
    return finished


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--state", type=Path, required=True, help="the folder that keeps every answer between runs")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--offline", action="store_true", help="build from the state folder only")
    parser.add_argument("--max-requests", type=int, default=6000)
    parser.add_argument("--gguf-limit", type=int, default=1400, help="how many open models, most downloaded first, get file lookups")
    arguments = parser.parse_args(argv)
    built_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    today = built_at[:10]
    documentation = sources.read_reviewed(REVIEWED / "provider_documentation.json")
    hardware = packaged_hardware(sources.read_reviewed(REVIEWED / "hardware.json"))
    reader = CachedReader(arguments.state, maximum_requests=arguments.max_requests, offline=arguments.offline)
    progress = lambda message: print(message, file=sys.stderr, flush=True)
    pairs, report, answers = assemble_models(reader, documentation, ROOT, today, arguments.gguf_limit, progress)
    if not answers["openrouter"].usable or not answers["modelsdev"].usable:
        progress("a required source gave no answer and has no kept copy; nothing was written")
        return 2
    baltor = sources.baltor_output_records(ROOT)
    models = finish_models(pairs, baltor, report, documentation)
    endpoints = []
    for row in assemble_endpoints(documentation, answers["modelsdev"], models, baltor):
        try:
            endpoints.append(records.validate_endpoint_row(row))
        except records.ModelDirectoryError as error:
            report["refused"].append({"row": row.get("slug"), "reason": str(error)[:300]})
    harnesses = harness_records(documentation)
    source_days: dict = {}
    for row in models + endpoints:
        for item in row["sources"]:
            source_days.setdefault(item["id"], set()).add(item["read"])
    sources_state = [{**record, "rows": sum(1 for row in models + endpoints if any(item["id"] == record["id"] for item in row["sources"])),
                      "oldest_read": min(source_days.get(record["id"], {""})), "newest_read": max(source_days.get(record["id"], {""}))}
                     for record in encode.SOURCE_RECORDS]
    report["reader"] = reader.summary()
    manifest = encode.write_directory(arguments.output, models, endpoints, harnesses, hardware, sources_state, built_at, report)
    print(json.dumps({"counts": manifest["counts"], "model_rows_by_source": manifest["model_rows_by_source"],
                      "files": {name: item["bytes"] for name, item in manifest["files"].items()},
                      "refused": len(report["refused"]), "reader": report["reader"]}, indent=1))
    return 1 if report["refused"] else 0


if __name__ == "__main__":
    sys.exit(main())
