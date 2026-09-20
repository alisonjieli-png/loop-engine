"""Project dated website observations into a comparison, not product certification."""
from pathlib import Path
import json
import re


PAGE_SIGNALS = (
    ("start", "Start or sign in", r"\b(?:sign.?up|sign.?in|log.?in|start(?:ed)?|console)\b"),
    ("docs", "Documentation", r"\bdocs\b|documentation|quick.?start"),
    ("pricing", "Pricing", r"pricing"),
    ("trust", "Security or trust", r"security|trust.center|compliance"),
    ("examples", "Examples or customer stories", r"example|template|case.stud|customer.stor"),
    ("operations", "Status or changelog", r"\bstatus\b|changelog"),
)


def website_comparison(root: Path) -> dict:
    manifest_path = root / "docs/research/WEBSITE-COMPARISON-POPULATION-2026-09-20.json"
    notes_path = root / "docs/research/WEBSITE-REVIEW-NOTES-2026-09-20.json"
    if not manifest_path.is_file() or not notes_path.is_file():
        return {"state": "not_recorded", "rows": []}
    population = json.loads(manifest_path.read_text())
    notes = json.loads(notes_path.read_text())
    observed = json.loads((root / notes["observations"]).read_text())
    ids = [row["id"] for row in population["sites"]]
    if (len(ids) != len(set(ids)) or set(ids) != set(notes["reviews"])
            or set(ids) != {row["id"] for row in observed["observations"]}):
        raise ValueError("Website population, notes and observations must match exactly")
    rows = []
    for row in observed["observations"]:
        signals = {}
        for key, _label, pattern in PAGE_SIGNALS:
            links = [link for link in row.get("links", [])
                     if re.search(pattern, link["label"], re.I)
                     and not link["url"].endswith("/#") and link["url"].startswith("https://")]
            signals[key] = {"state": "link_observed" if links else "not_observed_in_sample",
                            "links": links[:4]}
        rows.append({**row, **notes["reviews"][row["id"]], "page_signals": signals})
    return {"state": "dated_public_website_review", "observed_at": observed["observed_at"],
            "population_source": str(manifest_path.relative_to(root)), "observations_source": notes["observations"],
            "rows": rows, "unresolved_identities": population["unresolved_identities"],
            "columns": [{"id": key, "label": label} for key, label, _pattern in PAGE_SIGNALS],
            "limits": observed["limits"], "ranking": "No overall superiority ranking; cohorts and evidence scopes differ"}
