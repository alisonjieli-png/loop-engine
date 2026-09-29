"""Build the record behind /changelog, /features and /todo, three pages nothing links to, from the authoritative records.

Kind: development generator. The owner, September 26, 2026: "Do we have a public changelog, feature list, and todo
pages? We could add these, public links, but they can be undiscoverable (no page linking to them) but if you have those
it would be really helpful".

It reads the Fly release records (artifacts/architecture-audit-2026-09-19/pilot-release-*.json), the Community release
records (artifacts/community-release-*/README.md), the top-level CHANGELOG.md, the website's site map and layout
standard, the capabilities builder in http.py (read as code, never called), the served attribute declarations, the
client recipes of Get set up, the roadmap and the reviewed exclusion list (docs/roadmap/public-status-exclusions.json),
and writes one packaged record, src/loop_engine/core/service_runtime/web_assets/status-pages/status-pages.json, which
loop_engine.core.service_runtime.status_pages renders. The service reads nothing else at run time, so it needs no
artifacts folder and no roadmap.

Usage:

    PYTHONPATH=src python tools/build_public_status_pages.py            # write the record
    PYTHONPATH=src python tools/build_public_status_pages.py --check    # exit 1 when the committed record is stale

tools/build_continuation_status.py and tools/build_records_index.py run it with their own default run and --check, so
a session that edits the roadmap or adds a record regenerates the pages in the command it already runs.

What a page may print, and nothing else:

- a line of a record, cleaned by the declared rules below: a bracketed reference a visitor cannot follow (a roadmap
  step, a commit list, a file, a run) is taken out, a Markdown link keeps its words, and the first letter is raised.
  The line is left out, and counted, when it still carries an internal term: a word the public wording rules
  (tools/public_wording_rules.mjs) refuse, a revision hash or digest, a file name or a repository path, a code
  identifier, a record type, a command option, a run number, an address the site map does not list, a hostname the
  site map does not name, a price other than the plan, or a phrase the layout standard refuses;
- a roadmap step, a release line or a CHANGELOG.md line that the reviewed exclusion list names is left out, whatever
  its words; that list, not a match on words, decides what describes an open security or privacy weakness, an abuse
  path, a staff-only route or a private matter of the owner; a part of the capabilities record it names, such as the
  search backend that no page names, stays off the feature list;
- a roadmap step's title and its status in plain words, never its evidence, next work or owner;
- the facts of the site map, the layout standard, the capabilities builder, the attribute declarations and the client
  recipes, as those records state them.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402

RECORD_TYPE = "public_status_pages/v1"
EXCLUSIONS_RECORD_TYPE = "public_status_exclusions/v1"
GENERATED_BY = "tools/build_public_status_pages.py"
SERVICE_RUNTIME = ROOT / "src" / "loop_engine" / "core" / "service_runtime"
OUTPUT = SERVICE_RUNTIME / "web_assets" / "status-pages" / "status-pages.json"
RELEASE_RECORDS = "artifacts/architecture-audit-2026-09-19/pilot-release-*.json"
LIBRARY_RELEASES = "artifacts/community-release-*/README.md"
CHANGELOG = ROOT / "CHANGELOG.md"
ROADMAP = ROOT / "docs" / "roadmap" / "roadmap.yaml"
EXCLUSIONS = ROOT / "docs" / "roadmap" / "public-status-exclusions.json"
WORDING_RULES = ROOT / "tools" / "public_wording_rules.mjs"
SITE_MAP = SERVICE_RUNTIME / "web_site_map.json"
LAYOUT_STANDARD = SERVICE_RUNTIME / "web_layout_standard.json"
CLIENT_RECIPES = SERVICE_RUNTIME / "web_assets" / "client-recipes.json"
HTTP_SOURCE = SERVICE_RUNTIME / "http.py"
#: The three pages this record feeds. A line that names one of them is left out, so no page points at them.
ADDRESSES = ("/changelog", "/features", "/todo")
#: The public wording rules, by the names tools/public_wording_rules.mjs exports them.
WORDING_RULE_NAMES = ("internalTerms", "publicVocabulary", "retiredAccessWords", "invitationWords", "unpublishedTerms",
                      "cardStatusWords")
#: A roadmap step in one of these states is done; every other state is open work.
DONE_STATUSES = ("live_qualified", "offline_verified")
#: Each open status in plain words, from the status vocabulary of docs/roadmap/FABRIC-ROADMAP-2026-09-18.md. The words
#: the public wording rules refuse for status (planned, being built, coming soon) are not used.
STATUS_WORDS = {"proposed": "Named, not scheduled yet", "ready": "Ready to start", "building": "In progress",
                "published": "Released, not yet verified", "blocked": "Waiting on the owner",
                "superseded": "Replaced by later work"}
#: The heading of the open steps that no delivery package holds.
OTHER_WORK = "Other open work"
#: The capabilities record's own bookkeeping fields, which say nothing about a feature.
CAPABILITY_BOOKKEEPING = ("record_type", "api_version")
#: The table rows of a Community release record that hold its package count, and those that hold its time, in order.
LIBRARY_COUNT_ROWS = ("Served", "Items served", "Items")
LIBRARY_TIME_ROWS = ("Published", "Release")
_LIBRARY_FOLDER = re.compile(r"community-release-(?:(\d+)-)?(\d{4}-\d{2}-\d{2})")
_TIME = re.compile(r"\b(\d{2}):(\d{2})(?::\d{2})? UTC\b")
_PROSE_TIME = re.compile(r"\bAt (\d{2}):(\d{2}) UTC\b")
_NUMBER = re.compile(r"\d[\d,]*")

# The cleaning rules.
#: A bracketed reference a visitor cannot follow: a roadmap step, a commit list, a run, a hash, a file or a path.
_BRACKETED = re.compile(r"\s*\((?:[^()]*?(?:\bS-\d+\.\d+|\bcommits?\b|\bruns? \d|\b[0-9a-f]{7,}\b|\.(?:py|mjs|js|json|md|ya?ml)\b"
                        r"|/)[^()]*)\)")
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_EMPHASIS = re.compile(r"\*\*([^*]+)\*\*")
#: The internal terms a line may not carry, each with the name its check reports.
INTERNAL_MARKERS = (
    ("code span", re.compile(r"`")),
    ("revision hash or digest", re.compile(r"\b(?=[0-9a-f]*[0-9])(?=[0-9a-f]*[a-f])[0-9a-f]{7,}\b")),
    ("file name", re.compile(r"\b[\w.-]+\.(?:py|mjs|cjs|js|json|jsonl|md|ya?ml|toml|sh|txt|html|css|ts)\b")),
    ("repository path", re.compile(r"(?:^|[\s(\"'])(?:\.{0,2}/)?(?:src|tools|docs|artifacts|devtools|examples|core|showcase"
                                   r"|case-studies|\.github)/")),
    ("code identifier", re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", re.IGNORECASE)),
    ("record type", re.compile(r"\b[a-z][a-z0-9_]*/v\d+\b", re.IGNORECASE)),
    ("command option", re.compile(r"(?:^|\s)--[a-z]")),
    ("run number", re.compile(r"\b\d{8,}\b")),
    # The words the task of September 26, 2026 keeps off every public page beside the shared wording rules: the runtime
    # vocabulary, the words chronicle, receipt and child for a task, the retired two-word label that asks for the
    # following step (written below with \s+, since the conformance scan refuses the phrase itself in source), and the
    # retired waiting list.
    # "Runtimes" in the plural stays allowed: the model directory's page is titled "Endpoints and local runtimes", the
    # software that serves a model, not the product's runtime.
    ("runtime vocabulary", re.compile(r"\bruntime\b|\bLoops?\b|role profiles?", re.IGNORECASE)),
    ("refused word", re.compile(r"\bchronicles?\b|\breceipts?\b|\bchild(?:ren)?\b|\bwhat\s+next\b|\bwait(?:ing )?list\b",
                                re.IGNORECASE)),
)
#: A dash between words becomes a comma, the site's own punctuation (humanizer-context.md: no em or en dashes).
_DASH = re.compile(r"\s*[—–]\s*")
_ABSOLUTE_PATH = re.compile(r"(?:^|[\s(])(/[A-Za-z0-9._~/-]*)")
_HOSTNAME = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:ai|dev|io|com|net|org|app|co|sh)\b", re.IGNORECASE)
_PRICE = re.compile(r"\$\s?\d")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


class BuildError(ValueError):
    """A record this generator cannot read without guessing, with the reason."""


def wording_rules(path: Path = WORDING_RULES):
    """The public wording rules as compiled patterns and retired phrases, read from the one file every page check imports.

    The JavaScript patterns use the part of the syntax Python shares (word boundaries, groups, alternation, the i flag).
    A rule this reader cannot find is refused, so a changed file fails here rather than passing a word it should stop."""
    text = path.read_text("utf-8")
    patterns = {}
    for name, body, flags in re.findall(r"export const (\w+)=/(.+?)/([a-z]*);", text):
        patterns[name] = re.compile(body, re.IGNORECASE if "i" in flags else 0)
    missing = [name for name in WORDING_RULE_NAMES if name not in patterns]
    phrases = re.search(r"export const retiredPhrases=(\[.*?\]);", text, re.DOTALL)
    if missing or phrases is None:
        raise BuildError(f"{path} no longer exports the wording rules {missing or ['retiredPhrases']}")
    return tuple(patterns[name] for name in WORDING_RULE_NAMES), tuple(json.loads(phrases.group(1)))


class PublicText:
    """The declared rules that decide whether a line of a record may stand on a public page."""

    def __init__(self, site_map: dict, layout: dict, rules=None):
        self.patterns, self.phrases = rules or wording_rules()
        self.addresses = {page["address"] for page in site_map["pages"]} - set(ADDRESSES)
        self.hostnames = {row["hostname"] for row in site_map["hostnames"]} | {site_map["canonical_hostname"]}
        self.plan = layout["price"]["phrase"]
        self.refused = tuple(layout["price"]["refused_phrases"])

    def problem(self, line: str) -> str:
        """The name of the first internal term the line carries, or an empty string for a line that may stand."""
        for pattern in self.patterns:
            if pattern.search(line):
                return "public wording rule"
        if any(phrase in line for phrase in self.phrases + self.refused):
            return "retired phrase"
        for name, pattern in INTERNAL_MARKERS:
            if pattern.search(line):
                return name
        for found in _ABSOLUTE_PATH.finditer(line):
            address = found.group(1).rstrip(".,;:!?)")
            if address not in self.addresses:
                return "address the site map does not list"
        for found in _HOSTNAME.finditer(line):
            if found.group(0).lower() not in self.hostnames:
                return "hostname the site map does not name"
        if _PRICE.search(line.replace(self.plan, "")):
            return "price other than the plan"
        return ""


def clean(line: str) -> str:
    """One line of a record in the form a page prints: references out, link words kept, one sentence case."""
    text = _EMPHASIS.sub(r"\1", _MARKDOWN_LINK.sub(r"\1", " ".join(str(line).split())))
    text = _DASH.sub(", ", _BRACKETED.sub("", text)).strip()
    text = re.sub(r"^(?:and|And)\s+", "", text).strip(" ;,")
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else text + "."


def split_paragraph(text: str) -> list:
    """The changes a paragraph lists: its sentences, and within a sentence the items that semicolons separate."""
    items = []
    for sentence in _SENTENCE_END.split(" ".join(str(text).split())):
        items.extend(part for part in sentence.split("; ") if part.strip())
    return items


def _moment(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _shown(lines, public: PublicText, excluded: set) -> "tuple[list, int]":
    kept, left = [], 0
    for raw in lines:
        line = clean(raw)
        if not line:
            continue
        if line in excluded or public.problem(line):
            left += 1
            continue
        if line not in kept:
            kept.append(line)
    return kept, left


def release_number(record: dict):
    """The Fly release number a release record names: `fly_release`, else `fly_release_version`, else `release`."""
    return record.get("fly_release") or record.get("fly_release_version") or record.get("release")


def raw_changes(record: dict) -> list:
    """The changes a release record states: its list of changes, and the items of its paragraph of changes."""
    raw = [item for item in record.get("changes") or [] if isinstance(item, str)]
    if isinstance(record.get("what_this_release_changes"), str):
        raw += split_paragraph(record["what_this_release_changes"])
    return raw


def service_release(record: dict, where: str, public: PublicText, excluded_lines: dict) -> dict:
    """One Fly release, from either record shape the release records use."""
    number = release_number(record)
    at = record.get("deployed_at") or record.get("observed_at")
    if not isinstance(number, int) or not isinstance(at, str):
        raise BuildError(f"{where} names no release number or no time")
    lines, left = _shown(raw_changes(record), public, excluded_lines.get(number, set()))
    seen = (record.get("observed_after_the_restart") or {}).get("customer_visible_change") or ""
    seen = clean(seen) if isinstance(seen, str) and seen else ""
    if seen and public.problem(seen):
        seen, left = "", left + 1
    return {"kind": "service", "number": number, "at": _iso(_moment(at)), "lines": lines, "seen_after_release": seen,
            "not_shown": left}


def _table_rows(text: str) -> dict:
    rows = {}
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")] if line.lstrip().startswith("|") else []
        if len(cells) >= 2 and not set(cells[0]) <= set("-: ") and cells[0] not in rows:
            rows[cells[0]] = cells[1]
    return rows


def library_release(path: Path) -> dict:
    """One Community catalogue release: its number and day from its folder, its package count and time from its table."""
    match = _LIBRARY_FOLDER.fullmatch(path.parent.name)
    if match is None:
        raise BuildError(f"{path.parent.name} is not a dated Community release folder")
    text = path.read_text("utf-8")
    rows = _table_rows(text)
    count = next((_NUMBER.search(rows[name]) for name in LIBRARY_COUNT_ROWS if name in rows and _NUMBER.search(rows[name])),
                 None)
    time = next((_TIME.search(rows[name]) for name in LIBRARY_TIME_ROWS if name in rows and _TIME.search(rows[name])),
                None) or _PROSE_TIME.search(text)
    if count is None or time is None:
        raise BuildError(f"{path.parent.name}/{path.name}: no package count in the rows {LIBRARY_COUNT_ROWS} or no time in the "
                         f"rows {LIBRARY_TIME_ROWS}")
    packages = int(count.group(0).replace(",", ""))
    at = datetime.fromisoformat(f"{match.group(2)}T{time.group(1)}:{time.group(2)}:00+00:00")
    return {"kind": "library", "number": int(match.group(1) or 1), "at": _iso(at),
            "lines": [f"{packages:,} packages served."], "seen_after_release": "", "not_shown": 0}


def changelog_bullets(text: str) -> list:
    """The top-level changelog's sections in their order, as (heading, the first sentence of each change)."""
    sections, heading, bullets = [], None, []

    def close():
        if heading is not None and bullets:
            sections.append((heading, [_SENTENCE_END.split(" ".join(bullet.split()))[0] for bullet in bullets]))

    for line in text.splitlines():
        if line.startswith("### "):
            close()
            heading, bullets = line[4:].strip(), []
        elif line.startswith("#"):
            close()
            heading, bullets = None, []
        elif heading is not None and line.startswith("- "):
            bullets.append(line[2:])
        elif heading is not None and bullets and line.startswith("  ") and line.strip():
            bullets[-1] += " " + line.strip()
    close()
    return sections


def changelog_sections(text: str, public: PublicText, excluded: "dict | None" = None) -> list:
    """The top-level changelog's sections in their order, one line for each change: the change's first sentence.

    `excluded` maps a section heading to the exact cleaned lines the reviewed exclusion list leaves out of it."""
    sections = []
    for heading, firsts in changelog_bullets(text):
        lines, left = _shown(firsts, public, (excluded or {}).get(heading, set()))
        sections.append({"heading": heading, "lines": lines, "not_shown": left})
    return sections


def changelog(public: PublicText, exclusions: dict, root: Path = ROOT) -> dict:
    excluded, excluded_earlier = {}, {}
    for row in exclusions["changelog_lines"]:
        excluded.setdefault(row["release"], set()).add(row["line"])
    for row in exclusions["earlier_lines"]:
        excluded_earlier.setdefault(row["section"], set()).add(row["line"])
    releases, found = [], set()
    for path in sorted(root.glob(RELEASE_RECORDS)):
        record = json.loads(path.read_text("utf-8"))
        releases.append(service_release(record, str(path.relative_to(root)), public, excluded))
        found.update((release_number(record), clean(item)) for item in raw_changes(record))
    releases += [library_release(path) for path in sorted(root.glob(LIBRARY_RELEASES))]
    numbers = [(release["kind"], release["number"]) for release in releases]
    if len(set(numbers)) != len(numbers):
        raise BuildError(f"two release records name the same release: {sorted(numbers)}")
    stale = sorted((number, line) for number, lines in excluded.items() for line in lines if (number, line) not in found)
    if stale:
        raise BuildError(f"the exclusion list names release lines no release record holds: {stale}")
    releases.sort(key=lambda release: (release["at"], release["kind"] == "service", release["number"]), reverse=True)
    text = (root / CHANGELOG.name).read_text("utf-8") if (root / CHANGELOG.name).is_file() else ""
    held = {(heading, clean(first)) for heading, firsts in changelog_bullets(text) for first in firsts}
    stale = sorted((heading, line) for heading, lines in excluded_earlier.items() for line in lines if (heading, line) not in held)
    if stale:
        raise BuildError(f"the exclusion list names changelog lines that CHANGELOG.md does not hold: {stale}")
    return {"releases": releases, "earlier": changelog_sections(text, public, excluded_earlier)}


def words(identifier) -> str:
    """A code identifier as plain words: registration_available becomes Registration available."""
    text = str(identifier).replace("_", " ").strip()
    return text[:1].upper() + text[1:]


def _plain_value(value) -> "str | None":
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return f"{value:,}"
    if isinstance(value, str):
        return value.replace("_", " ")
    if isinstance(value, (list, tuple)) and all(isinstance(item, (str, int)) and not isinstance(item, bool) for item in value):
        return ", ".join(str(item).replace("_", " ") for item in value) or None
    return None


def _resolved(node, module) -> "str | None":
    """A value the capabilities builder fixes in code, as plain words, or None for a value each deployment sets."""
    if isinstance(node, ast.Constant):
        return _plain_value(node.value)
    if isinstance(node, (ast.List, ast.Tuple)) and all(isinstance(item, ast.Constant) for item in node.elts):
        return _plain_value([item.value for item in node.elts])
    if isinstance(node, ast.Name) and hasattr(module, node.id):
        return _plain_value(getattr(module, node.id))
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("list", "tuple")
            and len(node.args) == 1 and isinstance(node.args[0], ast.Name) and hasattr(module, node.args[0].id)):
        return _plain_value(getattr(module, node.args[0].id))
    return None


def capabilities(source: str, module) -> list:
    """Every part of the public capabilities record as the service code builds it, read from the source of `capabilities`.

    Nothing is called: a value written in the code, or named by a constant of the module, is fixed in this release;
    every other value is set by each deployment and reported by the running service."""
    tree = ast.parse(source)
    function = next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "capabilities"), None)
    returned = None if function is None else next(
        (node.value for node in ast.walk(function) if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)), None)
    if returned is None:
        raise BuildError("http.py no longer builds the capabilities record in one dictionary returned by capabilities()")
    rows = []
    for key, value in zip(returned.keys, returned.values):
        if not isinstance(key, ast.Constant) or key.value in CAPABILITY_BOOKKEEPING:
            continue
        members = zip(value.keys, value.values) if isinstance(value, ast.Dict) else [(None, value)]
        for name, node in members:
            if name is not None and not isinstance(name, ast.Constant):
                continue
            plain = _resolved(node, module)
            rows.append({"path": key.value if name is None else f"{key.value}.{name.value}", "section": words(key.value),
                         "feature": words(name.value) if name is not None else words(key.value),
                         "value": plain or "", "fixed": plain is not None})
    return rows


def features(site_map: dict, layout: dict, public: PublicText, exclusions: dict) -> dict:
    from loop_engine.core.provisioning_server import LIBRARY_TIERS, TIER_LABELS
    from loop_engine.core.service_runtime import http as service_http
    from loop_engine.core.service_runtime.catalogue_attributes import (
        COMPONENT_FORMS, HARNESS_KINDS, WELL_KNOWN_ATTRIBUTES, component_form_label, harness_kind_label)
    from loop_engine.core.service_runtime.catalogue_tiers import TIER_MEANINGS
    groups = []
    for group in site_map["groups"]:
        pages = [{"address": page["address"], "title": page["title"], "description": page["description"]}
                 for page in site_map["pages"] if page["group"] == group and page["indexed"] and page["address"] not in ADDRESSES]
        if pages:
            groups.append({"group": group, "pages": pages})
    labels = {"tier": dict(TIER_LABELS), "harness_kind": {kind: harness_kind_label(kind) for kind in HARNESS_KINDS},
              "component_form": {form: component_form_label(form) for form in COMPONENT_FORMS}}
    attributes = [{"name": words(item["name"]), "description": item["description"], "searchable": bool(item["searchable"]),
                   "filterable": bool(item["filterable"]),
                   "choices": [labels.get(item["name"], {}).get(choice, words(choice)) for choice in item.get("choices", [])]}
                  for item in WELL_KNOWN_ATTRIBUTES]
    recipes = json.loads(CLIENT_RECIPES.read_text("utf-8"))["recipes"]
    built = capabilities(HTTP_SOURCE.read_text("utf-8"), service_http)
    excluded = {row["path"] for row in exclusions["capability_rows"]}
    unknown = sorted(excluded - {row["path"] for row in built})
    if unknown:
        raise BuildError(f"the exclusion list names parts the capabilities record does not hold: {unknown}")
    rows = [{name: row[name] for name in ("section", "feature", "value", "fixed")} for row in built
            if row["path"] not in excluded and not public.problem(" ".join((row["section"], row["feature"], row["value"])))]
    return {"plan": layout["price"]["phrase"], "page_groups": groups,
            "harness_kinds": [harness_kind_label(kind) for kind in HARNESS_KINDS],
            "tiers": [{"label": TIER_LABELS[tier], "meaning": TIER_MEANINGS[tier]} for tier in LIBRARY_TIERS],
            "attributes": attributes, "harnesses": [recipe["name"] for recipe in recipes], "capabilities": rows}


def todo(roadmap: dict, exclusions: dict, public: PublicText) -> dict:
    steps = roadmap["steps"]
    by_id = {step["id"]: step for step in steps}
    plan = roadmap["continuation"]
    position = {identity: index for index, identity in enumerate(plan["launch_order"] + plan["improvement_order"])}
    excluded = [row["step"] for row in exclusions["todo_steps"]]
    unknown = sorted(set(excluded) - set(by_id))
    if unknown or len(set(excluded)) != len(excluded):
        raise BuildError(f"the exclusion list names steps the roadmap does not hold, or names one twice: {unknown}")
    unknown = sorted({step["status"] for step in steps} - set(STATUS_WORDS) - set(DONE_STATUSES))
    if unknown:
        raise BuildError(f"the roadmap uses statuses that have no plain words here: {unknown}")
    open_ids = [step["id"] for step in steps if step["status"] not in DONE_STATUSES]
    order = {identity: (position.get(identity, len(position)), index) for index, identity in enumerate(by_id)}

    def row(identity):
        step = by_id[identity]
        if identity in excluded or public.problem(step["title"]):
            return None
        return {"step": identity, "title": step["title"], "status": STATUS_WORDS[step["status"]]}

    packages = sorted(plan["delivery_batches"],
                      key=lambda batch: (min(order[identity] for identity in batch["steps"]), batch["id"]))
    placed, groups = set(), []
    for batch in packages:
        members = sorted((identity for identity in batch["steps"] if identity in open_ids and identity not in placed),
                         key=order.get)
        placed.update(members)
        rows = [item for item in map(row, members) if item]
        if rows:
            title = batch["title"] if not public.problem(batch["title"]) else f"Delivery package {int(batch['id'][2:])}"
            groups.append({"title": title, "steps": rows})
    rest = [item for item in map(row, sorted((identity for identity in open_ids if identity not in placed), key=order.get))
            if item]
    if rest:
        groups.append({"title": OTHER_WORK, "steps": rest})
    return {"steps": len(steps), "live": sum(1 for step in steps if step["status"] == "live_qualified"),
            "checked": sum(1 for step in steps if step["status"] == "offline_verified"), "open": len(open_ids),
            "listed": sum(len(group["steps"]) for group in groups), "groups": groups}


def load_exclusions(path: Path = EXCLUSIONS) -> dict:
    """The reviewed exclusion list, refused when a field, an entry's reason or the statement of its review is missing."""
    value = json.loads(path.read_text("utf-8"))
    fields = {"record_type", "purpose", "rule", "review", "reviews", "todo_steps", "changelog_lines", "earlier_lines",
              "capability_rows"}
    if not isinstance(value, dict) or set(value) != fields or value["record_type"] != EXCLUSIONS_RECORD_TYPE:
        raise BuildError(f"{path} is not a {EXCLUSIONS_RECORD_TYPE} record with the fields {sorted(fields)}")
    if "reviewed by a person or by an independent verifier" not in value["review"]:
        raise BuildError(f"{path} must state that a person or an independent verifier reviews the list")
    if not isinstance(value["reviews"], list) or any(
            not isinstance(row, dict) or set(row) != {"reviewer", "date", "entries"} or not str(row["reviewer"]).strip()
            or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row["date"])) or not isinstance(row["entries"], list)
            for row in value["reviews"]):
        raise BuildError(f"{path}: each review names its reviewer, its date and the entries it covered")
    for row in value["todo_steps"]:
        if not isinstance(row, dict) or set(row) != {"step", "reason"} or not str(row["reason"]).strip():
            raise BuildError(f"{path}: each step entry names the step and one reason")
    for row in value["changelog_lines"]:
        if (not isinstance(row, dict) or set(row) != {"release", "line", "reason"} or not isinstance(row["release"], int)
                or not str(row["reason"]).strip()):
            raise BuildError(f"{path}: each line entry names the release, the exact line and one reason")
    for row in value["earlier_lines"]:
        if (not isinstance(row, dict) or set(row) != {"section", "line", "reason"} or not str(row["section"]).strip()
                or not str(row["reason"]).strip()):
            raise BuildError(f"{path}: each changelog entry names the section, the exact line and one reason")
    for row in value["capability_rows"]:
        if (not isinstance(row, dict) or set(row) != {"path", "reason"} or not re.fullmatch(r"[a-z_]+(?:\.[a-z_]+)?", str(row["path"]))
                or not str(row["reason"]).strip()):
            raise BuildError(f"{path}: each capability entry names the part of the record and one reason")
    return value


_PARSED: dict = {}


def load_roadmap(path: Path = ROADMAP):
    """The roadmap as data. The C loader of PyYAML, when installed, reads the same values about nine times faster than
    the pure one; a parse is kept for the exact bytes it read, so a changed file is always read again."""
    raw = path.read_bytes()
    key = (str(path), hashlib.sha256(raw).hexdigest())
    if key not in _PARSED:
        _PARSED.clear()
        _PARSED[key] = yaml.load(raw.decode("utf-8"), Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    return copy.deepcopy(_PARSED[key])


def load_roadmap_titles(path: Path = ROADMAP) -> dict:
    """Each roadmap step's title by its identity, as the open work page prints it."""
    return {step["id"]: step["title"] for step in load_roadmap(path)["steps"]}


def build(root: Path = ROOT) -> dict:
    """The whole record, from the records as they stand in the checkout."""
    site_map = json.loads(SITE_MAP.read_text("utf-8"))
    layout = json.loads(LAYOUT_STANDARD.read_text("utf-8"))
    public = PublicText(site_map, layout)
    exclusions = load_exclusions()
    roadmap = load_roadmap()
    return {"record_type": RECORD_TYPE, "generated_by": GENERATED_BY, "changelog": changelog(public, exclusions, root),
            "features": features(site_map, layout, public, exclusions), "todo": todo(roadmap, exclusions, public)}


def render(value: dict) -> str:
    return json.dumps(value, indent=1, ensure_ascii=False) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 when the committed record is stale")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        text = render(build())
    except (BuildError, KeyError, TypeError, ValueError, yaml.YAMLError) as error:
        sys.stderr.write(f"The public status pages cannot be built: {error}\n")
        return 2
    from loop_engine.core.service_runtime.status_pages import page_record_from_value
    page_record_from_value(json.loads(text))
    if args.check:
        if not args.output.is_file() or args.output.read_text("utf-8") != text:
            sys.stderr.write(f"{args.output} is stale; run python tools/build_public_status_pages.py\n")
            return 1
        print(f"{args.output} is current")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, "utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
