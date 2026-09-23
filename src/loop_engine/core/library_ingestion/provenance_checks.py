"""Known-wrong checks for the outside provenance record and its reader.

Each check builds a record that is wrong in exactly one way and requires the
reader to refuse it with a stable code: a candidate with no provenance, a
record missing any one required field, another record version, an unknown
field, a branch name instead of a commit, a path that escapes its
repository, verbatim rights without a licence file digest, a registry entry
that claims verbatim rights, and a fetch time that is not an exact UTC time.
A positive control shows a complete record is read unchanged.
"""
from __future__ import annotations

from copy import deepcopy

from .provenance import (
    GITHUB_ORIGIN, LICENCE_EVIDENCE_RECORD_TYPE, OUTLINE_ONLY, PROVENANCE_FIELDS,
    PROVENANCE_RECORD_TYPE, REGISTRY_ORIGIN, VERBATIM, read_licence_evidence,
    read_outside_provenance, require_provenance)
from .record_rules import LibraryRecordError, bytes_digest, git_blob_identity

_BODY = b"---\nname: example-skill\ndescription: Example.\n---\n# Example\n"
_LICENCE = b"MIT licence text used only as a fixture digest\n"


def fixture_evidence(decision: str = VERBATIM, spdx: str = "MIT") -> dict:
    """Licence evidence for a file governed by a root MIT licence file."""
    governing = None if decision != VERBATIM else {
        "path": "LICENSE", "sha256": bytes_digest(_LICENCE), "matched_spdx": spdx, "similarity": 1.0}
    return {"record_type": LICENCE_EVIDENCE_RECORD_TYPE, "spdx_expression": spdx,
            "decision": decision, "reason": "repository_licence_accepted",
            "detector": "fixture", "repository_licence": {
                "path": "LICENSE", "sha256": bytes_digest(_LICENCE), "github_spdx_id": spdx,
                "matched_spdx": spdx, "similarity": 1.0},
            "governing_file": governing,
            "file_level_notices": [{"kind": "licence_file", "path": "LICENSE",
                                    "sha256": bytes_digest(_LICENCE), "value": spdx}]}


def fixture_provenance(**overrides) -> dict:
    """A complete GitHub provenance record; overrides replace single fields."""
    record = {"record_type": PROVENANCE_RECORD_TYPE, "origin": GITHUB_ORIGIN,
              "origin_host": "github.com", "repository": "example-owner/example-skills",
              "immutable_revision": "0123456789abcdef0123456789abcdef01234567",
              "path": "skills/example-skill/SKILL.md", "source_digest": bytes_digest(_BODY),
              "source_size_bytes": len(_BODY), "git_blob_sha": git_blob_identity(_BODY),
              "fetch_digest": bytes_digest(b"response"), "licence_evidence": fixture_evidence(),
              "fetched_at": "2026-09-22T12:00:00Z", "request_digest": bytes_digest(b"request")}
    record.update(overrides)
    return record


def fixture_registry_provenance(**overrides) -> dict:
    record = fixture_provenance(
        origin=REGISTRY_ORIGIN, origin_host="registry.modelcontextprotocol.io",
        repository="io.github.example/weather",
        immutable_revision="version:1.2.0;published:2026-09-01T10:00:00.123456Z",
        path="v0.1/servers/io.github.example%2Fweather/versions/1.2.0", git_blob_sha=None,
        licence_evidence={**fixture_evidence(OUTLINE_ONLY, "MIT"), "decision": "link_only",
                          "reason": "registry_entry_link_mode"})
    record.update(overrides)
    return record


def _code(action) -> str:
    try:
        action()
    except LibraryRecordError as error:
        return error.code
    except Exception as error:  # noqa: BLE001 - a crash is not a typed refusal
        return f"untyped:{type(error).__name__}"
    return ""


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:300]})

    complete = fixture_provenance()
    read = read_outside_provenance(deepcopy(complete))
    check("a_complete_github_provenance_record_is_read_unchanged",
          read.to_record() == complete and read.decision == VERBATIM and read.spdx == "MIT",
          read.digest[:12])

    codes = [_code(lambda: require_provenance({})),
             _code(lambda: require_provenance({"provenance": None})),
             _code(lambda: require_provenance({"provenance": []})),
             _code(lambda: require_provenance("not a candidate"))]
    check("a_candidate_without_provenance_is_refused",
          codes == ["provenance_required"] * 4
          and len(require_provenance({"provenance": [complete, fixture_provenance(
              path="docs/example-skill/SKILL.md")]})) == 2, codes)

    missing = {}
    for field in PROVENANCE_FIELDS:
        broken = deepcopy(complete)
        del broken[field]
        missing[field] = _code(lambda broken=broken: read_outside_provenance(broken))
    check("every_required_provenance_field_is_refused_when_missing",
          set(missing.values()) == {"missing_record_fields"} and len(missing) == 12, missing)

    newer = _code(lambda: read_outside_provenance({**complete, "record_type": "outside_source_provenance/v2"}))
    extra = _code(lambda: read_outside_provenance({**complete, "approved": True}))
    other = _code(lambda: read_outside_provenance({**complete, "record_type": "another_record/v1"}))
    check("another_version_or_an_unknown_field_is_refused",
          (newer, extra, other) == ("unsupported_record_version", "unknown_record_fields",
                                    "unknown_record_type"), (newer, extra, other))

    revisions = [_code(lambda: read_outside_provenance({**complete, "immutable_revision": "main"})),
                 _code(lambda: read_outside_provenance({**complete, "immutable_revision": "0123456"})),
                 _code(lambda: read_outside_provenance({**complete, "git_blob_sha": None}))]
    check("a_github_item_needs_a_forty_character_commit_and_blob_identity",
          revisions == ["invalid_revision"] * 3, revisions)

    paths = [_code(lambda value=value: read_outside_provenance({**complete, "path": value}))
             for value in ("../outside/SKILL.md", "/etc/passwd", "skills//SKILL.md",
                           "skills\\SKILL.md", "")]
    check("a_path_that_escapes_its_repository_is_refused", paths == ["unsafe_path"] * 5, paths)

    no_file = fixture_evidence()
    no_file["governing_file"] = None
    no_licence = fixture_evidence(spdx="NONE")
    disagree = fixture_evidence()
    disagree["governing_file"] = {**disagree["governing_file"], "matched_spdx": "Apache-2.0"}
    verbatim = [_code(lambda value=value: read_licence_evidence(value))
                for value in (no_file, no_licence, disagree)]
    check("verbatim_rights_need_a_named_licence_file_digest",
          verbatim == ["verbatim_without_licence_file", "verbatim_without_licence",
                       "verbatim_licence_disagrees"], verbatim)

    registry = fixture_registry_provenance()
    registry_read = read_outside_provenance(deepcopy(registry))
    claimed = _code(lambda: read_outside_provenance(
        {**registry, "licence_evidence": fixture_evidence()}))
    wrong_host = _code(lambda: read_outside_provenance({**registry, "origin_host": "github.com"}))
    check("a_registry_entry_can_never_claim_verbatim_rights",
          registry_read.decision == "link_only" and claimed == "registry_entry_is_never_verbatim"
          and wrong_host == "origin_host_mismatch", (claimed, wrong_host))

    times = [_code(lambda value=value: read_outside_provenance({**complete, "fetched_at": value}))
             for value in ("2026-09-22", "2026-13-40T00:00:00Z", "2026-09-22T12:00:00+00:00")]
    check("a_fetch_time_that_is_not_exact_utc_is_refused", times == ["invalid_time"] * 3, times)

    notices = fixture_evidence()
    notices["file_level_notices"].append({"kind": "frontmatter_licence",
                                          "path": "skills/example-skill/SKILL.md",
                                          "sha256": bytes_digest(_BODY), "value": "MIT"})
    kept = read_licence_evidence(deepcopy(notices))["file_level_notices"] == notices["file_level_notices"]
    bad_kind = deepcopy(notices)
    bad_kind["file_level_notices"][0]["kind"] = "badge"
    check("licence_evidence_keeps_every_file_level_notice",
          kept and _code(lambda: read_licence_evidence(bad_kind)) == "invalid_vocabulary")

    later = read_outside_provenance({**complete, "fetched_at": "2026-09-23T12:00:00Z"})
    changed = read_outside_provenance({**complete, "source_digest": bytes_digest(b"other bytes")})
    check("the_identity_key_follows_the_bytes_and_not_the_fetch_time",
          later.identity_key() == read.identity_key() and changed.identity_key() != read.identity_key())

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "library_provenance_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
