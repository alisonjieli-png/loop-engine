"""Records of the licensed import, each written name/vN and read strictly.

Every record the import writes has an exact type, version and field set, and
each reader refuses another version, an unknown field or a missing field
before anything is built from the record. The shared reading rules and the
provenance records are the library ingestion component's own
(`core/library_ingestion/record_rules.py` and `provenance.py`); this module
adds only the records that component does not have: leads, package
candidates, idea records, refusals, duplicate links, withdrawals, source
state, journal events and the batch report.

The closed vocabularies live here too, so no other module compares a raw
string: the owner's licence allowlist, the package kinds, the stages and the
refusal reasons.
"""
from __future__ import annotations

import re

from loop_engine.core.library_ingestion.record_rules import (
    LibraryRecordError, canonical_digest, digest_value, member, read_record, text_value)

SOURCES_RECORD_TYPE = "licensed_import_sources/v1"
LEAD_RECORD_TYPE = "licensed_import_lead/v1"
CANDIDATE_RECORD_TYPE = "licensed_import_candidate/v1"
IDEA_RECORD_TYPE = "licensed_import_idea/v1"
REFUSAL_RECORD_TYPE = "licensed_import_refusal/v1"
DUPLICATE_RECORD_TYPE = "licensed_import_duplicate/v1"
WITHDRAWAL_RECORD_TYPE = "licensed_import_withdrawal/v1"
SOURCE_STATE_RECORD_TYPE = "licensed_import_source_state/v1"
JOURNAL_RECORD_TYPE = "licensed_import_journal_event/v1"
REPORT_RECORD_TYPE = "licensed_import_batch_report/v1"
SNAPSHOT_RECORD_TYPE = "licensed_import_repository_snapshot/v1"

#: The owner's allowlist of September 24, 2026: only these licences may be copied.
ALLOWED_LICENCES = ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD", "CC0-1.0",
                    "CC-BY-4.0", "Unlicense")

#: What one package is. Each kind is a unit a harness picks up whole.
SKILL = "skill"
INSTRUCTION_FILE = "instruction_file"
RULES = "rules"
SUBAGENT = "subagent"
COMMAND = "command"
HOOK = "hook"
PLUGIN_MANIFEST = "plugin_manifest"
MARKETPLACE = "marketplace"
PROTOCOL_SERVER = "protocol_server_configuration"
CONTRACT_SCHEMA = "contract_schema"
CODE_MODULE = "code_module"
PACKAGE_KINDS = (SKILL, INSTRUCTION_FILE, RULES, SUBAGENT, COMMAND, HOOK, PLUGIN_MANIFEST, MARKETPLACE,
                 PROTOCOL_SERVER, CONTRACT_SCHEMA, CODE_MODULE)

#: The catalogue layer each kind's record is written under: instructions for a model are
#: Context Intelligence, and anything a harness runs or connects to is Code Intelligence.
CONTEXT_LAYER, CODE_LAYER = "context", "code"
KIND_LAYERS = {SKILL: CONTEXT_LAYER, INSTRUCTION_FILE: CONTEXT_LAYER, RULES: CONTEXT_LAYER,
               SUBAGENT: CONTEXT_LAYER, COMMAND: CONTEXT_LAYER, HOOK: CODE_LAYER, PLUGIN_MANIFEST: CODE_LAYER,
               MARKETPLACE: CODE_LAYER, PROTOCOL_SERVER: CODE_LAYER, CONTRACT_SCHEMA: CODE_LAYER,
               CODE_MODULE: CODE_LAYER}

#: What a file inside a package came from.
UPSTREAM_FILE, LICENCE_TEXT, ATTRIBUTION_FILE = "upstream", "licence_text", "attribution"
FILE_ORIGINS = (UPSTREAM_FILE, LICENCE_TEXT, ATTRIBUTION_FILE)

#: How the text of a candidate was authored.
IMPORTED_VERBATIM = "imported_verbatim_under_permissive_licence"
WRITTEN_FROM_FACTS = "written_from_registry_facts"
AUTHORING = (IMPORTED_VERBATIM, WRITTEN_FROM_FACTS)

#: Lifecycle values of the store records; nothing here is ever approved.
CANDIDATE_LIFECYCLE, IDEA_LIFECYCLE, WITHDRAWN_LIFECYCLE = "candidate", "idea", "withdrawn"
WITHDRAWAL_LIFECYCLE, SOURCE_STATE_LIFECYCLE = "withdrawal", "source_state"

#: What happened to one repository in a round.
READ_STATE, REFUSED_STATE, EMPTY_STATE, IDEA_STATE, UNCHANGED_STATE, NOT_READ_STATE = (
    "read", "refused", "empty", "idea", "unchanged", "not_read")

#: Stages, each with the closed list of reasons a refusal at that stage may give.
DISCOVERY, REPOSITORY, PACKAGE, LICENCE, CHECK, DUPLICATE = (
    "discovery", "repository", "package", "licence", "check", "duplicate")
REASONS = {
    DISCOVERY: ("source_unavailable", "query_failed", "ceiling_reached", "feed_entry_not_on_github",
                "lead_not_a_harness_path", "ambiguous_seed_name", "seed_name_not_found"),
    REPOSITORY: ("repository_unavailable", "repository_is_fork", "repository_is_private", "repository_empty",
                 "tree_too_large", "fetch_failed", "blob_fetch_incomplete", "no_harness_files",
                 "repository_declared_excluded"),
    PACKAGE: ("package_path_invalid", "package_too_many_files", "package_too_large", "file_above_fetch_limit",
              "file_bytes_mismatch", "symbolic_link_in_package", "submodule_in_package", "empty_package",
              "primary_file_not_text", "primary_file_too_short", "manifest_not_json"),
    LICENCE: ("licence_prohibits_derivatives", "licence_binds_to_outside_terms",
              "file_level_notice_prohibits_derivatives", "file_level_notice_binds_to_outside_terms"),
    CHECK: ("blocked_by_static_check",),
    DUPLICATE: ("copy_of_restricted_source",),
}
STAGES = tuple(REASONS)

#: What a duplicate link matched on, strongest first.
MATCH_KINDS = ("git_blob", "exact_bytes", "normalized_text", "near_text")
#: Where the matched item lives: this batch, the served catalogue, candidate folders under
#: artifacts, the overnight batch, the September 23 ingestion runs or an earlier import round.
CORPORA = ("batch", "served_catalogue", "artifacts_candidates", "overnight_batch", "ls1_staged",
           "import_store")
#: Why a candidate was withdrawn. History is kept; only the lifecycle changes.
WITHDRAWAL_REASONS = ("upstream_deleted", "licence_changed", "superseded_by_new_version")

_KEY = re.compile(r"[0-9a-f]{24}\Z")
_SLUG = re.compile(r"[^a-z0-9]+")


def refusal(stage: str, reason: str, *, repository: "str | None" = None, revision: "str | None" = None,
            path: "str | None" = None, detail: str = "", source_ids=()) -> dict:
    """One refusal with its stage and a reason from the closed vocabulary; never a body."""
    member(stage, "refusal.stage", STAGES)
    member(reason, "refusal.reason", REASONS[stage])
    return {"record_type": REFUSAL_RECORD_TYPE, "stage": stage, "reason": reason, "repository": repository,
            "revision": revision, "path": path, "detail": detail[:300], "source_ids": sorted(set(source_ids))}


def read_refusal(value) -> dict:
    record = read_record(value, REFUSAL_RECORD_TYPE,
                         ("stage", "reason", "repository", "revision", "path", "detail", "source_ids"))
    member(record["stage"], "refusal.stage", STAGES)
    member(record["reason"], "refusal.reason", REASONS[record["stage"]])
    return record


def upstream_key(origin: str, repository: str, package_root: str, kind: str) -> str:
    """The stable identity of one upstream package: the same folder of the same repository.

    A new commit changes the version, never the key, so a changed upstream file
    becomes a new version of the same candidate and a deleted one a withdrawal.
    """
    member(kind, "kind", PACKAGE_KINDS)
    return canonical_digest({"origin": origin, "repository": repository.lower(), "root": package_root,
                             "kind": kind})[:24]


def read_upstream_key(value) -> str:
    if type(value) is not str or not _KEY.match(value):
        raise LibraryRecordError("invalid_upstream_key", "an upstream key is 24 lowercase hexadecimal digits")
    return value


def slug(value: str, limit: int = 48) -> str:
    """A short lowercase identifier made from a name, for record identities and titles."""
    return _SLUG.sub("-", str(value).lower()).strip("-")[:limit] or "item"


def candidate_record_id(kind: str, key: str, package_digest: str) -> str:
    """One immutable store record per package version: kind, upstream key and package digest."""
    member(kind, "kind", PACKAGE_KINDS)
    read_upstream_key(key)
    digest_value(package_digest, "package_digest")
    return f"library.import.{kind}.{key}.{package_digest[:16]}"


def idea_record_id(key: str) -> str:
    return f"library.import.idea.{read_upstream_key(key)}"


def withdrawal_record_id(key: str, package_digest: str) -> str:
    digest_value(package_digest, "package_digest")
    return f"library.import.withdrawal.{read_upstream_key(key)}.{package_digest[:16]}"


def source_state_record_id(repository: str) -> str:
    text_value(repository, "repository", limit=140)
    return "library.import.source." + canonical_digest({"repository": repository.lower()})[:24]


def duplicate_link(kept: str, merged: dict, match: str, similarity: float, corpus: str) -> dict:
    """One merged item: what it matched, how and where; the merged item's provenance travels with it."""
    member(match, "duplicate.match", MATCH_KINDS)
    member(corpus, "duplicate.corpus", CORPORA)
    return {"record_type": DUPLICATE_RECORD_TYPE, "kept": kept, "merged": merged, "match": match,
            "similarity": round(float(similarity), 4), "corpus": corpus}
