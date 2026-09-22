"""Read source-backed architecture report sections without granting authority.

The historical comparison preserves its original cell semantics and date.
The running worklist is a projection of the existing roadmap, never a second
editable task store. Diagram declarations are software relationships only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import yaml

from build_continuation_status import validate, gate_status
from website_comparison import website_comparison

FEATURE_FAMILIES = ("Intelligence layers", "Memory", "Procedures", "Assurance", "Selection", "Business")
DEFINITION_HEADING = "Column definitions"
NOTES_HEADING = "Cell notes"


def historical_comparison(path: Path) -> dict:
    if not path.is_file():
        return {"state": "not_recorded", "tables": [], "definitions": {}, "notes": {}}
    raw = path.read_bytes()
    heading, mode, rows = "", "", []
    tables, definitions, notes = [], {}, {}
    for line in raw.decode("utf-8").splitlines() + [""]:
        if (line.startswith("| Company |") and mode in FEATURE_FAMILIES) or rows and line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r"[: -]+", cell) for cell in cells):
                rows.append(cells)
            continue
        if rows:
            if any(len(row) != len(rows[0]) for row in rows):
                raise ValueError("historical feature table has an inconsistent row width")
            if any(value not in {"Y", "P", "N", "?"} for row in rows[1:] for value in row[1:]):
                raise ValueError("historical feature table has an unsupported cell")
            tables.append({"title": heading, "columns": rows[0], "rows": rows[1:]})
            rows = []
        if line.startswith("### "):
            heading = line[4:]
            mode = heading
        elif line.startswith("## "):
            mode = ""
        elif line.startswith("- ") and ": " in line:
            key, value = line[2:].split(": ", 1)
            if mode == DEFINITION_HEADING:
                definitions[key] = value
            elif mode == NOTES_HEADING:
                notes[key] = value
    return {"state": "historical_claude_comparison", "date": "2026-09-18",
            "source": path.name, "source_sha256": hashlib.sha256(raw).hexdigest(),
            "tables": tables, "definitions": definitions, "notes": notes,
            "feature_count": sum(len(table["columns"]) - 1 for table in tables),
            "limits": "Original snapshot. N means not documented or documented as absent, not a verified absence. Y does not establish current runtime wiring or live qualification."}


def report_sections(root: Path) -> dict:
    roadmap_path = root / "docs/roadmap/roadmap.yaml"
    if roadmap_path.is_file():
        raw = roadmap_path.read_bytes()
        roadmap = yaml.safe_load(raw)
        validate(roadmap)
        plan = roadmap["continuation"]
        tasks = {"state": "roadmap_snapshot", "source": "docs/roadmap/roadmap.yaml",
                 "source_sha256": hashlib.sha256(raw).hexdigest(), "steps": roadmap["steps"],
                 "updated_at": plan["updated_at"], "target_at": plan["target_at"],
                 "verification_report": plan.get("verification_report"),
                 "launch_order": plan["launch_order"], "improvement_order": plan["improvement_order"],
                 "decisions": plan["decisions"], "activity": plan.get("activity", []),
                 "owner_actions": [{**row, "content_digest": hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()}
                                   for row in plan.get("owner_actions", [])],
                 "schedule_status": plan.get("schedule_status", "not_forecast"),
                 "delivery_batches": plan.get("delivery_batches", []),
                 "delivery_planning_note": plan.get("delivery_planning_note", "Planning only."),
                 "launch_benefits": plan.get("launch_benefits", []),
                 "gates": [{**gate, "state": gate_status(roadmap, gate)} for gate in plan["launch_gates"]]}
    else:
        tasks = {"state": "not_recorded", "steps": [], "decisions": [], "gates": [], "activity": []}
    diagram_path = Path(__file__).with_name("architecture_report") / "diagrams.json"
    diagrams = json.loads(diagram_path.read_text("utf-8"))
    view_ids = [view["id"] for view in diagrams["views"]]
    if len(set(view_ids)) != len(view_ids) or diagrams.get("default_view") not in view_ids:
        raise ValueError("architecture views need unique identities and an explicit default")
    for view in diagrams["views"]:
        ids = [component["id"] for component in view["components"]]
        if len(ids) != len(set(ids)) or any(edge[axis] not in ids for edge in view["edges"] for axis in ("from", "to")):
            raise ValueError("diagram references an unknown or duplicate software component")
        if not view.get("group") or any(not (root / component["source"]).is_file() for component in view["components"]):
            raise ValueError("every architecture area needs a group and real component sources")
    hosting = json.loads((diagram_path.parent / "hosting.json").read_text("utf-8"))
    sources = {
        "current_checkpoint": ("Current development checkpoint and Claude Code handoff", "docs/context/DEVELOPMENT-CHECKPOINT-2026-09-20.md"),
        "developer_handoff": ("Claude Code Fable 5.1 takeover instructions", "docs/context/FABLE-5-1-HANDOFF-2026-09-20.md"),
        "credential_handoff": ("Reuse existing credentials in Claude Code", "docs/guides/developer-credential-handoff.md"),
        "launch_benefits": ("Launch benefits, wording and required evidence", "docs/guides/launch-benefits-and-evidence.md"),
        "owner_checklist": ("Owner setup checklist", "docs/guides/launch-owner-checklist.md"),
        "runtime_guide": ("The canonical Loop runtime", "docs/components/loop-object/README.md"),
        "practitioner_guide": ("Practitioner solving", "docs/components/practitioner/README.md"),
        "solution_guide": ("Solution Canvas", "docs/components/solution-canvas/README.md"),
        "intelligence_guide": ("The four intelligence layers", "docs/components/intelligence-layers/README.md"),
        "capabilities_guide": ("Core Architecture capabilities", "docs/components/core-architecture/README.md"),
        "improvement_guide": ("Self-improvement as a Practitioner task", "docs/components/self-improvement/README.md"),
        "configuration_dimensions": ("Complete configuration dimensions", "docs/architecture/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-DIMENSIONS.md"),
        "wrapper_direction": ("Layered harness wrappers", "docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md"),
        "execution_plan": ("Continuation and first release", "docs/roadmap/CONTINUATION-AND-LAUNCH.md"),
        "client_server": ("Client and server architecture", "docs/architecture/MVP-CLIENT-SERVER.md"),
        "endpoint_migration": ("Service identity, endpoints, regions and migration", "docs/architecture/SERVICE-IDENTITY-ENDPOINTS-AND-MIGRATION.md"),
        "retrieval_architecture": ("Retrieval and runtime compatibility", "docs/architecture/RETRIEVAL-PIPELINE-AND-RUNTIME-COMPATIBILITY.md"),
        "original_comparison": ("Original Claude comparison", "docs/research/COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md"),
        "website_comparison_review": ("Website comparison, customer journeys and delivery decisions", "docs/research/WEBSITE-JOURNEY-REVIEW-2026-09-20.md"),
        "candidate_intelligence_guide": ("Local service and isolated candidate intelligence review", "examples/29_intelligence_service/README.md"),
        "durable_checkpoint": ("Durable service checkpoint", "artifacts/architecture-audit-2026-09-19/durable-service-checkpoint.md"),
        "http_checkpoint": ("Local HTTP and protocol checkpoint", "artifacts/architecture-audit-2026-09-19/http-service-checkpoint.md"),
        "session_checkpoint": ("Checkout and portal checkpoint", "artifacts/architecture-audit-2026-09-19/stripe-session-checkpoint.md"),
        "harness_layout": ("Harness instance files and context", "docs/guides/harness-instance-context-layout.md"),
        "retrieval_research": ("Self-improving retrieval candidates and qualification", "artifacts/continuation-research-2026-09-19/improving-retrieval-systems.md"),
        "publication_review": ("Adversarial publication review", "artifacts/architecture-audit-2026-09-19/publication-adversarial-review.md"),
        "public_content": ("Public website content and domain direction", "docs/guides/public-website-content-and-domain.md"),
        "frontier_positioning": ("Frontier harness positioning", "docs/guides/frontier-harness-positioning.md"),
        "launch_setup": ("Hosting, accounts and key setup", "docs/guides/launch-setup-runbook.md"),
        "legal_setup": ("Operator identity, terms and privacy", "docs/legal/README.md"),
        "product_style": ("Product style guide and the claim test", "docs/guides/product-style-guide.md"),
        "decision_tools": ("Jev and harness decision tools", "docs/guides/jev-and-harness-decision-tools.md"),
        "circuit_review": ("Circuit decision-engine source review", "docs/research/CIRCUIT-DECISION-ENGINE-REVIEW-2026-09-19.md"),
        "sol_pi_review": ("SoL-Pi: source review, comparison and integration plan", "docs/research/SOL-PI-HARNESS-REVIEW-2026-09-19.md"),
        "semif_review": ("SemIf, Circuit and decision readouts", "docs/research/SEMIF-DECISION-READOUT-REVIEW-2026-09-19.md"),
        "launch_slice": ("Local website and decision-engine checkpoint", "artifacts/architecture-audit-2026-09-19/launch-slice-checkpoint.md"),
        "decision_endpoint_checkpoint": ("Decision wrapper ownership and verification", "artifacts/architecture-audit-2026-09-19/decision-endpoints-checkpoint.md"),
    }
    documents = {key: {"title": title, "path": path, "text": (root / path).read_text("utf-8")}
                 for key, (title, path) in sources.items() if (root / path).is_file()}
    if any(row["guide"] not in {item["path"] for item in documents.values()} for row in tasks.get("owner_actions", [])):
        raise ValueError("every owner action must have its full guide embedded in the report")
    candidate_path = root / "artifacts/architecture-audit-2026-09-19/candidate-intelligence-2.json"
    candidate_report_path = root / "artifacts/architecture-audit-2026-09-19/candidate-intelligence-staging-2.json"
    candidate_review = {"state": "not_recorded", "records": []}
    if candidate_path.is_file() and candidate_report_path.is_file():
        exported = json.loads(candidate_path.read_text())
        report = json.loads(candidate_report_path.read_text())
        if (exported.get("record_type") != "catalog_export/v1" or report.get("committed") is not True
                or len(exported["records"]) != report["records"]
                or any(row["lifecycle"] != "candidate" for row in exported["records"])):
            raise ValueError("Candidate review requires a committed candidate-only catalogue export")
        candidate_review = {"state": "review_only_not_published", "records": exported["records"],
                            "report": report, "source": str(candidate_path.relative_to(root)),
                            "source_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest()}
    return {"roadmap": tasks, "architecture": diagrams, "hosting": hosting, "documents": documents,
            "website_comparison": website_comparison(root),
            "candidate_review": candidate_review,
            "historical_comparison": historical_comparison(root / "docs/research/COMPETITIVE-LANDSCAPE-AND-MONETIZATION-2026-09-18.md")}
