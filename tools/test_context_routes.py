"""Offline checks for active context routes and byte-preserved prior guidance.

Markdown parsing uses the installed markdown-it-py parser. Link checks cover
local Markdown/image targets and Markdown heading or explicit HTML anchors.
They do not fetch remote URLs, execute example code, inspect private logs, or
establish runtime behavior. Source checks and provider checks remain separate.
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
        for stale in ("Commit and push verified changes", "commit and push verified changes",
                      "The current provider direction is Ollama Cloud after",
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


class ContextRouteTests(unittest.TestCase):
    def setUp(self):
        self.documents = {path: (ROOT / path).read_text(encoding="utf-8") for path in ACTIVE}

    def test_active_routes_keep_current_authority_and_negotiation(self):
        self.assertEqual(route_findings(self.documents), [])

    def test_old_publish_instruction_is_detected(self):
        changed = dict(self.documents)
        changed["ASTRA.md"] += "\nCommit and push verified changes to main in the same turn.\n"
        self.assertTrue(route_findings(changed))

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
