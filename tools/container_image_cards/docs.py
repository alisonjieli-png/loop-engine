"""Read the facts a card takes from an image's folder of docker-library/docs (MIT, Copyright (c) 2014 Docker, Inc.).

```text
docker-library/docs/<name>/ at a pinned commit, each file proven by git blob identity (supply_lines.reading)
├── README-short.txt  the one-line summary Docker Hub shows; the only text a card quotes, marked as a quotation
├── metadata.json     hub.categories (web-servers, databases-and-storage, ...)
├── content.md        read for environment variable names only: a backticked upper-case name in a heading
│                     ("### `POSTGRES_PASSWORD`") or after -e or --env in an example command; no sentence and no
│                     example value is taken (an example's value may be a sample password)
├── license.md        read for its link targets: where the licence of the software inside the image is stated
└── github-repo       the address of the repository the image is built from
```

The repository's licence is MIT for every file; no image folder holds a licence file or states another licence
for its documentation. license.md is about the image's software, which the card links to and never relicenses.
Nothing here reads the network.
"""
from __future__ import annotations

import json
import re

#: The files a card reads from an image's documentation folder.
SUMMARY_FILE, METADATA_FILE, CONTENT_FILE, LICENCE_FILE, REPOSITORY_FILE = FILES = (
    "README-short.txt", "metadata.json", "content.md", "license.md", "github-repo")
#: Where metadata.json keeps Docker Hub's categories.
HUB_FIELD, CATEGORIES_FIELD = "hub", "categories"
#: The longest summary a card quotes (Docker Hub's own limit is 100 characters).
MAXIMUM_SUMMARY = 200
ENVIRONMENT_NAME = r"[A-Z][A-Z0-9_]{1,63}"
#: A Markdown heading, and a backticked environment variable name inside one.
HEADING = re.compile(r"^#{1,6}[ \t].*$", re.MULTILINE)
HEADING_NAME = re.compile(r"`(" + ENVIRONMENT_NAME + r")`")
#: An environment variable an example command sets: -e NAME=..., -e "NAME=...", --env NAME, --env=NAME.
EXAMPLE_NAME = re.compile(r"(?:^|[\s(])(?:-e|--env)(?:[ \t]+|=)[\"']?(" + ENVIRONMENT_NAME + r")(?=[=\s\"')]|$)",
                          re.MULTILINE)
#: A Markdown link target and a bare address.
LINK_TARGET = re.compile(r"\]\((https?://[^)\s]+)\)")
BARE_ADDRESS = re.compile(r"(?<![(\[])\bhttps?://[^\s)\]>\"']+")
#: How a documented name was found.
HEADING_EVIDENCE, EXAMPLE_EVIDENCE = "documentation_heading", "documentation_example"


def summary(data: "bytes | None") -> "str | None":
    """The one-line summary, whitespace folded; None when the folder has none or it is not one short line."""
    if not data:
        return None
    text = " ".join(data.decode("utf-8", "replace").split())
    return text if 0 < len(text) <= MAXIMUM_SUMMARY else None


def categories(data: "bytes | None") -> list:
    """Docker Hub's categories of the image, in the order metadata.json gives them."""
    if not data:
        return []
    try:
        value = json.loads(data)
    except ValueError:
        return []
    found = ((value or {}).get(HUB_FIELD) or {}).get(CATEGORIES_FIELD) if isinstance(value, dict) else None
    return [item for item in found if isinstance(item, str) and item] if isinstance(found, list) else []


def documented_environment(text: "str | None") -> list:
    """[{name, evidence}] of every environment variable the documentation names in a heading or an example, sorted
    by name; a name found both ways keeps both kinds of evidence."""
    if not text:
        return []
    found = {}
    for heading in HEADING.findall(text):
        for name in HEADING_NAME.findall(heading):
            found.setdefault(name, set()).add(HEADING_EVIDENCE)
    for name in EXAMPLE_NAME.findall(text):
        found.setdefault(name, set()).add(EXAMPLE_EVIDENCE)
    return [{"name": name, "evidence": sorted(kinds)} for name, kinds in sorted(found.items())]


def licence_links(data: "bytes | None") -> list:
    """The addresses license.md links to, in order and without repeats."""
    if not data:
        return []
    text = data.decode("utf-8", "replace")
    links = LINK_TARGET.findall(text) + BARE_ADDRESS.findall(text)
    return list(dict.fromkeys(link.rstrip(".,;") for link in links))


def source_repository(data: "bytes | None") -> "str | None":
    """The address github-repo names, when it is one https or http address on one line."""
    if not data:
        return None
    text = data.decode("utf-8", "replace").strip()
    return text if BARE_ADDRESS.fullmatch(text) else None


def facts(files: dict) -> dict:
    """The documentation facts of one image from {file name: bytes or None}."""
    content = files.get(CONTENT_FILE)
    return {"summary": summary(files.get(SUMMARY_FILE)), "categories": categories(files.get(METADATA_FILE)),
            "environment": documented_environment(content.decode("utf-8", "replace") if content else None),
            "software_licence_links": licence_links(files.get(LICENCE_FILE)),
            "source_repository": source_repository(files.get(REPOSITORY_FILE))}


__all__ = ["FILES", "SUMMARY_FILE", "METADATA_FILE", "CONTENT_FILE", "LICENCE_FILE", "REPOSITORY_FILE", "summary",
           "categories", "documented_environment", "licence_links", "source_repository", "facts",
           "HEADING_EVIDENCE", "EXAMPLE_EVIDENCE"]
