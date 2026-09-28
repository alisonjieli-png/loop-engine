"""Write the recorded demonstration steps from this release's library.

The homepage hero and the demonstration pages show real searches of the packaged
library, and ``tools/test_homepage_demonstration.py`` and
``tools/test_showcase_pages.py`` rerun those searches and compare every recorded
reference with what the search returns now. The recorded values were written by
hand, so every change to a packaged body moved the digests, sizes, kinds and
licences underneath them and the checks failed with a known-wrong page beside
the real one. This tool writes the record from the library instead, so the
record cannot drift from the release it describes.

It changes only the recorded facts of a reference: its kind, licence, size and
digest. It never invents an identity, never reorders results, never adds or
removes a step, and never touches a query, a choice or the folder the step
places files in. Running it on an unchanged library is a no-op, which is what
makes it safe to run on every release.

    PYTHONPATH=src:tools python tools/record_demonstration_steps.py --check
    PYTHONPATH=src:tools python tools/record_demonstration_steps.py --write
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_homepage_demonstration import shown_size  # noqa: E402

ASSETS = Path(__file__).resolve().parents[1] / "src" / "loop_engine" / "core" / "service_runtime" / "web_assets"
PAGE = ASSETS / "index.html"
RELEASE = (
    Path(__file__).resolve().parents[1]
    / "examples" / "29_intelligence_service" / "starter-catalogue" / "host-release"
)

#: One recorded reference as the page writes it: the element that names it, then
#: each fact it shows, and the digest, which the page writes as a prefix.
_ITEM = re.compile(
    r'(?P<head><li data-demo-item="(?P<identity>[a-z0-9_]+)")'
    r"(?P<middle>.*?)(?P<tail></li>)",
    re.DOTALL,
)
_KIND = re.compile(r'(<span data-fact="kind">)(?P<value>.*?)(</span>)')
_LICENCE = re.compile(r'(<span data-fact="licence">)(?P<value>.*?)(</span>)')
_SIZE = re.compile(r'(<span data-fact="size">)(?P<value>.*?)(</span>)')
_DIGEST = re.compile(r'(<span data-fact="digest">)(?P<value>[0-9a-f]{8,64})')


def released_items() -> dict[str, dict[str, Any]]:
    """This release's references by identity, from the packaged manifest."""
    manifest = json.loads((RELEASE / "manifest.json").read_text(encoding="utf-8"))
    return {row["reference"]["identity"]: row["reference"] for row in manifest["items"]}


def _sub(pattern: "re.Pattern[str]", text: str, value: str) -> tuple[str, bool]:
    """Put one fact in the page's own place, and say whether the page changed."""
    found = pattern.search(text)
    if found is None:
        return text, False
    start, end = found.span("value")
    replaced = text[:start] + value + text[end:]
    return replaced, replaced != text


def _record_one(item_html: str, reference: dict[str, Any]) -> tuple[str, list[str]]:
    """Write the four recorded facts of one reference; report every fact it did not hold."""
    changed = False
    problems: list[str] = []
    for pattern, expected, label in (
        (_KIND, reference.get("kind"), "kind"),
        (_LICENCE, reference.get("license", reference.get("licence")), "licence"),
        (_SIZE, shown_size(reference["size_bytes"]), "size"),
    ):
        found = pattern.search(item_html)
        if found is None:
            problems.append(f"the page shows no {label}")
            continue
        if found.group("value") != expected:
            item_html, wrote = _sub(pattern, item_html, expected)
            changed = changed or wrote
    digest = pattern_digest = _DIGEST.search(item_html)
    served = reference["digest"]
    if digest is None:
        problems.append("the page shows no sha256")
    elif not str(served).startswith(digest.group("value")):
        item_html, wrote = _sub(_DIGEST, item_html, str(served)[:8])
        changed = changed or wrote
    del pattern_digest
    return item_html, (problems if not changed else [])


def _rewrite(html: str) -> tuple[str, list[str]]:
    items = released_items()
    problems: list[str] = []

    def one(match: "re.Match[str]") -> str:
        identity = match.group("identity")
        reference = items.get(identity)
        if reference is None:
            problems.append(f"this release has no reference {identity}")
            return match.group(0)
        body, held = _record_one(match.group("middle"), reference)
        for text in held:
            problems.append(f"{identity}: {text}")
        return match.group("head") + body + match.group("tail")

    return _ITEM.sub(one, html), problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--write", action="store_true", help="write the record back to the page")
    parser.add_argument("--check", action="store_true", help="report drift and fail, without writing")
    args = parser.parse_args()

    page = PAGE.read_text(encoding="utf-8")
    written, problems = _rewrite(page)
    changed = written != page
    if args.write and changed:
        PAGE.write_text(written, encoding="utf-8")
    if args.check and changed:
        print("the recorded demonstrations do not match this release's library:")
        for problem in problems[:20]:
            print("  ", problem)
        print("run tools/record_demonstration_steps.py --write")
    if changed:
        print("recorded demonstrations updated" if args.write else "recorded demonstrations are stale")
    else:
        print("recorded demonstrations already match this release")
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
