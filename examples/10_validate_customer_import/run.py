"""Validate and normalize customer rows with a deterministic Solution Canvas.

Run from the repository directory:
    python examples/10_validate_customer_import/run.py

This example uses no model, network, or external service.
"""

from __future__ import annotations

import json
import re

from loop_engine import LoopLedger, SolutionLoopSpec, SolutionSpec, run_solution
from loop_engine.code_nodes.solution_compiler import compile_solution, render_canvas


RAW_CUSTOMERS = [
    {
        "customer_id": " cust-1042 ",
        "email": " Alice@Example.com ",
        "country": "ph",
        "status": " ACTIVE ",
    },
    {
        "customer_id": "CUST-1043",
        "email": "not-an-email",
        "country": "United States",
        "status": "trial",
    },
    {
        "customer_id": "cust-1042",
        "email": "alice.backup@example.com",
        "country": "Philippines",
        "status": "active",
    },
    {
        "customer_id": "CUST-1044",
        "email": "",
        "country": "gb",
        "status": "suspended",
    },
    {
        "customer_id": " CUST-1045 ",
        "email": "dev@example.com",
        "country": "us",
        "status": "ACTIVE",
    },
]


COUNTRY_CODES = {
    "gb": "GB",
    "ph": "PH",
    "philippines": "PH",
    "united kingdom": "GB",
    "united states": "US",
    "us": "US",
}


def normalize_fields(rows, _params):
    """Return clean values without changing the input rows."""
    normalized = []
    for source in rows:
        country = str(source.get("country", "")).strip().lower()
        normalized.append(
            {
                "customer_id": str(source.get("customer_id", "")).strip().upper(),
                "email": str(source.get("email", "")).strip().lower(),
                "country": COUNTRY_CODES.get(country, country.upper()),
                "status": str(source.get("status", "")).strip().lower(),
            }
        )
    return normalized


def validation_errors(row):
    """List the reasons that one row is not ready for import."""
    errors = []
    if not re.fullmatch(r"CUST-\d{4}", row["customer_id"]):
        errors.append("invalid_customer_id")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", row["email"]):
        errors.append("invalid_email")
    if row["country"] not in {"GB", "PH", "US"}:
        errors.append("unsupported_country")
    if row["status"] not in {"active", "suspended", "trial"}:
        errors.append("invalid_status")
    return errors


def require_every_row_to_be_valid(rows, _params):
    """Use the fast path only when every row passes validation."""
    invalid_count = sum(bool(validation_errors(row)) for row in rows)
    if invalid_count:
        raise ValueError(f"{invalid_count} rows failed validation")
    return {
        "received": len(rows),
        "ready_rows": list(rows),
        "quarantined_rows": [],
        "validation_path": "all_rows_valid",
    }


def quarantine_invalid_rows(rows, _params):
    """Keep valid rows and hold invalid rows for review."""
    ready = []
    quarantined = []
    for row in rows:
        errors = validation_errors(row)
        if errors:
            quarantined.append({"row": row, "reasons": errors})
        else:
            ready.append(row)
    return {
        "received": len(rows),
        "ready_rows": ready,
        "quarantined_rows": quarantined,
        "validation_path": "quarantine_invalid_rows",
    }


def hold_duplicate_ids(state, _params):
    """Keep the first row for each customer ID and hold later rows."""
    seen = set()
    unique = []
    quarantined = list(state["quarantined_rows"])
    for row in state["ready_rows"]:
        customer_id = row["customer_id"]
        if customer_id in seen:
            quarantined.append(
                {"row": row, "reasons": ["duplicate_customer_id"]}
            )
            continue
        seen.add(customer_id)
        unique.append(row)
    return {
        **state,
        "ready_rows": unique,
        "quarantined_rows": quarantined,
    }


def prepare_import_batch(state, _params):
    """Return the rows to import and a short review list."""
    return {
        "summary": {
            "received": state["received"],
            "ready": len(state["ready_rows"]),
            "quarantined": len(state["quarantined_rows"]),
            "validation_path": state["validation_path"],
        },
        "import_rows": state["ready_rows"],
        "review_rows": [
            {
                "customer_id": item["row"]["customer_id"],
                "reasons": item["reasons"],
            }
            for item in state["quarantined_rows"]
        ],
    }


REGISTRY = {
    "normalize_fields": normalize_fields,
    "require_every_row_to_be_valid": require_every_row_to_be_valid,
    "quarantine_invalid_rows": quarantine_invalid_rows,
    "hold_duplicate_ids": hold_duplicate_ids,
    "prepare_import_batch": prepare_import_batch,
}


CUSTOMER_IMPORT = SolutionSpec(
    "validate_customer_import",
    allowed_modes=("deterministic",),
    loops=(
        SolutionLoopSpec("normalize", "normalize_fields"),
        SolutionLoopSpec(
            "validate",
            "require_every_row_to_be_valid",
            fallback_operations=("quarantine_invalid_rows",),
        ),
        SolutionLoopSpec("deduplicate", "hold_duplicate_ids"),
        SolutionLoopSpec("prepare", "prepare_import_batch"),
    ),
)


def main():
    compiled = compile_solution(CUSTOMER_IMPORT, REGISTRY)
    if compiled["plan"] is None:
        raise RuntimeError("The Solution Canvas did not compile: "
                           + "; ".join(compiled["violations"]))

    view = render_canvas(compiled["plan"])
    trace = []
    ledger = LoopLedger()
    result = run_solution(
        CUSTOMER_IMPORT,
        REGISTRY,
        RAW_CUSTOMERS,
        trace=trace,
        ledger=ledger,
    )

    expected = {
        "received": 5,
        "ready": 2,
        "quarantined": 3,
        "validation_path": "quarantine_invalid_rows",
    }
    if result["summary"] != expected:
        raise AssertionError(f"unexpected summary: {result['summary']}")
    if not any(item.get("used_fallback") for item in trace):
        raise AssertionError("the declared validation fallback did not run")

    print("CUSTOMER IMPORT RESULT")
    print(json.dumps(result, indent=2, sort_keys=True))

    print("\nSOLUTION CANVAS")
    print(view["mermaid"])

    print("\nEXECUTION TRACE")
    for item in trace:
        print(json.dumps(item, sort_keys=True))

    solution_events = [
        event for event in ledger.events
        if str(event.get("event", "")).startswith("solution.")
        or event.get("event") == "solution_finalized"
    ]
    print("\nLEDGER SUMMARY")
    print(f"events: {len(ledger.events)}")
    print(f"solution events: {len(solution_events)}")
    print("model calls: 0")
    for event in solution_events:
        detail = {
            key: event[key]
            for key in ("loop_id", "event", "operation", "status", "served_by")
            if key in event
        }
        print(json.dumps(detail, sort_keys=True))


if __name__ == "__main__":
    main()
