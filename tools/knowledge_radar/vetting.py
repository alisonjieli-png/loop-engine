"""Vet each radar package along separate dimensions. There is no single "vetted" flag.

```text
knowledge_radar_vetting/v1 (one per package)
├── source_identity_checked            every link came from its source's own answer today, or a link
│                                      check of a seed resolved
├── claim_supported_by_cited_evidence  every claim names its source and its dates; no source prose is
│                                      repeated; the data files validate against their schemas
├── implementation_inspected           the existing native prechecks (licence, format, safety, effects,
│                                      secrets, duplicates) passed; not applicable to a brief without code
├── implementation_tested_or_reproduced the package's own tests passed in a sandbox with no network,
│                                      including a known-wrong case they must reject
├── compatibility_tested               native loading in each declared harness; not done in this version
└── publication_approved_for_scope     independent review by another model family; never done here
```

Nothing here approves, stages or publishes. A package that fails a dimension
stays a candidate with its reasons; the independent review path decides.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from .records import STRICT_REVIEW, VETTING_DIMENSIONS, VETTING_RECORD_TYPE

SHINGLE_WORDS = 8
_WORD = re.compile(r"[a-z0-9]+")


def shingles(text: str, size: int = SHINGLE_WORDS) -> set:
    words = _WORD.findall(text.lower())
    return {" ".join(words[index:index + size]) for index in range(0, max(0, len(words) - size + 1))}


def copied_text_findings(package_text: str, guard_texts, allowed_texts) -> list:
    """Eight-word runs a package shares with source prose it must not repeat. Titles and names are allowed."""
    guard = set()
    for text in guard_texts:
        if isinstance(text, str):
            guard |= shingles(text)
    if not guard:
        return []
    allowed = set()
    for text in allowed_texts:
        if isinstance(text, str):
            allowed |= shingles(text)
    shared = (shingles(package_text) & guard) - allowed
    return [("copied_source_text", f"the package repeats {len(shared)} eight-word runs of source prose")] if shared else []


def claim_findings(brief: dict) -> list:
    """Every claim must be dated and linked; a sensitive question's claims must each cite their source."""
    findings = []
    for section in brief["sections"]:
        if not section["checked_at"]:
            findings.append(("section_not_dated", f"{section['title']} has no check time"))
        for claim in section["claims"] + section["carried_claims"]:
            if not claim["url"].startswith("https://") or not claim["observed_at"]:
                findings.append(("claim_without_source", f"{claim['key']} lacks a link or an observation time"))
            if brief["review_requirement"] == STRICT_REVIEW and not claim["source_address"]:
                findings.append(("sensitive_claim_without_source", f"{claim['key']} names no source address"))
    if brief["state"] == "current" and brief["valid_until"] < brief["as_of"]:
        findings.append(("expired_brief_served_as_current", "the brief's valid-until day is before its as-of day"))
    return findings


def schema_findings(document: dict, schema: dict, label: str) -> list:
    try:
        import jsonschema
    except ImportError:
        return [("schema_validator_unavailable", "jsonschema is not installed")]
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda error: list(error.absolute_path))
    return [("schema_invalid", f"{label}: {errors[0].message[:200]}")] if errors else []


def native_prechecks(folder: Path, repository: Path) -> dict:
    """The existing native precheck engines over the prepared catalogue, one outcome per identity."""
    # The checker's own review resources, next to this module; the vetted repository only supplies the sources.
    tools = Path(__file__).resolve().parents[1]
    if str(tools) not in sys.path:
        sys.path.insert(0, str(tools))
    from candidate_review import native, native_profile, prechecks
    from candidate_review.configuration import PanelConfiguration
    base = PanelConfiguration.from_dict(json.loads(
        (tools / "candidate_review/resources/panel.json").read_text(encoding="utf-8")))
    catalogue = native.NativeCatalogue.load(folder, repository)
    population = catalogue.population_bodies()
    configuration = native_profile.configuration(base, population_size=len(population))
    engines = native_profile.engines(configuration)
    criteria, instructions = native_profile.resources()
    outcomes = {}
    for identity in catalogue.identities():
        request = catalogue.request(identity, catalogue.producer_for(identity), criteria, instructions.sha256)
        outcome = prechecks.run_prechecks(request, engines, prechecks.PrecheckContext(configuration.policy, population))
        outcomes[identity] = {"package_digest": request.package.package_digest, **outcome.to_dict()}
    return outcomes


def sandbox_test(package_root: Path, test_path: str, *, timeout_seconds: float = 90.0) -> dict:
    """Run a package's own test with no network, a read-only system and a private temporary folder."""
    from loop_engine.core.library_ingestion.processes import executable, launcher_environment, run_command, sandbox_argv
    bwrap = executable("bwrap")
    python = "/usr/bin/python3"
    if bwrap is None or not Path(python).is_file():
        return {"status": "not_done", "reason": "no bubblewrap sandbox or system Python on this machine"}
    root = Path(package_root).resolve()
    argv = sandbox_argv((python, "-I", "-B", test_path), read_only_paths=(root,), bwrap=bwrap)
    result = run_command(argv, timeout_seconds=timeout_seconds, maximum_output_bytes=256 * 1024,
                         environment=launcher_environment(), cwd=str(root))
    lines = [line for line in result.stdout.decode("utf-8", "replace").splitlines() if line.strip().startswith("{")]
    summary = None
    for line in reversed(lines):
        try:
            summary = json.loads(line)
            break
        except ValueError:
            continue
    known_wrong = summary.get("known_wrong_rejected") if isinstance(summary, dict) else None
    passed = (result.exit_code == 0 and isinstance(summary, dict) and summary.get("failed") == 0
              and isinstance(known_wrong, int) and known_wrong >= 1)
    return {"status": "passed" if passed else "failed", "exit_code": result.exit_code,
            "timed_out": result.timed_out, "summary": summary, "network": "none (bubblewrap --unshare-net)",
            "stderr_tail": result.stderr_tail[-300:] if not passed else ""}


def vetting_record(identity: str, *, source_identity, claims, inspected, tested, compatibility="not_done",
                   publication="not_done", notes=()) -> dict:
    dimensions = {"source_identity_checked": source_identity, "claim_supported_by_cited_evidence": claims,
                  "implementation_inspected": inspected, "implementation_tested_or_reproduced": tested,
                  "compatibility_tested": compatibility, "publication_approved_for_scope": publication}
    if set(dimensions) != set(VETTING_DIMENSIONS):
        raise ValueError("every vetting dimension is recorded")
    return {"record_type": VETTING_RECORD_TYPE, "identity": identity, "dimensions": dimensions,
            "notes": list(notes), "approved": False}
