"""Render one offline HTML report from separated, source-controlled assets.

Presentation cannot turn imports, historical cells or local checks into provider
qualification. The output embeds its own styles, scripts, data and pinned layout
library. Template markers inside data are never evaluated as presentation code.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
from pathlib import Path
import re

ASSETS = Path(__file__).with_name("architecture_report")
ELK_VERSION = "0.12.0"
ELK_SHA384 = "ww57TDqx4cGknIavPm0QKO+aygLUR1BLSn2Vhbnt1XdYKWcwLyWTFKX7aZMaKIi2"


def render(inventory: dict, counts: dict) -> str:
    files = []
    for row in inventory["files"]:
        source = inventory["python"].get(row["path"], {})
        files.append({**row, "symbols": source.get("symbols", []),
                      "tests": source.get("tests", []),
                      "description": source.get("module_description", ""),
                      "call_count": len(source.get("calls", [])),
                      "record_types": source.get("references", []),
                      "module": source.get("module", "")})
    edges = [row for row in inventory["relationships"]
             if row["relation"] not in {"declares", "contains_call_expression"}]
    data = {"files": files, "edges": edges, "counts": counts,
            "source_revision": inventory["source_revision"],
            "generated_at": inventory.get("generated_at", "Not recorded"),
            "population_digest": inventory.get("population_digest", ""),
            **{key: inventory.get(key, {} if key != "questions" else [])
               for key in ("entry_points", "check_evidence", "comparison",
                           "historical_comparison", "website_comparison", "candidate_review", "roadmap", "architecture", "hosting", "documents", "archives", "questions")},
            "components": inventory.get("components", [])}
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    vendor = ASSETS / "node_modules/elkjs"
    package = json.loads((vendor / "package.json").read_text("utf-8"))
    library = (vendor / "lib/elk.bundled.js").read_bytes()
    if (package["version"] != ELK_VERSION
            or base64.b64encode(hashlib.sha384(library).digest()).decode() != ELK_SHA384):
        raise ValueError("layout dependency does not match the reviewed release and digest")
    script = "\n".join((ASSETS / name).read_text("utf-8") for name in ("development.js", "hosting.js", "app.js"))
    if "</script" in library.decode("utf-8").lower() or "</script" in script.lower():
        raise ValueError("a script terminator cannot be embedded as raw library or application code")
    replacements = {"@@STYLE@@": (ASSETS / "style.css").read_text("utf-8"),
                    "@@SCRIPT@@": script, "@@PAYLOAD@@": payload,
                    "@@ELK@@": library.decode("utf-8"),
                    "@@ELK_LICENSE@@": html.escape((vendor / "LICENSE.md").read_text("utf-8")),
                    "@@REVISION@@": html.escape(inventory["source_revision"][:12])}
    template = (ASSETS / "template.html").read_text("utf-8")
    return re.sub(r"@@(?:STYLE|SCRIPT|PAYLOAD|ELK|ELK_LICENSE|REVISION)@@",
                  lambda match: replacements[match[0]], template)
