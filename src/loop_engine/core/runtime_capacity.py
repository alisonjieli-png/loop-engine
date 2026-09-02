"""What this machine and this run can actually do, measured rather than declared.

Architectural role: the one place a limit comes from. Nothing in the
solutioning path may declare how many bytes, paths, or rows it will tolerate;
it asks here, and what comes back is derived from something real — memory this
machine reports, disk this filesystem reports, the byte allowance this run's
own context budget already declares, or the size of the data actually present.
Every answer carries the measurement it came from, so a refusal can quote the
number that caused it instead of asserting a rule.

Why it exists: a declared limit is a ceiling on which tasks the system can ever
solve, chosen by someone who had not seen the task. The generated-project
workspace capped every file at a flat sixteen megabytes; a real competition's
training rows are forty-four, so the run could place its submission template
and nothing else, and no amount of model reasoning could reach a result. The
first repair raised the number, which is the same defect one order of magnitude
further out and fails identically on the next larger dataset. A limit that is
measured moves with the machine and the task. A limit that is declared waits
for someone to hit it.

The distinction this module keeps: bounds that exist because the hardware or
the model genuinely cannot go further are physical, and stating them exactly is
honest. Bounds that exist because a number was typed into a source file are
guesses about the future, and they are refused here.

Owns:
    - measured_memory_bytes(), measured_disk_bytes(): the raw measurements.
    - supplied_input_ceiling(): the largest single input this machine can
      materialize, with the basis for the figure.
    - model_evidence_bytes(): what one model call may carry, from the run's
      own declared context budget rather than a second copy of it.
    - paths_within_allowance(): how many exact paths fit, by their real length.
    - converged(): when a sample has stopped teaching and may stop growing.

Does not own: the context budget policy (core.context_budget), what is done
with any allowance, or any decision about the task.
"""
from __future__ import annotations

import os
import shutil

#: How many copies of one supplied input the materialization path holds at
#: once: the bytes read from the source, and the bytes carried on the input
#: artifact while the workspace write is planned and approved. This is a fact
#: about the current code path, not a safety guess, and it drops to one if
#: that path ever digests and writes as a stream.
SUPPLIED_INPUT_COPIES_HELD = 2


def measured_memory_bytes() -> tuple[int, str]:
    """Memory available to this process now, and how it was measured."""
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024, "/proc/meminfo MemAvailable"
    except (OSError, ValueError, IndexError):
        pass
    try:
        pages = os.sysconf("SC_AVPHYS_PAGES")
        size = os.sysconf("SC_PAGE_SIZE")
        if pages > 0 and size > 0:
            return pages * size, "sysconf SC_AVPHYS_PAGES"
    except (OSError, ValueError, AttributeError):
        pass
    return 0, "unmeasured"


def measured_disk_bytes(path: "str | os.PathLike") -> tuple[int, str]:
    """Free space on the filesystem holding ``path``, and how it was measured."""
    probe = os.fspath(path)
    while probe and not os.path.exists(probe):
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    try:
        return shutil.disk_usage(probe or "/").free, f"disk_usage({probe or '/'})"
    except OSError:
        return 0, "unmeasured"


def supplied_input_ceiling(workspace_root: "str | os.PathLike | None" = None,
                           ) -> dict:
    """The largest single input this machine can materialize, and why.

    Derived, never declared: memory bounds it because the path reads a whole
    file to digest it, and disk bounds it because the same bytes are written
    into the workspace. When neither can be measured the ceiling is absent
    rather than invented, because a number guessed here is exactly the failure
    this module exists to remove.
    """
    memory, memory_basis = measured_memory_bytes()
    disk, disk_basis = measured_disk_bytes(
        workspace_root if workspace_root is not None else os.getcwd())
    bounds = []
    if memory > 0:
        bounds.append(("memory", memory // SUPPLIED_INPUT_COPIES_HELD,
                       f"{memory_basis} / {SUPPLIED_INPUT_COPIES_HELD} copies "
                       "held while materializing"))
    if disk > 0:
        bounds.append(("disk", disk, disk_basis))
    if not bounds:
        return {"bytes": None, "basis": [],
                "note": ("neither memory nor disk could be measured, so no "
                         "ceiling is asserted; a guessed number here would be "
                         "the defect this module removes")}
    name, value, basis = min(bounds, key=lambda item: item[1])
    return {
        "bytes": value,
        "binding_constraint": name,
        "basis": [{"constraint": item[0], "bytes": item[1],
                   "measurement": item[2]} for item in bounds],
        "note": ("measured for this machine now; it moves with the machine "
                 "rather than waiting for a larger task to hit it"),
    }


def model_evidence_bytes(services) -> int:
    """Bytes one model call may carry, from the run's own declared budget.

    The run already states how many bytes a heavy list may spend on its way
    into a packet. Evidence assembled for a model call asks that policy rather
    than carrying a second copy of the same number, so raising one raises both
    and they cannot disagree.
    """
    budget = getattr(getattr(services, "request", None), "context_budget", None)
    allowance = getattr(budget, "list_total_bytes", 0)
    return int(allowance) if isinstance(allowance, int) and allowance > 0 else 0


def paths_within_allowance(paths, byte_allowance: int) -> int:
    """How many of these exact paths fit the allowance, by their real length.

    A path count is a guess about how long paths are. Measuring them removes
    the guess: sixty short paths and six very long ones cost the same, and
    both answers are correct for their own manifest.
    """
    if byte_allowance <= 0:
        return len(list(paths))
    spent = 0
    fitted = 0
    for path in paths:
        spent += len(str(path).encode("utf-8")) + 2
        if spent > byte_allowance and fitted:
            break
        fitted += 1
    return fitted


def converged(previous: object, current: object, unchanged_rounds: int,
              rounds_required: int = 2) -> bool:
    """Whether a growing sample has stopped teaching and may stop growing.

    Reading a fixed number of rows assumes how varied the data is. Reading
    until the observation stops changing does not: two labels settle almost
    at once, and a high-cardinality field keeps reading until its byte
    allowance is spent. The caller states what it is watching; this only says
    whether it moved.
    """
    return previous == current and unchanged_rounds + 1 >= rounds_required


#: The path from a task to its data to a model call. A capacity written into
#: any of these decides in advance which tasks the system can solve.
MEASURED_LIMIT_MODULES = (
    "adaptive_practitioner_source.py", "adaptive_practitioner_project.py",
    "source_role_orientation.py", "practitioner_runtime_facts.py",
    "generated_project.py", "runtime_capacity.py",
)

#: Named figures on that path that are not capacities, each with the reason
#: it is not one. Anything else numeric and capacity-shaped is a guess about
#: a task nobody has seen, and the guard refuses it.
NOT_A_CAPACITY = {
    "SUPPLIED_INPUT_COPIES_HELD": "counts copies this code path holds",
    "GENERATED_FILE_BYTE_FLOOR": "a floor beneath a measured value, so it "
                                 "never refuses work the machine can do",
    "MAXIMUM_COMMAND_TIMEOUT_SECONDS": "a safety bound on unbounded execution",
    "ROLE_TEXT_SHARE": "divides a measured allowance",
    "EVIDENCE_TEXT_SHARE": "divides a measured allowance",
    "PROFILE_EXAMPLE_VALUE_LIMIT": "shapes one report row, not how much is read",
    "PROFILE_VALUE_TEXT_LIMIT": "shapes one report row, not how much is read",
    "_SELECTED_CONTENT_BYTE_LIMIT": "fallback only; every production caller "
                                    "passes the run's measured allowance",
}

_CAPACITY_WORDS = ("LIMIT", "BYTES", "CEILING", "MAX", "ROWS", "SIZE", "COUNT")


def _literal_int(node) -> bool:
    """Whether a value is an integer written down, arithmetic included."""
    import ast
    if isinstance(node, ast.Constant):
        return isinstance(node.value, int) and not isinstance(node.value, bool)
    if isinstance(node, ast.BinOp):
        return _literal_int(node.left) and _literal_int(node.right)
    if isinstance(node, ast.UnaryOp):
        return _literal_int(node.operand)
    return False


def declared_capacities(directory: "str | os.PathLike") -> list[str]:
    """Capacity-shaped integers written into the solutioning path."""
    import ast
    from pathlib import Path

    found = []
    for name in MEASURED_LIMIT_MODULES:
        path = Path(directory) / name
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (isinstance(target, ast.Name)
                        and target.id.upper() == target.id
                        and target.id not in NOT_A_CAPACITY
                        and any(word in target.id
                                for word in _CAPACITY_WORDS)
                        and _literal_int(node.value)):
                    found.append(f"{name}:{target.id}")
    return found


def _reintroduced_ceiling_is_caught() -> bool:
    """Prove the guard is not vacuous by planting one and finding it."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory(prefix="loop-engine-capacity-") as room:
        planted = Path(room) / MEASURED_LIMIT_MODULES[0]
        planted.write_text("INPUT_BYTE_CEILING = 512 * 1024 * 1024\n",
                           encoding="utf-8")
        caught = bool(declared_capacities(room))
        planted.write_text("def ceiling(services):\n    return 0\n",
                           encoding="utf-8")
        return caught and not declared_capacities(room)


def self_test() -> dict:
    """Prove every limit here is measured, and that none is written down."""
    import ast
    from pathlib import Path
    from types import SimpleNamespace

    memory, memory_basis = measured_memory_bytes()
    disk, disk_basis = measured_disk_bytes(os.getcwd())
    ceiling = supplied_input_ceiling(os.getcwd())
    evidence = model_evidence_bytes(SimpleNamespace(
        request=SimpleNamespace(
            context_budget=SimpleNamespace(list_total_bytes=31_337))))
    short = paths_within_allowance([f"d/f{i}.csv" for i in range(200)], 100)
    long_paths = paths_within_allowance(["d/" + "x" * 300 + ".csv"] * 200, 100)

    # No literal byte or count threshold may live in this module's own code:
    # it would be the very thing it refuses everywhere else. The copies-held
    # figure is a count of copies the code makes, not a threshold, and the
    # convergence default is a number of rounds, not a capacity.
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    exempt = {"SUPPLIED_INPUT_COPIES_HELD", "rounds_required"}
    declared = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (isinstance(target, ast.Name)
                        and target.id.isupper()
                        and target.id not in exempt
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, int)):
                    declared.append(target.id)

    tests = [{
        "test": "memory_and_disk_are_read_from_the_machine",
        "passed": (memory > 0 and memory_basis != "unmeasured"
                   and disk > 0 and disk_basis != "unmeasured"),
        "detail": f"{memory_basis}={memory}, {disk_basis}={disk}",
    }, {
        "test": "the_input_ceiling_is_derived_and_carries_its_basis",
        "passed": (isinstance(ceiling.get("bytes"), int)
                   and ceiling["bytes"] > 0
                   and len(ceiling.get("basis") or ()) >= 1
                   and ceiling.get("binding_constraint") in
                   {"memory", "disk"}),
        "detail": (f"{ceiling.get('bytes')} bound by "
                   f"{ceiling.get('binding_constraint')}"),
    }, {
        "test": "the_evidence_allowance_comes_from_the_runs_own_budget",
        "passed": evidence == 31_337,
        "detail": f"{evidence} bytes, taken from the run's context budget",
    }, {
        "test": "path_counts_follow_real_path_lengths_not_a_fixed_number",
        "passed": short > long_paths and long_paths >= 1,
        "detail": f"{short} short paths fit where {long_paths} long ones do",
    }, {
        "test": "a_sample_stops_when_it_stops_teaching",
        "passed": (converged({"a"}, {"a"}, 1) is True
                   and converged({"a"}, {"a", "b"}, 5) is False
                   and converged({"a"}, {"a"}, 0) is False),
        "detail": "unchanged twice converges; a new value does not",
    }, {
        "test": "this_module_declares_no_threshold_of_its_own",
        "passed": not declared,
        "detail": str(declared) or "every limit is measured or asked for",
    }, {
        "test": "no_capacity_is_written_into_the_solutioning_path",
        "passed": not declared_capacities(Path(__file__).parent),
        "detail": (str(declared_capacities(Path(__file__).parent))
                   or "every capacity on the path from task to data to model "
                      "call is measured, derived, or reasoned as not one"),
    }, {
        "test": "the_capacity_guard_catches_a_reintroduced_ceiling",
        "passed": _reintroduced_ceiling_is_caught(),
        "detail": "a new byte ceiling in one of these modules fails the gate",
    }]
    return {"module": "core.runtime_capacity",
            "passed": all(item["passed"] for item in tests), "tests": tests}
