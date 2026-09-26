"""Export stored candidates as a candidate catalogue folder for the independent review panel.

The panel reads candidate packages from the version-three candidate catalogue
layout that the candidate factory writes. This export writes the same layout,
outside the repository, for packages imported under a permissive licence:

```text
Review export folder (outside the repository: it holds third-party bytes)
├── items.json                  starter_catalogue_candidate_items/v3: one row per package
├── specifications-NNN.json     candidate_intelligence_specifications/v3, fifty to a population
├── packages/<identity>/...     every file of the package, byte for byte
├── bodies/<identity>.package.json   the canonical catalogue_package/v1 document
└── export-report.json          the selection rule, the counts and what differs from original items
```

Two things differ from the panel's original-item profile, on purpose, and
the report names them: the provenance is the imported one (the upstream
repository, commit, path and digest in `outside_source_provenance/v1`, the
licence expression, the licence texts and the attribution file inside the
package), and the producer is the upstream author, a family no reviewing
model belongs to. Nothing else is invented: the reference, the package, its
roles and its declared effects are the stored candidate's.

The selection keeps the panel's bounds for reviewable text (every file one of
its text media types, at most 256 kilobytes a file and 2 megabytes a
package) and spreads the campaign across repositories (a ceiling per
repository). Two selection rules exist, chosen by the caller:

```text
kind mix
├── balanced (the default since September 26, 2026): every kind a harness picks
│   up is drawn each export in a declared share, skills with scripts as their
│   own share, by a weighted round robin, so any prefix of the selection keeps
│   the mix and an exhausted kind spills over to the others
└── ranked (the rule until then): instruction-only packages first, then by
    source and stars, which drew skills and instruction files before anything
    else while the stock lasted
```

The owner, September 26, 2026: the library "should be skills, plugins,
python scripts, literally a large mix of everything that can be placed into a
harness working directory". Slow scanners may run over the selection before
it is written; a blocked package is left out with its rule names and the next
package takes its place. Nothing here approves anything.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from loop_engine.core.harness_intelligence import HarnessIntelligenceItem
from loop_engine.core.intelligence_tagging import TagSet
from loop_engine.core.library_ingestion.record_rules import canonical_digest, now_utc
from loop_engine.core.service_runtime.catalogue_packages import EXECUTABLE_ROLES, CataloguePackage

from .checks import blocking_rules
from .records import (
    CODE_MODULE, COMMAND, CONTRACT_SCHEMA, HOOK, INSTRUCTION_FILE, MARKETPLACE, PLUGIN_MANIFEST, PROTOCOL_SERVER,
    RULES, SETTINGS, SKILL, SUBAGENT, refusal)

ITEMS_RECORD_TYPE = "starter_catalogue_candidate_items/v3"
SPECIFICATIONS_RECORD_TYPE = "candidate_intelligence_specifications/v3"
#: Version two adds the kind mix (`mix`) and the count of packages with scripts (`with_scripts`); the review panel's
#: imported reader serves version one, which earlier exports wrote, and version two.
EXPORT_REPORT_RECORD_TYPE = "licensed_import_review_export/v2"
IMPORTED_PROFILE = "imported_licensed_package/v1"
UPSTREAM_FAMILY = "upstream_author"
METHOD_IDENTITY = "licensed_import/github_verbatim/v1"
#: The panel's reviewable text media types and bounds; the same set as tools/candidate_review/native.py, which
#: the sync checks compare. Scripts in shell, JavaScript, TypeScript and PowerShell are text the reviewer reads
#: line by line since September 26, 2026 (roadmap S-6.205); images, archives and unknown bytes are not.
TEXT_MEDIA = frozenset({"text/plain", "text/markdown", "text/x-rst", "text/x-python", "application/x-python",
                        "application/json", "application/schema+json", "application/yaml", "text/yaml",
                        "application/toml", "application/x-sh", "text/javascript", "text/x-typescript",
                        "text/x-powershell", "text/x-ruby", "text/x-perl", "text/x-go", "text/x-rust", "text/x-php",
                        "text/x-lua", "text/html", "text/css", "text/csv", "application/xml", "application/sql"})
MAXIMUM_FILE_BYTES = 256 * 1024
MAXIMUM_PAYLOAD_BYTES = 2 * 1024 * 1024
POPULATION_SIZE = 50
#: The kind mixes a caller may ask for.
KIND_MIXES = ("balanced", "ranked")
BALANCED, RANKED = KIND_MIXES
#: A skill whose package holds a script is its own share, so code enters the library at a steady rate.
SKILL_WITH_SCRIPTS = "skill_with_scripts"
#: The balanced mix of one export, as shares of the limit. Chosen on September 26, 2026 from the stock then on
#: disk (25,096 skills, of which 2,162 with scripts; 6,799 subagents; 6,437 commands; 2,939 plugin manifests;
#: 2,932 instruction files; 2,787 rules; 1,077 marketplaces; 952 protocol server configurations; 942 hooks; 744
#: contract schemas; 82 code modules) so that every kind lasts about the same number of exports. A kind with
#: nothing left spills its share over to the others.
DEFAULT_KIND_SHARES = {SKILL: 0.30, SKILL_WITH_SCRIPTS: 0.10, SUBAGENT: 0.12, COMMAND: 0.12, RULES: 0.08,
                       INSTRUCTION_FILE: 0.08, PLUGIN_MANIFEST: 0.06, HOOK: 0.05, PROTOCOL_SERVER: 0.03,
                       MARKETPLACE: 0.02, CONTRACT_SCHEMA: 0.02, CODE_MODULE: 0.01, SETTINGS: 0.01}
#: The panel's item kinds; the harness file kind stays on the specification and in the tags. An imported code module
#: is served as a tool package in the harness_local layer, the files a harness picks up; the reusable_code kind names
#: Code Intelligence items that keep their identity in that layer, which an imported file is not (the item model
#: refused the first code module the balanced mix selected, on September 26, 2026, and the 16:17 UTC slot's export
#: failed).
REFERENCE_KINDS = {SKILL: "skill", INSTRUCTION_FILE: "instruction_file", RULES: "instruction_file",
                   SUBAGENT: "instruction_file", COMMAND: "instruction_file", HOOK: "tool", PLUGIN_MANIFEST: "tool",
                   MARKETPLACE: "tool", PROTOCOL_SERVER: "tool", CONTRACT_SCHEMA: "tool", CODE_MODULE: "tool",
                   SETTINGS: "tool"}
_IDENTITY = re.compile(r"[^a-z0-9]+")


def identity_for(payload: dict) -> str:
    """A path-safe identity: kind, name and the upstream key, at most 80 characters."""
    name = _IDENTITY.sub("_", payload["name"].lower()).strip("_")[:40] or "item"
    return f"import_{payload['kind']}_{name}_{payload['upstream_key'][:12]}"[:80]


def reviewable(payload: dict) -> "str | None":
    """None when the panel can read every file of the package, or the reason it cannot."""
    files = payload["package"]["files"]
    if any(entry["media_type"] not in TEXT_MEDIA for entry in files):
        return "a_file_is_not_reviewable_text"
    if any(entry["size_bytes"] > MAXIMUM_FILE_BYTES for entry in files):
        return "a_file_is_above_the_review_bound"
    if sum(entry["size_bytes"] for entry in files) > MAXIMUM_PAYLOAD_BYTES:
        return "the_package_is_above_the_review_bound"
    return None


def has_code(payload: dict) -> bool:
    return any(entry["role"] in EXECUTABLE_ROLES for entry in payload["package"]["files"])


def mix_key(payload: dict) -> str:
    """The share a package draws from: its kind, or skill_with_scripts for a skill that holds a script."""
    if payload["kind"] == SKILL and has_code(payload):
        return SKILL_WITH_SCRIPTS
    return payload["kind"]


def parse_kind_shares(values) -> dict:
    """KIND=FRACTION arguments over the default mix; a share is a fraction between 0 and 1 of a known kind."""
    shares = dict(DEFAULT_KIND_SHARES)
    for value in values or ():
        kind, separator, fraction = str(value).partition("=")
        if not separator or kind not in shares:
            raise ValueError(f"a kind share is KIND=FRACTION for one of {sorted(shares)}: {value!r}")
        try:
            share = float(fraction)
        except ValueError:
            raise ValueError(f"the share of {kind} is a number: {value!r}") from None
        if not 0 <= share <= 1:
            raise ValueError(f"the share of {kind} is between 0 and 1: {value!r}")
        shares[kind] = share
    if not any(shares.values()):
        raise ValueError("at least one kind keeps a share above zero")
    return shares


def _ranked(payloads, first_source: dict, priority: dict, skipped: Counter, *, code_last: bool) -> list:
    """Reviewable packages with their order key: source priority, then stars, then repository and path."""
    ranked = []
    for payload in payloads:
        reason = reviewable(payload)
        if reason:
            skipped[reason] += 1
            continue
        repository = payload["provenance"]["repository"]
        source = first_source.get(repository.lower(), "")
        # The ranked rule put instruction-only packages first, because the Community tier once asked a
        # package with code to pass its own tests; the balanced rule gives code its own share instead.
        order = ((has_code(payload),) if code_last else ()) + (
            priority.get(source, 99), -(payload["repository"].get("stars") or 0), repository.lower(),
            payload["provenance"]["path"])
        ranked.append((order, payload))
    ranked.sort(key=lambda row: row[0])
    return [payload for _order, payload in ranked]


def _balanced(ranked: list, shares: dict, skipped: Counter, *, limit: int, per_repository: int) -> list:
    """A weighted round robin over the kind buckets: at each draw the bucket furthest behind its share.

    The shares are renormalized over the buckets that still hold a package,
    so an exhausted kind spills over to the others, and any prefix of the
    result keeps the mix as closely as whole packages allow."""
    buckets = defaultdict(list)
    for payload in ranked:
        key = mix_key(payload)
        if shares.get(key, 0) > 0:
            buckets[key].append(payload)
        else:
            skipped["kind_share_is_zero"] += 1
    positions = {key: 0 for key in buckets}
    taken, per = Counter(), Counter()
    chosen = []
    while len(chosen) < limit:
        live = [key for key in buckets if positions[key] < len(buckets[key])]
        if not live:
            break
        total = sum(shares[key] for key in live)
        key = max(live, key=lambda name: (shares[name] / total * (len(chosen) + 1) - taken[name],
                                          shares[name], -sorted(buckets).index(name)))
        payload = buckets[key][positions[key]]
        positions[key] += 1
        repository = payload["provenance"]["repository"].lower()
        if per[repository] >= per_repository:
            skipped["repository_ceiling_reached"] += 1
            continue
        per[repository] += 1
        taken[key] += 1
        chosen.append(payload)
    return chosen


def select(payloads, first_source: dict, priority: dict, *, limit: int, per_repository: int,
           kind_mix: str = RANKED, kind_shares: "dict | None" = None) -> tuple:
    """(chosen, skipped reasons): reviewable packages spread across repositories, in the asked kind mix."""
    if kind_mix not in KIND_MIXES:
        raise ValueError(f"the kind mix is one of {KIND_MIXES}: {kind_mix!r}")
    skipped = Counter()
    if kind_mix == BALANCED:
        ranked = _ranked(payloads, first_source, priority, skipped, code_last=False)
        return _balanced(ranked, kind_shares or DEFAULT_KIND_SHARES, skipped, limit=limit,
                         per_repository=per_repository), skipped
    per = Counter()
    chosen = []
    for payload in _ranked(payloads, first_source, priority, skipped, code_last=True):
        repository = payload["provenance"]["repository"].lower()
        if per[repository] >= per_repository:
            skipped["repository_ceiling_reached"] += 1
            continue
        per[repository] += 1
        chosen.append(payload)
        if len(chosen) >= limit:
            break
    return chosen, skipped


def mix_counts(payloads) -> dict:
    """How many packages of each share a selection holds, most first."""
    return dict(Counter(mix_key(payload) for payload in payloads).most_common())


def scan_selection(chosen, body_reader, checks, *, target: int, scan_workers: int = 8) -> tuple:
    """Run the slow scanners over the selection; keep packages until the target, record the blocked."""
    from concurrent.futures import ThreadPoolExecutor
    if checks is None or not checks.engines:
        return chosen[:target], []
    packages = {payload["record_id"]: [(entry["path"], body_reader(entry["digest"]))
                                       for entry in payload["package"]["files"]] for payload in chosen}
    keys = sorted(packages)
    groups = [keys[index::scan_workers] for index in range(scan_workers) if keys[index::scan_workers]]
    found = {}
    with ThreadPoolExecutor(max_workers=max(1, len(groups))) as pool:
        for result in pool.map(lambda group: checks.scan({key: packages[key] for key in group}), groups):
            found.update(result)
    kept, refused = [], []
    for payload in chosen:
        findings = found.get(payload["record_id"], [])
        blocked = blocking_rules(findings)
        source = payload["provenance"]
        if blocked:
            refused.append(refusal("check", "blocked_by_static_check", repository=source["repository"],
                                   revision=source["immutable_revision"], path=source["path"],
                                   detail=",".join(blocked), source_ids=payload["sources"]))
            continue
        payload = {**payload, "findings": payload["findings"] + [
            {**finding, "path": finding.get("path", "")} for finding in findings]}
        kept.append(payload)
        if len(kept) >= target:
            break
    return kept, refused


def exported_record_ids(folders) -> set:
    """Store record identities already handed to review in earlier export folders."""
    found = set()
    for folder in folders:
        for path in sorted(Path(folder).glob("specifications-[0-9][0-9][0-9].json")):
            for spec in json.loads(path.read_text(encoding="utf-8"))["specifications"]:
                found.add(spec["provenance"]["store_record_id"])
    return found


def _reference(identity: str, payload: dict, package: CataloguePackage) -> dict:
    source = payload["provenance"]
    item = HarnessIntelligenceItem(
        identity=identity, kind=REFERENCE_KINDS[payload["kind"]],
        purpose=(payload.get("description") or f"{payload['kind']} {payload['name']}")[:1024],
        digest=package.served_digest, size_bytes=package.served_size, source_layer="harness_local",
        source_ref=f"github.com/{source['repository']}/{source['path']}@{source['immutable_revision']}",
        license_name=payload["licence"]["spdx_expression"], declared_effects=tuple(payload["declared_effects"]),
        styles=(payload["kind"], payload["native_format"]),
        tags=TagSet({"lifecycle": ["candidate"], "data_sensitivity": ["public"]}))
    return item.reference()


def export(chosen, body_reader, folder: Path, *, code_revision: str, first_source: dict, summary: dict) -> dict:
    """Write the catalogue folder for the chosen packages; refuse an existing folder."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    items, specifications = [], []
    for payload in chosen:
        identity = identity_for(payload)
        package = CataloguePackage.from_dict(payload["package"])
        if package.package_digest != payload["package_digest"]:
            raise ValueError(f"{payload['record_id']}: the stored package is not its recorded digest")
        root, body = f"packages/{identity}", f"bodies/{identity}.package.json"
        for entry in package.files:
            data = body_reader(entry.digest)
            target = folder / root / entry.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (folder / "bodies").mkdir(exist_ok=True)
        (folder / body).write_bytes(package.document())
        owner = payload["provenance"]["repository"].split("/", 1)[0]
        producer = {"producer_identity": f"github:{owner}", "family": UPSTREAM_FAMILY,
                    "method_identity": METHOD_IDENTITY}
        reference = _reference(identity, payload, package)
        items.append({"reference": reference, "body_path": body, "package": package.to_dict(),
                      "package_root": root, "producer": producer, "dependencies": []})
        specifications.append({
            "id": identity, "layer": "context" if reference["kind"] in ("skill", "instruction_file") else "code",
            "family": "harness", "title": payload["name"], "tags": [payload["kind"], payload["native_format"]],
            "text": "", "sources": [], "symbols": [], "kind": reference["kind"], "purpose": reference["purpose"],
            "styles": list(reference["styles"]), "dependencies": [], "producer": producer,
            "declared_effects": list(reference["declared_effects"]), "package": package.to_dict(),
            "package_digest": package.package_digest, "package_root": root, "body_path": body,
            "provenance": {"authoring": payload["authoring"], "profile": IMPORTED_PROFILE,
                           "outside_provenance": payload["provenance"], "merged_sources": payload["merged"],
                           "license": {"expression": payload["licence"]["spdx_expression"],
                                       "texts": payload["licence"]["texts"],
                                       "attribution": payload["licence"]["attribution"]},
                           "store_record_id": payload["record_id"], "findings": payload["findings"],
                           "harness_kind": payload["kind"], "placements": payload["placements"]}})
    (folder / "items.json").write_text(json.dumps(
        {"record_type": ITEMS_RECORD_TYPE, "source_revision": code_revision, "source_digests": {},
         "publication": "not_published", "items": items}, indent=1, sort_keys=True), encoding="utf-8")
    populations = [specifications[start:start + POPULATION_SIZE]
                   for start in range(0, len(specifications), POPULATION_SIZE)]
    for number, population in enumerate(populations, 1):
        (folder / f"specifications-{number:03d}.json").write_text(json.dumps(
            {"record_type": SPECIFICATIONS_RECORD_TYPE, "population": number, "populations": len(populations),
             "specifications": population}, indent=1, sort_keys=True), encoding="utf-8")
    by_source = defaultdict(Counter)
    for payload in chosen:
        by_source[first_source.get(payload["provenance"]["repository"].lower(), "unknown")][
            payload["licence"]["spdx_expression"]] += 1
    report = {"record_type": EXPORT_REPORT_RECORD_TYPE, "written_at": now_utc(), "code_revision": code_revision,
              "profile": IMPORTED_PROFILE, "items": len(items), "populations": len(populations),
              "files": sum(len(row["package"]["files"]) for row in items),
              "kinds": dict(Counter(payload["kind"] for payload in chosen).most_common()),
              "mix": mix_counts(chosen),
              "with_scripts": sum(1 for payload in chosen if has_code(payload)),
              "licences": dict(Counter(payload["licence"]["spdx_expression"] for payload in chosen).most_common()),
              "by_first_source_and_licence": {source: dict(counts) for source, counts in sorted(by_source.items())},
              "repositories": len({payload["provenance"]["repository"].lower() for payload in chosen}),
              "differs_from_original_profile": [
                  "provenance.authoring is imported_verbatim_under_permissive_licence, with the upstream "
                  "repository, commit, path and digest in provenance.outside_provenance",
                  "provenance.license names the licence expression, the licence texts and ATTRIBUTION.md, all "
                  "inside the package; items.json cites no repository source (source_digests is empty)",
                  "the producer is the upstream author (family upstream_author), which no reviewing model shares"],
              "selection": summary, "items_digest": canonical_digest([row["reference"]["identity"] for row in items])}
    (folder / "export-report.json").write_text(json.dumps(report, indent=1, sort_keys=True), encoding="utf-8")
    return report
