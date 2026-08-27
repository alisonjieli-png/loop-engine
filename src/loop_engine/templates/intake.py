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
        if path.stat().st_size > _MAX_TASK_FILE_BYTES:
            raise TaskIntakeError(
                f"task file exceeds {_MAX_TASK_FILE_BYTES} bytes")
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise TaskIntakeError("task file must be UTF-8 text") from exc
        return TaskIntake("file", body, (str(path),),
                          (("bytes", path.stat().st_size),))
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
        check("task_pack_keeps_source_provenance",
              pack.kind == "task_pack" and len(pack.source_refs) == 2)
        refused = False
        try:
            TaskIntakeRequest(text="x", file=str(task_file))
        except TaskIntakeError:
            refused = True
        check("ambiguous_intake_is_refused", refused)
    return {"tests": results}
