"""Export private organization drafts from bounded, already-permitted research inputs. Sends nothing."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from knowledge_radar.opportunities import MAXIMUM_BRIEFS, MAXIMUM_OBSERVATIONS, export_jsonl
from loop_engine.core.library_ingestion.record_rules import LibraryRecordError

MAXIMUM_INPUT_BYTES = 4 * 1024 * 1024


def _read(path, maximum, *, jsonl=True):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAXIMUM_INPUT_BYTES + 1)
    if len(raw) > MAXIMUM_INPUT_BYTES:
        raise ValueError("input_byte_limit")
    value = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()] if jsonl else json.loads(raw)
    if type(value) is not list or len(value) > maximum:
        raise ValueError("input_record_limit")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", required=True, type=Path, help="Request JSONL from the research operator.")
    parser.add_argument("--observations", required=True, type=Path, help="Existing radar observations as JSONL.")
    parser.add_argument("--suppressed-domains", required=True, type=Path, help="Host-managed suppression export: a JSON list, including an explicit empty list.")
    parser.add_argument("--as-of", required=True, help="Evidence review day, YYYY-MM-DD.")
    parser.add_argument("--output", type=Path, help="New private JSONL file. Existing files are never overwritten.")
    parser.add_argument("--authorize-local-writes", action="store_true")
    args = parser.parse_args(argv)
    if args.output and not args.authorize_local_writes:
        parser.error("--output requires --authorize-local-writes")
    try:
        if args.output and args.output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
            raise ValueError("private_output_must_be_outside_repository")
        requests = _read(args.requests, MAXIMUM_BRIEFS)
        observations = _read(args.observations, MAXIMUM_OBSERVATIONS)
        suppressed = _read(args.suppressed_domains, MAXIMUM_OBSERVATIONS, jsonl=False)
        body = export_jsonl(requests, observations, as_of=args.as_of, suppressed_domains=suppressed).encode("utf-8")
        if args.output:
            descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
    except (LibraryRecordError, ValueError, OSError) as error:
        print(json.dumps({"status": "refused", "reason": error.code if isinstance(error, LibraryRecordError) else type(error).__name__}))
        return 1
    print(json.dumps({"status": "written" if args.output else "validated_only", "drafts": len(requests),
                      "bytes": len(body), "delivery_scope": "private_draft", "outreach_authorized": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
