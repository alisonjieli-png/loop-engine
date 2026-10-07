"""The mining run: connectors over local files -> screened signals -> a local index.

Usage:

    python -m tools.conversation_mining.mine --root ~/baltor-private/owner-signals \\
        --claude ~/.claude/projects/-home-username-loop-engine \\
        --codex ~/.codex/sessions --chatgpt /path/to/export.zip --days 30

Writes JSONL of `owner_signal_record/v2` rows plus one `conversation_mining_run/v1`
summary under `--root` (which must be outside the repository). Sends nothing over
any network. A file that fails to read produces a refusal row; the run continues.
"""
from __future__ import annotations

import argparse
import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for entry in (ROOT / "src", ROOT / "tools", ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from conversation_mining import connectors, extract, map_dimensions, records


def _iso(now: float | None = None) -> str:
    stamp = datetime.now(timezone.utc) if now is None else datetime.fromtimestamp(now, timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%SZ")


def _files_for(source: str, path: Path, days: int | None) -> list[Path]:
    cutoff = None
    if days is not None:
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
    if not path.exists():
        return []
    if path.is_file():
        candidates = [path]
    elif source == "claude_code_jsonl":
        candidates = sorted(path.rglob("*.jsonl"))
    elif source == "codex_rollout_jsonl":
        candidates = sorted(path.rglob("rollout-*.jsonl")) or sorted(path.rglob("*.jsonl"))
    elif source == "chatgpt_export_json":
        candidates = [p for p in sorted(path.rglob("*")) if p.name == "conversations.json" or p.suffix == ".zip"]
    else:
        candidates = [p for p in sorted(path.rglob("*")) if p.suffix in (".txt", ".log", ".md")]
    if cutoff is not None:
        candidates = [p for p in candidates if p.stat().st_mtime >= cutoff]
    return candidates


def _timestamp(value):
    try:
        if str(value).replace(".", "", 1).isdigit():
            return datetime.fromtimestamp(float(value), timezone.utc)
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo else None
    except (ValueError, OverflowError, OSError):
        return None


def mine(sources: dict, *, days: int | None, limit_per_file: int = 200,
         since: datetime | None = None) -> tuple[list[dict], dict]:
    """Run every configured connector. Returns (signal records, run summary parts)."""
    out_signals: list[dict] = []
    files_read = []
    sensitive_dropped = 0
    phrases_emitted = 0
    dimensions_touched: set = set()
    read_errors = 0
    timestamp_excluded = truncated_turns = capped_files = 0
    if type(limit_per_file) is not int or not 1 <= limit_per_file <= 100_000:
        raise ValueError("limit_per_file_invalid")
    if days is not None and (type(days) is not int or days <= 0):
        raise ValueError("days_invalid")
    if since is not None and (not isinstance(since, datetime) or since.tzinfo is None):
        raise ValueError("since_requires_timezone")
    if since is None and days is not None:
        from datetime import timedelta
        since = datetime.now(timezone.utc) - timedelta(days=days)
    through = datetime.now(timezone.utc)
    for source, path in sources.items():
        connector = connectors.CONNECTORS[source]
        for file_path in _files_for(source, path, days):
            files_read.append(str(file_path))
            count = 0
            for turn in connector(file_path):
                if turn.role == connectors.READ_ERROR:
                    read_errors += 1
                    continue
                observed = _timestamp(turn.timestamp)
                if since is not None and (observed is None or not since <= observed <= through):
                    timestamp_excluded += 1
                    continue
                truncated_turns += len(turn.text) > connectors.MAX_TURN_CHARACTERS
                intent = extract.classify(turn.text)
                phrases, dropped = extract.extract_phrases(turn.text)
                references = extract.extract_references(turn.text)
                sensitive_dropped += dropped
                clean = list(phrases)
                if not clean and not references:
                    continue
                dims = map_dimensions.map_phrases(clean + [intent])
                signal = records.Signal(
                    source=source, locator=turn.locator, intent=intent,
                    phrases=tuple(clean), dimensions=dims,
                    weight=1 + (1 if references else 0),
                    recorded_at=observed.isoformat() if observed is not None else _iso(),
                    references=tuple(references),
                )
                out_signals.append(signal.record())
                phrases_emitted += len(clean)
                dimensions_touched.update(dims)
                count += 1
                if count >= limit_per_file:
                    capped_files += 1
                    break
    return out_signals, {
        "files_read": tuple(files_read), "signals_emitted": len(out_signals),
        "sensitive_dropped": sensitive_dropped, "phrases_emitted": phrases_emitted,
        "dimensions_touched": tuple(sorted(dimensions_touched)),
        "read_errors": read_errors,
        "timestamp_excluded": timestamp_excluded, "truncated_turns": truncated_turns,
        "capped_files": capped_files,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mine local conversation corpora for owner signals.")
    parser.add_argument("--root", required=True, help="Output folder; must be outside the repository.")
    parser.add_argument("--claude", help="Claude Code projects folder (e.g. ~/.claude/projects/-home-username-loop-engine).")
    parser.add_argument("--codex", help="Codex sessions folder (~/.codex/sessions).")
    parser.add_argument("--chatgpt", help="ChatGPT export .zip or its folder.")
    parser.add_argument("--prompt-log", help="A plain text file of prompts.")
    parser.add_argument("--days", type=int, help="Only timestamped owner turns within the last N days.")
    parser.add_argument("--hours", type=int, help="Only timestamped owner turns within the last N hours.")
    parser.add_argument("--limit-per-file", type=int, default=200)
    options = parser.parse_args(argv)

    os.umask(0o077)
    given = Path(options.root).expanduser().absolute()
    if any(p.is_symlink() for p in (given, *given.parents)):
        parser.error("--root must not contain symbolic links")
    root = given.resolve()
    repo = Path(__file__).resolve().parents[2]
    if repo in root.parents or root in (repo, Path.home(), Path(root.anchor)):
        parser.error("--root must be outside the repository")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    if options.days is not None and options.hours is not None:
        parser.error("choose --days or --hours")
    if options.hours is not None and options.hours <= 0:
        parser.error("--hours must be positive")

    sources = {}
    if options.claude:
        sources["claude_code_jsonl"] = Path(options.claude).expanduser()
    if options.codex:
        sources["codex_rollout_jsonl"] = Path(options.codex).expanduser()
    if options.chatgpt:
        sources["chatgpt_export_json"] = Path(options.chatgpt).expanduser()
    if options.prompt_log:
        sources["prompt_log_text"] = Path(options.prompt_log).expanduser()
    if not sources:
        parser.error("provide at least one --claude, --codex, --chatgpt or --prompt-log")

    started = _iso()
    from datetime import timedelta
    since = datetime.now(timezone.utc) - timedelta(hours=options.hours) if options.hours is not None else None
    signals, summary = mine(sources, days=options.days, limit_per_file=options.limit_per_file, since=since)
    run_id = f"{started.replace(':','').replace('-','')}"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    signals_path = root / f"owner-signals-{stamp}-{run_id}.jsonl"
    with signals_path.open("x", encoding="utf-8") as handle:
        for record in signals:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    run_record = records.RunRecord(
        run_id=run_id, files_read=summary["files_read"],
        signals_emitted=summary["signals_emitted"], sensitive_dropped=summary["sensitive_dropped"],
        phrases_emitted=summary["phrases_emitted"], dimensions_touched=summary["dimensions_touched"],
        started_at=started, finished_at=_iso(),
        read_errors=summary["read_errors"], timestamp_excluded=summary["timestamp_excluded"],
        truncated_turns=summary["truncated_turns"], capped_files=summary["capped_files"],
    ).record()
    run_path = root / f"mining-run-{stamp}-{run_id}.json"
    with run_path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(run_record, indent=1, ensure_ascii=False, sort_keys=True))

    print("conversation_mining run complete")
    print("  signals:", signals_path)
    print("  run:", run_path)
    print("  rows:", run_record["signals_emitted"], "| sensitive dropped:", run_record["sensitive_dropped"],
          "| dimensions:", len(run_record["dimensions_touched"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
