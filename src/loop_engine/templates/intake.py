"""One typed intake boundary for every public task source.

Adapters preserve the original input and source references without fetching,
executing, or granting authority. Compilation consumes one common record.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

INTAKE_KINDS = ("text", "file", "url", "dataset", "repository", "task_pack")
_MAX_TASK_FILE_BYTES = 1_000_000


class TaskIntakeError(ValueError):
    """An intake was ambiguous, unreadable, or exceeded its bounded contract."""


@dataclass(frozen=True)
class CapturedInstructionProvenance:
    """Identity of supplied instruction text, not external-data permission.

    File-byte facts come from intake metadata. A programmatic text record with
    only an origin reference remains provided_text and does not claim a file
    read. Origin references never require inspection to recover this text.
    """

    content_digest: str
    utf8_byte_count: int
    source_refs: tuple[str, ...] = ()
    capture_method: str = "provided_text"
    source_digest: str | None = None
    source_byte_count: int | None = None

    def __post_init__(self) -> None:
        for digest in (self.content_digest, self.source_digest):
            if digest is not None and (
                    type(digest) is not str or len(digest) != 64
                    or any(character not in "0123456789abcdef" for character in digest)):
                raise TaskIntakeError("instruction provenance needs SHA-256 digests")
        if self.content_digest is None:
            raise TaskIntakeError("instruction text digest is required")
        if type(self.utf8_byte_count) is not int or self.utf8_byte_count < 1:
            raise TaskIntakeError("instruction UTF-8 byte count must be positive")
        if (type(self.source_refs) not in (tuple, list)
                or any(type(ref) is not str or not ref.strip() for ref in self.source_refs)
                or len(self.source_refs) != len(set(self.source_refs))):
            raise TaskIntakeError("instruction origins must be unique text references")
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        if type(self.capture_method) is not str or self.capture_method not in (
                "provided_text", "file_bytes"):
            raise TaskIntakeError("unknown instruction capture method")
        if self.capture_method == "file_bytes":
            if (len(self.source_refs) != 1 or self.source_digest is None
                    or type(self.source_byte_count) is not int
                    or self.source_byte_count < self.utf8_byte_count):
                raise TaskIntakeError("file capture needs one origin and consistent byte facts")
        elif self.source_digest is not None or self.source_byte_count is not None:
            raise TaskIntakeError("provided text cannot claim observed file bytes")

    def validate_text(self, text: str) -> None:
        """Refuse a provenance record rebound to different instruction text."""
        if type(text) is not str or not text.strip():
            raise TaskIntakeError("instruction provenance requires nonempty text")
        body = text.encode("utf-8")
        if (len(body) != self.utf8_byte_count
                or hashlib.sha256(body).hexdigest() != self.content_digest):
            raise TaskIntakeError("instruction provenance differs from captured text")

    def to_dict(self) -> dict:
        return {
            "record_type": "captured_instruction_provenance/v1",
            "content_digest": self.content_digest,
            "utf8_byte_count": self.utf8_byte_count,
            "source_refs": list(self.source_refs),
            "capture_method": self.capture_method,
            "source_digest": self.source_digest,
            "source_byte_count": self.source_byte_count,
            "reference_role": "instruction_provenance_not_external_data",
            "external_source_permission_granted": False,
        }


@dataclass(frozen=True)
class TaskIntakeRequest:
    text: str = ""
    file: str = ""
    url: str = ""
    dataset: str = ""
    repository: str = ""
    task_pack: str = ""
    goal: str = ""

    def __post_init__(self) -> None:
        supplied = [value for value in (
            self.text, self.file, self.url, self.dataset, self.repository,
            self.task_pack) if str(value).strip()]
        if len(supplied) != 1:
            raise TaskIntakeError(
                "supply exactly one of text, file, url, dataset, repository, "
                "or task_pack")


@dataclass(frozen=True)
class TaskIntake:
    kind: str
    original_input: str
    source_refs: tuple[str, ...] = ()
    metadata: tuple[tuple[str, object], ...] = ()
    content_digest: str = ""

    def __post_init__(self) -> None:
        if self.kind not in INTAKE_KINDS:
            raise TaskIntakeError(f"kind must be one of {INTAKE_KINDS}")
        if (type(self.source_refs) not in (tuple, list)
                or any(type(ref) is not str or not ref.strip() for ref in self.source_refs)):
            raise TaskIntakeError("intake source references must be text sequences")
        object.__setattr__(self, "source_refs", tuple(self.source_refs))
        if not self.original_input.strip():
            raise TaskIntakeError("intake must preserve non-empty original input")
        expected = hashlib.sha256(self.original_input.encode("utf-8")).hexdigest()
        if self.content_digest and self.content_digest != expected:
            raise TaskIntakeError("intake content digest does not match input")
        object.__setattr__(self, "content_digest", expected)

    def to_dict(self) -> dict:
        return {
            "record_type": "task_intake/v1", "kind": self.kind,
            "original_input": self.original_input,
            "source_refs": list(self.source_refs),
            "metadata": dict(self.metadata),
            "content_digest": self.content_digest,
        }

    @property
    def external_source_refs(self) -> tuple[str, ...]:
        """Keep a captured instruction origin out of unread data references."""
        return () if self.kind == "file" else tuple(self.source_refs)

    @property
    def instruction_provenance(self) -> CapturedInstructionProvenance | None:
        """Expose captured file instructions without changing the v1 wire record."""
        if self.kind != "file":
            return None
        metadata = dict(self.metadata)
        provenance = CapturedInstructionProvenance(
            self.content_digest, len(self.original_input.encode("utf-8")),
            self.source_refs,
            metadata.get("instruction_capture_method", "provided_text"),
            metadata.get("instruction_source_digest"),
            metadata.get("instruction_source_byte_count"))
        provenance.validate_text(self.original_input)
        return provenance


def _resolved_path(value: str, *, directory: bool | None = None) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise TaskIntakeError(f"intake path does not exist: {path}")
    if directory is True and not path.is_dir():
        raise TaskIntakeError(f"expected a directory: {path}")
    if directory is False and not path.is_file():
        raise TaskIntakeError(f"expected a file: {path}")
    return path


def intake_task(request: TaskIntakeRequest) -> TaskIntake:
    """Normalize adapters into one immutable intake without executing work."""
    if request.text:
        return TaskIntake("text", request.text)
    if request.file:
        path = _resolved_path(request.file, directory=False)
        with path.open("rb") as handle:
            raw = handle.read(_MAX_TASK_FILE_BYTES + 1)
        if len(raw) > _MAX_TASK_FILE_BYTES:
            raise TaskIntakeError(
                f"task file exceeds {_MAX_TASK_FILE_BYTES} bytes")
        try:
            # Preserve the universal-newline behavior of the previous text reader.
            body = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        except UnicodeDecodeError as exc:
            raise TaskIntakeError("task file must be UTF-8 text") from exc
        return TaskIntake("file", body, (str(path),),
                          (("bytes", len(raw)),
                           ("instruction_capture_method", "file_bytes"),
                           ("instruction_source_digest", hashlib.sha256(raw).hexdigest()),
                           ("instruction_source_byte_count", len(raw))))
    if request.url:
        if not request.url.startswith(("http://", "https://")):
            raise TaskIntakeError("URL intake requires http or https")
        return TaskIntake("url", request.goal or request.url,
                          (request.url,), (("fetch_state", "not_fetched"),))
    if request.dataset:
        path = _resolved_path(request.dataset)
        if not request.goal.strip():
            raise TaskIntakeError("dataset intake needs an explicit goal")
        return TaskIntake("dataset", request.goal, (str(path),),
                          (("source_type", "dataset"),))
    if request.repository:
        path = _resolved_path(request.repository, directory=True)
        if not request.goal.strip():
            raise TaskIntakeError("repository intake needs an explicit goal")
        return TaskIntake("repository", request.goal, (str(path),),
                          (("source_type", "repository"),))
    path = _resolved_path(request.task_pack, directory=False)
    try:
        pack = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaskIntakeError("task pack must be one UTF-8 JSON object") from exc
    if not isinstance(pack, dict):
        raise TaskIntakeError("task pack root must be an object")
    original = str(pack.get("original_input") or pack.get("goal") or "")
    if not original.strip():
        raise TaskIntakeError("task pack needs original_input or goal")
    refs = tuple(str(value) for value in pack.get("source_refs", ())
                 if str(value).strip())
    return TaskIntake(
        "task_pack", original, (str(path), *refs),
        (("task_pack_version", str(pack.get("version", "unknown"))),))


def self_test() -> dict:
    import tempfile
    from dataclasses import replace

    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    with tempfile.TemporaryDirectory() as root:
        task_file = Path(root) / "task.txt"
        task_file.write_text("validate this object", encoding="utf-8")
        pack_file = Path(root) / "pack.json"
        pack_file.write_text(json.dumps({
            "version": "1.0.0", "goal": "rank the records",
            "source_refs": ["records.jsonl"],
        }), encoding="utf-8")
        text = intake_task(TaskIntakeRequest(text="classify these rows"))
        file_value = intake_task(TaskIntakeRequest(file=str(task_file)))
        pack = intake_task(TaskIntakeRequest(task_pack=str(pack_file)))
        dataset = intake_task(TaskIntakeRequest(
            dataset=str(task_file), goal="validate the dataset"))
        check("all_intake_forms_share_one_record",
              all(isinstance(value, TaskIntake)
                  for value in (text, file_value, pack, dataset)))
        check("original_input_is_preserved",
              text.original_input == "classify these rows"
              and file_value.original_input == "validate this object")
        captured = file_value.instruction_provenance
        check("file_text_capture_keeps_origin_separate_from_external_data",
              captured.capture_method == "file_bytes"
              and captured.content_digest == file_value.content_digest
              and captured.utf8_byte_count == len(file_value.original_input.encode("utf-8"))
              and captured.source_digest == hashlib.sha256(b"validate this object").hexdigest()
              and file_value.external_source_refs == ()
              and file_value.to_dict()["source_refs"] == [str(task_file)])
        task_file.write_text("changed after capture", encoding="utf-8")
        captured.validate_text(file_value.original_input)
        check("later_file_mutation_cannot_change_captured_instruction_text",
              file_value.original_input == "validate this object"
              and file_value.instruction_provenance == captured)
        manual = TaskIntake("file", "provided instruction", (str(task_file),))
        check("programmatic_text_does_not_invent_observed_file_bytes",
              manual.instruction_provenance.capture_method == "provided_text"
              and manual.instruction_provenance.source_digest is None
              and manual.instruction_provenance.source_byte_count is None
              and text.instruction_provenance is None
              and dataset.instruction_provenance is None
              and dataset.external_source_refs == dataset.source_refs)
        caller_refs = [str(task_file)]
        detached = TaskIntake("file", "provided instruction", caller_refs)
        caller_refs[0] = "another-origin.txt"
        rendered = detached.instruction_provenance.to_dict()
        rendered["source_refs"].clear()
        check("instruction_origin_references_are_detached_from_mutable_callers",
              detached.source_refs == (str(task_file),)
              and detached.instruction_provenance.source_refs == (str(task_file),))
        raw = b"caf\xc3\xa9\r\nsecond\rthird\n"
        task_file.write_bytes(raw)
        newline_capture = intake_task(TaskIntakeRequest(file=str(task_file)))
        check("raw_byte_capture_preserves_existing_text_newline_semantics",
              newline_capture.original_input == "caf\u00e9\nsecond\nthird\n"
              and newline_capture.instruction_provenance.source_digest
              == hashlib.sha256(raw).hexdigest()
              and newline_capture.instruction_provenance.source_byte_count == len(raw))
        invalid = 0
        for operation in (
                lambda: CapturedInstructionProvenance("z" * 64, 1),
                lambda: replace(captured, utf8_byte_count=True),
                lambda: replace(captured, capture_method="provided_text"),
                lambda: replace(captured, source_byte_count=0),
                lambda: replace(captured, content_digest="0" * 64).validate_text(
                    file_value.original_input),
                lambda: captured.validate_text("different text")):
            try:
                operation()
            except TaskIntakeError:
                invalid += 1
        check("malformed_or_rebound_instruction_provenance_fails_closed", invalid == 6)
        check("task_pack_keeps_source_provenance",
              pack.kind == "task_pack" and len(pack.source_refs) == 2)
        refused = False
        try:
            TaskIntakeRequest(text="x", file=str(task_file))
        except TaskIntakeError:
            refused = True
        check("ambiguous_intake_is_refused", refused)
    return {"tests": results}
