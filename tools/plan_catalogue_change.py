"""Report the consequences of one declared catalogue change before it is written or published; read only.

From the base bundle, the update bundles and the `catalogue_reconciliation_request/v1`, the report lists what the
change does to what is already served:

- the items it adds, replaces and withdraws, each with its exact versions;
- the file placements those items add or remove, the blobs that are new and the blobs no item references afterwards;
- the Public Good grants of the given policy files that pin an item version the change replaces or withdraws, that
  serve only after it, or that serve neither before nor after it;
- the judged search queries whose first ten results change when the service's own index and ranking run over the
  base and over the result, and each expected item a query loses from its first ten;
- the changed items whose declared effects hold their bodies until a client's step declares those effects.

The verdict is `conservative_over_judged_queries` when no judged query loses an expected item from its first ten
and no grant pins a version the change replaces or withdraws, otherwise `not_conservative_over_judged_queries`
with the rows that fail. It names what was measured, the stored judged queries and the given policy files, and is
never a claim about every query or every host grant. An additions-only release is expected to pass; a replacement
or withdrawal that orphans a grant or loses a judged result fails and is listed for separate review.

The command exits 0 with the conservative verdict, 1 with the other, and 2 when it refuses its inputs, which
happens for every change the reconciler would refuse.

The report is private operator evidence like the reconciler's `reconciliation.json` and is never uploaded as
material. This tool reads no live service and no body, writes only the report and grants nothing. It is a sibling
of `tools/reconcile_catalogue_bundle.py`, not a mode of it: the reconciler reads the live health view on every run,
while this report depends only on local, digest-bound inputs, so it also runs offline, in a rehearsal, and for a
change that is already live.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from reconcile_catalogue_bundle import REPOSITORY, Changes, bundle_content, compose, load_bundle, read_control
from loop_engine.core.harness_intelligence import HarnessIntelligenceCatalogue
from loop_engine.core.provisioning_server import (
    COMMUNITY_TIER, RUNNABLE_EFFECT, ProvisioningItemBinding, ProvisioningQualification,
)
from loop_engine.core.service_runtime.catalogue_bundle import strict_json, validated_attributes
from loop_engine.core.service_runtime.catalogue_releases import content_digest
from loop_engine.core.service_runtime.catalogue_search import IndexEntry, ReleaseSearchIndex, authorized_hits, entry_text
from loop_engine.core.service_runtime.catalogue_serving import (
    STORE_RESOLVER_ID, STORE_SOURCE, CatalogueView, _approved_resolver,
)
from loop_engine.core.service_runtime.http import DEFAULT_STEP_EFFECTS, effects_to_declare
from loop_engine.core.service_runtime.public_good import _matches
from loop_engine.core.service_runtime.public_good_operator import read_policy_file, read_request
from loop_engine.core.service_runtime.records import ServiceRuntimeError

PLAN_VERSION = "catalogue_change_plan/v1"
JUDGEMENTS_VERSION = "catalogue_search_judgements/v1"
CONSERVATIVE, NOT_CONSERVATIVE = "conservative_over_judged_queries", "not_conservative_over_judged_queries"
#: The results a customer's coding tool reads, and the service's default page of search hits.
TOP = 10
DEFAULT_JUDGEMENTS = REPOSITORY / "examples/30_search_quality/relevance-judgements.json"
MAXIMUM_JUDGEMENTS_BYTES = 8 * 1024 * 1024


def result_items(base, updates, changes):
    """The result's items in identity order, composed exactly as the reconciler composes its rows.

    `compose` applies every refusal of the reconciler, so a change it would refuse has no report either.
    """
    composed = compose(base, updates, changes)
    incoming = {entry.identity: entry for update in updates for entry in update.items}
    current = {entry.identity: entry for entry in base.items}
    items = tuple(incoming[identity] if identity in incoming else current[identity] for identity in sorted(composed.rows))
    if any(entry.version != composed.versions[entry.identity] for entry in items):
        raise ValueError("the composed rows name other versions than the validated bundle items")
    return items


def index_entry(entry, schema):
    """The search entry a store view indexes for one item version: its words, attributes, tier and runnable flag."""
    values = validated_attributes(schema, entry.attributes)
    return IndexEntry(entry.identity, entry_text(entry.item, schema.search_text(values)), values, entry.tier,
                      RUNNABLE_EFFECT in entry.item.declared_effects)


def served_view(items, schema):
    """The view a store serves for these items, built as `store_view` builds it, reading no body.

    Approvals, bindings, item versions, packages and search entries are the ones a published release of exactly
    these items gives, so a grant matches and a query ranks here as it would on the host.
    """
    catalogue, approvals, packages, attributes, bindings, entries = HarnessIntelligenceCatalogue(), {}, {}, {}, {}, []
    for entry in items:
        item, indexed = entry.item, index_entry(entry, schema)
        catalogue.register(item)
        exact = ProvisioningItemBinding.from_item(item)
        approvals[item.identity] = ProvisioningQualification(exact, "approved", "host_attested", entry.approval_ref,
                                                             entry.tier)
        packages[item.identity], attributes[item.identity], bindings[item.identity] = entry.package, indexed.values, exact
        entries.append(indexed)
    index_entries = tuple(entries)
    return CatalogueView(catalogue, _approved_resolver(STORE_RESOLVER_ID, approvals), None, source=STORE_SOURCE,
                         content_digest=content_digest(schema.digest, tuple((e.identity, e.version) for e in items)),
                         schema=schema, packages=packages, attributes=attributes, bindings=bindings,
                         _lazy={"index_builder": lambda: ReleaseSearchIndex(index_entries, schema)},
                         item_versions={entry.identity: entry.version for entry in items})


def first_results(view, query, top=TOP):
    """The identities a search answers first, for an account that receives every listed item.

    The service's own lexical ranking and tier order (verified before community) decide the order; an account that
    receives fewer items sees a subset of these candidates, ranked the same way.
    """
    def everyone(candidates):
        return {identity: {"library_tier": view.qualification_resolver.resolve(view.bindings[identity]).library_tier}
                for identity in candidates}
    hits, _rows = authorized_hits(view, {"query": query, "top_n": top}, everyone)
    return [identity for identity, _score, _modes in hits]


def read_judgements(path):
    """The judged queries, each a query and the identities that should come back for it, and the file's digest."""
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAXIMUM_JUDGEMENTS_BYTES:
        raise ValueError("the judged queries are one bounded regular file")
    raw = path.read_bytes()
    value = strict_json(raw, "judgements_invalid")
    rows = value.get("judgements") if isinstance(value, dict) else None
    if not isinstance(rows, list) or not rows or value.get("record_type") != JUDGEMENTS_VERSION:
        raise ValueError(f"the judged queries are one nonempty {JUDGEMENTS_VERSION} record")
    for row in rows:
        if (not isinstance(row, dict) or not isinstance(row.get("query"), str) or not row["query"].strip()
                or not isinstance(row.get("relevant"), list) or any(not isinstance(name, str) for name in row["relevant"])):
            raise ValueError("each judged query names its text and the identities that should come back")
    return hashlib.sha256(raw).hexdigest(), rows


def read_policies(paths):
    """Each Public Good policy request file, read and parsed by the operator's own bounded reader."""
    policies = []
    for path in paths:
        raw = read_policy_file(Path(path))
        request, grants, _limits = read_request(raw)
        policies.append({"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
                         "expected_release": request["expected_release"], "grants": grants})
    return policies


def _placements(entry):
    return [{"path": file.path, "digest": file.digest, "size_bytes": file.size_bytes, "role": file.role}
            for file in entry.package.files]


def _effects(entry):
    """What one item version declares, and what a step holding only the default effects must still declare."""
    declared = [effect for effect in entry.item.declared_effects if effect != "pure"]
    return {"identity": entry.identity, "version": entry.version, "declared_effects": declared,
            "effects_to_declare": effects_to_declare(declared, DEFAULT_STEP_EFFECTS),
            "community_runnable": entry.tier == COMMUNITY_TIER and RUNNABLE_EFFECT in entry.item.declared_effects}


def _item_row(entry):
    item = entry.item
    return {"identity": entry.identity, "version": entry.version, "tier": entry.tier, "kind": item.kind,
            "license": item.license_name, "size_bytes": item.size_bytes, "files": len(entry.package.files),
            "purpose": item.purpose}


def item_consequences(before, after, changes):
    """Added, replaced and withdrawn items with their versions, the placements and blobs they move, and their effects."""
    added = [after[identity] for identity in changes.additions]
    replaced = [(before[identity], after[identity]) for identity, _version in changes.replacements]
    withdrawn = [(before[identity], note) for identity, _version, note in changes.withdrawals]
    placements = {"added": [{"identity": entry.identity, "files": _placements(entry)} for entry in added],
                  "replaced": [], "removed": [{"identity": old.identity, "files": _placements(old)}
                                              for old, _note in withdrawn]}
    for old, new in replaced:
        was, now = ({file["path"]: file for file in _placements(entry)} for entry in (old, new))
        placements["replaced"].append({
            "identity": new.identity,
            "added": [now[path] for path in sorted(set(now) - set(was))],
            "removed": [was[path] for path in sorted(set(was) - set(now))],
            "changed": [{"path": path, "before": was[path], "after": now[path]}
                        for path in sorted(set(was) & set(now)) if was[path] != now[path]]})
    sizes_before = {file.digest: file.size_bytes for entry in before.values() for file in entry.package.files}
    sizes_after = {file.digest: file.size_bytes for entry in after.values() for file in entry.package.files}
    new_blobs = sorted(set(sizes_after) - set(sizes_before))
    items = {"base_items": len(before), "result_items": len(after),
             "unchanged": len(before) - len(replaced) - len(withdrawn),
             "added": [_item_row(entry) for entry in added],
             "replaced": [dict(_item_row(new), base_version=old.version) for old, new in replaced],
             "withdrawn": [dict(_item_row(old), note=note) for old, note in withdrawn]}
    files = {"placements": placements, "new_blobs": len(new_blobs),
             "new_blob_bytes": sum(sizes_after[digest] for digest in new_blobs),
             "blobs_no_longer_referenced": [{"digest": digest, "size_bytes": sizes_before[digest]}
                                            for digest in sorted(set(sizes_before) - set(sizes_after))]}
    added_effects = [_effects(entry) for entry in added]
    replaced_effects = [{"before": _effects(old), "after": _effects(new)} for old, new in replaced]
    effects = {"default_step_effects": list(DEFAULT_STEP_EFFECTS),
               "added": [row for row in added_effects if row["declared_effects"]],
               "replaced": [row for row in replaced_effects
                            if row["before"]["declared_effects"] or row["after"]["declared_effects"]],
               "withdrawn": [row for row in (_effects(old) for old, _note in withdrawn) if row["declared_effects"]],
               "held_until_declared": sorted(
                   [row["identity"] for row in added_effects if row["effects_to_declare"]]
                   + [row["after"]["identity"] for row in replaced_effects if row["after"]["effects_to_declare"]])}
    return items, files, effects


def grant_consequences(policies, before_view, after_view, removed_versions):
    """Each grant pinned to a version the change replaces or withdraws, and each grant whose service changes.

    A grant serves when the service's own `_matches` accepts it: the exact item version, binding, useful paths and
    approval. The service refuses to apply a policy file holding any grant that does not serve, so a replaced or
    withdrawn version orphans its grant whether or not the grant is active.
    """
    rows = {"orphaned": [], "serving_only_after": [], "serving_neither": [], "serving_before_and_after": 0}
    for policy in policies:
        for grant in policy["grants"]:
            identity = grant.binding.identity
            row = {"identity": identity, "item_version": grant.item_version, "display_name": grant.display_name,
                   "active": grant.active, "policy_sha256": policy["sha256"],
                   "listed_version_before": before_view.item_versions.get(identity),
                   "listed_version_after": after_view.item_versions.get(identity)}
            served, serves = _matches(grant, before_view), _matches(grant, after_view)
            if removed_versions.get(identity) == grant.item_version or (served and not serves):
                rows["orphaned"].append(row)
            elif serves and not served:
                rows["serving_only_after"].append(row)
            elif serves:
                rows["serving_before_and_after"] += 1
            else:
                rows["serving_neither"].append(row)
    return rows


def search_consequences(judgements, before_view, after_view, top=TOP):
    """Every judged query whose first results change, and every expected item one loses from its first ten."""
    changed, lost, measurable = [], [], 0
    for row in judgements:
        before, after = first_results(before_view, row["query"], top), first_results(after_view, row["query"], top)
        expected = row["relevant"]
        measurable += any(identity in before_view.item_versions for identity in expected)
        for identity in expected:
            if identity in before and identity not in after:
                lost.append({"query": row["query"], "identity": identity, "rank_before": before.index(identity) + 1})
        if before != after:
            changed.append({"query": row["query"], "expected": expected, "before": before, "after": after,
                            "entered": [identity for identity in after if identity not in before],
                            "left": [identity for identity in before if identity not in after],
                            "expected_ranks": {identity: [before.index(identity) + 1 if identity in before else None,
                                                          after.index(identity) + 1 if identity in after else None]
                                               for identity in expected}})
    return {"queries": len(judgements), "queries_with_an_expected_item_listed_before": measurable,
            "first_results_changed": changed, "expected_items_lost": lost}


def plan(base, updates, changes, *, policies, judgements, judgements_sha256, stated_no_policy=False,
         request_sha256=None):
    """The `catalogue_change_plan/v1` record of one declared change; it reads no body and writes nothing."""
    after_items = result_items(base, updates, changes)
    before = {entry.identity: entry for entry in base.items}
    after = {entry.identity: entry for entry in after_items}
    before_view, after_view = served_view(base.items, base.schema), served_view(after_items, base.schema)
    removed = dict(changes.replacements)
    removed.update((identity, version) for identity, version, _note in changes.withdrawals)
    items, files, effects = item_consequences(before, after, changes)
    grants = grant_consequences(policies, before_view, after_view, removed)
    search = search_consequences(judgements, before_view, after_view)
    entries = {"added": list(changes.additions),
               "changed": [identity for identity, _version in changes.replacements
                           if index_entry(before[identity], base.schema) != index_entry(after[identity], base.schema)],
               "removed": [identity for identity, _version, _note in changes.withdrawals]}
    failed = bool(search["expected_items_lost"] or grants["orphaned"])
    return {"record_type": PLAN_VERSION, "request_sha256": request_sha256,
            "base_release": changes.base_release, "base_bundle_digest": base.digest,
            "update_bundle_digests": [update.digest for update in updates],
            "base_content_digest": bundle_content(base), "result_content_digest": after_view.content_digest,
            "additions_only": not changes.replacements and not changes.withdrawals,
            "items": items, "files": files, "effects": effects,
            "search": {"mode": "lexical", "top": TOP, "scope": "an account that receives every listed item",
                       "judgements_sha256": judgements_sha256, "entries": entries, **search},
            "public_good": {"policies": [{"path": policy["path"], "sha256": policy["sha256"],
                                          "expected_release": policy["expected_release"], "grants": len(policy["grants"])}
                                         for policy in policies],
                            "stated_no_policy": stated_no_policy, **grants},
            "verdict": NOT_CONSERVATIVE if failed else CONSERVATIVE,
            "limits": ["The verdict covers the stored judged queries and the given policy files, not every query or "
                       "grant.", "Search ran in lexical mode for an account that receives every listed item.",
                       "Host records are not read: durable withdrawals, snapshot and following grants, and the "
                       "applied Public Good policy where it differs from the given files."]}


def write_report(path, record):
    """Write the report once, to a new private file outside this public repository."""
    path = Path(path)
    if (not path.is_absolute() or path.parent.resolve() != path.parent
            or path.resolve() == REPOSITORY or REPOSITORY in path.resolve().parents):
        raise ValueError("write the consequence report to a new absolute file outside the repository")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(record, stream, indent=1, sort_keys=True)
        stream.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-bundle", type=Path, required=True)
    parser.add_argument("--update-bundle", action="append", type=Path, default=[])
    parser.add_argument("--changes", type=Path, required=True, help="the catalogue_reconciliation_request/v1 file")
    parser.add_argument("--accept-license", action="append", default=[])
    granted = parser.add_mutually_exclusive_group(required=True)
    granted.add_argument("--public-good-policy", action="append", type=Path, default=[],
                         help="a service_public_good_policy_request/v1 file; repeat for each")
    granted.add_argument("--no-public-good-policy", action="store_true",
                         help="state that the host holds no Public Good policy")
    parser.add_argument("--judgements", type=Path, default=DEFAULT_JUDGEMENTS)
    parser.add_argument("--consequences", type=Path, required=True,
                        help="the report: a new file outside the repository")
    options = parser.parse_args(argv)
    try:
        raw, value = read_control(options.changes)
        changes = Changes.from_dict(value)
        licenses = tuple(options.accept_license) or ("MIT",)
        base = load_bundle(options.base_bundle, licenses)
        updates = tuple(load_bundle(path, licenses) for path in options.update_bundle)
        judgements_sha256, judgements = read_judgements(options.judgements)
        record = plan(base, updates, changes, policies=read_policies(options.public_good_policy),
                      judgements=judgements, judgements_sha256=judgements_sha256,
                      stated_no_policy=options.no_public_good_policy, request_sha256=hashlib.sha256(raw).hexdigest())
        write_report(options.consequences, record)
    except (OSError, ValueError, ServiceRuntimeError) as error:
        print(json.dumps({"record_type": PLAN_VERSION, "refused": True,
                          "code": getattr(error, "code", "plan_refused"), "message": str(error)}))
        return 2
    print(json.dumps({"record_type": PLAN_VERSION, "verdict": record["verdict"], "consequences": str(options.consequences),
                      "additions_only": record["additions_only"], "added": len(record["items"]["added"]),
                      "replaced": len(record["items"]["replaced"]), "withdrawn": len(record["items"]["withdrawn"]),
                      "grants_orphaned": len(record["public_good"]["orphaned"]),
                      "judged_queries_changed": len(record["search"]["first_results_changed"]),
                      "expected_items_lost": len(record["search"]["expected_items_lost"])}, sort_keys=True))
    return 0 if record["verdict"] == CONSERVATIVE else 1


if __name__ == "__main__":
    raise SystemExit(main())
