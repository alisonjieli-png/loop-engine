"""Write the packaged directory files: full rows for the service, compact indexes for the browser.

Kind: development tool module. Each file is written whole to a temporary name and then moved into
place, so a reader never sees half a file. The full rows are written one row per line, so a daily
refresh changes only the lines of rows that changed. The two browser indexes hold only the fields
their pages filter, sort and fit on, as arrays under a named field list, so thousands of rows stay
small enough to load on a phone.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from loop_engine.core.service_runtime import commercial_relationship as commercial
from loop_engine.core.service_runtime import model_directory as records
from loop_engine.core.service_runtime import model_directory_fit as fit
from loop_engine.core.service_runtime import model_directory_format as fmt

#: What each source is, where its terms are, and how the build uses it. The pages show this list.
SOURCE_RECORDS = (
    {"id": "openrouter", "name": "OpenRouter Models API", "address": "openrouter.ai/api/v1/models",
     "terms_address": "openrouter.ai/docs/guides/overview/models",
     "use": "Context length, output limit, supported parameters and benchmark indexes of hosted models. OpenRouter's documentation says its Models API makes this information freely available; the build reads only that documented interface."},
    {"id": "openrouter_endpoints", "name": "OpenRouter model endpoints API", "address": "openrouter.ai/api/v1/models",
     "terms_address": "openrouter.ai/docs/guides/overview/models",
     "use": "The providers that serve each model through OpenRouter, with the prices OpenRouter lists for each route."},
    {"id": "huggingface", "name": "Hugging Face Hub API", "address": "huggingface.co/api/models",
     "terms_address": "huggingface.co/terms-of-service",
     "use": "Licence, parameter count, publication date, downloads and task of open models, read within the API's published request limit."},
    {"id": "huggingface_config", "name": "Hugging Face model configurations", "address": "huggingface.co",
     "terms_address": "huggingface.co/terms-of-service",
     "use": "Layers, key and value heads, head size and context length, the numbers the memory formula needs."},
    {"id": "huggingface_gguf", "name": "Hugging Face GGUF file lists", "address": "huggingface.co",
     "terms_address": "huggingface.co/terms-of-service",
     "use": "The quantized files of a model and their sizes, from the GGUF copy its maker or the most downloaded copier publishes."},
    {"id": "modelsdev", "name": "models.dev", "address": "models.dev/api.json", "terms_address": "github.com/sst/models.dev/blob/dev/LICENSE",
     "use": "Direct provider prices, limits and capabilities, from a public database under the MIT licence."},
    {"id": "baltor_records", "name": "Baltor provider client records", "address": "github.com/alisonjieli-png/loop-engine",
     "terms_address": "github.com/alisonjieli-png/loop-engine",
     "use": "Output limits that Baltor's own provider clients declare or observed, each with its day."},
    {"id": "provider_documentation", "name": "Provider and runtime documentation", "address": "github.com/alisonjieli-png/loop-engine/blob/main/tools/model_directory/provider_documentation.json",
     "terms_address": "github.com/alisonjieli-png/loop-engine/blob/main/tools/model_directory/SOURCES.md",
     "use": "API styles, authentication, rate-limit, pricing and data-policy pages, read by a person on the day each fact names."},
    {"id": "harness_documentation", "name": "Harness documentation", "address": "github.com/alisonjieli-png/loop-engine/blob/main/tools/model_directory/provider_documentation.json",
     "terms_address": "github.com/alisonjieli-png/loop-engine/blob/main/tools/model_directory/SOURCES.md",
     "use": "How OpenCode, Pi, Codex and Claude Code read a model provider, from each harness's own documentation."},
)
#: The Ollama library is linked, never read: its terms refuse automated access without permission.
LINKED_ONLY = ({"name": "Ollama library", "address": "ollama.com/library", "terms_address": "ollama.com/terms",
                "use": "Linked only. Ollama's terms refuse automated access without permission, so no data is copied from it."},)
SEARCH_FIELDS = ("slug", "name", "maker", "kind", "parameters", "context", "licence", "released", "input_price", "uses", "tools",
                 "downloads", "providers")
FIT_FIELDS = ("slug", "name", "maker", "parameters", "active_parameters", "layers", "kv_heads", "head_dim", "attention",
              "latent_width", "max_context", "quantizations", "estimated", "uses", "licence")
ATTENTION_CODES = {fit.ATTENTION_FULL: "f", fit.ATTENTION_LATENT: "l", fit.ATTENTION_UNKNOWN: "u"}


def use_bits(row: dict) -> int:
    return sum(1 << records.USE_CASES.index(item["value"]) for item in row["use_cases"])


def max_fact(row: dict, name: str) -> "int | None":
    values = [item.get("value") for item in row["facts"].get(name) or () if isinstance(item.get("value"), int)]
    return max(values) if values else None


def tool_code(row: dict) -> "int | None":
    values = [item.get("value") for item in row["facts"].get("tool_calling") or () if isinstance(item.get("value"), bool)]
    return None if not values else 1 if any(values) else 0


def kind_code(row: dict) -> str:
    open_weights = "huggingface" in row["ids"] or (row["facts"].get("open_weights") or {}).get("value") is True
    return "b" if open_weights and row["prices"] else "o" if open_weights else "h"


def search_row(row: dict) -> list:
    cheapest = fmt.cheapest_input(row)
    prices = [cheapest["input"]] if cheapest else []
    popularity = row.get("popularity") or {}
    return [row["slug"], row["name"], row["maker"], kind_code(row), (row["facts"].get("parameters") or {}).get("value"),
            max_fact(row, "context"), (row["facts"].get("licence") or {}).get("value") or "",
            (row["facts"].get("released") or {}).get("value") or "", min(prices) if prices else None, use_bits(row),
            tool_code(row), popularity.get("downloads"), len({price["provider_slug"] for price in row["prices"]})]


def fit_row(row: dict) -> "list | None":
    """The numbers the can-I-run page needs for one model, or None when it cannot say anything useful."""
    facts = row["facts"]
    outputs = (facts.get("modalities") or {}).get("output") or []
    if outputs and "text" not in outputs:
        return None
    parameters = (facts.get("parameters") or {}).get("value")
    architecture = facts.get("architecture") or {}
    weights = fit.compared_weights({item["name"]: item["bytes"] for item in row["quantizations"]}, parameters)
    if not weights:
        return None
    quantizations = [[name, size] for name, size, _estimated in weights]
    estimated = int(any(flag for _name, _size, flag in weights))
    return [row["slug"], row["name"], row["maker"], parameters, (facts.get("active_parameters") or {}).get("value"),
            architecture.get("layers") or 0, architecture.get("kv_heads") or 0, architecture.get("head_dim") or 0,
            ATTENTION_CODES.get(architecture.get("attention") or fit.ATTENTION_UNKNOWN, "u"), architecture.get("latent_width") or 0,
            architecture.get("max_context") or max_fact(row, "context") or 0, quantizations, estimated, use_bits(row),
            (facts.get("licence") or {}).get("value") or ""]


def _write(path: Path, text: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(text, encoding="utf-8")
    partial.replace(path)
    body = text.encode("utf-8")
    return {"bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}


def _lines(record_type: str, key: str, rows: list, extra: "dict | None" = None) -> str:
    head = json.dumps({"record_type": record_type, **(extra or {})}, sort_keys=True)[:-1]
    body = ",\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows)
    return head + ', "' + key + '": [\n' + body + "\n]}\n"


def write_directory(folder: Path, models: list, endpoints: list, harnesses: list, hardware: dict, sources_state: list,
                    built_at: str, report: dict) -> dict:
    """Write every packaged file and return the manifest, which is written last."""
    files = {}
    ordered = sorted(models, key=lambda row: row["slug"])
    files["models.json"] = _write(folder / "models.json", _lines(records.MODELS_RECORD_TYPE, "models", ordered))
    files["endpoints.json"] = _write(folder / "endpoints.json", _lines(records.ENDPOINTS_RECORD_TYPE, "endpoints", endpoints,
                                                                         {"harnesses": harnesses}))
    files["hardware.json"] = _write(folder / "hardware.json", json.dumps(hardware, indent=1, sort_keys=True) + "\n")
    search = [search_row(row) for row in ordered]
    files["search-index.json"] = _write(folder / "search-index.json", json.dumps(
        {"record_type": records.SEARCH_INDEX_RECORD_TYPE, "fields": list(SEARCH_FIELDS), "uses": list(records.USE_CASES),
         "rows": search}, separators=(",", ":")) + "\n")
    fits = [item for item in (fit_row(row) for row in ordered) if item is not None]
    files["fit-index.json"] = _write(folder / "fit-index.json", json.dumps(
        {"record_type": records.FIT_INDEX_RECORD_TYPE, "fields": list(FIT_FIELDS), "uses": list(records.USE_CASES),
         "rows": fits}, separators=(",", ":")) + "\n")
    counts = {"models": len(ordered), "endpoints": sum(1 for row in endpoints if row["kind"] == records.ENDPOINT_HOSTED),
              "runtimes": sum(1 for row in endpoints if row["kind"] == records.ENDPOINT_LOCAL),
              "fit_rows": len(fits), "search_rows": len(search)}
    by_source: dict = {}
    for row in ordered:
        for source_id in {item["id"] for item in row["sources"]}:
            by_source[source_id] = by_source.get(source_id, 0) + 1
    manifest = {"record_type": records.MANIFEST_RECORD_TYPE, "built_at": built_at,
                "commercial_relationship_schema": commercial.SCHEMA, "files": files, "counts": counts,
                "model_rows_by_source": dict(sorted(by_source.items())), "sources": sources_state,
                "linked_only": list(LINKED_ONLY), "report": report}
    _write(folder / "manifest.json", json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    return manifest
