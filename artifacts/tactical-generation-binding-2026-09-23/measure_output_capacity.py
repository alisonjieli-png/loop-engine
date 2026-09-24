"""Measure one endpoint's output limit with one recorded, streamed model call.

Operator evidence tooling for September 23, 2026, not product code. The
server under test accepted ``max_tokens`` far above any plausible limit
without stating a limit, so acceptance proves nothing: this script asks for
a long deterministic answer with a very large ``max_tokens`` and records
where the server itself stopped, with ``finish_reason`` and the reported
token counts.

Every endpoint fact is an argument. The credential is resolved through
``tools/operator_credentials.py`` inside this process, placed only in the
request header by the custom endpoint adapter, and never printed, stored or
logged. The TLS trust contract (declared anchor, expected server name,
pinned leaf certificate) is the adapter's own, so a refused trust sends
nothing. One invocation makes at most one model request.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from loop_engine.core import custom_endpoint as ce
from tools import operator_credentials

#: Each prompt kind is (route, system text, user or raw text). Call 1 used
#: "count"; the model wrote 1 to 50 and then stopped by itself. Call 2 used
#: "count_checked"; it wrote 1 to 100, an ellipsis and the last three
#: numbers, then stopped. Call 3 used "raw_continuation" on the same
#: server's completions route: no chat template, a counting pattern that
#: greedy decoding extends. It streamed 105,574 tokens, then stalled with no
#: stop reason; capacity-record.json keeps the maximum unknown.
PROMPTS = {
    "count": ("chat", "",
              ("Count upward from 1. Write each whole number on its own line, "
               "in order, with no other text. Do not skip a number and never "
               "stop.")),
    "count_checked": ("chat",
                      ("You follow output instructions literally. You never "
                       "abbreviate, never summarize, never write an ellipsis "
                       "and never stop before the requested output is "
                       "complete."),
                      ("Write every whole number from 1 to 100000 in "
                       "increasing order, one number per line, with no other "
                       "text before, between or after the numbers. A program "
                       "reads your answer and rejects it if any single number "
                       "is missing, so write all 100000 lines.")),
    "raw_continuation": ("completions", "",
                         "".join(f"{number}\n" for number in range(1, 101))),
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def measure(args) -> dict:
    route, system, prompt = PROMPTS[args.prompt]
    ca_path = (ROOT / args.tls_ca_file).resolve()
    record = {
        "record_type": "endpoint_output_capacity_measurement/v1",
        "call_number": args.call_number, "call_ceiling": 3,
        "started_at": now(), "finished_at": None,
        "endpoint": args.endpoint, "model_requested": args.model,
        "tls": {"ca_file": args.tls_ca_file,
                "ca_sha256": hashlib.sha256(ca_path.read_bytes()).hexdigest(),
                "server_name": args.tls_server_name,
                "pinned_leaf_sha256": args.tls_pinned_sha256},
        "credential_reference": "operator:" + args.credential_reference,
        "request": {"route": route, "max_tokens": args.max_tokens,
                    "temperature": 0.0, "stream": True,
                    "stream_options": {"include_usage": True},
                    "prompt_kind": args.prompt, "system": system,
                    "prompt": prompt,
                    "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()},
        "response": None, "outcome": "not_sent", "error": "",
    }
    key = operator_credentials.resolve(args.credential_reference)
    endpoint = ce.CustomEndpoint(
        name="tactical", base_url=args.endpoint, model=args.model, api_key=key,
        wire="openai", locality="organization", stream="stream",
        tls_verification="ca_file", tls_ca_file=str(ca_path),
        tls_server_name=args.tls_server_name,
        tls_pinned_sha256=args.tls_pinned_sha256)
    payload = {"model": args.model, "max_tokens": args.max_tokens,
               "temperature": 0.0, "stream": True,
               "stream_options": {"include_usage": True}}
    if route == "chat":
        payload["messages"] = (
            ([{"role": "system", "content": system}] if system else [])
            + [{"role": "user", "content": prompt}])
        url = endpoint.chat_url
    else:
        payload["prompt"] = prompt
        url = endpoint.api_root + "/completions"
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers=ce._request_headers(endpoint))
    del key
    digest = hashlib.sha256()
    head, tail = "", ""
    chunks = content_bytes = 0
    identities, finish, stop_reason, usage = [], "", None, None
    saw_done, first_content, status = False, None, None
    started = time.monotonic()
    last_progress = started
    progress = Path(args.progress) if args.progress else None
    try:
        opener = ce._endpoint_opener(endpoint)
        record["outcome"] = "sent"
        with opener.open(request, timeout=args.read_timeout) as response:
            status = getattr(response, "status", None)
            for data in ce._sse_lines(response):
                if data.casefold() == "[done]":
                    saw_done = True
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                if not isinstance(chunk, dict):
                    continue
                chunks += 1
                model = chunk.get("model")
                if isinstance(model, str) and model not in identities:
                    identities.append(model)
                parts, _reasoning, reason = ce._sse_chunk_text(chunk)
                if route == "completions":
                    parts = [choice["text"] for choice in chunk.get("choices") or []
                             if isinstance(choice, dict)
                             and isinstance(choice.get("text"), str) and choice["text"]]
                for part in parts:
                    if first_content is None:
                        first_content = round(time.monotonic() - started, 3)
                    raw = part.encode("utf-8")
                    digest.update(raw)
                    content_bytes += len(raw)
                    if len(head) < 200:
                        head = (head + part)[:200]
                    tail = (tail + part)[-200:]
                if reason:
                    finish = reason
                for choice in chunk.get("choices") or []:
                    if isinstance(choice, dict) and "stop_reason" in choice \
                            and choice["stop_reason"] is not None:
                        stop_reason = choice["stop_reason"]
                if isinstance(chunk.get("usage"), dict):
                    usage = chunk["usage"]
                moment = time.monotonic()
                if progress and moment - last_progress >= 30:
                    last_progress = moment
                    progress.write_text(json.dumps({
                        "chunks": chunks, "content_bytes": content_bytes,
                        "elapsed_seconds": round(moment - started, 1),
                        "tail": tail[-40:]}) + "\n")
                if moment - started > args.deadline_seconds:
                    record["outcome"] = "stopped_by_client_deadline"
                    break
    except urllib.error.HTTPError as error:
        status = error.code
        record["error"] = f"HTTP {error.code}: " + error.read()[:300].decode(
            "utf-8", "replace")
        record["outcome"] = "http_error"
    except (urllib.error.URLError, OSError, ValueError) as error:
        refused = ce._trust_refusal(error)
        record["error"] = (f"tls_trust_refused: {refused}" if refused else
                           f"{type(error).__name__}: {str(error)[:250]}")
        record["outcome"] = "tls_trust_refused" if refused else "transport_error"
    elapsed = round(time.monotonic() - started, 3)
    lines = [line for line in (head + "\n" + tail).splitlines() if line.strip()]
    record["response"] = {
        "http_status": status, "model_identities": identities,
        "chunks": chunks, "content_bytes": content_bytes,
        "content_sha256": digest.hexdigest(), "content_head": head,
        "content_tail": tail, "last_line": lines[-1] if lines else "",
        "finish_reason": finish, "stop_reason": stop_reason, "usage": usage,
        "saw_done": saw_done, "time_to_first_content_seconds": first_content,
        "elapsed_seconds": elapsed}
    if record["outcome"] == "sent":
        completion = (usage or {}).get("completion_tokens")
        if finish == "length" and isinstance(completion, int) \
                and completion < args.max_tokens:
            record["outcome"] = "server_length_stop_below_request"
        elif finish == "length":
            record["outcome"] = "length_stop_at_request"
        elif finish:
            record["outcome"] = "model_stopped_before_any_limit"
        else:
            record["outcome"] = "incomplete_without_stop_reason"
    record["finished_at"] = now()
    return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--tls-ca-file", required=True,
                        help="repository-relative path of the trust anchor")
    parser.add_argument("--tls-server-name", required=True)
    parser.add_argument("--tls-pinned-sha256", required=True)
    parser.add_argument("--credential-reference", required=True)
    parser.add_argument("--max-tokens", type=int, required=True)
    parser.add_argument("--prompt", choices=sorted(PROMPTS), default="count")
    parser.add_argument("--call-number", type=int, required=True,
                        choices=(1, 2, 3))
    parser.add_argument("--read-timeout", type=float, default=300.0)
    parser.add_argument("--deadline-seconds", type=float, default=10800.0)
    parser.add_argument("--progress", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--authorize-model-call", action="store_true")
    args = parser.parse_args(argv)
    if not args.authorize_model_call:
        print(json.dumps({"refused": "model_call_authority_required"}))
        return 2
    output = Path(args.output)
    if output.exists():
        print(json.dumps({"refused": "output_exists_use_a_new_name"}))
        return 2
    record = measure(args)
    text = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    secret = operator_credentials.resolve(args.credential_reference)
    if secret in text:
        print(json.dumps({"refused": "credential_would_be_written"}))
        return 3
    del secret
    output.write_text(text, encoding="utf-8")
    print(json.dumps({"output": str(output), "outcome": record["outcome"],
                      "usage": record["response"]["usage"],
                      "finish_reason": record["response"]["finish_reason"],
                      "elapsed_seconds": record["response"]["elapsed_seconds"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
