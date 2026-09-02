"""Model-led orientation over what the run's files are, saved once and stated.

Architectural role: the runtime states which paths exist, what they weigh, and
where each one is materialized; one model call states what each one *is*. Each
half contributes only what it can hold exactly. The reading is a typed record,
admitted against the runtime's own manifest, saved on the run, and projected
into runtime facts, so every later call reads the same stated answer instead of
re-deriving it from whatever happens to be in its prompt.

Why it exists: file roles cannot be settled by a rule this runtime could hold.
Layouts, file names, and column meanings are open, and a live run showed both
halves of the cost. It wrote one path into its generated solution while the
runtime had materialized that file under a different prefix, and it read a
Yes/No column as continuous. There is no honest deterministic helper for
either: naming a file ``train.csv`` does not make it training rows, and the
first competition that names it something else breaks the helper silently. So
this module hardcodes no file name, no layout, and no role vocabulary. The
model names the role in its own words and cites the bytes it read; the runtime
refuses any claim about a path it did not admit.

Owns:
    - SOURCE_ROLE_ORIENTATION_RECORD_TYPE and the record's shape.
    - source_role_schema(): the contract one orientation call must satisfy.
    - validated_source_roles(): admission of one proposed reading.
    - orient_source_roles(): the single bounded call, and its saving.

Does not own: the manifest or the materialization rule
(core.adaptive_practitioner_source), the capability that reads bodies
(core.adaptive_practitioner_capabilities), or the projection into the rendered
packet (core.practitioner_runtime_facts).
"""
from __future__ import annotations

import hashlib
import json

from .adaptive_practitioner_records import (
    AdaptivePractitionerError, ModelStepRequest)
from .adaptive_practitioner_source import (
    inspectable_source_files, project_input_path, source_profile_operation)

SOURCE_ROLE_ORIENTATION_RECORD_TYPE = "source_role_orientation/v1"

#: Paths carried into one orientation call. The digest always covers the whole
#: manifest, so a truncated call can never be mistaken for a whole reading.
ORIENTED_PATH_LIMIT = 64

#: Bounds on model-authored text. They cap prompt growth; they do not
#: constrain what a role may be called.
ROLE_TEXT_LIMIT = 120
EVIDENCE_TEXT_LIMIT = 400

#: Bytes of file evidence carried into one orientation call. The total is the
#: real bound: a wide manifest trims its evidence rather than growing the
#: prompt, so this call costs about the same whether the run was handed three
#: files or sixty.
EVIDENCE_TOTAL_BYTES = 24_000
EVIDENCE_SAMPLE_BYTES = 600


def manifest_digest(paths) -> str:
    """The digest of one exact admitted path set."""
    return hashlib.sha256("\n".join(sorted(paths)).encode("utf-8")).hexdigest()


def source_role_schema() -> str:
    """The exact payload one orientation call must return."""
    return json.dumps({
        "manifest_digest": "the manifest_digest stated in the packet",
        "files": [{
            "path": "one exact admitted path, copied verbatim",
            "role": "what this file is, in your own words",
            "observed_fields": [
                "the field names you actually read, copied from the profile"],
            "evidence": "what those fields and their values establish",
            "confidence": 0.0,
        }],
        "unresolved": [
            "an admitted path whose role the observed bytes do not establish"],
    }, separators=(",", ":"))


def _text(value, limit: int) -> str:
    if not isinstance(value, str) or not value.strip():
        return ""
    return value.strip()[:limit]


def validated_source_roles(
        value: object, admitted: tuple[str, ...], digest: str,
        fields_by_path: "dict[str, tuple[str, ...]] | None" = None) -> dict:
    """Admit one proposed reading, or say exactly why it is not admissible.

    Every check compares the proposal against something the runtime holds
    exactly: the admitted path set and the manifest digest. Nothing here
    judges whether a role is the *right* role, because this runtime has no
    standard to judge it by. It judges only that the claim is about files
    that exist and leaves no admitted file silently unaccounted for.
    """
    if not isinstance(value, dict):
        raise AdaptivePractitionerError(
            "source role orientation must be one JSON object")
    if set(value) != {"manifest_digest", "files", "unresolved"}:
        raise AdaptivePractitionerError(
            "source role orientation fields do not match version 1; expected "
            "manifest_digest, files, unresolved")
    if str(value.get("manifest_digest") or "") != digest:
        raise AdaptivePractitionerError(
            "source role orientation states a different manifest_digest than "
            f"the one the runtime admitted ({digest})")
    rows = value.get("files")
    unresolved_value = value.get("unresolved")
    if not isinstance(rows, list) or not isinstance(unresolved_value, list):
        raise AdaptivePractitionerError(
            "source role orientation files and unresolved must be arrays")
    admitted_set = set(admitted)
    files = []
    claimed: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
                "path", "role", "observed_fields", "evidence", "confidence"}:
            raise AdaptivePractitionerError(
                "each oriented file needs exactly path, role, observed_fields, "
                "evidence, confidence")
        path = str(row.get("path") or "")
        if path not in admitted_set:
            raise AdaptivePractitionerError(
                f"source role orientation names unadmitted path {path!r}; "
                "use only the exact paths the runtime stated")
        if path in claimed:
            raise AdaptivePractitionerError(
                f"source role orientation gives {path!r} more than one role")
        role = _text(row.get("role"), ROLE_TEXT_LIMIT)
        if not role:
            raise AdaptivePractitionerError(
                f"the role for {path!r} is empty; name it or list the path "
                "under unresolved")
        evidence = _text(row.get("evidence"), EVIDENCE_TEXT_LIMIT)
        if not evidence:
            raise AdaptivePractitionerError(
                f"the role for {path!r} cites no observed evidence")
        claimed_fields = row.get("observed_fields")
        if not isinstance(claimed_fields, list) or any(
                not isinstance(item, str) for item in claimed_fields):
            raise AdaptivePractitionerError(
                f"observed_fields for {path!r} must be a list of field names")
        observed_fields = [item.strip() for item in claimed_fields
                           if item.strip()]
        # The runtime holds the field names exactly, so a name it never
        # profiled was not read. This is the whole verification the runtime
        # can honestly perform: not whether the role is right, but whether
        # the reading rests on anything that exists.
        known = (fields_by_path or {}).get(path)
        if known:
            invented = sorted(set(observed_fields) - set(known))
            if invented:
                raise AdaptivePractitionerError(
                    f"observed_fields for {path!r} name {invented}, which the "
                    f"runtime did not profile in that file; its fields are "
                    f"{list(known)[:24]}")
            if not observed_fields:
                raise AdaptivePractitionerError(
                    f"{path!r} has profiled fields but the reading names "
                    "none of them; cite the fields the role rests on")
        try:
            confidence = float(row.get("confidence"))
        except (TypeError, ValueError) as exc:
            raise AdaptivePractitionerError(
                f"the confidence for {path!r} is not a number") from exc
        if not 0.0 <= confidence <= 1.0:
            raise AdaptivePractitionerError(
                f"the confidence for {path!r} is outside 0.0 to 1.0")
        claimed.add(path)
        files.append({"path": path, "role": role,
                      "observed_fields": observed_fields,
                      "evidence": evidence, "confidence": confidence})
    unresolved = []
    for item in unresolved_value:
        path = str(item or "")
        if path not in admitted_set:
            raise AdaptivePractitionerError(
                f"source role orientation lists unadmitted path {path!r} as "
                "unresolved")
        if path in claimed:
            raise AdaptivePractitionerError(
                f"{path!r} is both given a role and listed as unresolved")
        if path not in unresolved:
            unresolved.append(path)
    unaccounted = sorted(admitted_set - claimed - set(unresolved))
    if unaccounted:
        raise AdaptivePractitionerError(
            f"source role orientation accounts for neither a role nor an "
            f"unresolved state for {unaccounted}; an unknown role is a state "
            "to record, not a file to omit")
    return {
        "record_type": SOURCE_ROLE_ORIENTATION_RECORD_TYPE,
        "authority": "model_reading_over_runtime_manifest",
        "manifest_digest": digest,
        "files": sorted(files, key=lambda item: item["path"]),
        "unresolved": sorted(unresolved),
    }


def _evidence_rows(services, admitted) -> tuple[list[dict], dict]:
    """What the runtime holds exactly about each admitted path.

    The evidence is the deterministic profile, not a byte prefix. A prefix
    shows a header and invites the reader to infer a type from the word in
    it; the profile states the field names and, for the rows it sampled, how
    many distinct values each field held, some of them, and whether they all
    parse as numbers. That is the difference between a header that reads like
    a number and a column that is one.
    """
    profiles = source_profile_operation(
        {"paths": list(admitted),
         "maximum_sample_bytes": EVIDENCE_SAMPLE_BYTES},
        services)["profiles"]
    rows = []
    for profile in profiles:
        relative = str(profile.get("path") or "")
        rows.append({
            "path": relative,
            "sandbox_path": project_input_path(relative),
            "byte_count": profile.get("byte_count"),
            "line_count": profile.get("line_count"),
            "structure_kind": profile.get("structure_kind"),
            "fields": list(profile.get("fields") or ()),
            "field_profiles": [dict(item) for item
                               in profile.get("field_profiles") or ()],
            "sample": profile.get("sample"),
        })
    fields_by_path = {row["path"]: tuple(row["fields"]) for row in rows}
    return _within_evidence_budget(rows), fields_by_path


def _within_evidence_budget(rows: list[dict]) -> list[dict]:
    """Trim evidence to the budget in a stated order, never silently.

    Field names survive everything, because they are what the reading is
    checked against. The raw sample goes first, then example values thin,
    then they go. A trimmed row says so.
    """
    def size(value) -> int:
        return len(json.dumps(value, default=str).encode("utf-8"))

    if size(rows) <= EVIDENCE_TOTAL_BYTES:
        return rows
    for row in rows:
        row["sample"] = ""
        row["evidence_trimmed"] = "sample"
    if size(rows) <= EVIDENCE_TOTAL_BYTES:
        return rows
    for row in rows:
        for profile in row["field_profiles"]:
            profile["example_values"] = profile["example_values"][:2]
        row["evidence_trimmed"] = "sample and most example values"
    if size(rows) <= EVIDENCE_TOTAL_BYTES:
        return rows
    for row in rows:
        for profile in row["field_profiles"]:
            profile["example_values"] = []
        row["evidence_trimmed"] = "sample and every example value"
    return rows


def orient_source_roles(services) -> dict | None:
    """Read the manifest once with a model call, admit it, and save it.

    Returns the saved record, or None when this run has no admitted source.
    A saved reading of the same manifest is reused without a call, so the
    cost is one call per distinct manifest rather than one per pass.
    """
    request = services.request
    if not (request.allow_source_materialization_to_model
            and request.source_refs):
        return None
    try:
        files = inspectable_source_files(services)
    except (AdaptivePractitionerError, OSError, ValueError):
        return None
    if not files:
        return None
    all_paths = sorted(relative for relative, _path in files)
    digest = manifest_digest(all_paths)
    saved = getattr(services, "source_roles", None)
    if isinstance(saved, dict) and saved.get("manifest_digest") == digest:
        return saved
    admitted = tuple(all_paths[:ORIENTED_PATH_LIMIT])
    try:
        evidence, fields_by_path = _evidence_rows(services, admitted)
    except (AdaptivePractitionerError, OSError, ValueError):
        return None
    schema = source_role_schema()
    failures: list[dict] = []
    record = None
    for attempt in range(1, 3):
        try:
            value = _read_once(services, attempt, digest, admitted, all_paths,
                               evidence, failures, schema)
        except Exception as exc:  # noqa: BLE001
            # A reading is an improvement on a source inspection that has
            # already succeeded. It never turns that success into a failure,
            # and a transport or budget error is not repaired by asking again.
            services.publish("practitioner.source_roles.unresolved",
                             step="orient", manifest_digest=digest)
            services.diagnostic("source_role_orientation_call_failed", {
                "attempt": attempt, "error": f"{type(exc).__name__}: "
                                             f"{str(exc)[:300]}"})
            return None
        try:
            record = validated_source_roles(value, admitted, digest,
                                            fields_by_path)
            break
        except AdaptivePractitionerError as exc:
            failures.append({"attempt": attempt, "error": str(exc)[:500]})
            services.diagnostic("source_role_orientation_invalid",
                                {"attempt": attempt, "error": str(exc)[:500]})
    if record is None:
        services.publish("practitioner.source_roles.unresolved", step="orient",
                         manifest_digest=digest)
        return None
    services.source_roles = record
    services.publish(
        "practitioner.source_roles.stated", step="orient",
        manifest_digest=digest, oriented=len(record["files"]),
        unresolved=len(record["unresolved"]))
    return record


def _read_once(services, attempt, digest, admitted, all_paths, evidence,
               failures, schema) -> dict:
    """One orientation call. Its transport failures belong to the caller."""
    return services.model(ModelStepRequest(
        "orient",
            ("State what each supplied file is, from the bytes shown and "
             "nothing else."
             if attempt == 1 else
             "Repair the rejected reading of the supplied files."),
            {
                "manifest_digest": digest,
                "admitted_paths": list(admitted),
                "admitted_total": len(all_paths),
                "observed": evidence,
                "orientation_failures": failures,
                "instruction": (
                    "Do not infer a role from a file name, a directory name, "
                    "or a competition convention. Decide from the profile: "
                    "the fields present, the values they actually hold, and "
                    "which fields one file has that another lacks. A field "
                    "whose sampled values are labels is not a number, "
                    "whatever its name suggests. Name each role in your own "
                    "words and cite the observation that establishes it. "
                    "Where the profile does not establish a role, list the "
                    "path under unresolved rather than guessing. "
                    "Name the fields you read in observed_fields, copied from "
                    "the profile; a name the runtime did not profile is "
                    "refused. sandbox_path is where generated code will find "
                    "the file; path is what core.source.inspect admits."),
            }, schema))


#: Tokens that would mean this runtime had decided in advance what a file is
#: called or what role it plays. Prose may name them as the counterexample;
#: executable code may not carry them.
_FORBIDDEN_FILE_KNOWLEDGE = (
    "train", "test.csv", "sample_submission", "submission", "holdout",
    "validation")


def _executable_file_name_knowledge(source: str = "") -> list[str]:
    """Return forbidden tokens reachable from running code in ``source``.

    Defaults to this module. Docstrings are excluded deliberately: the module
    explains the trap it exists to avoid, and naming the trap is not falling
    into it. Every other string constant and every identifier is code, and
    code that knows a file name is the hardcoding this module refuses.
    """
    import ast
    from pathlib import Path

    tree = ast.parse(
        source or Path(__file__).read_text(encoding="utf-8"))
    exempt = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = getattr(node, "body", ())
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                exempt.add(id(body[0].value))
        # The list of forbidden tokens must name them to forbid them.
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name)
                and target.id == "_FORBIDDEN_FILE_KNOWLEDGE"
                for target in node.targets):
            exempt.update(id(inner) for inner in ast.walk(node))
    found = []
    for node in ast.walk(tree):
        texts = []
        if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                and id(node) not in exempt):
            texts.append(node.value)
        elif isinstance(node, ast.Name):
            texts.append(node.id)
        elif isinstance(node, ast.Attribute):
            texts.append(node.attr)
        for text_value in texts:
            lowered = text_value.lower()
            found.extend(token for token in _FORBIDDEN_FILE_KNOWLEDGE
                         if token in lowered and token not in found)
    return found


def self_test() -> dict:
    """Prove the reading is model-authored, admitted, and reused once saved."""
    import tempfile
    from pathlib import Path
    from types import SimpleNamespace

    with tempfile.TemporaryDirectory(prefix="loop-engine-roles-") as root:
        source = Path(root) / "some-competition"
        source.mkdir()
        # The shape that misled a live run: a label column whose header reads
        # like a quantity, beside a file that lacks it.
        (source / "a.csv").write_text(
            "id,Age,Outcome_Score\n1,66,No\n2,38,Yes\n3,26,No\n",
            encoding="utf-8")
        (source / "b.csv").write_text(
            "id,Age\n9,44\n10,51\n", encoding="utf-8")
        calls = []

        def model(step_request):
            calls.append(step_request)
            state = step_request.state
            first = state["observed"][0]
            return {
                "manifest_digest": state["manifest_digest"],
                "files": [{
                    "path": first["path"],
                    "role": "rows carrying the labelled outcome",
                    "observed_fields": ["Outcome_Score"],
                    "evidence": "Outcome_Score holds two label values, "
                                "No and Yes, and never parses as a number",
                    "confidence": 0.9,
                }],
                "unresolved": [row["path"] for row in state["observed"][1:]],
            }

        services = SimpleNamespace(
            request=SimpleNamespace(
                allow_source_materialization_to_model=True,
                source_refs=(str(source),)),
            model=model, source_roles=None,
            publish=lambda *args, **kwargs: None,
            diagnostic=lambda *args, **kwargs: None)
        first_reading = orient_source_roles(services)
        second_reading = orient_source_roles(services)
        paths = sorted(relative for relative, _p
                       in inspectable_source_files(services))
        digest = manifest_digest(paths)
        # Read while the sources still exist, so an empty list cannot make
        # the sandbox-path assertion pass by saying nothing.
        evidence, fields_by_path = _evidence_rows(services, tuple(paths))
        label_profile = next(
            item for row in evidence for item in row["field_profiles"]
            if item["field"] == "Outcome_Score")

        def refuse(payload) -> str:
            try:
                validated_source_roles(payload, tuple(paths), digest,
                                       fields_by_path)
            except AdaptivePractitionerError as exc:
                return str(exc)[:70]
            return ""

        def reading(path, **changes) -> dict:
            row = {"path": path, "role": "r",
                   "observed_fields": ["Age"], "evidence": "e",
                   "confidence": 1.0}
            row.update(changes)
            return {"manifest_digest": digest, "files": [row],
                    "unresolved": [item for item in paths if item != path]}

        rejections = [
            refuse({"manifest_digest": "0" * 64, "files": [],
                    "unresolved": []}),
            refuse(reading("not/admitted.csv")),
            refuse(reading(paths[0], evidence="")),
            refuse({"manifest_digest": digest, "files": [], "unresolved": []}),
            refuse(reading(paths[0], observed_fields=["Nonexistent_Column"])),
            refuse(reading(paths[0], observed_fields=[])),
        ]
        accepted = validated_source_roles(
            reading(paths[0]), tuple(paths), digest, fields_by_path)

    tests = [{
        "test": "the_reading_is_authored_by_a_model_call_not_a_rule",
        "passed": (len(calls) == 1 and first_reading is not None
                   and first_reading["files"][0]["role"]
                   == "rows carrying the labelled outcome"),
        "detail": f"{len(calls)} call(s)",
    }, {
        "test": "a_saved_reading_of_the_same_manifest_costs_no_second_call",
        "passed": len(calls) == 1 and second_reading == first_reading,
        "detail": f"{len(calls)} call(s) after two orientations",
    }, {
        "test": "the_runtime_states_where_generated_code_finds_each_file",
        "passed": (len(evidence) == len(paths) and bool(evidence) and all(
            row["sandbox_path"] == project_input_path(row["path"])
            and row["fields"] for row in evidence)),
        "detail": str([row["sandbox_path"] for row in evidence])[:120],
    }, {
        "test": "a_label_column_is_stated_as_labels_not_left_to_its_header",
        "passed": (label_profile["every_sampled_value_is_a_number"] is False
                   and label_profile["distinct_sampled_values"] == 2
                   and label_profile["example_values"] == ["No", "Yes"]),
        "detail": str(label_profile),
    }, {
        "test": "forged_digest_unadmitted_path_bare_claim_and_gap_refused",
        "passed": all(rejections) and len(rejections) == 6,
        "detail": str(rejections)[:240],
    }, {
        "test": "a_field_the_runtime_never_profiled_is_not_an_observation",
        "passed": ("Nonexistent_Column" in rejections[4]
                   and bool(accepted["files"][0]["observed_fields"])),
        "detail": rejections[4],
    }, {
        "test": "no_role_vocabulary_or_file_name_is_written_into_this_runtime",
        "passed": not _executable_file_name_knowledge(),
        "detail": str(_executable_file_name_knowledge())[:200],
    }, {
        "test": "the_file_name_guard_detects_reintroduced_hardcoding",
        # The token is assembled here rather than written, so proving the
        # guard works does not itself plant the knowledge it forbids.
        "passed": (
            _executable_file_name_knowledge(
                "def role(p):\n return 1 if p == \"" + "trai" + "n.csv"
                + "\" else 0\n")
            and not _executable_file_name_knowledge(
                '"""Prose may name ' + "trai" + "n.csv" + '."""\n')),
        "detail": "a name-matching helper is caught; prose is not",
    }]
    return {"module": "core.source_role_orientation",
            "passed": all(item["passed"] for item in tests), "tests": tests}
