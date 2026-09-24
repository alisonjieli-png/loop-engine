"""One recorded call: does the Tactical server enforce a JSON Schema on output?

Decision data after two generation runs whose drafts failed on JSON escaping.
The request asks for a draft-shaped object whose one file is a JSON document,
the exact case that failed (the model wrote the file's contents as a raw
array instead of a string). It sends ``response_format`` with that schema. A
server with grammar-constrained decoding must return a string; a server
without it refuses the field or ignores it. Endpoint, trust and credential
come from the committed binding through the capacity probe's helpers. One
invocation makes one model call and writes one secret-free record.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parents[1] / "artifacts/tactical-capacity-probe-2026-09-24")]

import probe

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["record_type", "method_id", "files"],
          "properties": {"record_type": {"const": "original_native_file_draft/v1"}, "method_id": {"type": "string"},
                         "files": {"type": "array", "items": {
                             "type": "object", "additionalProperties": False, "required": ["path", "content"],
                             "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}}}}
PROMPT = ("Return one JSON object with record_type original_native_file_draft/v1, method_id probe_pair, and files "
          "holding exactly one file: path data.json, whose content is a JSON document listing the numbers 1 and 2.")


def main(output: Path) -> int:
    if output.exists():
        raise SystemExit("output exists; use a new name")
    key = probe.operator_credentials.resolve("tactical-model-generation")
    binding, ep = probe.endpoint(key)
    payload = {"model": ep.model, "messages": [{"role": "user", "content": PROMPT}], "max_tokens": 512,
               "temperature": 0.0, "response_format": {"type": "json_schema", "json_schema": {
                   "name": "original_native_file_draft", "schema": SCHEMA, "strict": True}}}
    request = urllib.request.Request(ep.chat_url, data=json.dumps(payload).encode(),
                                     headers=probe.ce._request_headers(ep))
    row = probe.read(probe.ce._endpoint_opener(ep), request, 120)
    body = row.pop("body", b"").decode("utf-8", "replace")
    record = {"record_type": "tactical_structured_output_probe/v1", "at": datetime.now(timezone.utc).isoformat(),
              "endpoint": ep.base_url, "model": ep.model, "binding_id": binding["binding_id"],
              "model_calls": 1, "request": payload, "response": row}
    try:
        value = json.loads(body)
        record["response_json"] = value
        content = ((value.get("choices") or [{}])[0].get("message") or {}).get("content")
        record["answer"] = content
        try:
            answer = json.loads(content)
            files = answer.get("files") if isinstance(answer, dict) else None
            record["answer_is_json"] = True
            record["file_content_is_string"] = bool(files) and all(isinstance(item.get("content"), str)
                                                                   for item in files)
        except (TypeError, ValueError):
            record["answer_is_json"] = False
    except ValueError:
        record["response_text"] = body[:2000]
    text = json.dumps(record, indent=1, ensure_ascii=False) + "\n"
    if key in text:
        raise SystemExit("credential_would_be_written")
    output.write_text(text, encoding="utf-8")
    print(json.dumps({key_: record.get(key_) for key_ in ("answer", "answer_is_json", "file_content_is_string")}
                     | {"status": row.get("status"), "error": row.get("error")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1])))
