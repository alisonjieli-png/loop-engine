"""Knowledge loader — turn your own files into searchable intelligence.

Architectural role: static architecture (the ingest surface beneath the store).

Before this, the store read exactly one format: JSONL, one record per line. Two
consequences, and the second is the worse one:

    A user's actual knowledge is not JSONL. It is Markdown runbooks, notes,
    CSV tables of past decisions, JSON exports, docstrings in their own code.
    None of it could become intelligence without being converted by hand.

    Pointing the store at any other file did not fail — it returned an EMPTY
    store. The loader caught every exception per line and continued, so a
    Markdown file produced zero records and no error. Silence that looks like
    success is worse than a crash, because nothing tells you to look.

So this module loads many formats, and it REPORTS what it could not read
rather than swallowing it. Large files can instead become compact locator and
digest cards, selected by size before the body reaches the text loader.

    load_knowledge("docs/")            -> LoadResult(records, skipped, errors)
    load_knowledge("runbook.md")
    load_knowledge("decisions.csv", kind="context")
    load_knowledge("large.parquet", content_mode="reference")

Supported without any dependency:

    .jsonl .ndjson   one record per line (the original format)
    .json            a list of records, or an object of them
    .md .markdown    split at headings; each section is a record
    .txt .rst .log   split at blank lines; each paragraph is a record
    .csv .tsv        one record per row
    .py              module and function docstrings

``.yaml``/``.yml`` load when PyYAML is present and are reported as needing it
when it is not — an honest refusal, never a silent skip.

Owns:
    - FORMAT_LOADERS: extension -> parser, the one dispatch table;
    - load_knowledge(): files, directories, or globs -> records + a report;
    - ExternalPayloadRef: a content-addressed locator for an external body;
    - LoadResult: what loaded, referenced, what did not, and exactly why;
    - records_to_store(): the records as a SolverStore.

Does not own:
    - the store (store_serve), ranking (retrieval), or any loop semantics.

Key invariants:
    - a file that cannot be read is REPORTED, never silently skipped;
    - every record carries provenance back to its file and position;
    - record ids are stable across runs, so re-loading is idempotent;
    - reference mode checks size before decoding and never inlines the body;
    - loading costs zero model calls and zero network.

Verification: self_test() — every format round-trips, provenance survives,
ids are stable, a directory walk works, and the adversarial silent-skip and
malformed-file paths are refused.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import mimetypes
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..loop.loop_capsule import ExternalPayloadRef
from .store_serve import STORE_KINDS, StoreRecord

#: Default kind for loaded knowledge. "context" is the honest choice: an
#: arbitrary document is background a loop may consult, not a registered
#: executable node or a curated question.
DEFAULT_KIND = "context"

#: Files never worth loading as knowledge.
_SKIP_NAMES = {".git", "__pycache__", ".venv", "venv", "node_modules",
               ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist", "build"}
_SKIP_SUFFIXES = {".pyc", ".pyo", ".so", ".dylib", ".dll", ".zip", ".gz",
                  ".tar", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico",
                  ".woff", ".woff2", ".ttf", ".mp4", ".wav", ".parquet"}

#: A single document larger than this is chunked rather than loaded whole, so
#: one big file cannot dominate a search index.
MAX_CHARS_PER_RECORD = 4000

#: Inline remains default; reference modes never decode the external body.
CONTENT_MODES = ("inline", "reference", "auto")
DEFAULT_REFERENCE_THRESHOLD_BYTES = 8_000_000
_DIGEST_CHUNK_BYTES = 1024 * 1024


@dataclass
class LoadResult:
    """What loaded, what did not, and why — the report IS the result."""
    records: list = field(default_factory=list)
    skipped: list = field(default_factory=list)      # (path, reason)
    errors: list = field(default_factory=list)       # (path, reason)
    files_read: int = 0
    files_referenced: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> dict:
        return {"record_type": "knowledge_load/v1",
                "records": len(self.records), "files_read": self.files_read,
                "files_referenced": self.files_referenced,
                "skipped": len(self.skipped), "errors": len(self.errors),
                "by_format": self._by_format(),
                "skipped_detail": [{"path": p, "reason": r}
                                   for p, r in self.skipped[:20]],
                "errors_detail": [{"path": p, "reason": r}
                                  for p, r in self.errors[:20]]}

    def _by_format(self) -> dict:
        out: dict = {}
        for r in self.records:
            ext = str(r.body.get("format", "?"))
            out[ext] = out.get(ext, 0) + 1
        return out

    def explain(self) -> str:
        """Plain English, for someone wondering why they got fewer records
        than they expected."""
        lines = [f"Loaded {len(self.records)} records from "
                 f"{self.files_read} file(s)."]
        if self.files_referenced:
            lines.append(f"  referenced {self.files_referenced} file(s) without "
                         "inlining their bodies.")
        if self._by_format():
            lines.append("  by format: " + ", ".join(
                f"{k} {v}" for k, v in sorted(self._by_format().items())))
        if self.skipped:
            lines.append(f"  skipped {len(self.skipped)} file(s):")
            for p, r in self.skipped[:8]:
                lines.append(f"    {os.path.basename(p)}: {r}")
            if len(self.skipped) > 8:
                lines.append(f"    ... and {len(self.skipped) - 8} more")
        if self.errors:
            lines.append(f"  FAILED on {len(self.errors)} file(s):")
            for p, r in self.errors[:8]:
                lines.append(f"    {os.path.basename(p)}: {r}")
        return "\n".join(lines)


def _stable_id(path: str, index: int, text: str) -> str:
    """Same file + same position + same text -> same id, across runs and
    machines, so re-loading a corpus does not duplicate it."""
    h = hashlib.sha256(f"{os.path.basename(path)}:{index}:{text[:200]}"
                       .encode()).hexdigest()[:12]
    stem = re.sub(r"[^a-z0-9]+", "_",
                  os.path.splitext(os.path.basename(path))[0].lower())[:28]
    return f"k.{stem}.{h}"


def _chunk(text: str, limit: int = MAX_CHARS_PER_RECORD) -> list:
    """Split oversized text on paragraph boundaries where possible."""
    if len(text) <= limit:
        return [text]
    out, buf = [], ""
    for para in text.split("\n\n"):
        if len(buf) + len(para) + 2 > limit and buf:
            out.append(buf.strip())
            buf = ""
        buf += para + "\n\n"
        while len(buf) > limit:                  # a single huge paragraph
            out.append(buf[:limit])
            buf = buf[limit:]
    if buf.strip():
        out.append(buf.strip())
    return out


def _record(path: str, index: int, title: str, text: str, *, kind: str,
            fmt: str, extra: "dict | None" = None) -> StoreRecord:
    return StoreRecord(
        record_id=_stable_id(path, index, text),
        kind=kind,
        title=(title or text[:80]).strip()[:200],
        body={"text": text, "source_path": path, "format": fmt,
              "position": index, **(extra or {})},
        tags=("knowledge", fmt.lstrip(".")),
        source="org")


def _read_text_file(path: str) -> str:
    """The one inline text read; reference-mode tests spy on this seam."""
    return open(path, encoding="utf-8", errors="replace").read()


def _sha256_file(path: str) -> str:
    """Hash exact bytes in bounded chunks without materializing the body."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(_DIGEST_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _reference_record(path: str, *, kind: str, size_bytes: int,
                      reference_reason: str,
                      threshold_bytes: "int | None" = None) -> StoreRecord:
    """One compact search card for an external file; never reads text."""
    absolute = str(Path(path).resolve())
    ext = os.path.splitext(path)[1].lower()
    payload = ExternalPayloadRef(
        uri=Path(absolute).as_uri(), digest=_sha256_file(path),
        size_bytes=size_bytes,
        media_type=mimetypes.guess_type(path)[0] or "application/octet-stream",
        storage="local_file")
    external_payload = payload.to_dict()
    external_payload.update({
        "schema": "external_payload_ref/v1", "digest_algorithm": "sha256",
        "source_path": path})
    body = {
        "role": "external_payload_ref",
        "payload_ref": payload.uri,
        "payload_digest": payload.digest,
        "payload_size_bytes": payload.size_bytes,
        "payload_media_type": payload.media_type,
        "body_inline": False,
        "source_path": path,
        "format": ext or "<no_suffix>",
        "position": 0,
        "reference_reason": reference_reason,
        "external_payload": external_payload,
    }
    if threshold_bytes is not None:
        body["reference_threshold_bytes"] = int(threshold_bytes)
    return StoreRecord(
        record_id=_stable_id(path, 0, f"external:{payload.digest}"),
        kind=kind,
        title=f"External knowledge file: {os.path.basename(path)}",
        body=body,
        tags=("knowledge", "external_reference", ext.lstrip(".") or "file"),
        source="org")


# --- per-format parsers ----------------------------------------------------

def _load_jsonl(path: str, text: str, kind: str) -> tuple:
    """One record per line. A malformed line is an ERROR with its line number,
    not a silently dropped record."""
    records, errors = [], []
    for n, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"line {n}: {e.msg}")
            continue
        records.append(_record_from_mapping(d, path, n, ".jsonl", kind))
    return records, errors


def _record_from_mapping(d, path: str, index: int, fmt: str,
                         kind: str) -> StoreRecord:
    """A dict that already looks like a record keeps its fields; anything else
    is carried whole so nothing is lost in translation."""
    if isinstance(d, dict) and {"record_id", "kind", "title"} <= set(d):
        rid, k = str(d["record_id"]), str(d["kind"])
        if k not in STORE_KINDS:
            k = kind
        body = dict(d.get("body") or {})
        body.setdefault("source_path", path)
        body.setdefault("format", fmt)
        return StoreRecord(record_id=rid, kind=k, title=str(d["title"]),
                           body=body, tags=tuple(d.get("tags", ())),
                           source="org")
    text = (json.dumps(d, sort_keys=True) if not isinstance(d, str) else d)
    title = ""
    if isinstance(d, dict):
        for key in ("title", "name", "question", "summary", "id"):
            if d.get(key):
                title = str(d[key])
                break
    return _record(path, index, title, text, kind=kind, fmt=fmt)


def _load_json(path: str, text: str, kind: str) -> tuple:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return [], [f"not valid JSON: {e.msg} (line {e.lineno})"]
    if isinstance(data, dict):
        # an object of records, or one record
        items = (list(data.values())
                 if all(isinstance(v, (dict, str)) for v in data.values())
                 and len(data) > 1 else [data])
    elif isinstance(data, list):
        items = data
    else:
        items = [data]
    return [_record_from_mapping(d, path, i, ".json", kind)
            for i, d in enumerate(items)], []


_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)


def _load_markdown(path: str, text: str, kind: str) -> tuple:
    """Split at headings — a section is the natural unit of a document, and
    keeping its heading as the title is what makes it findable."""
    matches = list(_HEADING.finditer(text))
    if not matches:
        return [_record(path, i, os.path.basename(path), chunk, kind=kind,
                        fmt=".md")
                for i, chunk in enumerate(_chunk(text))], []
    records = []
    preamble = text[:matches[0].start()].strip()
    if preamble:
        records.append(_record(path, 0, os.path.basename(path), preamble,
                               kind=kind, fmt=".md"))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = m.group(2).strip()
        section = text[m.end():end].strip()
        if not section:
            continue
        for j, chunk in enumerate(_chunk(section)):
            records.append(_record(
                path, len(records) + 1, heading, chunk, kind=kind, fmt=".md",
                extra={"heading": heading, "level": len(m.group(1)),
                       "part": j}))
    return records, []


def _load_text(path: str, text: str, kind: str, fmt: str = ".txt") -> tuple:
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    records = []
    for i, para in enumerate(paras):
        for chunk in _chunk(para):
            records.append(_record(path, i, para.splitlines()[0][:80], chunk,
                                   kind=kind, fmt=fmt))
    return records, []


def _load_csv(path: str, text: str, kind: str, delim: str = ",") -> tuple:
    try:
        rows = list(csv.DictReader(io.StringIO(text), delimiter=delim))
    except csv.Error as e:
        return [], [f"unreadable delimited file: {e}"]
    if not rows:
        return [], []
    records = []
    for i, row in enumerate(rows):
        pairs = [f"{k}: {v}" for k, v in row.items() if v]
        title = next((str(v) for k, v in row.items()
                      if k and k.lower() in ("title", "name", "question",
                                             "summary") and v), "")
        records.append(_record(path, i, title or (pairs[0] if pairs else ""),
                               "\n".join(pairs), kind=kind,
                               fmt=".tsv" if delim == "\t" else ".csv",
                               extra={"row": i, "columns": list(row)}))
    return records, []


def _load_python(path: str, text: str, kind: str) -> tuple:
    """Docstrings become knowledge — so a codebase can be searched by what its
    code SAYS it does, with no model involved."""
    import ast
    try:
        tree = ast.parse(text)
    except SyntaxError as e:
        return [], [f"could not parse Python: {e.msg} (line {e.lineno})"]
    records = []
    mod_doc = ast.get_docstring(tree)
    if mod_doc:
        for chunk in _chunk(mod_doc):
            records.append(_record(path, 0, os.path.basename(path), chunk,
                                   kind=kind, fmt=".py",
                                   extra={"symbol": "<module>"}))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            doc = ast.get_docstring(node)
            if not doc:
                continue
            for chunk in _chunk(doc):
                records.append(_record(
                    path, node.lineno, node.name, chunk, kind=kind, fmt=".py",
                    extra={"symbol": node.name, "line": node.lineno}))
    return records, []


def _load_yaml(path: str, text: str, kind: str) -> tuple:
    try:
        import yaml
    except ImportError:
        return [], ["needs PyYAML for .yaml/.yml. Reinstall with: "
                    "python -m pip install --force-reinstall git+https://github.com/alisonjieli-png/loop-engine.git"]
    try:
        data = list(yaml.safe_load_all(text))
    except yaml.YAMLError as e:
        return [], [f"not valid YAML: {str(e)[:120]}"]
    items = data[0] if len(data) == 1 and isinstance(data[0], list) else data
    return [_record_from_mapping(d, path, i, ".yaml", kind)
            for i, d in enumerate(items)], []


#: The ONE dispatch table. Adding a format is adding a row.
FORMAT_LOADERS = {
    ".jsonl": _load_jsonl,
    ".ndjson": _load_jsonl,
    ".json": _load_json,
    ".md": _load_markdown,
    ".markdown": _load_markdown,
    ".txt": _load_text,
    ".rst": _load_text,
    ".log": _load_text,
    ".csv": _load_csv,
    ".tsv": lambda p, t, k: _load_csv(p, t, k, delim="\t"),
    ".py": _load_python,
    ".yaml": _load_yaml,
    ".yml": _load_yaml,
}

SUPPORTED_FORMATS = tuple(sorted(FORMAT_LOADERS))


def _iter_files(target: str, recursive: bool = True):
    if os.path.isfile(target):
        yield target
        return
    if not os.path.isdir(target):
        import glob
        for p in sorted(glob.glob(target)):
            if os.path.isfile(p):
                yield p
        return
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in sorted(dirs)
                   if d not in _SKIP_NAMES and not d.startswith(".")]
        for name in sorted(files):
            yield os.path.join(root, name)
        if not recursive:
            break


def load_knowledge(target: str, *, kind: str = DEFAULT_KIND,
                   recursive: bool = True, max_files: int = 5000,
                   content_mode: str = "inline",
                   reference_threshold_bytes: int =
                       DEFAULT_REFERENCE_THRESHOLD_BYTES,
                   ledger=None) -> LoadResult:
    """Load knowledge from a file, a directory, or a glob.

    Every file is accounted for: loaded, skipped with a reason, or failed with
    a reason. Nothing disappears quietly — that was the original defect.

    ``inline`` preserves parsing; ``reference`` emits locator cards; ``auto``
    does so only at the threshold, decided by ``stat`` before text decoding.
    """
    if kind not in STORE_KINDS:
        raise ValueError(f"kind must be one of {STORE_KINDS}, got {kind!r}")
    if content_mode not in CONTENT_MODES:
        raise ValueError(f"content_mode must be one of {CONTENT_MODES}, got "
                         f"{content_mode!r}")
    if int(reference_threshold_bytes) <= 0:
        raise ValueError("reference_threshold_bytes must be positive")
    result = LoadResult()

    for path in _iter_files(target, recursive):
        if result.files_read >= max_files:
            result.skipped.append((path, f"file cap of {max_files} reached"))
            continue
        try:
            size_bytes = os.path.getsize(path)
        except OSError as e:
            result.errors.append((path, f"could not stat: {e}"))
            continue
        if size_bytes == 0:
            result.skipped.append((path, "empty file"))
            continue
        if os.path.basename(path).startswith("."):
            result.skipped.append((path, "hidden files are not loaded"))
            continue

        should_reference = (
            content_mode == "reference"
            or (content_mode == "auto"
                and size_bytes >= int(reference_threshold_bytes)))
        if should_reference:
            reason = ("explicit_reference_mode" if content_mode == "reference"
                      else "size_threshold")
            try:
                record = _reference_record(
                    path, kind=kind, size_bytes=size_bytes,
                    reference_reason=reason,
                    threshold_bytes=(int(reference_threshold_bytes)
                                     if content_mode == "auto" else None))
            except OSError as e:
                result.errors.append((path, f"could not hash: {e}"))
                continue
            result.files_read += 1
            result.files_referenced += 1
            result.records.append(record)
            continue

        ext = os.path.splitext(path)[1].lower()
        if ext in _SKIP_SUFFIXES:
            # NOTE: no multi-line expression inside an f-string here. That is
            # PEP 701 and only parses on Python 3.12+, while this package
            # supports 3.10 — CI caught it, a 3.14 workstation did not.
            shown = ext or "no suffix"
            result.skipped.append((path, f"not a text format ({shown})"))
            continue
        loader = FORMAT_LOADERS.get(ext)
        if loader is None:
            result.skipped.append(
                (path, f"no loader for {ext or 'files without a suffix'}; "
                       f"supported: {', '.join(SUPPORTED_FORMATS)}"))
            continue
        try:
            text = _read_text_file(path)
        except OSError as e:
            result.errors.append((path, f"could not read: {e}"))
            continue
        if not text.strip():
            result.skipped.append((path, "empty file"))
            continue
        try:
            records, errors = loader(path, text, kind)
        except (ValueError, TypeError, RecursionError) as e:
            result.errors.append((path, f"{type(e).__name__}: {str(e)[:120]}"))
            continue
        result.files_read += 1
        result.records.extend(records)
        for err in errors:
            result.errors.append((path, err))

    if ledger is not None:
        # a canonical kind: loading knowledge is Context Intelligence being
        # retrieved, and a computed or invented kind cannot have its family
        # checked, so the gate refuses one
        ledger.record(loop_id="knowledge.load",
                      event="intelligence.string.retrieved",
                      kind="context", served=len(result.records))
    return result


def records_to_store(records, *, core_records=()):
    """The loaded records as a SolverStore, ready to search."""
    from .store_serve import SolverStore
    store = SolverStore(core_records=list(core_records))
    for r in records:
        store._records[r.record_id] = r          # the store's own registry
    return store


def load_into_store(target: str, *, kind: str = DEFAULT_KIND,
                    core_records=(), content_mode: str = "inline",
                    reference_threshold_bytes: int =
                        DEFAULT_REFERENCE_THRESHOLD_BYTES,
                    ledger=None) -> tuple:
    """One call: files in, a searchable store plus the load report out."""
    result = load_knowledge(
        target, kind=kind, content_mode=content_mode,
        reference_threshold_bytes=reference_threshold_bytes, ledger=ledger)
    return records_to_store(result.records, core_records=core_records), result


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    try:
        # a small corpus in every supported format
        open(os.path.join(d, "notes.md"), "w").write(
            "intro text here\n\n# Deploying\nRun the deploy script.\n\n"
            "## Rollback\nUse the previous tag.\n")
        open(os.path.join(d, "facts.jsonl"), "w").write(
            '{"record_id":"q.1","kind":"question","title":"is it leaking?"}\n'
            '{"not":"a record but still json"}\n'
            'THIS LINE IS NOT JSON\n')
        open(os.path.join(d, "config.json"), "w").write(
            '[{"name":"alpha","detail":"first"},{"name":"beta"}]')
        open(os.path.join(d, "decisions.csv"), "w").write(
            "title,outcome,why\nuse postgres,accepted,mature\n"
            "use mongo,rejected,no joins\n")
        open(os.path.join(d, "runbook.txt"), "w").write(
            "First paragraph about restarts.\n\nSecond paragraph about logs.\n")
        open(os.path.join(d, "helper.py"), "w").write(
            '"""Module that helps."""\n\n\ndef compute(x):\n'
            '    """Compute the thing carefully."""\n    return x\n')
        open(os.path.join(d, "image.png"), "wb").write(b"\x89PNG binary")
        os.makedirs(os.path.join(d, "__pycache__"), exist_ok=True)
        open(os.path.join(d, "__pycache__", "x.pyc"), "w").write("junk")

        res = load_knowledge(d)

        # 1. NON-JSONL FORMATS LOAD. This is the whole point: a user's
        # knowledge is Markdown, CSV, notes and code — not JSONL.
        fmts = res._by_format()
        check("markdown_csv_text_python_and_json_all_load",
              {".md", ".csv", ".txt", ".py", ".json", ".jsonl"} <= set(fmts)
              and len(res.records) >= 10,
              f"{len(res.records)} records across {sorted(fmts)}")

        # 2. MARKDOWN SPLITS AT HEADINGS and keeps them as titles, which is
        # what makes a section findable rather than a wall of text.
        md = [r for r in res.records if r.body.get("format") == ".md"]
        titles = {r.title for r in md}
        check("markdown_sections_become_records_titled_by_their_heading",
              "Deploying" in titles and "Rollback" in titles
              and any("deploy script" in r.body["text"] for r in md),
              f"sections: {sorted(titles)}")

        # 3. THE ORIGINAL DEFECT: a malformed line is REPORTED, not swallowed.
        # Silence that looks like success is worse than a crash.
        jsonl_errors = [e for p, e in res.errors if "facts.jsonl" in p]
        check("a_malformed_line_is_reported_with_its_position",
              len(jsonl_errors) == 1 and "line 3" in jsonl_errors[0]
              and not res.ok,
              f"reported: {jsonl_errors[0] if jsonl_errors else 'NOTHING'}")

        # 4. EVERY FILE IS ACCOUNTED FOR — loaded, skipped with a reason, or
        # failed with a reason. Nothing disappears quietly.
        skipped = {os.path.basename(p): r for p, r in res.skipped}
        check("unloadable_files_are_skipped_with_a_stated_reason",
              "image.png" in skipped and "not a text format" in skipped["image.png"]
              and not any("__pycache__" in p for p, _ in res.skipped)
              and not any("__pycache__" in str(r.body.get("source_path"))
                          for r in res.records),
              f"skipped: {sorted(skipped)}")

        # 5. PROVENANCE survives, so a retrieved record can be traced back to
        # the file and position it came from.
        csv_recs = [r for r in res.records if r.body.get("format") == ".csv"]
        check("every_record_carries_its_source_file_and_position",
              all(r.body.get("source_path") for r in res.records)
              and all("position" in r.body or "row" in r.body
                      for r in csv_recs)
              and any("postgres" in r.body["text"] for r in csv_recs),
              f"{len(csv_recs)} csv rows, each traceable")

        # 6. IDS ARE STABLE: loading the same corpus twice yields the same
        # ids, so a re-load updates rather than duplicating.
        again = load_knowledge(d)
        check("loading_the_same_corpus_twice_gives_the_same_ids",
              [r.record_id for r in res.records]
              == [r.record_id for r in again.records]
              and len({r.record_id for r in res.records})
              == len(res.records),
              f"{len(res.records)} stable, unique ids")

        # 7. THE LOADED CORPUS IS SEARCHABLE — the actual goal.
        store, report = load_into_store(d)
        hits = store.search("rollback previous tag")["hits"]
        check("loaded_knowledge_is_immediately_searchable",
              hits and any("Rollback" in store.serve(h["record_id"]).title
                           for h in hits[:3])
              and report.files_read >= 6,
              f"top hit: {hits[0]['record_id'] if hits else 'NONE'}")

        # 8. the report explains itself to a person
        text = res.explain()
        check("the_load_report_explains_itself_in_plain_english",
              "Loaded" in text and "skipped" in text and "FAILED" in text
              and "by format" in text,
              text.splitlines()[0])

        # 9. ADVERSARIAL: a single file, a glob, an unreadable kind, and a
        # directory containing nothing loadable.
        single = load_knowledge(os.path.join(d, "notes.md"))
        globbed = load_knowledge(os.path.join(d, "*.csv"))
        empty_dir = tempfile.mkdtemp()
        open(os.path.join(empty_dir, "a.png"), "wb").write(b"x")
        nothing = load_knowledge(empty_dir)
        bad_kind = False
        try:
            load_knowledge(d, kind="not_a_kind")
        except ValueError:
            bad_kind = True
        shutil.rmtree(empty_dir, ignore_errors=True)
        check("single_files_globs_empty_dirs_and_bad_kinds_behave",
              single.records and all(r.body["format"] == ".md"
                                     for r in single.records)
              and globbed.records
              and all(r.body["format"] == ".csv" for r in globbed.records)
              and not nothing.records and nothing.skipped and nothing.ok
              and bad_kind,
              "an empty result is empty and honest, not an error")

        # 10. Decide from stat before decoding; stream only for SHA-256.
        large_path = os.path.join(d, "large_reference_payload.dat")
        large_bytes = b"NEVER_INLINE_THIS_LARGE_BODY\n" * 4096
        open(large_path, "wb").write(large_bytes)
        inline_reads = []
        original_reader = globals()["_read_text_file"]

        def spy_reader(path):
            inline_reads.append(path)
            return original_reader(path)

        globals()["_read_text_file"] = spy_reader
        try:
            large_ref = load_knowledge(large_path, content_mode="auto",
                                       reference_threshold_bytes=1024)
            explicit_ref = load_knowledge(os.path.join(d, "notes.md"),
                                          content_mode="reference")
        finally:
            globals()["_read_text_file"] = original_reader
        card = large_ref.records[0]
        serialized_card = json.dumps(card.to_dict(), sort_keys=True)
        expected_digest = hashlib.sha256(large_bytes).hexdigest()
        ref_store = records_to_store(large_ref.records)
        ref_hits = ref_store.search("large reference payload")["hits"]
        check("large_files_become_compact_content_addressed_references",
              large_ref.ok and large_ref.files_read == 1
              and large_ref.files_referenced == 1
              and card.body["body_inline"] is False
              and card.body["payload_digest"] == expected_digest
              and card.body["payload_size_bytes"] == len(large_bytes)
              and card.body["payload_ref"].startswith("file://")
              and "text" not in card.body
              and "NEVER_INLINE_THIS_LARGE_BODY" not in serialized_card
              and len(serialized_card) < 2500 and ref_hits,
              "stat -> streamed digest -> one small locator card; no body")
        check("reference_paths_never_reach_the_inline_text_reader",
              not inline_reads and explicit_ref.files_referenced == 1
              and len(explicit_ref.records) == 1
              and explicit_ref.records[0].body["body_inline"] is False,
              f"inline reader calls: {inline_reads}")

        # 11. Default and below-threshold behavior remain inline.
        small_auto = load_knowledge(os.path.join(d, "notes.md"),
                                    content_mode="auto",
                                    reference_threshold_bytes=10_000_000)
        large_again = load_knowledge(large_path, content_mode="auto",
                                     reference_threshold_bytes=1024)
        check("inline_default_and_below_threshold_behavior_are_preserved",
              single.files_referenced == 0
              and any("text" in record.body for record in single.records)
              and small_auto.files_referenced == 0
              and any("text" in record.body for record in small_auto.records)
              and large_again.records[0].record_id == card.record_id
              and large_again.records[0].body["payload_digest"]
              == expected_digest,
              "existing callers still get parsed text; reference IDs are stable")

        # 12. Unknown modes and nonsensical thresholds fail closed.
        bad_mode = bad_threshold = False
        try:
            load_knowledge(large_path, content_mode="maybe")
        except ValueError:
            bad_mode = True
        try:
            load_knowledge(large_path, content_mode="auto", reference_threshold_bytes=0)
        except ValueError:
            bad_threshold = True
        check("reference_configuration_is_validated_fail_closed",
              bad_mode and bad_threshold,
              f"modes={CONTENT_MODES}; threshold must be positive")
    finally:
        shutil.rmtree(d, ignore_errors=True)

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
