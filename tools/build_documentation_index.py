"""Build the website's documentation pages from the Markdown pages the index names.

Kind: development tool. The website's Documentation view reads one versioned
data file, `web_assets/documentation-index.json`. It names the sections, the
pages, their order, their titles, their one-line summaries and the address of
each. This tool reads that index, converts each page it names from the
Markdown under `docs/guides/` into a bounded subset of HTML, and writes two
things:

- one body file for each page, under `web_assets/docs/`, which the service
  serves at the page's body address and the view places inside the site's one
  header and footer;
- `documentation_pages.json`, the record of what was built: for each page the
  Markdown it came from, the digest of that Markdown and the digest of the
  body built from it.

An index entry is one of two things. A page with a `body` is built here and
read at `/docs/` followed by its identity. A page without one is another page
of the website, such as the setup guide at `/setup`; the view links to it and
nothing is built for it. Its `repository_path`, when it names one, is the
Markdown that the website page stands for, so a link to that Markdown opens
the website page.

Nothing here infers a page from a file name. A page that the index names and
that does not exist is a failure, not a shorter list.

The converter is strict. It understands headings, paragraphs, fenced code
blocks, tables, unordered and ordered lists, and three inline forms: code
spans, bold text and links. Anything else raises `DocumentationBuildError`
instead of being dropped or passed through. Every link is resolved here, once:

- a link to a page the index names opens that page on the website, and an
  anchor in it must name a heading of that page;
- a link to `https://app.baltor.ai` followed by an address the service serves
  as a page opens that page on the same origin, so it works on every hostname;
- a link to any other repository file opens that file in the repository on
  the web, at the address `pyproject.toml` names as the project's home;
- any other web address opens in a new tab.

The first line of a page is its title and the paragraph after it states the
document's kind for this repository. The index gives the website's title and
summary instead, so both are recorded in `documentation_pages.json` and left
out of the served body.

It reads and writes files. It starts no server, opens no connection and needs
no credential. It is not a runtime boundary and grants no authority.

Build the served files:

    python tools/build_documentation_index.py --repository .

Check that the served files match the pages without writing anything:

    python tools/build_documentation_index.py --repository . --check
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import posixpath
import re
import sys
from datetime import date
from html import escape
from pathlib import Path

INDEX_VERSION = "website_documentation_index/v1"
PAGES_VERSION = "website_documentation_pages/v1"
PAGE_VERSION = "website_documentation_page/v1"

WEB_ASSETS = "src/loop_engine/core/service_runtime/web_assets"
INDEX_FILE = WEB_ASSETS + "/documentation-index.json"
#: One file per page holds that page's built body. A body is copy written for
#: a customer to read, so it is kept as its own document: a change to one page
#: shows up as a change to that page's file.
BODY_DIRECTORY = WEB_ASSETS + "/docs"
BODY_SUFFIX = ".html"
PAGES_FILE = "src/loop_engine/core/service_runtime/documentation_pages.json"
#: The served address table. A website address a page links to must be one of
#: its page addresses.
PAGE_TABLE_MODULE = "src/loop_engine/core/service_runtime/web_pages.py"
PAGE_TABLE_NAME = "WEB_ASSETS"
PAGE_FILE = "index.html"
PROJECT_FILE = "pyproject.toml"
#: Where a built page is read, and where its body is served.
PAGE_ADDRESS_PREFIX = "/docs/"
BODY_ADDRESS_PREFIX = "/assets/docs/"
#: The origin every page uses for the service. A link to a page of the website
#: is written with it, and served as an address on the reader's own origin.
WEBSITE_ORIGIN = "https://app.baltor.ai"
#: The address schemes that mark a link as leaving the repository.
EXTERNAL_LINK_SCHEMES = ("http://", "https://")
#: The four kinds of link a page can hold, decided once by `_resolve_link`.
LINK_TO_PAGE, LINK_TO_WEBSITE, LINK_TO_REPOSITORY, LINK_TO_EXTERNAL = "page", "website", "repository", "external"
#: The line that states a document's kind in this repository.
KIND_MARKER = "Kind:"
SUMMARY_LIMIT = 100

PAGE_FIELDS = {"id", "title", "summary", "address", "body", "repository_path", "aliases"}
SECTION_FIELDS = {"id", "title", "pages"}
INDEX_FIELDS = {"record_type", "reviewed_at", "sections"}
IDENTITY = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
DATE = re.compile(r"^20[0-9]{2}-[01][0-9]-[0-3][0-9]$")
ADDRESS = re.compile(r"^/[a-z0-9][a-z0-9/-]*$")
HEADING = re.compile(r"^(#{1,4}) +(\S.*)$")
DEEP_HEADING = re.compile(r"^#{5,} ")
FENCE = re.compile(r"^```([A-Za-z0-9+-]*)\s*$")
UNORDERED = re.compile(r"^- +(\S.*)$")
ORDERED = re.compile(r"^([0-9]+)\. +(\S.*)$")
SEPARATOR_CELL = re.compile(r"^:?-+:?$")
#: The three inline forms, scanned left to right in one pass so that a link
#: inside a code span stays inside the code span.
INLINE = re.compile(r"`([^`\n]+)`|\*\*([^*\n]+)\*\*|\[([^\]\n]+)\]\(([^)\n]+)\)")
#: Markup that plain escaping would silently swallow, so it is refused.
LEFTOVER = re.compile(r"`|\]\(|\*\*|<[A-Za-z/!]")


class DocumentationBuildError(Exception):
    """The index, a page it names, or a construct inside a page is unusable."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _text(value, where: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 200 or any(char in value for char in "\r\n\t"):
        raise DocumentationBuildError(f"{where} has no usable {field}")
    return value


def _page(entry, section: str, seen: set) -> dict:
    """Validate one index entry; every failure names the entry."""
    if not isinstance(entry, dict):
        raise DocumentationBuildError(f"section {section!r} holds a page that is not an object")
    identity = entry.get("id")
    if not isinstance(identity, str) or not IDENTITY.fullmatch(identity):
        raise DocumentationBuildError(f"section {section!r} holds a page with no usable id")
    where = f"page {identity!r}"
    if identity in seen:
        raise DocumentationBuildError(f"two pages share the id {identity!r}")
    unknown = sorted(set(entry) - PAGE_FIELDS)
    if unknown:
        raise DocumentationBuildError("{} has fields the index version does not define: {}".format(where, ", ".join(unknown)))
    for field in ("title", "summary", "address"):
        _text(entry.get(field), where, field)
    if len(entry["summary"]) > SUMMARY_LIMIT or "\n" in entry["summary"]:
        raise DocumentationBuildError(f"{where} has a summary that is not one short line")
    if not ADDRESS.fullmatch(entry["address"]):
        raise DocumentationBuildError("{} has the address {!r}, which is not a page address".format(where, entry["address"]))
    path = entry.get("repository_path")
    if "repository_path" in entry and (not isinstance(path, str) or not re.fullmatch(r"docs/guides/[a-z0-9-]+\.md", path)):
        raise DocumentationBuildError(f"{where} does not name a Markdown page")
    if "body" in entry:
        if entry["address"] != PAGE_ADDRESS_PREFIX + identity:
            raise DocumentationBuildError("{} has the address {!r}, which is not {} followed by its id".format(where, entry["address"], PAGE_ADDRESS_PREFIX))
        if entry["body"] != BODY_ADDRESS_PREFIX + identity + BODY_SUFFIX:
            raise DocumentationBuildError("{} has the body address {!r}, which is not {} followed by its id".format(where, entry["body"], BODY_ADDRESS_PREFIX))
        if path is None:
            raise DocumentationBuildError(f"{where} is built and names no Markdown page")
    elif entry["address"] != "/setup":
        raise DocumentationBuildError(f"{where} is a documentation address with no body to build")
    aliases = entry.get("aliases", [])
    if (not isinstance(aliases, list) or len(aliases) > 10 or not all(isinstance(alias, str) for alias in aliases)
            or len(set(aliases)) != len(aliases)
            or not all(isinstance(alias, str) and re.fullmatch(r"/docs/[a-z][a-z0-9-]*", alias) for alias in aliases)):
        raise DocumentationBuildError(f"{where} has aliases that are not documentation addresses")
    return entry


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member: " + key)
        result[key] = value
    return result


def load_index(root: Path) -> dict:
    """Read and validate the index; every failure names the offending entry."""
    path = root / INDEX_FILE
    if not path.is_file():
        raise DocumentationBuildError("the documentation index is missing at " + INDEX_FILE)
    try:
        index = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except ValueError as error:
        raise DocumentationBuildError(f"the documentation index is not valid JSON: {error}") from None
    if not isinstance(index, dict) or index.get("record_type") != INDEX_VERSION:
        raise DocumentationBuildError(f"the documentation index must declare record_type {INDEX_VERSION}")
    unknown = sorted(set(index) - INDEX_FIELDS)
    if unknown:
        raise DocumentationBuildError("the documentation index has fields its version does not define: "
                                      + ", ".join(unknown))
    if not isinstance(index.get("reviewed_at"), str) or not DATE.fullmatch(index["reviewed_at"]):
        raise DocumentationBuildError("the documentation index names no review date")
    try:
        date.fromisoformat(index["reviewed_at"])
    except ValueError:
        raise DocumentationBuildError("the documentation review date is not a calendar date") from None
    sections = index.get("sections")
    if not isinstance(sections, list) or not sections or len(sections) > 32:
        raise DocumentationBuildError("the documentation index declares no sections")
    seen_sections, seen_pages, addresses = set(), set(), set()
    for position, section in enumerate(sections):
        if not isinstance(section, dict) or not isinstance(section.get("id"), str) \
                or not IDENTITY.fullmatch(section["id"]):
            raise DocumentationBuildError(f"the section at position {position} has no usable id")
        identity = section["id"]
        if identity in seen_sections:
            raise DocumentationBuildError(f"two sections share the id {identity!r}")
        seen_sections.add(identity)
        unknown = sorted(set(section) - SECTION_FIELDS)
        if unknown:
            raise DocumentationBuildError("section {!r} has fields the index version does not define: {}".format(identity, ", ".join(unknown)))
        _text(section.get("title"), f"section {identity!r}", "title")
        pages = section.get("pages")
        if not isinstance(pages, list) or not pages or len(pages) > 100:
            raise DocumentationBuildError(f"section {identity!r} lists no pages")
        for entry in pages:
            _page(entry, identity, seen_pages)
            seen_pages.add(entry["id"])
            for address in [entry["address"], *entry.get("aliases", [])]:
                if address in addresses:
                    raise DocumentationBuildError(f"two pages share the address {address!r}")
                addresses.add(address)
    paths = [page["repository_path"] for page in index_pages(index) if page.get("repository_path")]
    if len(set(paths)) != len(paths):
        raise DocumentationBuildError("two pages name the same Markdown page")
    return index


def index_pages(index: dict) -> list:
    """Every page the index names, in the order the index gives them."""
    return [page for section in index["sections"] for page in section["pages"]]


def built_pages(index: dict) -> list:
    """The pages this tool builds: the ones with a body."""
    return [page for page in index_pages(index) if "body" in page]


def served_page_addresses(root: Path) -> set:
    """The addresses the service answers with its one page, read from the address table."""
    tree = ast.parse((root / PAGE_TABLE_MODULE).read_text(encoding="utf-8"))
    for node in tree.body:
        if (isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == PAGE_TABLE_NAME
                                                  for target in node.targets)
                and isinstance(node.value, ast.Dict)):
            return {key.value for key, value in zip(node.value.keys, node.value.values)
                    if isinstance(key, ast.Constant) and isinstance(value, ast.Tuple) and value.elts
                    and isinstance(value.elts[0], ast.Constant) and value.elts[0].value == PAGE_FILE}
    raise DocumentationBuildError("the served address table was not found in " + PAGE_TABLE_MODULE)


def repository_address(root: Path) -> str:
    """The web address of this repository, from the Homepage entry of the project file."""
    text = (root / PROJECT_FILE).read_text(encoding="utf-8")
    table = text.split("[project.urls]", 1)[1].split("\n[", 1)[0] if "[project.urls]" in text else ""
    found = re.search(r'^Homepage = "(https://[^"\s]+)"$', table, re.MULTILINE)
    if not found:
        raise DocumentationBuildError("the project file names no Homepage address")
    return found.group(1).rstrip("/")


def plain_text(text: str) -> str:
    """The words a reader sees in one line of inline markup."""
    return re.sub(r"\[([^\]\n]+)\]\([^)\n]+\)", r"\1", text).replace("**", "").replace("`", "")


def slug(text: str) -> str:
    """The anchor of a heading, made the way the repository's web view makes it."""
    value = re.sub(r"[^\w\- ]", "", plain_text(text).strip().lower())
    return value.replace(" ", "-")


def heading_anchors(text: str) -> list:
    """The anchor of every heading below the title, in order, with repeats numbered."""
    anchors, counts, inside = [], {}, False
    for line in text.replace("\r\n", "\n").split("\n")[1:]:
        if FENCE.match(line):
            inside = not inside
            continue
        heading = HEADING.match(line)
        if heading and not inside:
            base = slug(heading.group(2))
            count = counts.get(base, 0)
            counts[base] = count + 1
            anchors.append(base if count == 0 else f"{base}-{count}")
    return anchors


class PageBuilder:
    """Resolves links and renders one page, with the facts of every other page at hand."""

    def __init__(self, root: Path, index: dict):
        self.root, self.index = root, index
        self.by_path = {page["repository_path"]: page for page in index_pages(index) if page.get("repository_path")}
        self.anchors = {}
        for page in built_pages(index):
            source = root / page["repository_path"]
            if source.is_file():
                self.anchors[page["repository_path"]] = set(heading_anchors(source.read_text(encoding="utf-8")))
        self.website = served_page_addresses(root)
        self.repository = repository_address(root)

    def resolve(self, page_path: str, target: str) -> tuple:
        """Turn one Markdown link into the address a reader of the website follows."""
        if target.startswith(WEBSITE_ORIGIN + "/"):
            address = target[len(WEBSITE_ORIGIN):]
            if address.split("#")[0].split("?")[0] not in self.website:
                raise DocumentationBuildError(f"{page_path} links to {target!r}, which the service does not serve as a page")
            return LINK_TO_WEBSITE, address
        if target.startswith(EXTERNAL_LINK_SCHEMES):
            return LINK_TO_EXTERNAL, target
        document, _, anchor = target.partition("#")
        if not document:
            if anchor not in self.anchors.get(page_path, set()):
                raise DocumentationBuildError(f"{page_path} links to the anchor {target!r}, which no heading of it has")
            return LINK_TO_PAGE, "#" + anchor
        if document.startswith("/"):
            raise DocumentationBuildError(f"{page_path} links to the absolute address {target!r}; name a file or a web address")
        # Normalised lexically rather than resolved, so that a checkout reached
        # through a link is still measured against the repository it belongs to.
        relative = posixpath.normpath(posixpath.join(posixpath.dirname(page_path), document))
        if relative.startswith(".."):
            raise DocumentationBuildError(f"{page_path} links outside the repository: {target!r}")
        if relative in self.by_path:
            entry = self.by_path[relative]
            if anchor and "body" not in entry:
                raise DocumentationBuildError("{} links to an anchor of {}, which the website shows as {}".format(page_path, relative, entry["address"]))
            if anchor and anchor not in self.anchors.get(relative, set()):
                raise DocumentationBuildError(f"{page_path} links to {target!r}, and {relative} has no heading with that anchor")
            return LINK_TO_PAGE, entry["address"] + ("#" + anchor if anchor else "")
        if not (self.root / relative).exists():
            raise DocumentationBuildError(f"{page_path} links to {relative!r}, which does not exist")
        return LINK_TO_REPOSITORY, "{}/blob/main/{}{}".format(self.repository, relative, "#" + anchor if anchor else "")

    def inline(self, page_path: str, text: str) -> str:
        """Render code spans, bold text and links; refuse anything else."""
        output, position = [], 0
        for match in INLINE.finditer(text):
            output.append(self._plain(page_path, text[position:match.start()]))
            code, bold, label, target = match.groups()
            if code is not None:
                output.append(f"<code>{escape(code, quote=False)}</code>")
            elif bold is not None:
                output.append(f"<strong>{self._plain(page_path, bold)}</strong>")
            else:
                kind, address = self.resolve(page_path, target)
                attributes = ' rel="noopener noreferrer" target="_blank"' if kind in (
                    LINK_TO_REPOSITORY, LINK_TO_EXTERNAL) else ""
                output.append(f'<a href="{escape(address, quote=True)}"{attributes}>{self.inline(page_path, label)}</a>')
            position = match.end()
        output.append(self._plain(page_path, text[position:]))
        return "".join(output)

    @staticmethod
    def _plain(page_path: str, text: str) -> str:
        if LEFTOVER.search(text):
            raise DocumentationBuildError(f"{page_path} holds inline markup this build does not render: {text.strip()!r}")
        return escape(text, quote=False)

    def table(self, page_path: str, rows: list) -> str:
        """Render one pipe table; the second row must be its separator."""
        def cells(line):
            stripped = line.strip()
            if not stripped.endswith("|"):
                raise DocumentationBuildError(f"{page_path} holds a table row that does not end with a bar")
            return [cell.strip() for cell in stripped[1:-1].split("|")]

        if len(rows) < 3:
            raise DocumentationBuildError(f"{page_path} holds a table with no body")
        header, separator = cells(rows[0]), cells(rows[1])
        if len(separator) != len(header) or not all(SEPARATOR_CELL.match(cell) for cell in separator):
            raise DocumentationBuildError(f"{page_path} holds a table whose second row is not a separator")
        output = ["<table><thead><tr>"]
        output.extend(f"<th>{self.inline(page_path, cell)}</th>" for cell in header)
        output.append("</tr></thead><tbody>")
        for line in rows[2:]:
            body = cells(line)
            if len(body) != len(header):
                raise DocumentationBuildError(f"{page_path} holds a table row with {len(body)} cells, not {len(header)}")
            output.append("<tr>{}</tr>".format("".join(f"<td>{self.inline(page_path, cell)}</td>" for cell in body)))
        output.append("</tbody></table>")
        return "".join(output)

    def page(self, page_path: str, text: str) -> tuple:
        """Convert one Markdown page into its title, its kind line and its served body."""
        lines = text.replace("\r\n", "\n").split("\n")
        title = HEADING.match(lines[0]) if lines else None
        if not title or len(title.group(1)) != 1:
            raise DocumentationBuildError(f"{page_path} does not begin with a first level heading")
        anchors = iter(heading_anchors(text))
        output, position, kind_line = [], 1, ""
        while position < len(lines):
            line = lines[position]
            if not line.strip():
                position += 1
                continue
            fence = FENCE.match(line)
            if fence:
                language, body, position = fence.group(1), [], position + 1
                while position < len(lines) and not FENCE.match(lines[position]):
                    body.append(lines[position])
                    position += 1
                if position >= len(lines):
                    raise DocumentationBuildError(f"{page_path} holds a code block that is never closed")
                position += 1
                attribute = f' class="language-{escape(language, quote=True)}"' if language else ""
                output.append("<pre><code{}>{}</code></pre>".format(attribute, escape("\n".join(body), quote=False)))
                continue
            if DEEP_HEADING.match(line):
                raise DocumentationBuildError(f"{page_path} holds a heading deeper than the fourth level")
            heading = HEADING.match(line)
            if heading:
                level = len(heading.group(1))
                if level == 1:
                    raise DocumentationBuildError(f"{page_path} holds a second first level heading")
                output.append(f'<h{level} id="{escape(next(anchors), quote=True)}">'
                              f'{self.inline(page_path, heading.group(2))}</h{level}>')
                position += 1
                continue
            if line.startswith("|"):
                rows = []
                while position < len(lines) and lines[position].strip().startswith("|"):
                    rows.append(lines[position])
                    position += 1
                output.append(self.table(page_path, rows))
                continue
            if UNORDERED.match(line) or ORDERED.match(line):
                rendered, position = self._list(page_path, lines, position)
                output.append(rendered)
                continue
            paragraph = []
            while position < len(lines) and lines[position].strip():
                candidate = lines[position]
                if (HEADING.match(candidate) or FENCE.match(candidate) or candidate.startswith("|")
                        or UNORDERED.match(candidate) or ORDERED.match(candidate)):
                    break
                paragraph.append(candidate.strip())
                position += 1
            if not paragraph:
                raise DocumentationBuildError(f"{page_path} holds a line this build cannot place: {line!r}")
            joined = " ".join(paragraph)
            if not output and not kind_line and joined.startswith(KIND_MARKER):
                # The repository's statement of what kind of document this is.
                # The website states the page's purpose in its summary instead.
                kind_line = joined
                continue
            output.append(f"<p>{self.inline(page_path, joined)}</p>")
        if not output:
            raise DocumentationBuildError(f"{page_path} has nothing to serve below its title")
        return plain_text(title.group(2)), kind_line, "\n".join(output) + "\n"

    def _list(self, page_path: str, lines: list, position: int) -> tuple:
        """Render one list and return it with the position of the first line after it."""
        ordered = ORDERED.match(lines[position]) is not None
        first = int(ORDERED.match(lines[position]).group(1)) if ordered else 1
        items, current = [], None
        while position < len(lines):
            candidate = lines[position]
            match = ORDERED.match(candidate) if ordered else UNORDERED.match(candidate)
            if match:
                current = [match.group(2) if ordered else match.group(1)]
                items.append(current)
            elif candidate.startswith("  ") and candidate.strip() and current is not None:
                if FENCE.match(candidate.strip()):
                    raise DocumentationBuildError(f"{page_path} holds a code block inside a list item")
                current.append(candidate.strip())
            elif not candidate.strip() and current is not None and _continues(lines, position, ordered):
                current.append("")
            else:
                break
            position += 1
        tag = "ol" if ordered else "ul"
        start = f' start="{first}"' if ordered and first != 1 else ""
        rendered = "".join("<li>{}</li>".format(self.inline(page_path, " ".join(part for part in item if part)))
                           for item in items)
        return f"<{tag}{start}>{rendered}</{tag}>", position


def _continues(lines, position, ordered) -> bool:
    """A blank line stays inside a list only when the next line continues it."""
    following = position + 1
    if following >= len(lines):
        return False
    candidate = lines[following]
    return bool((ORDERED if ordered else UNORDERED).match(candidate)) or candidate.startswith("  ")


def body_name(page: dict) -> str:
    return page["id"] + BODY_SUFFIX


def build(root: Path) -> tuple:
    """Return the record of what was built and the body of each built page."""
    index = load_index(root)
    for page in index_pages(index):
        if page.get("repository_path") and not (root / page["repository_path"]).is_file():
            raise DocumentationBuildError("the index names {!r}, which does not exist".format(page["repository_path"]))
    builder = PageBuilder(root, index)
    built, bodies = {}, {}
    for page in built_pages(index):
        source = (root / page["repository_path"]).read_bytes()
        heading, kind_line, body = builder.page(page["repository_path"], source.decode("utf-8"))
        bodies[body_name(page)] = body
        built[page["id"]] = {
            "record_type": PAGE_VERSION, "id": page["id"], "title": page["title"], "heading": heading,
            "kind_line": kind_line, "repository_path": page["repository_path"], "source_digest": _digest(source),
            "body_address": page["body"], "body_digest": _digest(body.encode("utf-8"))}
    return ({"record_type": PAGES_VERSION, "reviewed_at": index["reviewed_at"],
             "index_digest": _digest((root / INDEX_FILE).read_bytes()), "pages": built}, bodies)


def serialize(record: dict) -> str:
    return json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def written_bodies(root: Path) -> dict:
    """Every body file on disk today, whether or not a page names it."""
    directory = root / BODY_DIRECTORY
    if not directory.is_dir():
        return {}
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(directory.iterdir()) if path.is_file()}


def differences(root: Path, wanted: str, bodies: dict) -> list:
    """Every way the files on disk differ from what the pages produce today."""
    target = root / PAGES_FILE
    found = []
    if (target.read_text(encoding="utf-8") if target.is_file() else "") != wanted:
        found.append(PAGES_FILE)
    present = written_bodies(root)
    for name in sorted(set(present) | set(bodies)):
        if present.get(name) != bodies.get(name):
            found.append(BODY_DIRECTORY + "/" + name)
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repository", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--check", action="store_true",
                        help="fail when the served files do not match the pages, and write nothing")
    arguments = parser.parse_args(argv)
    root = Path(arguments.repository).resolve()
    try:
        record, bodies = build(root)
    except DocumentationBuildError as error:
        print(f"documentation build failed: {error}")
        return 1
    wanted = serialize(record)
    stale = differences(root, wanted, bodies)
    if arguments.check:
        if stale:
            print("stale, run python tools/build_documentation_index.py: " + ", ".join(stale))
            return 1
        print(f"{PAGES_FILE} and {len(bodies)} body files match the pages the index names")
        return 0
    directory = root / BODY_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    for name in sorted(set(written_bodies(root)) - set(bodies)):
        # A page the index no longer names must not keep being served.
        (directory / name).unlink()
    for name, body in sorted(bodies.items()):
        (directory / name).write_text(body, encoding="utf-8")
    (root / PAGES_FILE).write_text(wanted, encoding="utf-8")
    print(f"wrote {PAGES_FILE} and {len(bodies)} body files under {BODY_DIRECTORY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
