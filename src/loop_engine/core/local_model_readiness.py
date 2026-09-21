"""Will tonight's run actually start on this machine, and say so plainly.

An unattended night that dies at 2am with an out of memory error, or that
never starts because the server was not running, costs a whole night and
tells the operator nothing in the morning. Every one of those failures is
knowable in under a second before anyone goes to bed.

This module asks the local server four questions and refuses the night when
any of them has the wrong answer:

  * is a server answering at the declared address at all;
  * does that server hold the exact model the night names;
  * does the server report the model's own information, including a context
    length, so nothing has to be guessed;
  * do the weights, the key and value cache at the requested context, and
    the declared runtime reserve fit in the video memory the operator
    declared.

Two refusals exist because guessing is worse than stopping. A server that
reports no context length is refused rather than given a default, because
the default would be wrong on the first unusual model. Video memory that
the operator has not declared is refused rather than assumed, because this
module cannot see the card and a wrong assumption produces a confident
sentence about a night that cannot finish.

The cache arithmetic is the standard one and the reader can redo it:

    cache bytes = 2 x layers x key/value heads x head dimension
                  x context tokens x bytes per cache element

The factor of two is the key half and the value half. Every input comes
from the server's own model information, never from a table kept here. The
weights figure is the size the server reports for the model, which is the
size of the file it loads.

Nothing here is a measurement of speed or quality, and no rate is produced.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

MIB = 1024 ** 2
GIB = 1024 ** 3

#: What one key or value element costs. A cache kept at 16 bit precision is
#: the common server default. An 8 bit cache is an explicit server setting,
#: so it is declared here rather than detected.
CACHE_ELEMENT_BYTES = {"f16": 2, "bf16": 2, "f32": 4, "q8": 1}

#: Working space the inference runtime needs beside the weights and the
#: cache: activations, the compute graph and the server's own allocations.
#: It is a declared reserve, not a measurement. Raise it when a load fails
#: close to the line.
DEFAULT_RUNTIME_RESERVE_BYTES = 768 * MIB

#: The model information keys that carry the numbers the cache needs. A
#: server names them with the architecture as a prefix, so the prefix is
#: read from the record rather than assumed.
_INFORMATION_SUFFIXES = {
    "context_length": "context_length",
    "block_count": "block_count",
    "head_count_kv": "attention.head_count_kv",
    "head_count": "attention.head_count",
    "embedding_length": "embedding_length",
}


class ReadinessError(ValueError):
    """An input this preflight cannot use, refused instead of guessed."""


@dataclass(frozen=True)
class LocalModelRequest:
    """What the night intends to run, before anything has been contacted."""

    base_url: str
    model: str
    context_tokens: int
    #: The operator's own figure for the video memory a model may actually
    #: occupy, which is the card's total less whatever else already holds
    #: part of it. Observed on 2026-09-21: a card of 12288 MiB had 1096 MiB
    #: free because two server processes were still holding the rest, so
    #: the card's total would have been the wrong number to compare
    #: against. Zero means undeclared, and undeclared is refused rather
    #: than assumed.
    video_memory_bytes: int = 0
    runtime_reserve_bytes: int = DEFAULT_RUNTIME_RESERVE_BYTES
    cache_element: str = "f16"

    def __post_init__(self) -> None:
        if not str(self.base_url).startswith(("http://", "https://")):
            raise ReadinessError(
                f"base_url {self.base_url!r} must be an http or https address")
        if not str(self.model).strip():
            raise ReadinessError("name the exact model the night will run")
        for name in ("context_tokens", "video_memory_bytes",
                     "runtime_reserve_bytes"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ReadinessError(
                    f"{name} must be a whole number of units, zero or more")
        if self.context_tokens < 1:
            raise ReadinessError("context_tokens must be positive")
        if self.cache_element not in CACHE_ELEMENT_BYTES:
            raise ReadinessError(
                f"unknown cache element {self.cache_element!r}; known: "
                + ", ".join(sorted(CACHE_ELEMENT_BYTES)))

    @property
    def api_root(self) -> str:
        base = str(self.base_url).rstrip("/")
        for suffix in ("/api/chat", "/api"):
            if base.endswith(suffix):
                return base[: -len(suffix)].rstrip("/")
        return base


@dataclass(frozen=True)
class Finding:
    """One question, its answer, and the sentence a person reads."""

    check: str
    state: str                       # passed | refused | unknown
    sentence: str
    observed: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.state not in ("passed", "refused", "unknown"):
            raise ReadinessError(
                "a finding is passed, refused or unknown; nothing else")

    def to_dict(self) -> dict:
        return {"check": self.check, "state": self.state,
                "sentence": self.sentence, "observed": dict(self.observed)}


def kv_cache_bytes(*, layers: int, key_value_heads: int, head_dimension: int,
                   context_tokens: int, cache_element: str = "f16") -> int:
    """Key and value cache size at one context length."""
    values = {"layers": layers, "key_value_heads": key_value_heads,
              "head_dimension": head_dimension,
              "context_tokens": context_tokens}
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ReadinessError(f"{name} must be a positive whole number")
    if cache_element not in CACHE_ELEMENT_BYTES:
        raise ReadinessError(f"unknown cache element {cache_element!r}")
    return (2 * layers * key_value_heads * head_dimension * context_tokens
            * CACHE_ELEMENT_BYTES[cache_element])


def _http_json(opener, url: str, *, payload=None, timeout: float) -> dict:
    """One request, with every failure returned as a record rather than raised."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(8 * 1024 * 1024)
    except urllib.error.HTTPError as error:
        return {"_reached": True, "_status": int(error.code), "_error":
                f"the server answered {int(error.code)}"}
    except (urllib.error.URLError, OSError, ValueError) as error:
        return {"_reached": False, "_status": None,
                "_error": f"{type(error).__name__}"}
    try:
        body = json.loads(raw)
    except ValueError:
        return {"_reached": True, "_status": 200,
                "_error": "the server answered with a body that is not JSON"}
    if not isinstance(body, dict):
        return {"_reached": True, "_status": 200,
                "_error": "the server answered with a body that is not a record"}
    body["_reached"] = True
    body["_status"] = 200
    return body


def _model_information(show: dict) -> dict:
    """The four numbers the cache needs, read from the server's own record.

    Returns the numbers it found and the keys it could not find. Nothing is
    substituted: an absent key/value head count is reported absent, because
    grouped query attention makes the cache several times smaller than the
    attention head count alone suggests and guessing overstates it.
    """
    information = show.get("model_info")
    if not isinstance(information, dict):
        return {"present": {}, "missing": sorted(_INFORMATION_SUFFIXES)}
    present, missing = {}, []
    for name, suffix in _INFORMATION_SUFFIXES.items():
        found = None
        for key, value in information.items():
            if str(key).endswith("." + suffix) and isinstance(value, int) \
                    and not isinstance(value, bool) and value > 0:
                found = int(value)
                break
        if found is None:
            missing.append(name)
        else:
            present[name] = found
    return {"present": present, "missing": sorted(missing)}


def _head_dimension(present: dict) -> int:
    """Head dimension, stated or derived from the two numbers that define it."""
    embedding = present.get("embedding_length", 0)
    heads = present.get("head_count", 0)
    if embedding and heads and embedding % heads == 0:
        return embedding // heads
    return 0


def largest_context_that_fits(*, weights_bytes: int, layers: int,
                              key_value_heads: int, head_dimension: int,
                              cache_element: str, video_memory_bytes: int,
                              runtime_reserve_bytes: int,
                              ceiling_tokens: int) -> int:
    """The longest context still leaving room, or zero when none does.

    Searched with the same arithmetic the report prints, so the answer can
    never disagree with the number beside it.
    """
    def fits(tokens: int) -> bool:
        return (weights_bytes + runtime_reserve_bytes + kv_cache_bytes(
            layers=layers, key_value_heads=key_value_heads,
            head_dimension=head_dimension, context_tokens=tokens,
            cache_element=cache_element)) <= video_memory_bytes

    if ceiling_tokens < 1 or not fits(1):
        return 0
    low, high, best = 1, int(ceiling_tokens), 0
    while low <= high:
        middle = (low + high) // 2
        if fits(middle):
            best, low = middle, middle + 1
        else:
            high = middle - 1
    return best


def _opener_for(opener):
    return opener if opener is not None else urllib.request.build_opener()


def _resident_finding(request: LocalModelRequest, opener,
                      timeout: float) -> Finding:
    """What the server says it is already holding, before this night adds to it.

    An observation, never a refusal: this reads the server's own report and
    cannot see the card, so it states what it found and leaves the memory
    decision to the arithmetic against the memory the operator declared.
    """
    running = _http_json(opener, request.api_root + "/api/ps", timeout=timeout)
    listed = running.get("models")
    if running.get("_error") or not isinstance(listed, list):
        return Finding(
            "the_server_reports_what_it_already_holds", "passed",
            "The server did not report which models it currently holds, so "
            "this check has nothing to add about memory already in use.",
            {"reported": False})
    held = [{"model": str(item.get("name") or item.get("model") or ""),
             "video_memory_bytes": int(item.get("size_vram") or 0),
             "context_length": int(item.get("context_length") or 0)}
            for item in listed if isinstance(item, dict)]
    total = sum(item["video_memory_bytes"] for item in held)
    others = [item for item in held if item["model"] != request.model]
    sentence = (
        f"The server holds nothing right now." if not held else
        f"The server already holds {len(held)} model(s) using "
        f"{round(total / MIB)} MiB of video memory"
        + (f", including {len(others)} that this night does not use: "
           + ", ".join(item["model"] for item in others[:4]) + "."
           if others else ", which is the model this night runs."))
    return Finding(
        "the_server_reports_what_it_already_holds", "passed", sentence,
        {"reported": True, "held": held,
         "video_memory_in_use_bytes": total,
         "models_this_night_does_not_use": [item["model"] for item in others]})


def _server_findings(request: LocalModelRequest, opener,
                     timeout: float) -> tuple:
    """The first two questions: is anything there, and does it hold the model."""
    tags = _http_json(opener, request.api_root + "/api/tags", timeout=timeout)
    if not tags.get("_reached") or tags.get("_error"):
        return ([Finding(
            "a_local_server_answers", "refused",
            f"No local model server answered at {request.base_url}. Start the "
            "server, then run this check again.",
            {"address": request.base_url, "detail": str(tags.get("_error"))})],
            None)
    listed = tags.get("models")
    names = [str(item.get("name") or item.get("model") or "")
             for item in listed if isinstance(item, dict)] \
        if isinstance(listed, list) else []
    findings = [Finding(
        "a_local_server_answers", "passed",
        f"A local model server answered at {request.base_url} and lists "
        f"{len(names)} model(s).", {"address": request.base_url,
                                    "models_listed": len(names)})]
    entry = None
    for item in (listed if isinstance(listed, list) else []):
        if isinstance(item, dict) and request.model in (
                str(item.get("name") or ""), str(item.get("model") or "")):
            entry = item
            break
    if entry is None:
        findings.append(Finding(
            "the_server_holds_this_model", "refused",
            f"The server at {request.base_url} answers but does not hold "
            f"{request.model!r}. It holds: "
            + (", ".join(sorted(names)[:12]) or "nothing") + ".",
            {"model": request.model, "models": sorted(names)[:12]}))
        return (findings, None)
    findings.append(Finding(
        "the_server_holds_this_model", "passed",
        f"The server holds {request.model!r}.",
        {"model": request.model,
         "weights_bytes": int(entry.get("size") or 0),
         "quantisation": str((entry.get("details") or {}).get(
             "quantization_level", "")),
         "parameter_size": str((entry.get("details") or {}).get(
             "parameter_size", ""))}))
    return (findings, entry)


def _memory_findings(request: LocalModelRequest, weights_bytes: int,
                     present: dict, head_dimension: int) -> list:
    """The memory question, refused rather than guessed when undeclared."""
    cache = kv_cache_bytes(
        layers=present["block_count"],
        key_value_heads=present["head_count_kv"],
        head_dimension=head_dimension,
        context_tokens=request.context_tokens,
        cache_element=request.cache_element)
    needed = weights_bytes + cache + request.runtime_reserve_bytes
    observed = {
        "weights_bytes": weights_bytes,
        "kv_cache_bytes": cache,
        "runtime_reserve_bytes": request.runtime_reserve_bytes,
        "needed_bytes": needed,
        "needed_mib": round(needed / MIB),
        "context_tokens": request.context_tokens,
        "layers": present["block_count"],
        "key_value_heads": present["head_count_kv"],
        "head_dimension": head_dimension,
        "cache_element": request.cache_element,
    }
    if request.video_memory_bytes <= 0:
        return [Finding(
            "the_model_fits_the_memory_this_machine_has", "unknown",
            "The video memory a model may occupy on this machine was not "
            "declared, and this check cannot read the card. It needs "
            f"{round(needed / MIB)} MiB for {request.model!r} at "
            f"{request.context_tokens} context tokens. Declare the free "
            "memory with --video-memory-mib and run the check again.",
            observed)]
    observed["video_memory_bytes"] = request.video_memory_bytes
    observed["video_memory_mib"] = round(request.video_memory_bytes / MIB)
    if needed > request.video_memory_bytes:
        largest = largest_context_that_fits(
            weights_bytes=weights_bytes, layers=present["block_count"],
            key_value_heads=present["head_count_kv"],
            head_dimension=head_dimension,
            cache_element=request.cache_element,
            video_memory_bytes=request.video_memory_bytes,
            runtime_reserve_bytes=request.runtime_reserve_bytes,
            ceiling_tokens=present["context_length"])
        observed["largest_context_that_fits"] = largest
        return [Finding(
            "the_model_fits_the_memory_this_machine_has", "refused",
            f"{request.model!r} at {request.context_tokens} context tokens "
            f"needs {round(needed / MIB)} MiB and this machine declared "
            f"{round(request.video_memory_bytes / MIB)} MiB. "
            + (f"The longest context that fits is {largest} tokens."
               if largest else
               "The weights alone do not fit; a smaller model or a smaller "
               "quantisation is the only way to run this tonight."),
            observed)]
    room = request.video_memory_bytes - needed
    observed["room_left_bytes"] = room
    observed["room_left_mib"] = round(room / MIB)
    observed["largest_context_that_fits"] = largest_context_that_fits(
        weights_bytes=weights_bytes, layers=present["block_count"],
        key_value_heads=present["head_count_kv"],
        head_dimension=head_dimension, cache_element=request.cache_element,
        video_memory_bytes=request.video_memory_bytes,
        runtime_reserve_bytes=request.runtime_reserve_bytes,
        ceiling_tokens=present["context_length"])
    return [Finding(
        "the_model_fits_the_memory_this_machine_has", "passed",
        f"{request.model!r} at {request.context_tokens} context tokens needs "
        f"{round(needed / MIB)} MiB of the {round(request.video_memory_bytes / MIB)} "
        f"MiB declared, leaving {round(room / MIB)} MiB. The longest context "
        f"that fits is {observed['largest_context_that_fits']} tokens.",
        observed)]


def check_readiness(request: LocalModelRequest, *, opener=None,
                    timeout: float = 20.0) -> dict:
    """Ask the machine whether tonight can start, and answer in sentences.

    Returns a record whose ``ready`` is true only when every question was
    answered and none of them refused. ``sentence`` is the one line an
    operator reads at the keyboard before going to bed.
    """
    if not isinstance(request, LocalModelRequest):
        raise ReadinessError("check_readiness takes a LocalModelRequest")
    opener = _opener_for(opener)
    findings, entry = _server_findings(request, opener, timeout)
    if entry is not None:
        show = _http_json(opener, request.api_root + "/api/show",
                          payload={"model": request.model}, timeout=timeout)
        information = _model_information(show if not show.get("_error") else {})
        present, missing = information["present"], information["missing"]
        head_dimension = _head_dimension(present)
        needed_names = ("context_length", "block_count", "head_count_kv")
        absent = [name for name in needed_names if name not in present]
        if absent or not head_dimension:
            findings.append(Finding(
                "the_server_reports_the_model_information", "refused",
                f"The server did not report "
                + ", ".join(absent or ["a usable head dimension"])
                + f" for {request.model!r}. This check will not substitute a "
                "default, because a wrong one is a night that stops at 2am. "
                "Use a server build that reports the model information.",
                {"missing": absent or ["head_dimension"],
                 "reported": dict(present)}))
        else:
            findings.append(Finding(
                "the_server_reports_the_model_information", "passed",
                f"The server reports {present['context_length']} context "
                f"tokens, {present['block_count']} layers and "
                f"{present['head_count_kv']} key and value heads for "
                f"{request.model!r}, so nothing had to be guessed.",
                {"reported": dict(present), "head_dimension": head_dimension}))
            if request.context_tokens > present["context_length"]:
                findings.append(Finding(
                    "the_requested_context_is_within_what_the_server_reports",
                    "refused",
                    f"The night asks for {request.context_tokens} context "
                    f"tokens and the server reports {request.model!r} holds "
                    f"{present['context_length']}. Ask for no more than the "
                    "server reports.",
                    {"requested": request.context_tokens,
                     "reported": present["context_length"]}))
            else:
                findings.append(Finding(
                    "the_requested_context_is_within_what_the_server_reports",
                    "passed",
                    f"The night asks for {request.context_tokens} of the "
                    f"{present['context_length']} context tokens the server "
                    "reports.",
                    {"requested": request.context_tokens,
                     "reported": present["context_length"]}))
                findings.append(_resident_finding(request, opener, timeout))
                findings.extend(_memory_findings(
                    request, int(entry.get("size") or 0), present,
                    head_dimension))
    refused = [item for item in findings if item.state == "refused"]
    unknown = [item for item in findings if item.state == "unknown"]
    ready = not refused and not unknown and len(findings) >= 5
    sentence = ("This machine can start the night."
                if ready else (refused or unknown)[0].sentence)
    return {
        "record_type": "local_model_readiness/v1",
        "base_url": request.base_url,
        "model": request.model,
        "context_tokens": request.context_tokens,
        "ready": ready,
        "sentence": sentence,
        "findings": [item.to_dict() for item in findings],
        "refused": [item.check for item in refused],
        "unknown": [item.check for item in unknown],
        "note": ("Every number here is reported by the server or declared by "
                 "the operator. Nothing here measures speed or quality."),
    }


class _FixedOpener:
    """A stand-in server: routes are declared, so the checks stay offline."""

    def __init__(self, routes: dict) -> None:
        self._routes = routes

    def open(self, request, timeout=None):                # noqa: ARG002
        body = self._routes.get(request.full_url)
        if body is None:
            raise urllib.error.URLError("no route")
        if isinstance(body, Exception):
            raise body
        payload = json.dumps(body).encode("utf-8")

        class _Response:
            def read(self, *_a):
                return payload

            def __enter__(self_inner):
                return self_inner

            def __exit__(self, *_a):
                return False

        return _Response()


def _qwen_like_routes(root: str = "http://127.0.0.1:11434") -> dict:
    """A server record shaped like a real one, with stated numbers."""
    return {
        root + "/api/tags": {"models": [{
            "name": "a-model:7b", "model": "a-model:7b", "size": 4_683_087_561,
            "details": {"quantization_level": "Q4_K_M",
                        "parameter_size": "7.6B"}}]},
        root + "/api/show": {"model_info": {
            "arch.context_length": 32768, "arch.block_count": 28,
            "arch.attention.head_count": 28,
            "arch.attention.head_count_kv": 4,
            "arch.embedding_length": 3584}},
        root + "/api/ps": {"models": [
            {"name": "another-model:14b", "size_vram": 6434 * MIB,
             "context_length": 4096}]},
    }


def self_test() -> dict:
    """Every guard beside the known wrong machine it exists to refuse."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:220]})

    def refuses(name, call, fragment):
        try:
            call()
        except ReadinessError as error:
            check(name, fragment in str(error), str(error))
        else:
            check(name, False, "accepted a known wrong input")

    root = "http://127.0.0.1:11434"
    twelve_gib = 12288 * MIB

    # Arithmetic a reader can redo by hand.
    check("the_cache_is_two_halves_and_doubles_with_the_context",
          kv_cache_bytes(layers=28, key_value_heads=4, head_dimension=128,
                         context_tokens=8192)
          == 2 * kv_cache_bytes(layers=28, key_value_heads=4,
                                head_dimension=128, context_tokens=4096))
    check("a_grouped_query_cache_is_smaller_than_one_head_per_query",
          kv_cache_bytes(layers=28, key_value_heads=4, head_dimension=128,
                         context_tokens=4096) * 7
          == kv_cache_bytes(layers=28, key_value_heads=28,
                            head_dimension=128, context_tokens=4096))

    # Known wrong inputs, refused rather than guessed.
    refuses("an_address_that_is_not_http_is_refused",
            lambda: LocalModelRequest(base_url="127.0.0.1:11434",
                                      model="m", context_tokens=4096),
            "http or https")
    refuses("a_night_with_no_context_is_refused",
            lambda: LocalModelRequest(base_url=root, model="m",
                                      context_tokens=0), "must be positive")
    refuses("an_unknown_cache_element_is_refused",
            lambda: LocalModelRequest(base_url=root, model="m",
                                      context_tokens=1, cache_element="maybe"),
            "unknown cache element")

    # A server that is not there.
    silent = check_readiness(
        LocalModelRequest(base_url=root, model="a-model:7b",
                          context_tokens=4096, video_memory_bytes=twelve_gib),
        opener=_FixedOpener({}))
    check("a_server_that_does_not_answer_refuses_the_night",
          silent["ready"] is False
          and "No local model server answered" in silent["sentence"],
          silent["sentence"])

    # A server that answers but holds something else.
    routes = _qwen_like_routes(root)
    wrong_model = check_readiness(
        LocalModelRequest(base_url=root, model="another-model:70b",
                          context_tokens=4096, video_memory_bytes=twelve_gib),
        opener=_FixedOpener(routes))
    check("a_server_without_this_model_refuses_and_names_what_it_holds",
          wrong_model["ready"] is False
          and "does not hold" in wrong_model["sentence"]
          and "a-model:7b" in wrong_model["sentence"], wrong_model["sentence"])

    # A server that reports no model information.
    blind = dict(routes)
    blind[root + "/api/show"] = {"model_info": {"arch.block_count": 28}}
    no_information = check_readiness(
        LocalModelRequest(base_url=root, model="a-model:7b",
                          context_tokens=4096, video_memory_bytes=twelve_gib),
        opener=_FixedOpener(blind))
    check("a_server_that_reports_no_context_length_is_refused_not_defaulted",
          no_information["ready"] is False
          and "context_length" in no_information["sentence"]
          and "will not substitute a default" in no_information["sentence"],
          no_information["sentence"])

    # A context longer than the server says the model holds.
    too_long = check_readiness(
        LocalModelRequest(base_url=root, model="a-model:7b",
                          context_tokens=65536,
                          video_memory_bytes=twelve_gib),
        opener=_FixedOpener(routes))
    check("a_context_beyond_what_the_server_reports_is_refused",
          too_long["ready"] is False
          and "no more than the server reports" in too_long["sentence"],
          too_long["sentence"])

    # Undeclared video memory is refused rather than assumed.
    undeclared = check_readiness(
        LocalModelRequest(base_url=root, model="a-model:7b",
                          context_tokens=32768),
        opener=_FixedOpener(routes))
    check("undeclared_video_memory_refuses_rather_than_assuming_a_card",
          undeclared["ready"] is False
          and undeclared["unknown"] == [
              "the_model_fits_the_memory_this_machine_has"]
          and "--video-memory-mib" in undeclared["sentence"],
          undeclared["sentence"])

    # A card too small, with the context that would fit named.
    small_card = check_readiness(
        LocalModelRequest(base_url=root, model="a-model:7b",
                          context_tokens=32768,
                          video_memory_bytes=6 * GIB),
        opener=_FixedOpener(routes))
    check("a_card_too_small_refuses_and_names_the_context_that_would_fit",
          small_card["ready"] is False
          and "longest context that fits" in small_card["sentence"],
          small_card["sentence"])

    # The machine that can run it.
    ready = check_readiness(
        LocalModelRequest(base_url=root, model="a-model:7b",
                          context_tokens=32768,
                          video_memory_bytes=twelve_gib),
        opener=_FixedOpener(routes))
    memory = [item for item in ready["findings"]
              if item["check"] == "the_model_fits_the_memory_this_machine_has"]
    check("a_machine_with_room_is_ready_and_states_the_room_left",
          ready["ready"] is True and bool(memory)
          and memory[0]["observed"]["kv_cache_bytes"] == 1_879_048_192
          and memory[0]["observed"]["room_left_mib"] > 0, ready["sentence"])
    check("the_reported_need_is_weights_plus_cache_plus_the_declared_reserve",
          memory[0]["observed"]["needed_bytes"]
          == 4_683_087_561 + 1_879_048_192 + DEFAULT_RUNTIME_RESERVE_BYTES)

    # What the server already holds. Observed on 2026-09-21: a card of
    # 12288 MiB had 1096 MiB free because two earlier server processes were
    # still holding the rest, and the card's total was the wrong number to
    # compare against.
    resident = [item for item in ready["findings"]
                if item["check"] == "the_server_reports_what_it_already_holds"]
    check("the_check_reports_a_model_already_holding_memory_this_night_needs",
          bool(resident)
          and resident[0]["observed"]["models_this_night_does_not_use"]
          == ["another-model:14b"]
          and "does not use" in resident[0]["sentence"],
          resident[0]["sentence"] if resident else "no finding")
    quiet = dict(routes)
    quiet.pop(root + "/api/ps")
    silent_ps = check_readiness(
        LocalModelRequest(base_url=root, model="a-model:7b",
                          context_tokens=32768,
                          video_memory_bytes=twelve_gib),
        opener=_FixedOpener(quiet))
    check("a_server_that_reports_nothing_resident_does_not_block_the_night",
          silent_ps["ready"] is True
          and any(item["observed"].get("reported") is False
                  for item in silent_ps["findings"]
                  if item["check"]
                  == "the_server_reports_what_it_already_holds"),
          silent_ps["sentence"])
    passed = sum(item["passed"] for item in tests)
    return {"name": "local_model_readiness", "tests": tests,
            "passed": passed, "total": len(tests)}
