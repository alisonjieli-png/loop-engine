"""Read back a file this run wrote, so generated code can be repaired.

A live run on 2026-09-02 generated a Python file with an unterminated string
literal, was told so exactly, reached the right conclusion immediately — read
the file, find the line, fix it — and then could not read the file. Both
routes were closed, and neither was wrong on its own:
``core.source.inspect`` admits the supplied source manifest and a generated
file is not in it; ``core.generated_project`` requires commands to run the
registered Python executable over reviewed authored files, so ``cat`` is not
admissible either. Between the input boundary and the execution boundary
there was no way to observe what the run itself had produced, and the model
spent twenty passes correctly restating a repair it had no way to perform.

This capability is that observation and nothing else. It reads inside the
run's own workspace, which the runtime created and owns; it never reaches the
original supplied source roots, which remain ``core.source.inspect``'s to
admit, and it never executes anything. The workspace includes partial failed
attempts and admitted input copies, not only completed outputs.

Owns:
    - workspace_read_operation(): the capability's whole behaviour.
    - WorkspaceReadError: its typed refusal.

Does not own: the workspace itself (core.generated_project), the supplied
input manifest (core.adaptive_practitioner_source), or the capability
registry entry that makes it selectable.
"""
from __future__ import annotations

import os

from .runtime_capacity import model_evidence_bytes

WORKSPACE_READ_RECORD_TYPE = "workspace_read_result/v1"

#: How much of one file the model may be shown, as a share of the measured
#: evidence allowance for this call rather than a number written down here.
#: A syntax error needs its line and its neighbours, not the whole file.
_FILE_SHARE = 3


class WorkspaceReadError(ValueError):
    """A workspace read was refused, and says what it would have admitted."""


def _within(root: str, path: str) -> str:
    """Resolve a requested path inside the workspace, or refuse by name.

    The workspace root is the boundary. A path that resolves outside it is
    refused whatever it looks like, so neither ``..`` nor a symbolic link nor
    an absolute path can turn a read of this run's own output into a read of
    anything else.
    """
    root_real = os.path.realpath(root)
    candidate = path if os.path.isabs(path) else os.path.join(root_real, path)
    resolved = os.path.realpath(candidate)
    if resolved != root_real and not resolved.startswith(root_real + os.sep):
        raise WorkspaceReadError(
            f"{path!r} resolves outside this run's workspace; this capability "
            f"reads only files the run itself produced under {root_real}. "
            "Supplied input files are admitted by core.source.inspect")
    return resolved


def _listing(root: str) -> list:
    """Every file the run has produced, relative to the workspace root."""
    found = []
    for base, _dirs, names in os.walk(root):
        for name in names:
            full = os.path.join(base, name)
            try:
                _within(root, full)
                size = os.path.getsize(full)
            except (OSError, WorkspaceReadError):
                continue
            found.append({"path": os.path.relpath(full, root),
                          "byte_count": size})
    return sorted(found, key=lambda item: item["path"])


def workspace_read_operation(arguments, services) -> dict:
    """Return the listing, or the numbered lines of one produced file.

    With no path this states what the run has produced, which is the reading
    a model needs when it does not yet know what it wrote. With a path it
    returns numbered lines, because the failures this exists to repair are
    reported by line number and a model cannot count to line 131 in a blob.
    """
    root = str(getattr(services, "workspace_base", "") or "")
    if root and os.path.islink(root):
        raise WorkspaceReadError("this run's workspace root cannot be a symbolic link")
    if not root or not os.path.isdir(root):
        raise WorkspaceReadError(
            "this run has no workspace directory yet; nothing has been "
            "produced to read")
    listing = _listing(root)
    path = str((arguments or {}).get("path") or "").strip()
    if not path:
        return {"record_type": WORKSPACE_READ_RECORD_TYPE,
                "workspace_root": root,
                "produced_files": listing,
                "read": None,
                "note": ("these are the files this run has produced; request "
                         "one by path to read its numbered lines")}
    known = {item["path"] for item in listing}
    resolved = _within(root, path)
    relative = os.path.relpath(resolved, os.path.realpath(root))
    if not os.path.isfile(resolved):
        raise WorkspaceReadError(
            f"{path!r} is not a file this run has produced; the produced "
            f"files are {sorted(known)[:40]}")
    allowance = model_evidence_bytes(services)
    budget = max(2000, allowance // _FILE_SHARE) if allowance > 0 else 20000
    with open(resolved, "rb") as handle:
        raw = handle.read(budget + 1)
    truncated = len(raw) > budget
    text = raw[:budget].decode("utf-8", errors="replace")
    lines = text.splitlines()
    first = int((arguments or {}).get("first_line") or 1)
    first = max(1, first)
    numbered = [{"line": first + index, "text": value}
                for index, value in enumerate(lines[first - 1:])]
    return {
        "record_type": WORKSPACE_READ_RECORD_TYPE,
        "workspace_root": root,
        "produced_files": listing,
        "read": {
            "path": relative,
            "byte_count": os.path.getsize(resolved),
            "bytes_shown": len(raw[:budget]),
            "truncated": truncated,
            "first_line": first,
            "lines": numbered,
        },
        "note": ("lines are numbered as the interpreter numbers them, so a "
                 "reported line number can be looked up directly"),
    }


def self_test() -> dict:
    """Prove the read, the numbering, the listing, and the boundary."""
    import tempfile

    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    class Services:
        def __init__(self, workspace):
            self.workspace_base = workspace
            self.request = type("R", (), {"context_budget": None})()

    with tempfile.TemporaryDirectory(prefix="loop-engine-wsread-") as root:
        os.makedirs(os.path.join(root, "src"), exist_ok=True)
        broken = os.path.join(root, "src", "pipeline.py")
        with open(broken, "w", encoding="utf-8") as handle:
            handle.write("import os\n" * 4 + 'text = "unterminated\n')
        services = Services(root)

        listing = workspace_read_operation({}, services)
        check("with_no_path_it_states_what_the_run_produced",
              [item["path"] for item in listing["produced_files"]]
              == [os.path.join("src", "pipeline.py")]
              and listing["read"] is None,
              str(listing["produced_files"]))

        value = workspace_read_operation({"path": "src/pipeline.py"}, services)
        lines = value["read"]["lines"]
        check("a_produced_file_reads_back_with_interpreter_line_numbers",
              lines[0] == {"line": 1, "text": "import os"}
              and lines[4]["line"] == 5
              and lines[4]["text"] == 'text = "unterminated',
              str(lines[-1]))

        offset = workspace_read_operation(
            {"path": "src/pipeline.py", "first_line": 5}, services)
        check("a_reported_line_number_can_be_asked_for_directly",
              offset["read"]["lines"][0]["line"] == 5
              and offset["read"]["lines"][0]["text"] == 'text = "unterminated',
              str(offset["read"]["lines"][:1]))

        # The boundary. A generated file is the run's own output; a supplied
        # input is not, and stays core.source.inspect's to admit.
        escapes = 0
        for attempt in ("../outside.txt", "/etc/passwd",
                        "src/../../outside.txt"):
            try:
                workspace_read_operation({"path": attempt}, services)
            except WorkspaceReadError as exc:
                if "outside this run's workspace" in str(exc):
                    escapes += 1
        check("a_path_outside_the_workspace_is_refused_by_name",
              escapes == 3, f"{escapes}/3 refused")

        named = ""
        try:
            workspace_read_operation({"path": "src/absent.py"}, services)
        except WorkspaceReadError as exc:
            named = str(exc)
        check("an_absent_file_names_what_was_produced_instead",
              "pipeline.py" in named and "not a file this run has produced"
              in named, named[:160])

        empty = Services(os.path.join(root, "nothing-here"))
        stated = ""
        try:
            workspace_read_operation({}, empty)
        except WorkspaceReadError as exc:
            stated = str(exc)
        check("a_run_with_no_workspace_says_so_rather_than_failing_opaquely",
              "nothing has been produced" in stated, stated[:120])

        with tempfile.TemporaryDirectory(prefix="loop-engine-wsread-outside-") as outside:
            outside_file = os.path.join(outside, "fixture.txt")
            with open(outside_file, "w", encoding="utf-8") as handle:
                handle.write("outside fixture")
            os.symlink(outside_file, os.path.join(root, "outside-link.txt"))
            try:
                workspace_read_operation({"path": "outside-link.txt"}, services)
                refused = False
            except WorkspaceReadError:
                refused = True
            listed = workspace_read_operation({}, services)["produced_files"]
            check("escaped_file_symlink_is_neither_read_nor_stat_listed",
                  refused and all(item["path"] != "outside-link.txt" for item in listed))
            os.symlink(root, os.path.join(outside, "root-link"))
            try:
                workspace_read_operation({}, Services(os.path.join(outside, "root-link")))
                root_refused = False
            except WorkspaceReadError:
                root_refused = True
            check("workspace_root_symlink_is_refused", root_refused)

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "workspace_read_test/v1",
            "tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
