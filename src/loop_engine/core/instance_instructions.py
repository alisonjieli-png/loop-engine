"""One instruction file per harness instance, in the name every harness reads.

A discrete cognitive or act step Loop node can be performed by a separately
initialized harness process. That process reads an instruction file from the
folder it starts in. The file name has settled on ``AGENTS.md`` across
harnesses, and the ones that read a different name can be given that name as
well, so one composition serves every instance rather than one composition per
harness.

WHAT THE FILE IS FOR
The instance needs to know its assignment, the authority it holds, the
capabilities it may call by name, the folder it may write in, how to report,
and what to refuse. Today an instance is given a goal string and whatever the
harness picks up from the machine it runs on. That is how an instance ends up
reading a repository's own instruction file and adopting rules written for a
different task.

WHAT THE FILE IS NOT FOR
The file describes authority. It never grants it. Every section that names an
effect must name an effect the step already holds, and a section that names
anything else is refused by name before a byte is written. A harness that
reads "you may call the network" in its instruction file still reaches the
network only if the sandbox and the approval say so. The file is written by
the engine from typed fields, never assembled from a model's free text, so a
model cannot compose its own instructions and widen them.

WHY A DIGEST
The composed bytes carry a digest in a trailing marker. The engine refuses to
overwrite a file without that marker, so an instruction file a person wrote by
hand is never silently replaced, and a file the engine wrote can be checked
after the run to show what the instance was actually given. A promise that the
instructions did not change is worth less than a recomputed digest.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from .facets import EFFECTS

#: The file name coding harnesses look for beside the working folder.
STANDARD_FILE = "AGENTS.md"
RECORD_TYPE = "instance_instruction_file/v1"
MARKER_PREFIX = "<!-- composed by Loop Engine "
#: The parts an instruction file may carry. A part outside this list is refused.
SECTION_KINDS = ("assignment", "authority", "capabilities", "working_folder",
                 "reporting", "refusals")
#: Without these two, the file is not an instruction file.
REQUIRED_SECTIONS = ("assignment", "authority")
#: How a second file carries the same instructions.
ALIAS_MODES = ("import", "copy")
#: What verification can say about a file on disk.
VERIFICATION_STATES = ("unchanged", "changed", "absent")
(UNCHANGED, CHANGED, ABSENT) = VERIFICATION_STATES
#: A harness that documents no ceiling for its instruction file.
NO_DOCUMENTED_CEILING = 0


class InstanceInstructionError(ValueError):
    """The composition names an unknown part, or an effect the step does not hold."""


class ForeignInstructionFileError(InstanceInstructionError):
    """A file of this name exists and the engine did not write it."""


@dataclass(frozen=True)
class StyleInstructionFiles:
    """The file names one harness style reads, the standard one first.

    ``max_bytes`` is the ceiling that harness documents for its instruction
    file. Several harnesses stop reading at their ceiling without saying so,
    so a file over the ceiling is refused here rather than silently truncated
    where nobody sees it. A style that documents no ceiling declares zero.
    """

    style: str
    files: tuple[str, ...]
    alias_mode: str = "import"
    max_bytes: int = NO_DOCUMENTED_CEILING

    def __post_init__(self) -> None:
        if not self.style or not self.files or self.files[0] != STANDARD_FILE:
            raise InstanceInstructionError(
                f"a style must name at least {STANDARD_FILE} first")
        if self.alias_mode not in ALIAS_MODES:
            raise InstanceInstructionError(f"alias mode must be one of {ALIAS_MODES}")
        if not isinstance(self.max_bytes, int) or self.max_bytes < NO_DOCUMENTED_CEILING:
            raise InstanceInstructionError("a documented ceiling is a byte count or zero")


#: Styles that read a second name. Data, not a branch: a style absent from this
#: table is given the standard file alone.
#: Read from each harness's own documentation on 2026-09-18. The second name is
#: the file that harness reads when the standard one is not enough on its own:
#: Claude Code reads the standard file only when no CLAUDE.md takes precedence,
#: so its alias imports rather than duplicates; Gemini CLI and Qwen read their
#: own name by default, so their alias carries the whole body.
STYLE_FILES = (
    StyleInstructionFiles("claude_code", (STANDARD_FILE, "CLAUDE.md"), "import"),
    StyleInstructionFiles("gemini_cli", (STANDARD_FILE, "GEMINI.md"), "copy"),
    StyleInstructionFiles("qwen_code", (STANDARD_FILE, "QWEN.md"), "copy"),
    StyleInstructionFiles("codex", (STANDARD_FILE,), "import", 32 * 1024),
    StyleInstructionFiles("windsurf", (STANDARD_FILE,), "import", 12_000),
    StyleInstructionFiles("factory", (STANDARD_FILE,), "import", 80_000),
)

#: How an alias file points at the standard one, by mode.
ALIAS_BODIES = {"import": "@" + STANDARD_FILE + "\n"}


def files_for(style: str) -> StyleInstructionFiles:
    """The files one style reads. An unlisted style reads the standard file."""
    for entry in STYLE_FILES:
        if entry.style == style:
            return entry
    return StyleInstructionFiles(style or "unlisted", (STANDARD_FILE,))


@dataclass(frozen=True)
class InstructionSection:
    """One part of the file, with the effects its text names."""

    kind: str
    heading: str
    lines: tuple[str, ...] = ()
    declares_effects: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in SECTION_KINDS:
            raise InstanceInstructionError(
                f"{self.kind!r} is not one of {SECTION_KINDS}")
        if not self.heading.strip():
            raise InstanceInstructionError("a section needs a heading")
        unknown = [effect for effect in self.declares_effects if effect not in EFFECTS]
        if unknown:
            raise InstanceInstructionError(
                f"{unknown} is not drawn from the declared effects {EFFECTS}")

    def text(self) -> str:
        body = "\n".join(self.lines)
        return f"## {self.heading}\n\n{body}\n" if body else f"## {self.heading}\n"


@dataclass(frozen=True)
class InstructionFile:
    """The composed instructions, their digest, and what they declare."""

    style: str
    files: tuple[str, ...]
    alias_mode: str
    body: str
    effects: tuple[str, ...]
    section_kinds: tuple[str, ...]
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "digest",
                           hashlib.sha256(self.body.encode("utf-8")).hexdigest())

    def text(self) -> str:
        """The bytes written to disk: the body and the marker that carries the digest."""
        return f"{self.body}\n{MARKER_PREFIX}{RECORD_TYPE} digest {self.digest} -->\n"

    def record(self) -> dict:
        """What a run keeps: digests and counts, never the instructions themselves."""
        return {"record_type": RECORD_TYPE, "style": self.style, "files": list(self.files),
                "alias_mode": self.alias_mode, "digest": self.digest,
                "bytes": len(self.body.encode("utf-8")),
                "section_kinds": list(self.section_kinds),
                "declared_effects": list(self.effects)}


def _secret_shaped(text: str) -> str:
    """The first secret pattern the text matches, or an empty string."""
    import re
    from .model_call_records import default_secret_patterns
    for pattern in default_secret_patterns():
        if re.search(pattern, text):
            return pattern
    return ""


def compose(sections, *, authority_effects=(), style: str = "",
            title: str = "Assignment instructions") -> InstructionFile:
    """Compose the file, refusing any effect the step does not already hold.

    ``authority_effects`` is what the step holds. A section that names
    something outside it is refused with both names in the message, because a
    file that describes authority the instance does not have is a file that
    teaches the instance to try.
    """
    sections = tuple(sections)
    if not sections:
        raise InstanceInstructionError("an instruction file needs at least one section")
    held = tuple(authority_effects)
    unknown_authority = [effect for effect in held if effect not in EFFECTS]
    if unknown_authority:
        raise InstanceInstructionError(
            f"the authority names {unknown_authority}, outside the declared effects {EFFECTS}")
    kinds = tuple(section.kind for section in sections)
    missing = [kind for kind in REQUIRED_SECTIONS if kind not in kinds]
    if missing:
        raise InstanceInstructionError(
            f"an instruction file needs its {' and '.join(missing)} section")
    declared: list = []
    for section in sections:
        for effect in section.declares_effects:
            if effect not in held:
                raise InstanceInstructionError(
                    f"the {section.kind!r} section names the effect {effect!r}, which this step "
                    f"does not hold; the step holds {list(held)}. An instruction file describes "
                    "authority and never grants it")
            if effect not in declared:
                declared.append(effect)
    body = f"# {title}\n\n" + "\n".join(section.text() for section in sections)
    found = _secret_shaped(body)
    if found:
        raise InstanceInstructionError(
            "the composed instructions match a secret pattern, so they are not written; "
            "an instruction file never carries a key")
    entry = files_for(style)
    size = len(body.encode("utf-8"))
    if entry.max_bytes and size > entry.max_bytes:
        raise InstanceInstructionError(
            f"the instructions are {size} bytes and {entry.style} documents a ceiling of "
            f"{entry.max_bytes}; that harness stops reading at its ceiling without saying so, "
            "so shorten the instructions or move the detail behind a reference")
    return InstructionFile(entry.style, entry.files, entry.alias_mode, body,
                           tuple(declared), kinds)


def _confined(root: Path, name: str) -> Path:
    """The file inside the folder, refusing traversal and a symlink that leaves it."""
    if "/" in name or "\\" in name or name in ("", ".", ".."):
        raise InstanceInstructionError(f"{name!r} is not a plain file name")
    resolved_root = root.resolve()
    target = (resolved_root / name)
    if target.is_symlink():
        raise ForeignInstructionFileError(
            f"{name} is a link; the engine does not write through a link")
    if resolved_root not in target.resolve().parents:
        raise InstanceInstructionError(f"{name} resolves outside the instance folder")
    return target


def _engine_written(path: Path) -> bool:
    try:
        return MARKER_PREFIX in path.read_text("utf-8")
    except (OSError, UnicodeDecodeError):
        return False


def write(composed: InstructionFile, working_folder) -> dict:
    """Write the instruction files into one instance folder and report what was written."""
    root = Path(working_folder)
    if not root.is_dir():
        raise InstanceInstructionError(
            f"the instance folder {root} does not exist, so no instructions are written")
    standard, *aliases = composed.files
    written = []
    for name in composed.files:
        target = _confined(root, name)
        if target.exists() and not _engine_written(target):
            raise ForeignInstructionFileError(
                f"{name} exists and the engine did not write it, so it is left alone; "
                "compose into a folder the engine owns")
    for name in composed.files:
        target = _confined(root, name)
        if name == standard:
            payload = composed.text()
        elif composed.alias_mode in ALIAS_BODIES:
            payload = (ALIAS_BODIES[composed.alias_mode]
                       + f"\n{MARKER_PREFIX}{RECORD_TYPE} digest {composed.digest} -->\n")
        else:
            payload = composed.text()
        target.write_text(payload, "utf-8")
        written.append(name)
    record = composed.record()
    record["written"] = written
    record["folder"] = str(root)
    return record


def verify(composed: InstructionFile, working_folder) -> dict:
    """Recompute the digest of what is on disk, for every file that was written."""
    root = Path(working_folder)
    results = {}
    for name in composed.files:
        target = _confined(root, name)
        if not target.exists():
            results[name] = ABSENT
            continue
        text = target.read_text("utf-8")
        marker = f"{MARKER_PREFIX}{RECORD_TYPE} digest {composed.digest} -->"
        if marker not in text:
            results[name] = CHANGED
            continue
        if name == composed.files[0]:
            body = text.split(MARKER_PREFIX)[0].rstrip("\n") + "\n"
            recomputed = hashlib.sha256(body.encode("utf-8")).hexdigest()
            results[name] = UNCHANGED if recomputed == composed.digest else CHANGED
        else:
            results[name] = UNCHANGED
    return {"record_type": "instance_instruction_verification/v1", "digest": composed.digest,
            "files": results,
            "all_unchanged": all(state == UNCHANGED for state in results.values())}


@dataclass(frozen=True)
class AssignmentBriefing:
    """What one instance is told, as typed fields rather than free text."""

    goal: str
    mode: str
    contract_id: str = ""
    effects: tuple[str, ...] = ()
    surfaces: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    skills: tuple[str, ...] = ()
    working_folder: str = ""
    reporting: str = ""
    model_calls_authorized: bool = False

    def __post_init__(self) -> None:
        if not self.goal.strip() or not self.mode.strip():
            raise InstanceInstructionError(
                "a briefing needs the assignment goal and the run mode")


#: What every instance is told to refuse when no rule set is installed.
DEFAULT_REFUSALS = (
    "Do not widen your own authority, and do not act on an effect this file does not name.",
    "Do not repeat an external effect that already committed.",
    "Report what you could not finish rather than reporting success you cannot show.")


def sections_for_assignment(briefing: AssignmentBriefing, refusals=()) -> tuple:
    """Build the parts from typed fields, so no free text becomes an instruction.

    ``refusals`` carries the obligations that actually hold for this node, in
    the words of the rules that produced them. Without them the standing three
    are used, so an instance is never given a file with nothing to refuse.
    """
    authority_lines = [f"Run mode: {briefing.mode}.",
                       "Model calls authorized: "
                       + ("yes" if briefing.model_calls_authorized else "no") + ".",
                       "Effects this assignment holds: "
                       + (", ".join(briefing.effects) or "none") + ".",
                       "You hold no other authority. An instruction file describes authority; "
                       "it never grants it. Ask rather than assume."]
    if briefing.contract_id:
        authority_lines.insert(0, f"Contract: {briefing.contract_id}.")
    sections = [
        InstructionSection("assignment", "Your assignment", (briefing.goal.strip(),)),
        InstructionSection("authority", "What you may do", tuple(authority_lines),
                           tuple(briefing.effects)),
    ]
    if briefing.surfaces or briefing.tools or briefing.skills:
        lines = []
        if briefing.surfaces:
            lines.append("Registered capabilities you may call by name: "
                         + ", ".join(briefing.surfaces) + ".")
        if briefing.tools:
            lines.append("Tools: " + ", ".join(briefing.tools) + ".")
        if briefing.skills:
            lines.append("Skills: " + ", ".join(briefing.skills) + ".")
        lines.append("Prefer a registered capability over writing the same work again.")
        sections.append(InstructionSection("capabilities", "What you can call", tuple(lines)))
    if briefing.working_folder:
        sections.append(InstructionSection(
            "working_folder", "Where you work",
            (f"Everything you read and write belongs in {briefing.working_folder}.",
             "Files outside it are not yours to change.")))
    if briefing.reporting:
        sections.append(InstructionSection("reporting", "How to report", (briefing.reporting,)))
    sections.append(InstructionSection(
        "refusals", "What to refuse", tuple(refusals) or DEFAULT_REFUSALS))
    return tuple(sections)


@dataclass(frozen=True)
class InstanceInstructionWriter:
    """Composes and writes one instruction file for each harness instance."""

    root: str
    authority_effects: tuple[str, ...] = ()
    surfaces: tuple[str, ...] = ()
    reporting: str = ""

    def write_for(self, request, style: str = "") -> dict:
        """Compose from one typed harness request and write into the instance folder.

        A request without its goal or its run mode is refused by the briefing,
        which owns that rule; this method does not repeat it.
        """
        composed = compose(
            sections_for_assignment(AssignmentBriefing(
                goal=request.goal, mode=request.mode,
                contract_id=getattr(getattr(request, "contract", None), "contract_id", ""),
                effects=tuple(self.authority_effects), surfaces=tuple(self.surfaces),
                tools=tuple(getattr(request, "tool_refs", ()) or ()),
                skills=tuple(getattr(request, "skill_refs", ()) or ()),
                working_folder=self.root, reporting=self.reporting,
                model_calls_authorized=bool(getattr(request, "authorize_model_calls", False)))),
            authority_effects=self.authority_effects,
            style=style or getattr(request, "harness_id", ""))
        return write(composed, self.root)


def self_test() -> dict:
    """Compose, refuse an effect the step lacks, write, verify, and leave a hand file alone."""
    import tempfile
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action, kind=InstanceInstructionError):
        try:
            action()
        except kind:
            return True
        except Exception:  # noqa: BLE001 - a crash is not a typed refusal
            return False
        return False

    parts = sections_for_assignment(AssignmentBriefing(
        goal="Correct the supplier names", mode="non_deterministic",
        contract_id="practitioner.solver/1.0.0", effects=("reads_fs", "writes_fs"),
        surfaces=("text_conformance",), tools=("read",), skills=(),
        working_folder="/workspace/task", reporting="Report through the response contract.",
        model_calls_authorized=True))
    composed = compose(parts, authority_effects=("reads_fs", "writes_fs"),
                       style="claude_code")
    check("the_file_carries_the_assignment_the_authority_and_the_capabilities",
          "Correct the supplier names" in composed.body
          and "reads_fs, writes_fs" in composed.body
          and "text_conformance" in composed.body
          and composed.section_kinds[:2] == ("assignment", "authority")
          and composed.effects == ("reads_fs", "writes_fs"),
          composed.body[:80])
    check("a_section_that_names_an_effect_the_step_does_not_hold_is_refused_by_name",
          refuses(lambda: compose(
              (InstructionSection("assignment", "a", ("do the work",)),
               InstructionSection("authority", "b", ("call out",), ("network",))),
              authority_effects=("reads_fs",)))
          and refuses(lambda: compose(
              (InstructionSection("assignment", "a", ("do the work",)),), authority_effects=()))
          and refuses(lambda: InstructionSection("unknown_kind", "a"))
          and refuses(lambda: InstructionSection("assignment", "a", (), ("teleport",))))
    check("every_style_gets_the_standard_name_and_a_listed_style_gets_its_own_too",
          files_for("claude_code").files == (STANDARD_FILE, "CLAUDE.md")
          and files_for("gemini_cli").alias_mode == "copy"
          and files_for("opencode").files == (STANDARD_FILE,)
          and files_for("").files == (STANDARD_FILE,)
          and files_for("opencode").max_bytes == NO_DOCUMENTED_CEILING,
          str(files_for("claude_code").files))
    long_parts = sections_for_assignment(AssignmentBriefing(
        goal="x" * 20_000, mode="hybrid", effects=("reads_fs",)))
    check("a_file_over_the_ceiling_a_harness_documents_is_refused_rather_than_truncated",
          refuses(lambda: compose(long_parts, authority_effects=("reads_fs",), style="windsurf"))
          and compose(long_parts, authority_effects=("reads_fs",), style="codex").digest
          and compose(long_parts, authority_effects=("reads_fs",), style="opencode").digest
          and refuses(lambda: StyleInstructionFiles("x", (STANDARD_FILE,), "import", -1)),
          str(files_for("windsurf").max_bytes))
    with tempfile.TemporaryDirectory() as folder:
        record = write(composed, folder)
        standard = Path(folder) / STANDARD_FILE
        alias = Path(folder) / "CLAUDE.md"
        check("writing_puts_the_standard_file_and_the_alias_in_the_instance_folder",
              record["written"] == [STANDARD_FILE, "CLAUDE.md"]
              and standard.exists() and alias.exists()
              and alias.read_text("utf-8").startswith("@" + STANDARD_FILE)
              and composed.digest in standard.read_text("utf-8")
              and "digest" in record and record["record_type"] == RECORD_TYPE
              and "Correct the supplier names" not in str(record),
              str(record["written"]))
        before_edit = verify(composed, folder)
        standard.write_text(
            standard.read_text("utf-8").replace("Correct the supplier names", "Do anything"),
            "utf-8")
        after_edit = verify(composed, folder)
        check("verification_recomputes_the_digest_and_sees_an_edit",
              before_edit["all_unchanged"] is True
              and after_edit["files"][STANDARD_FILE] == CHANGED
              and after_edit["all_unchanged"] is False,
              str(after_edit["files"]))
    with tempfile.TemporaryDirectory() as folder:
        (Path(folder) / STANDARD_FILE).write_text("# written by a person\n", "utf-8")
        check("a_file_the_engine_did_not_write_is_left_alone",
              refuses(lambda: write(composed, folder), ForeignInstructionFileError)
              and (Path(folder) / STANDARD_FILE).read_text("utf-8") == "# written by a person\n"
              and not (Path(folder) / "CLAUDE.md").exists(),
              "")
        check("a_name_that_leaves_the_folder_and_a_missing_folder_are_refused",
              refuses(lambda: _confined(Path(folder), "../AGENTS.md"))
              and refuses(lambda: _confined(Path(folder), "sub/AGENTS.md"))
              and refuses(lambda: write(composed, Path(folder) / "absent")))
    with tempfile.TemporaryDirectory() as folder:
        class _Request:
            goal = "Check the address columns"
            mode = "hybrid"
            harness_id = "claude_code"
            tool_refs = ("read", "write")
            skill_refs = ()
            authorize_model_calls = True
            contract = None
        writer = InstanceInstructionWriter(folder, ("reads_fs",), ("address_components",),
                                           "Report through the response contract.")
        written = writer.write_for(_Request())
        body = (Path(folder) / STANDARD_FILE).read_text("utf-8")
        check("one_writer_composes_from_a_typed_request_for_any_instance",
              written["written"] == [STANDARD_FILE, "CLAUDE.md"]
              and "Check the address columns" in body and "address_components" in body
              and "reads_fs" in body and "writes_fs" not in body
              and refuses(lambda: writer.write_for(type("_Bare", (), {"goal": "", "mode": "hybrid",
                                                                     "harness_id": "x"})())),
              body[:60])
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "instance_instructions_test/v1", "tests": tests,
            "passed": passed, "total": len(tests), "all_passed": passed == len(tests)}
