"""The records of the public model and endpoint directory, and the rules every row must meet.

Kind: passive typed records with their strict reader. The builder in `tools/model_directory/`
writes the packaged files under `web_assets/model-directory/`; the pages in
`model_directory_pages.py` read them through `load_directory`. Both sides call the same
`validate_model_row` and `validate_endpoint_row`, so a row the builder would refuse is also a row
the service refuses to show.

The rules, each with a known-wrong case in `tools/test_model_directory.py`:

- every row names at least one source, and every source has an address and the date it was read;
- every fact, price, quantization, use case and benchmark names the source it came from;
- a price carries the date it applies to, so a page can show how old it is;
- an unknown fact is absent, never a guess, and a page renders it as "Unknown";
- every row carries a `commercial_relationship` object read by the shared schema, and nothing that
  orders, filters, includes or fits a row reads it.

Addresses are stored without their scheme, because every public source address is an https
address; a stored address that carries a scheme is refused. A local runtime's own address is not
a source address: it names its scheme, host and path as separate fields.

Nothing here serves a page, reads a request or opens a connection.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache

from . import commercial_relationship as commercial

MANIFEST_RECORD_TYPE = "model_directory_manifest/v1"
MODELS_RECORD_TYPE = "model_directory_models/v1"
ENDPOINTS_RECORD_TYPE = "model_directory_endpoints/v1"
HARDWARE_RECORD_TYPE = "model_directory_hardware/v1"
FIT_INDEX_RECORD_TYPE = "model_directory_fit_index/v1"
SEARCH_INDEX_RECORD_TYPE = "model_directory_search_index/v1"
#: The packaged folder, inside web_assets, that holds every directory file.
DATA_FOLDER = "model-directory"
#: The scheme every stored source address uses. Addresses are stored without it.
SCHEME = "https"
#: A price older than this, measured from the day a page is served, is shown as stale with its date.
STALE_PRICE_DAYS = 30
#: The sources a row may name, by id. Each has a record in the manifest with its terms.
SOURCE_IDS = ("huggingface", "huggingface_config", "huggingface_gguf", "openrouter", "openrouter_endpoints",
              "modelsdev", "baltor_records", "provider_documentation", "harness_documentation")
#: The API styles an endpoint can speak, which decide the setup a harness needs.
API_OPENAI_CHAT = "openai_chat"
API_OPENAI_RESPONSES = "openai_responses"
API_ANTHROPIC_MESSAGES = "anthropic_messages"
API_NATIVE = "native"
API_STYLES = (API_OPENAI_CHAT, API_OPENAI_RESPONSES, API_ANTHROPIC_MESSAGES, API_NATIVE)
#: How a price reached the directory: the provider's own list, or the route through OpenRouter.
ROUTE_DIRECT = "direct"
ROUTE_OPENROUTER = "openrouter"
ROUTES = (ROUTE_DIRECT, ROUTE_OPENROUTER)
ENDPOINT_HOSTED = "hosted"
ENDPOINT_LOCAL = "local"
ENDPOINT_KINDS = (ENDPOINT_HOSTED, ENDPOINT_LOCAL)
#: The use cases a row may name. Each one names its basis and source; none is an editorial pick.
USE_CASES = ("coding", "reasoning", "classification", "embeddings", "rerank", "vision")
#: The facts a model row may hold. A fact outside this list is refused, so a typo cannot hide.
SINGLE_FACTS = ("released", "licence", "open_weights", "parameters", "active_parameters", "modalities",
                "architecture", "knowledge_cutoff")
LIST_FACTS = ("context", "max_output", "tool_calling", "structured_output", "reasoning")
MODEL_FIELDS = ("slug", "name", "maker", "ids", "sources", "facts", "quantizations", "prices", "use_cases",
                "benchmarks", "popularity", "commercial_relationship")
ENDPOINT_FIELDS = ("slug", "name", "kind", "sources", "apis", "auth", "facts", "setup", "models",
                   "openrouter_provider", "commercial_relationship")

_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_DAY = re.compile(r"^20[0-9]{2}-[01][0-9]-[0-3][0-9]$")
_ADDRESS = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)+(?::[0-9]{2,5})?(?:/[^\s]*)?$",
                      re.IGNORECASE)


class ModelDirectoryError(ValueError):
    """A directory record or row the reader refuses, with the reason."""


def source_address(address: str) -> str:
    """The full https address of a stored source address."""
    return SCHEME + "://" + address


def _text(value, where: str, empty: bool = False) -> str:
    if not isinstance(value, str) or value != value.strip() or (not empty and not value):
        raise ModelDirectoryError(f"{where} is a trimmed{'' if empty else ' nonempty'} string")
    return value


def _day(value, where: str) -> str:
    _text(value, where)
    if not _DAY.match(value):
        raise ModelDirectoryError(f"{where} is a date written YYYY-MM-DD, not {value!r}")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ModelDirectoryError(f"{where} is not a calendar date: {value!r}") from error
    return value


def _address(value, where: str) -> str:
    _text(value, where)
    if "://" in value or not _ADDRESS.match(value) or "@" in value.split("/", 1)[0]:
        raise ModelDirectoryError(f"{where} is an address without its scheme or user information: {value!r}")
    return value


def _number(value, where: str, whole: bool = False, nullable: bool = False):
    if value is None and nullable:
        return None
    kinds = (int,) if whole else (int, float)
    if not isinstance(value, kinds) or isinstance(value, bool) or value < 0:
        raise ModelDirectoryError(f"{where} is a {'whole ' if whole else ''}number of at least zero")
    return value


def _fields(value, where: str, required: tuple, optional: tuple = ()) -> dict:
    if not isinstance(value, dict):
        raise ModelDirectoryError(f"{where} is an object")
    missing = sorted(set(required) - set(value))
    unknown = sorted(set(value) - set(required) - set(optional))
    if missing or unknown:
        raise ModelDirectoryError(f"{where} has missing fields {missing} and unknown fields {unknown}")
    return value


def _sources(row: dict, where: str) -> int:
    sources = row.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ModelDirectoryError(f"{where} names no source; every row keeps the source of its facts")
    for index, item in enumerate(sources):
        at = f"{where}.sources[{index}]"
        _fields(item, at, ("id", "address", "read"))
        if item["id"] not in SOURCE_IDS:
            raise ModelDirectoryError(f"{at}.id is one of {SOURCE_IDS}")
        _address(item["address"], at + ".address")
        _day(item["read"], at + ".read")
    return len(sources)


def _source_ref(value, count: int, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < count:
        raise ModelDirectoryError(f"{where} names no source of this row; every fact keeps its source")
    return value


def _fact(value, count: int, where: str) -> dict:
    """One sourced fact: a value, the source it came from, and optionally its basis and estimate flag."""
    if not isinstance(value, dict) or "source" not in value:
        raise ModelDirectoryError(f"{where} names no source; a fact without its source is refused")
    _fields(value, where, ("source",), ("value", "basis", "estimate", "link", "input", "output", "layers",
                                         "kv_heads", "head_dim", "attention", "latent_width", "max_context",
                                         "sliding"))
    _source_ref(value["source"], count, where + ".source")
    if "basis" in value:
        _text(value["basis"], where + ".basis")
    if "link" in value:
        _address(value["link"], where + ".link")
    if "estimate" in value and not isinstance(value["estimate"], bool):
        raise ModelDirectoryError(f"{where}.estimate is true or false")
    return value


def _price(value, count: int, where: str) -> dict:
    _fields(value, where, ("provider", "provider_slug", "route", "model_id", "input", "output", "as_of", "source"),
            ("cache_read", "context", "quantization", "max_output"))
    _text(value["provider"], where + ".provider")
    if not _SLUG.match(_text(value["provider_slug"], where + ".provider_slug")):
        raise ModelDirectoryError(f"{where}.provider_slug is a lowercase address part")
    if value["route"] not in ROUTES:
        raise ModelDirectoryError(f"{where}.route is one of {ROUTES}")
    _text(value["model_id"], where + ".model_id")
    for name in ("input", "output", "cache_read"):
        _number(value.get(name), f"{where}.{name}", nullable=True)
    for name in ("context", "max_output"):
        _number(value.get(name), f"{where}.{name}", whole=True, nullable=True)
    _day(value["as_of"], where + ".as_of")
    _source_ref(value["source"], count, where + ".source")
    return value


def _quantization(value, count: int, where: str) -> dict:
    _fields(value, where, ("name", "format", "bytes", "repository", "files", "source"))
    _text(value["name"], where + ".name")
    _text(value["format"], where + ".format")
    if _number(value["bytes"], where + ".bytes", whole=True) <= 0:
        raise ModelDirectoryError(f"{where}.bytes is positive")
    _text(value["repository"], where + ".repository")
    if not isinstance(value["files"], list) or not value["files"]:
        raise ModelDirectoryError(f"{where}.files lists the files of this quantization")
    _source_ref(value["source"], count, where + ".source")
    return value


def validate_model_row(row) -> dict:
    """Refuse a model row that breaks a rule; return it unchanged when it meets every rule."""
    where = f"model {row.get('slug', '?') if isinstance(row, dict) else '?'}"
    _fields(row, where, MODEL_FIELDS)
    if not _SLUG.match(_text(row["slug"], where + ".slug")) or len(row["slug"]) > 120:
        raise ModelDirectoryError(f"{where}.slug is a lowercase address part of at most 120 characters")
    _text(row["name"], where + ".name")
    _text(row["maker"], where + ".maker")
    if not isinstance(row["ids"], dict) or not row["ids"]:
        raise ModelDirectoryError(f"{where}.ids names the model in at least one source")
    count = _sources(row, where)
    facts = row["facts"]
    if not isinstance(facts, dict):
        raise ModelDirectoryError(f"{where}.facts is an object")
    unknown = sorted(set(facts) - set(SINGLE_FACTS) - set(LIST_FACTS))
    if unknown:
        raise ModelDirectoryError(f"{where}.facts holds unknown facts {unknown}")
    for name in SINGLE_FACTS:
        if name in facts:
            _fact(facts[name], count, f"{where}.facts.{name}")
    for name in LIST_FACTS:
        if name in facts:
            if not isinstance(facts[name], list) or not facts[name]:
                raise ModelDirectoryError(f"{where}.facts.{name} is a nonempty list or absent")
            for index, item in enumerate(facts[name]):
                _fact(item, count, f"{where}.facts.{name}[{index}]")
    for index, item in enumerate(_list(row["quantizations"], where + ".quantizations")):
        _quantization(item, count, f"{where}.quantizations[{index}]")
    for index, item in enumerate(_list(row["prices"], where + ".prices")):
        _price(item, count, f"{where}.prices[{index}]")
    for index, item in enumerate(_list(row["use_cases"], where + ".use_cases")):
        _fact(item, count, f"{where}.use_cases[{index}]")
        if item.get("value") not in USE_CASES:
            raise ModelDirectoryError(f"{where}.use_cases[{index}] is one of {USE_CASES}")
    for index, item in enumerate(_list(row["benchmarks"], where + ".benchmarks")):
        _fields(item, f"{where}.benchmarks[{index}]", ("name", "publisher", "address", "source"), ("value",))
        _address(item["address"], f"{where}.benchmarks[{index}].address")
        _source_ref(item["source"], count, f"{where}.benchmarks[{index}].source")
    if row["popularity"] is not None:
        _fields(row["popularity"], where + ".popularity", ("downloads", "likes", "source"))
        _source_ref(row["popularity"]["source"], count, where + ".popularity.source")
    commercial.from_record(row["commercial_relationship"])
    return row


def validate_endpoint_row(row) -> dict:
    """Refuse an endpoint row that breaks a rule; return it unchanged when it meets every rule."""
    where = f"endpoint {row.get('slug', '?') if isinstance(row, dict) else '?'}"
    _fields(row, where, ENDPOINT_FIELDS)
    if not _SLUG.match(_text(row["slug"], where + ".slug")):
        raise ModelDirectoryError(f"{where}.slug is a lowercase address part")
    _text(row["name"], where + ".name")
    if row["kind"] not in ENDPOINT_KINDS:
        raise ModelDirectoryError(f"{where}.kind is one of {ENDPOINT_KINDS}")
    count = _sources(row, where)
    for index, api in enumerate(_list(row["apis"], where + ".apis")):
        at = f"{where}.apis[{index}]"
        _fields(api, at, ("style", "base", "source"), ("scheme", "note"))
        if api["style"] not in API_STYLES:
            raise ModelDirectoryError(f"{at}.style is one of {API_STYLES}")
        if row["kind"] == ENDPOINT_LOCAL:
            if api.get("scheme") not in ("http", SCHEME):
                raise ModelDirectoryError(f"{at}.scheme names the scheme of a local runtime")
            _text(api["base"], at + ".base")
        else:
            _address(api["base"], at + ".base")
        _source_ref(api["source"], count, at + ".source")
    if row["auth"] is not None:
        _fields(row["auth"], where + ".auth", ("header", "variable", "source"), ("note",))
        if not (isinstance(row["auth"]["variable"], list) and all(isinstance(part, str) and part for part in row["auth"]["variable"])):
            raise ModelDirectoryError(f"{where}.auth.variable lists the parts of a variable name")
        _source_ref(row["auth"]["source"], count, where + ".auth.source")
    if not isinstance(row["facts"], dict):
        raise ModelDirectoryError(f"{where}.facts is an object")
    for name, value in row["facts"].items():
        _fields(value, f"{where}.facts.{name}", ("source",), ("value", "note", "address"))
        _source_ref(value["source"], count, f"{where}.facts.{name}.source")
        if "address" in value:
            _address(value["address"], f"{where}.facts.{name}.address")
    if not isinstance(row["setup"], dict):
        raise ModelDirectoryError(f"{where}.setup is an object")
    for index, item in enumerate(_list(row["models"], where + ".models")):
        _fields(item, f"{where}.models[{index}]", ("id", "name", "source", "as_of"),
                ("model_slug", "input", "output", "context", "tool_calling"))
        _source_ref(item["source"], count, f"{where}.models[{index}].source")
        _day(item["as_of"], f"{where}.models[{index}].as_of")
    commercial.from_record(row["commercial_relationship"])
    return row


def _list(value, where: str) -> list:
    if not isinstance(value, list):
        raise ModelDirectoryError(f"{where} is a list")
    return value


def price_is_stale(price: dict, today: str) -> bool:
    """True when a price applies to a day more than STALE_PRICE_DAYS before today."""
    return (date.fromisoformat(today) - date.fromisoformat(price["as_of"])).days > STALE_PRICE_DAYS


def relationship_of(row: dict) -> commercial.CommercialRelationship:
    """The typed commercial relationship of a row. Presentation reads it; ordering never does."""
    return commercial.from_record(row["commercial_relationship"])


@dataclass(frozen=True, eq=False)
class Directory:
    """The packaged directory, read and checked once per process."""

    manifest: dict
    models: tuple
    endpoints: tuple
    hardware: dict
    models_by_slug: dict
    endpoints_by_slug: dict
    harnesses: tuple

    def model(self, slug: str) -> "dict | None":
        return self.models_by_slug.get(slug)

    def endpoint(self, slug: str) -> "dict | None":
        return self.endpoints_by_slug.get(slug)


def directory_from_records(manifest, models, endpoints, hardware) -> Directory:
    """Read the four packaged records, refusing any that another reader version wrote."""
    for record, kind in ((manifest, MANIFEST_RECORD_TYPE), (models, MODELS_RECORD_TYPE),
                         (endpoints, ENDPOINTS_RECORD_TYPE), (hardware, HARDWARE_RECORD_TYPE)):
        if not isinstance(record, dict) or record.get("record_type") != kind:
            raise ModelDirectoryError(f"this reader reads {kind}")
    if manifest.get("commercial_relationship_schema") != commercial.SCHEMA:
        raise ModelDirectoryError(f"the manifest names the commercial relationship schema {commercial.SCHEMA}")
    rows = tuple(validate_model_row(row) for row in _list(models.get("models"), "models"))
    slugs = [row["slug"] for row in rows]
    if len(slugs) != len(set(slugs)):
        raise ModelDirectoryError("two model rows share a slug")
    endpoint_rows = tuple(validate_endpoint_row(row) for row in _list(endpoints.get("endpoints"), "endpoints"))
    by_endpoint = {row["slug"]: row for row in endpoint_rows}
    if len(by_endpoint) != len(endpoint_rows):
        raise ModelDirectoryError("two endpoint rows share a slug")
    harnesses = tuple(validate_harness(item) for item in _list(endpoints.get("harnesses"), "harnesses"))
    return Directory(manifest, rows, endpoint_rows, hardware, dict(zip(slugs, rows)), by_endpoint, harnesses)


def validate_harness(value) -> dict:
    """Refuse a harness record without its styles, its file or the dated source of its setup."""
    where = f"harness {value.get('slug', '?') if isinstance(value, dict) else '?'}"
    _fields(value, where, ("slug", "name", "styles", "file", "note", "api_names", "oss_providers", "oss_names", "sources",
                           "source_address", "source_read"))
    if not _SLUG.match(_text(value["slug"], where + ".slug")):
        raise ModelDirectoryError(f"{where}.slug is a lowercase address part")
    if not value["styles"] or any(style not in API_STYLES for style in value["styles"]):
        raise ModelDirectoryError(f"{where}.styles names API styles from {API_STYLES}")
    _text(value["file"], where + ".file")
    _address(value["source_address"], where + ".source_address")
    _day(value["source_read"], where + ".source_read")
    _sources(value, where)
    return value


def _packaged(name: str):
    from importlib.resources import files
    path = files("loop_engine").joinpath("core", "service_runtime", "web_assets", DATA_FOLDER, name)
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_directory() -> Directory:
    """The packaged directory, read through the rules above."""
    return directory_from_records(_packaged("manifest.json"), _packaged("models.json"),
                                  _packaged("endpoints.json"), _packaged("hardware.json"))
