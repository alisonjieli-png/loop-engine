"""Write the library sites' item record from the library release the live service serves.

Kind: development tool. The three library sites (deterministicskills.baltor.ai, tools.baltor.ai and
cornercases.baltor.ai, the owner's request of October 16, 2026) show real library items, chosen by exact identity in
`web_assets/library-sites/hosts.json`, which people edit. This tool reads that choice and four local inputs that stay outside
the repository, and writes `web_assets/library-sites/items.json`, which nobody edits by hand:

- the release folder of the served catalogue release (`bundle.json`, `release-segments.jsonl`, `segments/` and
  `items/`), whose content digest must equal the publication record in this repository that confirmed it;
- the admission packages of the creative originals release, for each item's contract card (`component.json`) and its
  known wrong example;
- the admission packages of the API constraint case release, for each case group's cases;
- nothing else: no network, no model, no catalogue write.

An identity the release does not serve, an item that breaks its host's rule (the deterministic skills host takes only
items with tests and without network access), or item text that the public wording rules refuse stops the build, so a
library site page can never name an item the library does not hold.

Usage (October 16, 2026, the release 29a2bc33 confirmed on October 9):

    python3 tools/build_library_sites.py \\
      --release ~/baltor-private/creative-publication-20261009-dd8349/reconciled-creative-01 \\
      --creative-packages ~/.le-creative-3d/out/supply/admission-d25e6cb4/packages \\
      --case-packages ~/baltor-private/supply-recovery-20261009-X5MGw2/admission-cleared-01/packages

`--check` compares the written record with what the inputs give and changes nothing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.service_runtime import library_site_records as records  # noqa: E402
from loop_engine.core.service_runtime.gallery_records import PUBLIC_TIERS  # noqa: E402

#: The repository record that confirmed the release this build reads; its content digest binds the build.
EVIDENCE = "artifacts/architecture-audit-2026-09-19/catalogue-creative-originals-2026-10-09.json"
GALLERY = ROOT / "src/loop_engine/core/service_runtime/web_assets/gallery/gallery.json"
WORDING_RULES = ROOT / "tools/public_wording_rules.mjs"
TEST_FILE = re.compile(r"(?:^|/)(?:test_[^/]+\.py|tests?/[^/]+|verification/test_[^/]+|[^/]+\.test\.[a-z]+)$")
HARNESS_NAMES = {"claude_code": "Claude Code", "codex": "Codex", "opencode": "OpenCode", "pi": "Pi", "cursor": "Cursor"}
#: The files an MCP server entry carries for each harness, as the mcp_registry line writes them.
MCP_FILES = {".mcp.json": "Claude Code", ".codex/config.toml": "Codex", ".cursor/mcp.json": "Cursor",
             "opencode.json": "OpenCode"}
MAXIMUM_CASES = 8
#: The harness kinds an imported file is named by; any other is a file.
IMPORTED_LABELS = {"command": "command", "hook": "hook"}
MAXIMUM_NOTES = 4


class BuildError(ValueError):
    """An input this tool refuses, with the reason."""


def _require(condition, reason):
    if not condition:
        raise BuildError(reason)


def _json(path):
    return json.loads(Path(path).read_text("utf-8"))


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --- The release ------------------------------------------------------------------------------------------------------

def release_index(folder):
    """{identity: item record digest} for every item of the release, read from its segment list."""
    folder = Path(folder)
    index = {}
    for line in (folder / "release-segments.jsonl").read_text("utf-8").splitlines():
        row = json.loads(line)
        if not isinstance(row, list):
            continue
        segment = _json(folder / "segments" / "sha256" / row[0][:2] / row[0])
        for identity, digest in segment["items"]:
            index[identity] = digest
    return index


def item_record(folder, digest):
    return _json(Path(folder) / "items" / "sha256" / digest[:2] / digest)


def binding(folder, index):
    """The release this build reads, held to the repository's publication record."""
    bundle = _json(Path(folder) / "bundle.json")
    evidence = _json(ROOT / EVIDENCE)
    _require(bundle.get("content_digest") == evidence.get("content_digest"),
             "the release folder is not the release the publication record confirmed")
    _require(bundle.get("release_items") == evidence.get("items_after") == len(index),
             "the release folder does not hold every item the publication record counts")
    return {"evidence": EVIDENCE, "release_id": evidence["active_release"], "content_digest": evidence["content_digest"],
            "release_items": evidence["items_after"], "confirmed_at": evidence["confirmed_at"]}


# --- Wording ----------------------------------------------------------------------------------------------------------

def wording_rules():
    """The public wording rules every customer page follows, read from their one source."""
    source = WORDING_RULES.read_text("utf-8")
    rules = []
    for name in ("internalTerms", "retiredAccessWords", "invitationWords", "cardStatusWords"):
        found = re.search(r"^export const " + name + r"=/(.+)/([a-z]*);$", source, re.MULTILINE)
        _require(found is not None, f"the wording rule {name} is not in {WORDING_RULES.name}")
        rules.append((name, re.compile(found.group(1), re.IGNORECASE if "i" in found.group(2) else 0)))
    return rules


def refused_words(text, rules):
    return [name for name, rule in rules if rule.search(text)]


# --- Normalized items -------------------------------------------------------------------------------------------------

def _slug(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


def _sentence(text):
    """The first sentence of a description, which a row shows."""
    text = " ".join(text.split())
    found = re.match(r"(.+?[.!?])(?:\s|$)", text)
    return found.group(1) if found else text


def _title_from(text, limit=90):
    """A short title from a description: its first clause when that fits, else the words before the last joining word
    that fits, so a title never stops in the middle of a phrase."""
    text = " ".join(text.split())
    cuts = [text.index(mark) for mark in (": ", " - ", "; ", ". ", " (", ", ", " — ") if mark in text]
    head = text[:min(cuts)] if cuts else text
    if len(head) <= limit and len(head) >= 20:
        return head.rstrip(".")
    found = [match.start() for match in re.finditer(r" (?:at|with|while|from|for|by|in|into|using|and|or|to) ", head)
             if 20 <= match.start() <= limit]
    return (head[:found[-1]] if found else head[:limit].rsplit(" ", 1)[0]).rstrip(",;:.")


def _source(reference):
    """The source an item restates, without its revision."""
    return (reference.get("source_ref") or "").split("@", 1)[0]


def _files(package):
    return [[entry["path"], entry["size_bytes"]] for entry in package["files"]]


def _harnesses(reference):
    return [HARNESS_NAMES[style] for style in reference.get("styles") or () if style in HARNESS_NAMES]


def _base(identity, record):
    reference, attributes = record["reference"], record.get("attributes") or {}
    _require(reference.get("identity") == identity and record["approval"]["approved_digest"] == reference.get("digest"),
             f"{identity}: the release record names another item or version")
    return {"identity": identity, "version": reference["digest"], "slug": "", "name": "", "title": "",
            "summary": " ".join(reference["purpose"].split()), "kind": attributes.get("harness_kind") or "",
            "form": attributes.get("component_form") or "", "licence": reference.get("license") or "",
            "effects": sorted(reference.get("declared_effects") or ()), "harnesses": _harnesses(reference),
            "source": _source(reference), "files": _files(record["package"]),
            "bytes": sum(entry["size_bytes"] for entry in record["package"]["files"]),
            "facts": [], "cases": [], "notes": [], "gallery": "", "family": ""}


def _creative(item, record, packages, gallery):
    cited = (record.get("attributes") or {}).get("cited_source") or ""
    parts = cited.split("/")
    _require(len(parts) >= 3 and parts[-2] == "items", f"{item['identity']}: no creative source path")
    family, job = parts[-3], parts[-1]
    card = _json(Path(packages) / item["identity"] / "component.json")
    contract = card.get("contract") or {}
    item.update(family=family, name=job, title=card["title"], summary=" ".join(card["purpose"].split()),
                gallery=gallery.get(item["identity"], ""))
    engine = card.get("engine") or {}
    if engine.get("name"):
        item["facts"].append(["Runs with", f"{engine['name'].capitalize()} {engine.get('minimum_version', '')}".strip()
                              + (" or later" if engine.get("minimum_version") else "")])
    entry_points = contract.get("entry_points")
    if isinstance(entry_points, dict) and entry_points.get("command"):
        item["facts"].append(["Command", entry_points["command"]])
        if entry_points.get("module") and entry_points.get("function"):
            item["facts"].append(["Function", f"{entry_points['module']}.{entry_points['function']}"])
    elif isinstance(entry_points, list) and entry_points:
        names = [point.get("name") if isinstance(point, dict) else str(point) for point in entry_points]
        item["facts"].append(["Entry points", ", ".join(name for name in names if name)])
    if contract.get("known_answers"):
        item["facts"].append(["Known answers", f"{len(contract['known_answers'])} cases its tests reproduce"])
    if isinstance(contract.get("input_schema"), dict):
        required = contract["input_schema"].get("required") or []
        if required:
            item["facts"].append(["Required input", ", ".join(required)])
    checks = (card.get("verification") or {}).get("native") or {}
    if checks.get("checks"):
        item["facts"].append(["Engine checks", f"{len(checks['checks'])} recorded"])
    if card.get("limits"):
        item["notes"].append(["Limits", " ".join(str(card["limits"]).split())])
    for name, label in (("guarantees", "Guarantees"), ("assumptions", "Assumes"), ("proves", "Proves"),
                        ("does_not_prove", "Does not prove")):
        values = contract.get(name)
        if isinstance(values, list) and values:
            item["notes"].append([label, " ".join(" ".join(str(value).split()) for value in values[:3])])
        elif isinstance(values, str) and values:
            item["notes"].append([label, " ".join(values.split())])
    for wrong in contract.get("known_wrong") or ():
        if isinstance(wrong, dict) and wrong.get("name") and wrong.get("why"):
            item["cases"].append([wrong["name"].replace("_", " "), " ".join(wrong["why"].split())])
    failures = [str(failure) for failure in contract.get("failures_detected") or () if isinstance(failure, str)]
    if failures:
        item["facts"].append(["Failure codes", f"{len(failures)} the checker reports by name"])
        item["cases"].extend([failure.replace("_", " "), "a failure code the check reports"] for failure in failures)
    for reason in contract.get("refusal_reasons") or ():
        text = reason if isinstance(reason, str) else (reason.get("reason") or reason.get("code") or "")
        if text:
            item["cases"].append([str(text).replace("_", " "), "refused with exit code 2"])
    wrong_example = Path(packages) / item["identity"] / "examples" / "known_wrong.json"
    if wrong_example.is_file():
        example = _json(wrong_example)
        if example.get("description"):
            reason = (example.get("expected_refusal") or {}).get("reason", "")
            item["cases"].insert(0, ["Known wrong example", " ".join(example["description"].split())
                                     + (f" Refused as {reason.replace('_', ' ')}." if reason else "")])
    activities = contract.get("activities") or []
    if activities:
        item["notes"].append(["Work activities", "; ".join(activity["title"].rstrip(".") for activity in activities[:3]) + "."])
    return item


def _case_group(item, packages):
    folder = Path(packages) / item["identity"]
    group, contract = _json(folder / "constraint-group.json"), _json(folder / "contract.schema.json")
    meta = contract.get("x-baltor-contract") or {}
    found = re.search(r"amazonaws\.com/([a-z0-9-]+)/(\d{4}-\d{2}-\d{2})/", item["source"])
    service = f"{found.group(1)} {found.group(2)}" if found else ""
    operation = meta.get("operation_id") or contract.get("title", "")
    item.update(family="api_constraint_cases", name=contract.get("title", ""),
                title=f"{operation} request cases" + (f" ({service.split(' ')[0]})" if service else ""))
    cases = [_json(folder / case["path"]) for case in group["cases"]]
    validators = sorted({case["expected"]["validator"] for case in cases})
    item["facts"] = [["Operation", f"{meta.get('method', '')} {operation}".strip()],
                     ["Case jobs", f"{len(cases)}, one changed field each"],
                     ["Validators", ", ".join(validators)],
                     ["Replay", "python constraint_case_runtime.py ."]]
    if service:
        item["facts"].insert(1, ["API", f"amazonaws.com/{service.replace(' ', ', version ')}"])
    ranked = sorted(cases, key=lambda case: (case["expected"]["validator"] == "type", case["expected"]["validator"]))
    seen = set()
    for case in ranked:
        expected = case["expected"]
        if expected["validator"] in seen and len(seen) < len(validators):
            continue
        seen.add(expected["validator"])
        path = ".".join(str(part) for part in expected["instance_path"]) or "request"
        message = expected["shipped_message"]
        values = case.get("constraint_value")
        if expected["validator"] == "enum" and isinstance(values, list) and 0 < len(values) <= 6:
            message = "must be one of " + ", ".join(str(value) for value in values)
        item["cases"].append([path, f"{message} ({expected['validator']})"])
        if len(item["cases"]) >= MAXIMUM_CASES:
            break
    return item


def _supply(item, record):
    """An item of a supply line without a contract card: its facts come from its record and file list."""
    identity, summary = item["identity"], item["summary"]
    files = [path for path, _size in item["files"]]
    if identity.startswith("library.supply.mcp_registry."):
        found = re.match(r"Connection settings for the protocol server (\S+), version (\S+)\.", summary)
        _require(found is not None, f"{identity}: no server name in its description")
        runner = re.search(r"It starts on your machine with (\S+) from the (\S+) package (\S+?)\.", summary)
        variables = re.search(r"It reads these environment variables: ([^.]+)\.", summary)
        item.update(family="mcp_registry", name=found.group(1), title=f"MCP server settings for {found.group(1)}")
        item["facts"] = [["Server", found.group(1)], ["Server version", found.group(2)]]
        if runner:
            item["facts"].append(["Starts with", f"{runner.group(1)}, {runner.group(2)} package {runner.group(3)}"])
        if variables:
            item["facts"].append(["Environment variables", variables.group(1)])
        item["facts"].append(["Settings for", ", ".join(MCP_FILES[path] for path in files if path in MCP_FILES)])
    elif identity.startswith("library.supply.program_installs."):
        found = re.match(r"(\S+) (\S+) \((.+?)\): the install recipe", summary)
        _require(found is not None, f"{identity}: no program name in its description")
        item.update(family="program_installs", name=f"{found.group(1)} {found.group(2)}",
                    title=f"{found.group(3)[0].upper() + found.group(3)[1:]} ({found.group(1)})")
        wrapper = next((path for path in files if path.endswith("_program.py")), "")
        item["facts"] = [["Program", found.group(1)], ["Program version", found.group(2)], ["Recipe", "install.json"]]
        if wrapper:
            item["facts"].append(["Wrapper", wrapper])
    elif identity.startswith("library.supply.function_extracts."):
        found = re.match(r"(\S+) from (.+?): (.+)", summary)
        _require(found is not None, f"{identity}: no function name in its description")
        project = found.group(2).split(" (", 1)[0]
        item.update(family="function_extracts", name=found.group(1), title=f"{found.group(1)} from {project}")
        module = next((path for path in files if path.endswith(".py") and not path.startswith("test_")), "")
        item["facts"] = [["Function", found.group(1)], ["Project", found.group(2)], ["Module", module]]
    elif identity.startswith("library.supply.data_tables."):
        rows = re.search(r": (\d+) rows with a JSON Schema", summary)
        data = next((path for path in files if path.startswith("data/")), "")
        item.update(family="data_tables", name=data.split("/")[-1], title=_title_from(summary))
        item["facts"] = [["Rows", rows.group(1) if rows else ""], ["Data file", data], ["Schema", "schema.json"]]
    elif identity.startswith("import_"):
        own = [path for path in files if path not in ("ATTRIBUTION.md", "LICENSE", "LICENSE.md")]
        name = own[0] if own else identity
        label = IMPORTED_LABELS.get(item["kind"], "file")
        # An imported file whose description only names it, such as "hook session-start.sh", is titled by its name and
        # described by where it comes from; any other keeps its own description.
        thin = len(summary.split()) <= 3
        item.update(family="imported_" + label, name=name, title=f"{name} {label}" if thin else _title_from(summary))
        if thin:
            item["summary"] = (f"The {label} file {name}, from {'/'.join(item['source'].split('/')[1:3])}, with its "
                               "licence and attribution.")
        item["facts"] = [["File", name], ["From", "/".join(item["source"].split("/")[:3])]]
        folder = "/".join(item["source"].split("/")[3:-1])
        if folder:
            item["facts"].append(["Placed in its source", folder + "/"])
    else:
        item.update(family="first_party", name=identity, title=_title_from(summary))
        skill = [path for path in files if path in ("SKILL.md",) or path.startswith(("scripts/", "contracts/"))]
        item["facts"] = [["Files", ", ".join(skill[:5]) or ", ".join(files[:3])]]
        if item["harnesses"]:
            item["facts"].append(["Placed for", ", ".join(item["harnesses"])])
    item["facts"] = [fact for fact in item["facts"] if fact[1]]
    return item


def verified_package(identity, record, folders):
    """A local copy of an item whose every file has the digest the release records, or None. Only such a copy is read."""
    for folder in folders:
        candidate = Path(folder) / identity
        if candidate.is_dir() and all((candidate / entry["path"]).is_file()
                                      and _digest(candidate / entry["path"]) == entry["digest"]
                                      for entry in record["package"]["files"]):
            return candidate
    return None


def _section(markdown, heading):
    """The text under one level-two heading of a Markdown file, without the heading."""
    found = re.search(r"^## " + re.escape(heading) + r"\s*$(.*?)(?=^## |\Z)", markdown, re.MULTILINE | re.DOTALL)
    return found.group(1) if found else ""


def _first_command(section):
    found = re.search(r"```(?:bash|sh)?\n(.+?)\n", section)
    return found.group(1).strip() if found else ""


def _schema_fields(path, limit=8):
    if not path.is_file():
        return ""
    schema = _json(path)
    names = [name for name in (schema.get("properties") or {}) if name not in ("schema_version", "engine", "privacy")]
    shown = ", ".join(names[:limit])
    return shown + (f" and {len(names) - limit} more" if len(names) > limit else "")


def _enrich_skill(item, folder):
    """The facts a skill with scripts states in its own files: how to run it, what it takes and returns, how to test it,
    and the first paragraph of its limits."""
    skill = (folder / "SKILL.md").read_text("utf-8")
    command = _first_command(_section(skill, "Invoke"))
    test = _first_command(_section(skill, "Check and provenance")) or _first_command(_section(skill, "Check"))
    facts = [["Command", command], ["Input fields", _schema_fields(folder / "contracts" / "input.schema.json")],
             ["Output fields", _schema_fields(folder / "contracts" / "output.schema.json")], ["Test", test]]
    item["facts"] = [fact for fact in facts if fact[1]] + item["facts"]
    limits = " ".join(_section(skill, "Limits and effects").strip().split("\n\n", 1)[0].split())
    if limits:
        # A sentence ends at a stop followed by a capital letter, so 1.2 and SDG 3.1 stay inside their sentence.
        sentences = re.findall(r".+?[.!?](?=\s+[A-Z(]|$)", limits)
        item["notes"].append(["Limits", " ".join(sentence.strip() for sentence in sentences[:2]) or limits])
    return item


def normalize(identity, record, packages, gallery, titles=None):
    item = _base(identity, record)
    if identity.startswith("library.supply.creative_originals."):
        item = _creative(item, record, packages["creative"], gallery)
    elif (Path(packages["cases"]) / identity / "constraint-group.json").is_file():
        item = _case_group(item, packages["cases"])
    else:
        item = _supply(item, record)
        if item["family"] == "first_party":
            folder = verified_package(identity, record, packages["skills"])
            if folder is not None and (folder / "SKILL.md").is_file():
                item = _enrich_skill(item, folder)
    # A title written from a description starts with a capital; a contract card's own title (glTF ...) stays as written.
    if item["family"] in ("first_party", "data_tables", "imported_command"):
        item["title"] = item["title"][0].upper() + item["title"][1:]
    if titles and identity in titles:
        item["title"] = titles[identity]
    item["slug"] = (_slug(identity) if not identity.startswith("library.supply.")
                    else _slug(item["title"])[:56].strip("-") + "-" + identity.rsplit(".", 1)[-1][:8])
    item["cases"], item["notes"] = item["cases"][:MAXIMUM_CASES], item["notes"][:MAXIMUM_NOTES]
    return item


def count(rule, index, release):
    """How many items of the release a category's count rule names."""
    if "evidence" in rule:
        value = _json(ROOT / rule["evidence"])
        for field in rule["fields"]:
            value = value[field]
        return value
    identities = [identity for identity in index if identity.startswith(tuple(rule["prefixes"]))]
    if rule.get("harness_kinds"):
        identities = [identity for identity in identities
                      if (item_record(release, index[identity]).get("attributes") or {}).get("harness_kind")
                      in rule["harness_kinds"]]
    return len(identities)


def build(release, creative_packages, case_packages, skill_packages=()):
    hosts = records.hosts_record()
    index = release_index(release)
    gallery = {item["identity"]: item["slug"] for item in _json(GALLERY)["items"] if item["tier"] in PUBLIC_TIERS}
    rules = wording_rules()
    packages = {"creative": creative_packages, "cases": case_packages, "skills": [Path(path) for path in skill_packages]}
    items, counts, problems = {}, {}, []
    for host in hosts["hosts"]:
        for category in host["categories"]:
            key = f"{host['id']}/{category['slug']}"
            for identity in category["items"]:
                if identity not in index:
                    problems.append(f"{key}: {identity} is not in the release")
                    continue
                if identity not in items:
                    items[identity] = normalize(identity, item_record(release, index[identity]), packages, gallery,
                                                hosts["titles"])
                item = items[identity]
                if host["rule"].get("no_network") and {"network", "reads_secret"} & set(item["effects"]):
                    problems.append(f"{key}: {identity} declares network or secret access")
                if host["rule"].get("tests_required") and not any(TEST_FILE.search(path) for path, _ in item["files"]):
                    problems.append(f"{key}: {identity} carries no test file")
                text = " ".join([item["title"], item["summary"], *(value for _label, value in item["facts"]),
                                 *(value for pair in item["cases"] + item["notes"] for value in pair)])
                for name in refused_words(text, rules):
                    problems.append(f"{key}: {identity} has text the {name} wording rule refuses")
            if category.get("library_count"):
                counts[key] = count(category["library_count"], index, release)
    _require(not problems, "the build is refused:\n" + "\n".join(problems))
    slugs = [item["slug"] for item in items.values()]
    _require(len(slugs) == len(set(slugs)), "two items share a page address")
    return {"record_type": records.ITEMS_RECORD_TYPE, "built_from": {**binding(release, index),
            "selection_sha256": records.selection_digest(hosts)},
            "counts": counts, "items": sorted(items.values(), key=lambda item: item["identity"])}


def text_of(record):
    return json.dumps(record, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--release", required=True)
    parser.add_argument("--creative-packages", required=True)
    parser.add_argument("--case-packages", required=True)
    parser.add_argument("--skill-packages", nargs="*", default=[],
                        help="folders of local skill packages; a copy is read only when every file has the released digest")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    record = build(Path(args.release).expanduser(), Path(args.creative_packages).expanduser(),
                   Path(args.case_packages).expanduser(), [Path(path).expanduser() for path in args.skill_packages])
    text, target = text_of(record), records.ITEMS_PATH
    if args.check:
        current = target.read_text("utf-8") if target.is_file() else ""
        print(f"{target} is current" if current == text else f"{target} differs from what the inputs give")
        return 0 if current == text else 1
    records.parse_items(text, records.hosts_record())
    target.write_text(text, "utf-8")
    print(f"wrote {target}: {len(record['items'])} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
