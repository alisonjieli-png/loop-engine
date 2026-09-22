"""Offline checks for active context routes and byte-preserved prior guidance.

Markdown parsing uses the installed markdown-it-py parser. Link checks cover
local Markdown/image targets and Markdown heading or explicit HTML anchors.
They do not fetch remote URLs, execute example code, inspect private logs, or
establish runtime behavior. Source checks and provider checks remain separate.

The owner's standing rules for committing, pushing, branching and releasing
live in one section of AGENTS.md. On September 19, 2026 a sub-agent replaced
the owner's commit rule in the start documents with its opposite, without an
owner request, and added a check here that protected the replacement. The
authority checks below hold the opposite line: every entry route links the one
section, no entry route restates it under a heading of its own, no route
document withholds commit or push authority or sends work to a side branch,
and the section keeps each owner rule with its words and its date.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = "docs/evidence/context-route-snapshot-2026-09-19"
ACTIVE = (
    "ASTRA.md", "docs/context/START-HERE.md", "docs/context/CODEX-START-HERE.md",
    "docs/README.md", "docs/contracts/README.md",
    "docs/components/loop-object/RECORD-COMPATIBILITY.md",
)
PARSER = MarkdownIt("commonmark")

AUTHORITY_SOURCE = "AGENTS.md"
AUTHORITY_HEADING = "Commit, push and release authority"
AUTHORITY_ANCHOR = "commit-push-and-release-authority"
#: Where a person or an agent is told to begin. Each one links the authority
#: section and carries no commit, push or release rule of its own.
ENTRY_ROUTES = (
    "CLAUDE.md", "ASTRA.md", "docs/context/START-HERE.md",
    "docs/context/CODEX-START-HERE.md", "docs/README.md",
)
#: Every document held to the authority section: the section's own file, the
#: entry routes and the other active context routes.
AUTHORITY_SCOPE = tuple(dict.fromkeys((AUTHORITY_SOURCE, *ENTRY_ROUTES, *ACTIVE)))
#: The owner's standing rules that the section must keep, each by the words
#: that carry it and the date the owner gave it. A rewrite that drops one fails
#: under the rule's name.
AUTHORITY_RULES = (
    ("commit_and_push_reviewed_work",
     ("Commit reviewed work to `main` and push it",
      'September 2, 2026: "stop asking me to push, when you fix something you push!"',
      '"push improvements into production/main branch"')),
    ("two_branches_and_no_others",
     ("`main`, and `checkpoint/full-capability-2026-09-21`",
      "Make no feature, fork or worktree branch",
      '"Only the snapshot should survive as a backup branch"')),
    ("guarded_release_then_live_checks",
     ("whose continuous integration run passed", "`.github/workflows/fly-pilot.yml`",
      "every hostname", 'September 22, 2026: "make sure we are deploying and updating fly.io"')),
    ("decide_instead_of_asking",
     ("Decide instead of asking", "September 20, 2026, in the evening",
      '"Use your best judgement, document it"')),
    ("never_suggest_rotating_a_credential",
     ("Never tell the owner to rotate, revoke or re-create a credential",
      'September 21, 2026: "NEVER tell me to rotate or revoke an API key"')),
    ("swappable_engines_and_prior_art",
     ("so that its engine can be swapped",
      "search existing projects, repositories, published designs and papers",
      '"projects, repos, github, designs, or papers that we could use / leverage so we '
      "don't have to reinvent the wheel\"")),
    ("destructive_operations_need_the_owner",
     ("destroying or deleting an application, a volume, a domain record, a name "
      "server delegation, a provider resource or a secret",)),
    ("spending_beyond_the_allowance_needs_the_owner",
     ("spending beyond the recorded allowance",)),
    ("legal_commitments_need_the_owner", ("a legal commitment",)),
    ("identity_or_bank_verification_needs_the_owner", ("identity or bank verification",)),
)
_COMMIT_WORD = r"(?:commit(?:s|ted|ting)?|push(?:es|ed|ing)?)"
#: Sentence shapes that withhold the standing commit and push authority. Each
#: is refused even when a writer means something narrower; a narrower rule is
#: stated positively, as the authority section does.
CONTRARY_COMMIT_RULES = (
    ("standing_instructions_withhold_commit_authority", re.compile(
        r"\b(?:no|not|never|nothing|none)\b[^.;:!?]*\b(?:authori[sz]\w*|grant\w*)\b[^.;:!?]*\b"
        + _COMMIT_WORD + r"\b")),
    ("commit_needs_a_separate_grant", re.compile(
        r"\b" + _COMMIT_WORD + r"\b[^.;:!?]*\b(?:without|unless)\b[^.;:!?]*\b"
        r"(?:explicit(?:ly)?|separate(?:ly)?|specific(?:ally)?|further|additional)\b")),
    ("ask_before_committing", re.compile(
        r"\bask\w*\b[^.;:!?]*\bbefore\b[^.;:!?]*\b" + _COMMIT_WORD + r"\b")),
    ("commit_or_push_forbidden", re.compile(
        r"\b(?:do not|don't|never|must not|may not|cannot)\s+" + _COMMIT_WORD
        + r"\b(?:\s*,\s*\w+)*(?:,?\s+(?:or|and)\s+\w+)?\s*(?:[.;!]|$|\b(?:reviewed|verified|"
        r"finished|changes|work|anything|to main|to github|to origin|the (?:work|change|changes|"
        r"result|fix))\b)")),
)
#: A branch outside `main` and the checkpoint, named where no negation precedes it.
SIDE_BRANCH = re.compile(
    r"\b(?:(?:feature|topic|fork|side|task|personal|separate)[ -]branch(?:es)?"
    r"|own (?:git )?branch(?:es)?)\b")
NEGATION = re.compile(r"\b(?:no|not|never|nor|without|instead of|rather than)\b")


class HtmlReferences(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []
        self.anchors = set()

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        self.anchors.update(value for key, value in attrs if key in ("id", "name") and value)
        if tag == "a" and fields.get("href"):
            self.references.append(fields["href"])
        if tag == "img" and fields.get("src"):
            self.references.append(fields["src"])


def markdown_references(text):
    """Return parsed references with approximate source line and heading anchors."""
    references, anchors, used = [], set(), {}
    tokens = PARSER.parse(text)
    for index, token in enumerate(tokens):
        line = token.map[0] + 1 if token.map else 1
        if token.type == "heading_open" and index + 1 < len(tokens):
            inline = tokens[index + 1]
            words = "".join(child.content for child in inline.children or ()
                            if child.type in ("text", "code_inline"))
            slug = re.sub(r"[^\w\- ]", "", words.lower()).replace(" ", "-")
            count = used.get(slug, 0)
            used[slug] = count + 1
            anchors.add(slug + (f"-{count}" if count else ""))
        for child in (token, *(token.children or ())):
            if child.type == "link_open":
                references.append((line, child.attrGet("href")))
            elif child.type == "image":
                references.append((line, child.attrGet("src")))
            elif child.type in ("html_block", "html_inline"):
                parsed = HtmlReferences()
                parsed.feed(child.content)
                references.extend((line, value) for value in parsed.references)
                anchors.update(parsed.anchors)
    return references, anchors


def local_link_findings(root, paths, *, overrides=None, incoming_targets=None):
    """Check local file and Markdown fragment targets without network access."""
    overrides = overrides or {}
    findings, anchor_cache = [], {}
    checked = 0
    for name in paths:
        path = root / name
        text = overrides.get(name, path.read_text(encoding="utf-8"))
        references, _ = markdown_references(text)
        for line, href in references:
            if not href:
                continue
            parsed = urlsplit(href)
            if parsed.scheme or parsed.netloc:
                continue
            location = unquote(parsed.path)
            target = ((root / location.lstrip("/")) if location.startswith("/")
                      else path.parent / location if location else path)
            target = target.resolve()
            try:
                target_name = target.relative_to(root.resolve()).as_posix()
            except ValueError:
                target_name = str(target)
            if incoming_targets is not None and target_name not in incoming_targets:
                continue
            checked += 1
            if not target.exists():
                findings.append({"path": name, "line": line, "target": href, "reason": "missing_local_target"})
                continue
            if parsed.fragment and target.suffix.lower() == ".md" and target.is_file():
                if target_name not in anchor_cache:
                    target_text = overrides.get(target_name, target.read_text(encoding="utf-8"))
                    anchor_cache[target_name] = markdown_references(target_text)[1]
                fragment = unquote(parsed.fragment)
                if fragment not in anchor_cache[target_name]:
                    findings.append({"path": name, "line": line, "target": href,
                                     "reason": "missing_markdown_fragment"})
    return {"files": len(paths), "local_links_checked": checked, "findings": findings,
            "limitations": "No remote URLs, dynamic HTML, JavaScript routes, or code examples executed; GitHub-style Markdown heading slugs are locally approximated."}


def route_findings(documents):
    findings = []
    for path, text in documents.items():
        flat = " ".join(text.split())
        for stale in ("The current provider direction is Ollama Cloud after",
                      "saved v3, v4, and v5 records remain readable",
                      "When the target model is GPT-6 Astra, also read"):
            if stale in flat:
                findings.append((path, "stale_current_instruction", stale))
    for path in ("docs/context/START-HERE.md", "docs/context/CODEX-START-HERE.md", "ASTRA.md"):
        text = documents.get(path, "")
        for needed in ("CONTINUATION-AND-LAUNCH.md", "CONTINUATION-STATUS.md",
                       "MVP-CLIENT-SERVER.md", "ADR-PRELAUNCH-VERSIONED-CONTRACTS.md",
                       "DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md"):
            if needed not in text:
                findings.append((path, "missing_current_route", needed))
        flat = " ".join(text.lower().split())
        if "runtime" not in flat or "negotiation" not in flat or "independently deployed" not in flat:
            findings.append((path, "runtime_negotiation_requirement_missing", ""))
    return findings


def authority_section(text):
    """The body of the authority section of AGENTS.md, or an empty string."""
    lines = text.splitlines()
    heading = "## " + AUTHORITY_HEADING
    if heading not in lines:
        return ""
    start = lines.index(heading) + 1
    end = next((index for index in range(start, len(lines)) if lines[index].startswith("## ")),
               len(lines))
    return "\n".join(lines[start:end])


def statement_units(text):
    """Sentences, list items and table cells, lowercased, ready for the rule patterns.

    Fenced code and link targets are removed, and the section's own name is
    replaced, so a link to the section never reads as a statement about commits.
    """
    text = re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(re.escape(AUTHORITY_HEADING), "the authority section", text, flags=re.IGNORECASE)
    units = []
    for block in re.split(r"\n\s*\n|\n(?=\s*(?:[-*+]|\d+\.)\s)|\|", text):
        flat = " ".join(block.split()).lower()
        units.extend(part for part in re.split(r"(?<=[.!?])\s+", flat) if part)
    return units


def links_to_authority(root, name, text):
    """True when the document links the authority section of AGENTS.md."""
    base = (root / name).parent
    for _, href in markdown_references(text)[0]:
        if not href:
            continue
        parsed = urlsplit(href)
        if parsed.scheme or parsed.netloc or unquote(parsed.fragment) != AUTHORITY_ANCHOR:
            continue
        location = unquote(parsed.path)
        target = (root / location.lstrip("/")) if location.startswith("/") else base / location
        if target.resolve() == (root / AUTHORITY_SOURCE).resolve():
            return True
    return False


def authority_findings(documents, root=ROOT):
    """Findings that break the one authority section or the routes that point to it.

    ``documents`` maps a repository path to its text and must hold every path in
    ``AUTHORITY_SCOPE``. Each finding is (path, reason, detail).
    """
    findings = []
    source = documents[AUTHORITY_SOURCE]
    section = " ".join(re.sub(r"\]\([^)]*\)", "]", authority_section(source)).split()).lower()
    if not section or AUTHORITY_ANCHOR not in markdown_references(source)[1]:
        findings.append((AUTHORITY_SOURCE, "authority_section_missing", AUTHORITY_ANCHOR))
    for rule, phrases in AUTHORITY_RULES:
        for phrase in phrases:
            if " ".join(phrase.split()).lower() not in section:
                findings.append((AUTHORITY_SOURCE, "owner_rule_missing", f"{rule}: {phrase}"))
    for path in ENTRY_ROUTES:
        text = documents[path]
        if not links_to_authority(root, path, text):
            findings.append((path, "authority_route_missing", AUTHORITY_ANCHOR))
        prose = re.sub(r"^```.*?^```", "", text, flags=re.MULTILINE | re.DOTALL)
        for line in prose.splitlines():
            if re.match(r"#{1,6}\s", line) and "authority" in line.lower():
                findings.append((path, "authority_restated_under_own_heading", line.strip()))
    for path in AUTHORITY_SCOPE:
        for unit in statement_units(documents[path]):
            for reason, pattern in CONTRARY_COMMIT_RULES:
                if pattern.search(unit):
                    findings.append((path, "contradicts_commit_authority", f"{reason}: {unit[:160]}"))
            for match in SIDE_BRANCH.finditer(unit):
                if not NEGATION.search(unit[:match.start()]):
                    findings.append((path, "branch_outside_main_and_checkpoint", unit[:160]))
    return findings


def snapshot_findings(manifest, read_bytes):
    findings = []
    for row in manifest["files"]:
        if hashlib.sha256(read_bytes(row["snapshot_path"])).hexdigest() != row["sha256"]:
            findings.append(row["snapshot_path"])
    return findings


def owner_explanation(text):
    return text.split("## Complete behavioral explanation\n")[1].split(
        "\n## Runtime classification\n")[0].strip()


def documentation_scope(root):
    named = ("AGENTS.md", "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
             "humanizer-context.md", "showcase/README.md")
    paths = [name for name in named if (root / name).is_file()]
    for pattern in ("docs/**/*.md", "case-studies/*.md", "examples/**/*.md"):
        paths.extend(path.relative_to(root).as_posix() for path in root.glob(pattern) if path.is_file())
    return sorted(set(paths))


#: The sentences that withheld the owner's commit rule, as a sub-agent wrote them
#: into the start documents on September 19, 2026, and the older prompt forms.
WITHHELD_COMMIT_AUTHORITY = (
    "No standing instruction here authorizes a commit, push, live trial, or publication.",
    "A historical instruction does not authorize a commit, push, provider call, deployment, "
    "or repeated effect.",
    "Do not commit or push without explicit authority for the current task.",
    "Do not commit or push unless explicitly instructed.",
    "Ask the owner before you commit or push reviewed work.",
    "Never commit, push, or merge.",
    "Advice here does not grant model, network, file, spending, deployment, commit, or "
    "publication authority.",
)
#: Sentences that agree with the authority section and must not be flagged.
CONSISTENT_WITH_AUTHORITY = (
    "Commit and push verified changes to main in the same turn.",
    "A historical instruction does not authorize a provider call, a deployment or a "
    "repeated effect beyond the recorded authority.",
    "Do not commit secrets or bake them into a container image.",
    "Never push a revision whose checks failed.",
    "Advice here grants no authority of its own.",
    "Parallel agents work in detached worktrees, which make no branch.",
    "Treat existing changes as user or concurrent-agent work. Do not discard, restore, "
    "reformat, commit, or publish changes without resolving ownership.",
    "Unknown calls, tokens, costs, commit outcomes, and deployment status remain unknown.",
)


class ContextRouteTests(unittest.TestCase):
    def setUp(self):
        self.documents = {path: (ROOT / path).read_text(encoding="utf-8") for path in ACTIVE}
        self.authority_documents = {
            path: (ROOT / path).read_text(encoding="utf-8") for path in AUTHORITY_SCOPE}

    def test_active_routes_keep_current_authority_and_negotiation(self):
        self.assertEqual(route_findings(self.documents), [])

    def test_every_route_follows_the_one_authority_section(self):
        self.assertEqual(authority_findings(self.authority_documents), [])

    def test_owner_commit_rule_is_not_treated_as_stale(self):
        # The check this replaces refused the owner's own words of September 2.
        for path in ENTRY_ROUTES:
            changed = dict(self.authority_documents)
            changed[path] += "\n\nCommit and push verified changes to main in the same turn.\n"
            self.assertEqual(authority_findings(changed), [], path)
            if path in ACTIVE:
                self.assertEqual(route_findings({**self.documents, path: changed[path]}), [], path)

    def test_withheld_commit_authority_is_detected_in_every_route(self):
        for path in AUTHORITY_SCOPE:
            for sentence in WITHHELD_COMMIT_AUTHORITY:
                changed = dict(self.authority_documents)
                changed[path] += "\n\n" + sentence + "\n"
                reasons = {(row[0], row[1]) for row in authority_findings(changed)}
                self.assertIn((path, "contradicts_commit_authority"), reasons, (path, sentence))

    def test_consistent_sentences_are_not_flagged(self):
        changed = dict(self.authority_documents)
        changed["docs/context/START-HERE.md"] += "\n\n" + "\n\n".join(CONSISTENT_WITH_AUTHORITY) + "\n"
        self.assertEqual(authority_findings(changed), [])

    def test_lost_authority_link_is_detected(self):
        for path in ENTRY_ROUTES:
            changed = dict(self.authority_documents)
            changed[path] = changed[path].replace("#" + AUTHORITY_ANCHOR, "")
            self.assertIn((path, "authority_route_missing", AUTHORITY_ANCHOR),
                          authority_findings(changed), path)

    def test_restated_authority_section_is_detected(self):
        changed = dict(self.authority_documents)
        changed["CLAUDE.md"] += "\n## Authority recorded on September 20, 2026\n\nDetails.\n"
        self.assertIn("authority_restated_under_own_heading",
                      {row[1] for row in authority_findings(changed) if row[0] == "CLAUDE.md"})

    def test_side_branch_instruction_is_detected(self):
        changed = dict(self.authority_documents)
        changed["docs/README.md"] += "\n\nEach agent works on its own branch and opens a pull request.\n"
        self.assertIn(("docs/README.md", "branch_outside_main_and_checkpoint"),
                      {(row[0], row[1]) for row in authority_findings(changed)})

    def test_each_dropped_owner_rule_is_detected_by_name(self):
        source = self.authority_documents[AUTHORITY_SOURCE]
        section = authority_section(source)
        flat = " ".join(section.split())
        for rule, phrases in AUTHORITY_RULES:
            for phrase in phrases:
                words = re.escape(" ".join(phrase.split()))
                removed, count = re.subn(words, "", flat, flags=re.IGNORECASE)
                self.assertGreater(count, 0, (rule, phrase))
                changed = dict(self.authority_documents)
                changed[AUTHORITY_SOURCE] = source.replace(section, removed + "\n")
                self.assertIn((AUTHORITY_SOURCE, "owner_rule_missing", f"{rule}: {phrase}"),
                              authority_findings(changed), (rule, phrase))

    def test_missing_authority_section_is_detected(self):
        changed = dict(self.authority_documents)
        changed[AUTHORITY_SOURCE] = changed[AUTHORITY_SOURCE].replace(
            "## " + AUTHORITY_HEADING, "## Release notes")
        reasons = {row[1] for row in authority_findings(changed)}
        self.assertIn("authority_section_missing", reasons)
        self.assertIn("owner_rule_missing", reasons)

    def test_entry_route_links_resolve(self):
        self.assertEqual(local_link_findings(ROOT, list(ENTRY_ROUTES))["findings"], [])

    def test_old_outcome_reader_promise_is_detected(self):
        changed = dict(self.documents)
        changed["docs/contracts/README.md"] += "\nsaved v3, v4, and v5 records remain readable.\n"
        self.assertTrue(route_findings(changed))

    def test_lost_current_route_is_detected(self):
        changed = dict(self.documents)
        changed["docs/context/START-HERE.md"] = changed["docs/context/START-HERE.md"].replace(
            "CONTINUATION-STATUS.md", "obsolete-snapshot.md")
        self.assertTrue(route_findings(changed))

    def test_snapshots_are_exact_original_bytes_and_not_active_imports(self):
        manifest = json.loads((ROOT / SNAPSHOT / "manifest.json").read_text())
        self.assertEqual({row["original_path"] for row in manifest["files"]}, set(ACTIVE))
        for row in manifest["files"]:
            self.assertTrue(row["snapshot_path"].endswith(".md.txt"))
        self.assertEqual(snapshot_findings(manifest, lambda path: (ROOT / path).read_bytes()), [])
        for path in ("AGENTS.md", "CLAUDE.md"):
            for line in (ROOT / path).read_text().splitlines():
                if line.startswith("@"):
                    self.assertNotIn("evidence/", line)

    def test_changed_snapshot_is_detectable(self):
        manifest = json.loads((ROOT / SNAPSHOT / "manifest.json").read_text())
        first = manifest["files"][0]["snapshot_path"]
        def changed(path):
            value = (ROOT / path).read_bytes()
            return value + b"changed" if path == first else value
        self.assertEqual(snapshot_findings(manifest, changed), [first])

    def test_complete_owner_explanation_and_public_anchor_are_preserved(self):
        before = (ROOT / SNAPSHOT / "ASTRA.md.txt").read_text()
        self.assertEqual(owner_explanation(before), owner_explanation(self.documents["ASTRA.md"]))
        self.assertIn("complete-behavioral-explanation", markdown_references(self.documents["ASTRA.md"])[1])

    def test_removing_owner_behavior_from_the_explanation_is_detectable(self):
        before = (ROOT / SNAPSHOT / "ASTRA.md.txt").read_text()
        after = self.documents["ASTRA.md"].replace(
            "Publishing an output does not necessarily mean that the producing assignment\nhas finished.", "")
        self.assertNotEqual(after, self.documents["ASTRA.md"])
        self.assertNotEqual(owner_explanation(before), owner_explanation(after))

    def test_active_links_and_existing_incoming_anchors_resolve(self):
        self.assertEqual(local_link_findings(ROOT, list(ACTIVE))["findings"], [])
        self.assertEqual(local_link_findings(ROOT, documentation_scope(ROOT), incoming_targets=set(ACTIVE))["findings"], [])

    def test_missing_file_and_fragment_controls_are_detected(self):
        changed = self.documents["ASTRA.md"] + "\n[missing](docs/no-such-context-route.md)\n[anchor](#no-such-anchor)\n"
        findings = local_link_findings(ROOT, ["ASTRA.md"], overrides={"ASTRA.md": changed})["findings"]
        self.assertEqual({row["reason"] for row in findings}, {"missing_local_target", "missing_markdown_fragment"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--links", action="store_true", help="check the full documentation local-link scope")
    args, remaining = parser.parse_known_args()
    if args.links:
        report = local_link_findings(ROOT, documentation_scope(ROOT))
        print(json.dumps(report, indent=2, sort_keys=True))
        raise SystemExit(1 if report["findings"] else 0)
    unittest.main(argv=[__file__, *remaining])
