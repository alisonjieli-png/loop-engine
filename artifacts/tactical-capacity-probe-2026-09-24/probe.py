"""Read-only metadata and bounded capacity probes for the Tactical binding.

Operator evidence tooling for September 24, 2026, not product code. The
endpoint, model and TLS trust come from the committed provider binding and go
through the same ``ProviderSettings.custom_endpoint`` path and trust contract
as the generator. The credential is resolved through
``tools/operator_credentials.py`` inside this process, reaches only the
request header, and is checked absent from every record before it is written.

Operations:
  metadata   GET-only routes and the server's OpenAPI description. No model.
  chat       One streamed chat request. It stops reading after a declared
             number of streamed chunks or seconds and closes the connection,
             so a server that accepts a huge max_tokens is not left
             generating for long.
  tokenize   One POST to the server's tokenizer route. The tokenizer runs;
             the model does not generate.
  kv-events  One POST to the documented cache event route. No model.
  complete   One streamed raw completion read to the server's own stop, with
             a client deadline. One model call.
Each run writes one new record and refuses to overwrite an existing file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from loop_engine.core import custom_endpoint as ce
from loop_engine.core import settings_loader
from tools import operator_credentials

BINDING = ROOT / "tools/resources/original-native-generation-providers/tactical-gemma-4-coding-abliterated.json"
LIMIT_WORDS = ("max_seq_len", "max_model_len", "max_num_tokens", "max_input_len", "max_tokens",
               "max_batch_size", "context", "limit")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def endpoint(key: str):
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    provider = dict(binding["provider"])
    identity = {name: provider.pop(name) for name in ("tls_server_name", "tls_pinned_sha256") if name in provider}
    settings = settings_loader.runtime_settings_from_mapping(
        {"version": 1, "models": {"providers": [provider]}}).models.providers[0]
    settings = replace(settings, tls_ca_file=str(ROOT / settings.tls_ca_file), **identity)
    return binding, settings.custom_endpoint(key)


def origin(ep) -> str:
    return ep.api_root.removesuffix("/v1")


def read(opener, request, timeout, limit=4 * 1024 * 1024):
    row = {"url": request.full_url, "method": request.get_method()}
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(limit + 1)
            row.update(status=response.status, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            row["body"] = raw[:limit]
    except urllib.error.HTTPError as error:
        body = error.read()[:4096]
        row.update(status=error.code, bytes=len(body), body=body)
    except (urllib.error.URLError, OSError, ValueError) as error:
        refused = ce._trust_refusal(error)
        row["error"] = f"tls_trust_refused: {refused}" if refused else f"{type(error).__name__}: {str(error)[:250]}"
    row["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return row


def schema_for(spec, value, depth=0):
    """Resolve one OpenAPI schema with its references, bounded."""
    if depth > 6 or not isinstance(value, dict):
        return value
    if "$ref" in value:
        name = value["$ref"].rsplit("/", 1)[-1]
        return {"$ref": name, **schema_for(spec, spec.get("components", {}).get("schemas", {}).get(name, {}), depth + 1)}
    return {key: (schema_for(spec, item, depth + 1) if isinstance(item, dict) else
                  [schema_for(spec, entry, depth + 1) for entry in item] if isinstance(item, list) else item)
            for key, item in value.items()}


def metadata(args, ep, opener, headers) -> dict:
    base = origin(ep)
    reads = []
    for path in ("/v1/models", "/server_info", "/metrics", "/health", "/version"):
        row = read(opener, urllib.request.Request(base + path, headers=headers), 30)
        body = row.pop("body", b"")
        row["text"] = body.decode("utf-8", "replace")[:2000]
        reads.append(row)
    spec_row = read(opener, urllib.request.Request(base + "/openapi.json", headers=headers), 60)
    body = spec_row.pop("body", b"")
    spec_summary = {}
    if spec_row.get("status") == 200:
        spec = json.loads(body)
        paths = spec.get("paths", {})
        spec_summary["routes"] = sorted(paths)
        spec_summary["tokenize"] = schema_for(spec, paths.get("/_internal/tokenize", {}))
        spec_summary["schemas_naming_limits"] = sorted(
            f"{name}.{field}" for name, schema in spec.get("components", {}).get("schemas", {}).items()
            for field in (schema.get("properties") or {}) if any(word in field for word in LIMIT_WORDS))
    reads.append(spec_row)
    return {"operation": "metadata", "model_calls": 0, "reads": reads, "openapi": spec_summary}


def tokenize(args, ep, opener, headers) -> dict:
    payload = json.loads(args.payload)
    request = urllib.request.Request(origin(ep) + "/_internal/tokenize", data=json.dumps(payload).encode(),
                                     headers=headers)
    row = read(opener, request, 60)
    body = row.pop("body", b"")
    text = body.decode("utf-8", "replace")
    try:
        value = json.loads(text)
        if isinstance(value, dict) and isinstance(value.get("tokens"), list) and len(value["tokens"]) > 64:
            value["tokens"] = value["tokens"][:64] + [f"... {len(value['tokens']) - 64} more"]
        row["json"] = value
    except ValueError:
        row["text"] = text[:2000]
    return {"operation": "tokenize", "model_calls": 0, "tokenizer_calls": 1, "request": payload, "response": row}


def kv_events(args, ep, opener, headers) -> dict:
    """TensorRT-LLM's documented cache event route. When the server keeps an
    event buffer, the first event states the cache size in blocks."""
    request = urllib.request.Request(origin(ep) + "/kv_cache_events", data=b"", headers=headers, method="POST")
    row = read(opener, request, 60)
    body = row.pop("body", b"")
    text = body.decode("utf-8", "replace")
    try:
        value = json.loads(text)
        if isinstance(value, list) and len(value) > 20:
            value = value[:20] + [f"... {len(value) - 20} more events"]
        row["json"] = value
    except ValueError:
        row["text"] = text[:2000]
    return {"operation": "kv_cache_events", "model_calls": 0, "response": row}


def complete(args, ep, opener, headers) -> dict:
    """One streamed raw completion read to its end: the server's own stop
    reason and usage decide the outcome. The prompt is the counting text of
    the September 23 call 3, which greedy decoding never ends by itself."""
    prompt = "".join(f"{number}\n" for number in range(1, 101))
    payload = {"model": ep.model, "prompt": prompt, "max_tokens": args.max_tokens, "temperature": 0.0,
               "stream": True, "stream_options": {"include_usage": True}}
    request = urllib.request.Request(ep.api_root + "/completions", data=json.dumps(payload).encode(), headers=headers)
    record = {"operation": "completion_to_requested_ceiling", "model_calls": 1, "request": payload,
              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "deadline_seconds": args.stop_after_seconds}
    started = time.monotonic()
    chunks, finish, stop_reason, usage, identities, first = 0, "", None, None, [], None
    digest, tail, content_bytes = hashlib.sha256(), "", 0
    progress = Path(args.progress) if args.progress else None
    last = started
    try:
        with opener.open(request, timeout=args.read_timeout) as response:
            record["http_status"] = response.status
            for data in ce._sse_lines(response):
                if data.casefold() == "[done]":
                    record["saw_done"] = True
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                if not isinstance(chunk, dict):
                    continue
                chunks += 1
                if isinstance(chunk.get("model"), str) and chunk["model"] not in identities:
                    identities.append(chunk["model"])
                for choice in chunk.get("choices") or []:
                    if not isinstance(choice, dict):
                        continue
                    if isinstance(choice.get("text"), str) and choice["text"]:
                        if first is None:
                            first = round(time.monotonic() - started, 3)
                        raw = choice["text"].encode()
                        digest.update(raw)
                        content_bytes += len(raw)
                        tail = (tail + choice["text"])[-200:]
                    if choice.get("finish_reason"):
                        finish = choice["finish_reason"]
                    if choice.get("stop_reason") is not None:
                        stop_reason = choice["stop_reason"]
                if isinstance(chunk.get("usage"), dict):
                    usage = chunk["usage"]
                moment = time.monotonic()
                if progress and moment - last >= 30:
                    last = moment
                    progress.write_text(json.dumps({"chunks": chunks, "elapsed_seconds": round(moment - started, 1),
                                                    "tail": tail[-30:]}) + "\n")
                if moment - started > args.stop_after_seconds:
                    record["client_deadline_reached"] = True
                    break
    except urllib.error.HTTPError as error:
        record["http_status"] = error.code
        record["error_body"] = error.read()[:4096].decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError) as error:
        refused = ce._trust_refusal(error)
        record["error"] = f"tls_trust_refused: {refused}" if refused else f"{type(error).__name__}: {str(error)[:250]}"
    completion = (usage or {}).get("completion_tokens")
    record.update(chunks=chunks, content_bytes=content_bytes, content_sha256=digest.hexdigest(), content_tail=tail,
                  finish_reason=finish or None, stop_reason=stop_reason, usage=usage, model_identities=identities,
                  time_to_first_content_seconds=first, elapsed_seconds=round(time.monotonic() - started, 3),
                  clean_stop_at_requested_ceiling=bool(finish == "length" and completion == args.max_tokens
                                                       and record.get("saw_done") and identities == [ep.model]))
    return record


def chat(args, ep, opener, headers) -> dict:
    messages = [{"role": "user", "content": args.prompt}]
    payload = {"model": ep.model, "messages": messages, "max_tokens": args.max_tokens, "temperature": 0.0,
               "stream": True, "stream_options": {"include_usage": True}}
    request = urllib.request.Request(ep.chat_url, data=json.dumps(payload).encode(), headers=headers)
    record = {"operation": "chat", "model_calls": 1, "request": payload,
              "stop_after_chunks": args.stop_after_chunks, "stop_after_seconds": args.stop_after_seconds}
    started = time.monotonic()
    chunks, text, finish, stop_reason, usage, identities = 0, "", "", None, None, []
    first = None
    try:
        with opener.open(request, timeout=args.read_timeout) as response:
            record["http_status"] = response.status
            for data in ce._sse_lines(response):
                if data.casefold() == "[done]":
                    record["saw_done"] = True
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                if not isinstance(chunk, dict):
                    continue
                chunks += 1
                if isinstance(chunk.get("model"), str) and chunk["model"] not in identities:
                    identities.append(chunk["model"])
                parts, _reasoning, reason = ce._sse_chunk_text(chunk)
                if parts and first is None:
                    first = round(time.monotonic() - started, 3)
                text += "".join(parts)
                finish = reason or finish
                for choice in chunk.get("choices") or []:
                    if isinstance(choice, dict) and choice.get("stop_reason") is not None:
                        stop_reason = choice["stop_reason"]
                if isinstance(chunk.get("usage"), dict):
                    usage = chunk["usage"]
                if not finish and (chunks >= args.stop_after_chunks
                                   or time.monotonic() - started > args.stop_after_seconds):
                    record["client_closed_early"] = True
                    break
    except urllib.error.HTTPError as error:
        record["http_status"] = error.code
        record["error_body"] = error.read()[:4096].decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, ValueError) as error:
        refused = ce._trust_refusal(error)
        record["error"] = f"tls_trust_refused: {refused}" if refused else f"{type(error).__name__}: {str(error)[:250]}"
    record.update(chunks=chunks, text=text[:2000], finish_reason=finish or None, stop_reason=stop_reason,
                  usage=usage, model_identities=identities, time_to_first_content_seconds=first,
                  elapsed_seconds=round(time.monotonic() - started, 3))
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("metadata", "chat", "tokenize", "kv-events", "complete"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--credential-reference", default="tactical-model-generation")
    parser.add_argument("--prompt", default="Reply with one word: READY")
    parser.add_argument("--max-tokens", type=int, default=10_000_000)
    parser.add_argument("--stop-after-chunks", type=int, default=32)
    parser.add_argument("--stop-after-seconds", type=float, default=20.0)
    parser.add_argument("--read-timeout", type=float, default=120.0)
    parser.add_argument("--payload", default="")
    parser.add_argument("--progress", default="")
    parser.add_argument("--authorize-model-call", action="store_true")
    args = parser.parse_args(argv)
    output = Path(args.output)
    if output.exists():
        print(json.dumps({"refused": "output_exists_use_a_new_name"}))
        return 2
    if args.operation in ("chat", "complete") and not args.authorize_model_call:
        print(json.dumps({"refused": "model_call_authority_required"}))
        return 2
    key = operator_credentials.resolve(args.credential_reference)
    binding, ep = endpoint(key)
    headers = ce._request_headers(ep)
    opener = ce._endpoint_opener(ep)
    record = {"record_type": "tactical_capacity_probe/v1", "at": now(), "endpoint": ep.base_url,
              "model": ep.model, "binding_id": binding["binding_id"],
              "binding_sha256": hashlib.sha256(BINDING.read_bytes()).hexdigest(),
              "tls": {"server_name": ep.tls_server_name, "pinned_leaf_sha256": ep.tls_pinned_sha256,
                      "anchor_sha256": binding["trust_anchor_sha256"]},
              "credential_reference": "operator:" + args.credential_reference,
              **{"metadata": metadata, "chat": chat, "tokenize": tokenize,
                 "kv-events": kv_events, "complete": complete}[args.operation](args, ep, opener, headers)}
    text = json.dumps(record, indent=1, ensure_ascii=False, default=lambda value: value.decode("utf-8", "replace")
                      if isinstance(value, bytes) else str(value)) + "\n"
    if key in text:
        print(json.dumps({"refused": "credential_would_be_written"}))
        return 3
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")
    print(text[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
