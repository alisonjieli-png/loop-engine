"""Source engines of the directory build: each reads one public source into plain records.

Kind: development tool module. A reader returns what one source says and the Answer that carries
the day it was read; it decides nothing about which model a record belongs to. The assembly step
in `assemble.py` joins records only on exact identifiers.

Terms, as read on September 24, 2026 and recorded in SOURCES.md:

- OpenRouter documents its Models API as making model information "freely available" and designed
  for integration; the build reads only that documented interface, never the website pages.
- The Hugging Face Hub API is documented for programmatic use and its terms do not restrict it; the
  build stays under the anonymous limit the API announces.
- models.dev publishes api.json from a repository under the MIT licence.
- Ollama's terms refuse automated access without permission, so no reader here touches it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .fetch import Answer, CachedReader

HF_HOST, OPENROUTER_HOST, MODELSDEV_HOST = "huggingface.co", "openrouter.ai", "models.dev"
#: The Hugging Face lists the directory reads, each by a documented sort order. The union of the lists,
#: without quantized copies and adapters, is the set of open models.
HF_LISTS = (("text-generation", "downloads", 1000), ("text-generation", "likes", 1000),
            ("text-generation", "trendingScore", 500), ("image-text-to-text", "downloads", 400),
            ("image-text-to-text", "likes", 200), ("feature-extraction", "downloads", 250),
            ("sentence-similarity", "downloads", 250), ("text-ranking", "downloads", 120))
HF_EXPAND = ("safetensors", "cardData", "downloads", "likes", "gated", "createdAt", "lastModified",
             "pipeline_tag", "tags", "library_name", "baseModels", "author", "sha", "config")
#: Repository kinds that are a copy of another model in another format. Their files become the
#: quantizations of the model they copy, not rows of their own.
COPY_TAGS = frozenset({"gguf", "mlx", "awq", "gptq", "exl2", "exl3", "4-bit", "8-bit", "bitsandbytes", "onnx"})
COPY_RELATIONS = frozenset({"quantized", "adapter"})


def _expand() -> list:
    return [("expand[]", name) for name in HF_EXPAND]


def openrouter_models(reader: CachedReader) -> Answer:
    return reader.get_json(OPENROUTER_HOST, "/api/v1/models")


def openrouter_endpoints(reader: CachedReader, details_path: str) -> Answer:
    """The providers that serve one OpenRouter model, with their prices on OpenRouter."""
    return reader.get_json(OPENROUTER_HOST, details_path)


def modelsdev(reader: CachedReader) -> Answer:
    return reader.get_json(MODELSDEV_HOST, "/api.json")


def hf_list(reader: CachedReader, pipeline_tag: str, sort: str, limit: int) -> Answer:
    query = [("pipeline_tag", pipeline_tag), ("sort", sort), ("direction", "-1"), ("limit", str(limit)), *_expand()]
    return reader.get_json(HF_HOST, "/api/models", query)


def hf_model(reader: CachedReader, repository: str) -> Answer:
    return reader.get_json(HF_HOST, "/api/models/" + repository, _expand(), maximum_age_hours=72)


def hf_config(reader: CachedReader, repository: str) -> Answer:
    """The configuration file of one repository; a gated repository answers without it."""
    return reader.get_json(HF_HOST, "/" + repository + "/raw/main/config.json", maximum_age_hours=24 * 14)


def hf_quantized(reader: CachedReader, repository: str, library: str) -> Answer:
    """Repositories that declare themselves quantized copies of one model, in one file format."""
    query = [("filter", "base_model:quantized:" + repository), ("filter", library), ("sort", "downloads"),
             ("direction", "-1"), ("limit", "8"), ("expand[]", "downloads"), ("expand[]", "author"),
             ("expand[]", "gated")]
    return reader.get_json(HF_HOST, "/api/models", query, maximum_age_hours=24 * 7)


def hf_tree(reader: CachedReader, repository: str) -> Answer:
    return reader.get_json(HF_HOST, "/api/models/" + repository + "/tree/main", [("recursive", "true")],
                           maximum_age_hours=24 * 7)


def is_copy(record: dict) -> bool:
    """True for a quantized copy, an adapter or a repository in a copy format."""
    relation = (record.get("baseModels") or {}).get("relation")
    tags = {str(tag).lower() for tag in record.get("tags") or ()}
    library = str(record.get("library_name") or "").lower()
    return relation in COPY_RELATIONS or bool(tags & COPY_TAGS) or library in COPY_TAGS


_QUANT = re.compile(r"(?<![A-Za-z0-9])((?:UD-)?(?:IQ[1-4]_(?:XXS|XS|NL|S|M)|Q[2-8]_K(?:_(?:XL|S|M|L))?|Q[4-8]_[01]|"
                    r"TQ[12]_0|MXFP4(?:_MOE)?|BF16|F16|F32))(?![A-Za-z0-9])", re.IGNORECASE)


#: Bits per weight a whole quantized model can have, by the leading part of its name. Wide on purpose: mixed-precision
#: quantizations keep some tensors larger. A group outside its range belongs to another model or lacks files.
_BITS_RANGE = (("IQ1", 1.3, 2.7), ("TQ1", 1.3, 2.7), ("TQ2", 1.8, 3.2), ("IQ2", 1.9, 3.9), ("Q2", 1.9, 3.9), ("IQ3", 2.9, 4.9),
               ("Q3", 2.9, 4.9), ("IQ4", 3.9, 6.0), ("Q4", 3.9, 6.0), ("MXFP4", 3.9, 6.0), ("Q5", 4.9, 6.9), ("Q6", 5.9, 7.7),
               ("Q8", 7.5, 9.9), ("BF16", 14.0, 18.0), ("F16", 14.0, 18.0), ("F32", 30.0, 34.0))
_PART = re.compile(r"-(\d{5})-of-(\d{5})\.gguf$", re.IGNORECASE)


def plausible_bits(name: str, size: int, parameters) -> bool:
    """True when the size fits the quantization's bits per weight, or when the parameter count is unknown."""
    if not isinstance(parameters, int) or parameters <= 0:
        return True
    bits = size * 8 / parameters
    plain = name.upper().removeprefix("UD-")
    return next(((low <= bits <= high) for prefix, low, high in _BITS_RANGE if plain.startswith(prefix)), False)


def gguf_quantizations(tree: list, parameters=None) -> dict:
    """The complete GGUF quantizations of a repository: name -> (total bytes, file paths).

    Split files of one quantization are summed, and a split quantization counts only when every part is
    listed, because a long listing can stop part way. A group whose size does not fit its bits per weight
    for the model's parameter count is left out. Vision projector files are loaded beside the weights, so
    they are left out too.
    """
    grouped: dict = {}
    parts: dict = {}
    for item in tree or ():
        path = str(item.get("path") or "")
        if item.get("type") != "file" or not path.lower().endswith(".gguf") or "mmproj" in path.lower():
            continue
        found = _QUANT.findall(path.replace("/", "-"))
        if not found:
            continue
        name = found[-1].upper()
        size = (item.get("lfs") or {}).get("size") or item.get("size")
        if not isinstance(size, int) or size <= 0:
            continue
        total, files = grouped.get(name, (0, []))
        grouped[name] = (total + size, files + [path])
        part = _PART.search(path)
        if part:
            parts.setdefault(name, {"count": int(part.group(2)), "seen": set()})["seen"].add(int(part.group(1)))
    complete = {}
    for name, (size, files) in grouped.items():
        split = parts.get(name)
        if split and (split["seen"] != set(range(1, split["count"] + 1)) or len(files) != split["count"]):
            continue
        if plausible_bits(name, size, parameters):
            complete[name] = (size, files)
    return complete


def baltor_output_records(root: Path) -> list:
    """The source-backed output limits that Baltor's provider clients declare, with their dates.

    These are the records that `src/loop_engine` keeps for Ollama Cloud, the OpenAI Responses route
    and Mistral. Each carries the source the client names and the day it was observed or declared.
    """
    import importlib
    rows = []
    for module_name, provider, path in (("loop_engine.core.ollama_client", "ollama-cloud", "src/loop_engine/core/ollama_client.py"),
                                        ("loop_engine.core.openai_responses_client", "openai", "src/loop_engine/core/openai_responses_client.py"),
                                        ("loop_engine.core.mistral_client", "mistral", "src/loop_engine/core/mistral_client.py")):
        module = importlib.import_module(module_name)
        for model, capability in sorted(getattr(module, "MODEL_OUTPUT_CAPABILITIES", {}).items()):
            if capability.declared_maximum is None or not capability.observed_at:
                continue
            rows.append({"provider": provider, "model": model, "maximum_output_tokens": capability.declared_maximum,
                         "basis": capability.source, "observed_at": capability.observed_at, "path": path})
    return rows


def read_reviewed(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
