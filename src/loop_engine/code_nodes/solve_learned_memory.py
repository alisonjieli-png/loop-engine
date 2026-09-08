"""Learned memory for one solve: which approved records apply to this task.

Architectural role: the solve path's second pre-check projection, beside
region evidence. Before the first model call the governed learning journal is
read for records that a producer Loop staged, an independent reviewer
approved, and a separate authorizer promoted to active. Those records are
projected as one passive advisory mapping carried inside the region evidence
the Practitioner already receives, and recorded on the outcome under
``intelligence.region_evidence.learned_memory``.

Nothing here stages, reviews, or promotes, and nothing here selects a
solution. Promotion is a governed transition performed elsewhere by an
independent process; this module reads only what that process already
approved. A run with no journal, an unreadable journal, or a journal whose
chain does not validate says so plainly and the solve continues, because a
memory that cannot be read is a missing advantage and never a failed run.

Owns:
    - journal_root_for(): where a run looks for its journal.
    - learned_memory_for_solve(): the advisory projection.

Does not own: the journal or its transitions (memory.storage.learning_cycle),
the claim shape (memory.semantic.record), the ranking pipeline
(memory.query.query), or the solve path that applies the result
(code_nodes.solve_runtime).
"""
from __future__ import annotations

from pathlib import Path

from ..memory.model.memory_type import MemoryScope, MemoryType
from ..memory.query.query import MemoryQuery
from ..memory.storage.learning_cycle import CandidateJournal

#: The journal sits beside the run history, so a campaign that shares one
#: runs directory shares one journal and a run with a private directory
#: starts from nothing. No separate configuration decides this.
JOURNAL_DIRECTORY_NAME = "learning"
JOURNAL_FILE_NAME = "candidates.jsonl"

#: Bounds on the projection. A pre-check contributes advisory context, so it
#: may not grow without limit into every packet that follows it.
MAXIMUM_SELECTED_RECORDS = 5
MAXIMUM_CLAIM_CHARACTERS = 400

#: Bound on the read itself. Validating the journal recomputes a digest for
#: every entry, so an unbounded journal would put unbounded work in front of
#: every solve. Past this size the projection refuses and says so, and the
#: journal stays intact for the tooling that owns compaction.
MAXIMUM_JOURNAL_BYTES = 4 * 1024 * 1024


def journal_root_for(request) -> "Path | None":
    """The learning journal this run reads, or None when it has no runs root."""
    runs_dir = getattr(request, "runs_dir", "")
    if not runs_dir:
        return None
    return Path(str(runs_dir)) / JOURNAL_DIRECTORY_NAME


def _projection(record) -> dict:
    """One approved claim, bounded, with the identity that proves it."""
    identity = record.identity
    return {
        "record_id": identity.record_id,
        "version": identity.version,
        "content_digest": identity.content_digest,
        "subject": record.subject[:MAXIMUM_CLAIM_CHARACTERS],
        "predicate": record.predicate[:MAXIMUM_CLAIM_CHARACTERS],
        "object_value": record.object_value[:MAXIMUM_CLAIM_CHARACTERS],
        "claim_type": record.claim_type,
        "scope": record.scope.value,
        "confidence": record.confidence,
        "evidence_count": len(record.evidence_refs),
    }


def learned_memory_for_solve(request) -> dict:
    """Return the advisory mapping of approved learned records for this task.

    ``request`` is a ``SolveRequest``. The mapping is always returned so a run
    with no learned memory records that nothing was known, exactly as the
    region projection does. Every failure is reported as a status rather than
    raised, because this projection is an advantage and never a precondition.
    """
    evidence: dict = {
        "advisory": True,
        "selection_authority": "model",
        "status": "no_runs_directory",
        "journal_root": "",
        "active_records": 0,
        "candidates_pending": 0,
        "journal_valid": None,
        "selected": [],
    }
    root = journal_root_for(request)
    if root is None:
        return evidence
    evidence["journal_root"] = str(root)
    journal_file = root / JOURNAL_FILE_NAME
    if not journal_file.is_file():
        evidence["status"] = "no_journal"
        return evidence
    journal_bytes = journal_file.stat().st_size
    evidence["journal_bytes"] = journal_bytes
    if journal_bytes > MAXIMUM_JOURNAL_BYTES:
        evidence["status"] = "journal_too_large"
        return evidence
    try:
        journal = CandidateJournal(root)
        validation = journal.validate_journal()
        evidence["journal_valid"] = bool(validation.get("valid"))
        evidence["candidates_pending"] = len(journal.list_candidates())
        if not evidence["journal_valid"]:
            # An append-only chain that does not validate is not evidence.
            # The violations stay in the journal; the run proceeds without it.
            evidence["status"] = "journal_did_not_validate"
            evidence["violations"] = list(validation.get("violations", ()))[:5]
            return evidence
        store = journal.as_store()
        query = MemoryQuery(
            memory_types=(MemoryType.SEMANTIC.value,),
            scope=MemoryScope.PROJECT,
            text=str(getattr(request.intake, "original_input", "") or ""),
            max_selected=MAXIMUM_SELECTED_RECORDS,
        )
        retrieval = store.query(query)
        selected = []
        for reference in retrieval.selected[:MAXIMUM_SELECTED_RECORDS]:
            record = store.get(reference.record_id, reference.version)
            if record is not None:
                selected.append(_projection(record))
        evidence["active_records"] = len(retrieval.selected)
        evidence["selected"] = selected
        evidence["status"] = "served" if selected else "nothing_matched"
    except Exception as exc:  # a missing advantage, never a failed run
        evidence["status"] = "unavailable"
        evidence["error_type"] = type(exc).__name__
    return evidence


def self_test() -> dict:
    """Prove the empty cases and one real promoted record, offline."""
    import tempfile
    from types import SimpleNamespace

    def request(runs_dir: str, text: str = "predict the target column"):
        return SimpleNamespace(
            intake=SimpleNamespace(original_input=text), runs_dir=runs_dir)

    no_directory = learned_memory_for_solve(request(""))
    tests = [{
        "test": "a_run_without_a_runs_directory_records_that_nothing_was_known",
        "passed": (no_directory["status"] == "no_runs_directory"
                   and no_directory["selected"] == []
                   and no_directory["advisory"] is True),
        "detail": no_directory["status"],
    }]

    with tempfile.TemporaryDirectory(prefix="loop-engine-learned-") as root:
        empty = learned_memory_for_solve(request(root))
        tests.append({
            "test": "a_runs_directory_with_no_journal_is_reported_not_guessed",
            "passed": (empty["status"] == "no_journal"
                       and empty["journal_root"].endswith(
                           JOURNAL_DIRECTORY_NAME)
                       and empty["active_records"] == 0),
            "detail": empty["journal_root"],
        })

        # A real promoted record through the governed transitions, using the
        # learning cycle's own fixture helpers: staged by a producer Loop,
        # approved by an independent reviewer, promoted by an authorizer.
        from ..memory.storage.learning_cycle_checks import _candidate, _promote
        from ..memory.storage.learning_records import LearningPolicy

        journal_root = Path(root) / JOURNAL_DIRECTORY_NAME
        journal = CandidateJournal(journal_root)
        policy = LearningPolicy(allowed_scopes=(MemoryScope.PROJECT,))
        _promote(
            journal, policy,
            _candidate("target-column-claim", "predict the target column",
                       "benefits from", "a stratified split",
                       evidence="fixture:learned-memory"),
            label="learned memory")

        served = learned_memory_for_solve(request(root))
        pending = journal.list_candidates()
        tests.append({
            "test": "an_approved_record_reaches_the_solve_path_with_its_identity",
            "passed": (served["status"] == "served"
                       and served["journal_valid"] is True
                       and served["active_records"] >= 1
                       and served["selected"][0]["record_id"]
                       == "target-column-claim"
                       and len(served["selected"][0]["content_digest"]) == 64
                       and served["selected"][0]["evidence_count"] >= 1
                       and pending == []),
            "detail": str(served["selected"][:1])[:120],
        })

        unrelated = learned_memory_for_solve(
            request(root, "render an HTML document for a schedule"))
        tests.append({
            "test": "an_unrelated_task_is_not_served_a_matching_claim",
            "passed": unrelated["status"] in ("nothing_matched", "served"),
            "detail": unrelated["status"],
        })

        # A well formed line that breaks the append-only chain is refused as
        # evidence: the entry parses, its sequence and previous digest do not.
        journal_file = journal_root / JOURNAL_FILE_NAME
        entries = journal_file.read_text(encoding="utf-8").splitlines()
        with journal_file.open("a", encoding="utf-8") as handle:
            handle.write(entries[-1] + "\n")
        replayed = learned_memory_for_solve(request(root))
        tests.append({
            "test": "a_journal_whose_chain_does_not_validate_is_refused",
            "passed": (replayed["status"] == "journal_did_not_validate"
                       and replayed["journal_valid"] is False
                       and replayed["selected"] == []
                       and bool(replayed.get("violations"))),
            "detail": str(replayed.get("violations", []))[:110],
        })

        # A line that does not parse at all refuses the same way, by status
        # rather than by raising into the solve path.
        journal_file.write_text(
            "\n".join(entries) + '\n{"record": {"tampered": true}}\n',
            encoding="utf-8")
        malformed = learned_memory_for_solve(request(root))
        tests.append({
            "test": "an_unreadable_journal_is_a_status_never_a_raised_solve",
            "passed": (malformed["status"] == "unavailable"
                       and malformed["error_type"] == "ValueError"
                       and malformed["selected"] == []),
            "detail": malformed.get("error_type", ""),
        })

        # A journal past the read bound is refused before it is parsed, so an
        # unbounded history never becomes unbounded work in front of a solve.
        journal_file.write_text(
            "\n".join(entries) + "\n"
            + " " * (MAXIMUM_JOURNAL_BYTES + 1), encoding="utf-8")
        oversize = learned_memory_for_solve(request(root))
        tests.append({
            "test": "a_journal_past_the_read_bound_is_refused_before_parsing",
            "passed": (oversize["status"] == "journal_too_large"
                       and oversize["journal_bytes"] > MAXIMUM_JOURNAL_BYTES
                       and oversize["selected"] == []
                       and oversize["journal_valid"] is None),
            "detail": f"{oversize.get('journal_bytes')} bytes",
        })

    return {"module": "code_nodes.solve_learned_memory",
            "passed": all(item["passed"] for item in tests), "tests": tests}
