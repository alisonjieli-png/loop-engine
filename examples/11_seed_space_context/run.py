"""Seed candidate Context Intelligence for space work without inventing facts."""
from collections import Counter

from loop_engine import ContextSeedSpec, run_context_seed


SPACE_SEED = ContextSeedSpec(
    industry="space economy",
    domain="space",
    subdomain="earth observation and launch operations",
    project_types=("earth observation mission", "launch readiness program"),
    task_types=("requirements review", "mission risk analysis"),
    job_roles=(
        "orbital mechanics engineer",
        "mission operations lead",
        "spacecraft systems engineer",
        "earth observation scientist",
        "space policy researcher",
    ),
    geography="global",
    source_policy="official_first",
    max_candidates=240,
)


def main():
    result = run_context_seed(SPACE_SEED)
    summary = result.to_dict()
    if summary["model_calls"] != 0 or not summary["staged_only"]:
        raise AssertionError("the deterministic seed crossed its declared boundary")
    if result.manifest["promoted"] or result.manifest["installed"]:
        raise AssertionError("a seed run may not install or promote candidates")

    hierarchies = [record.body["classification"]["context_hierarchy"]
                   for record in result.candidates]
    roles = Counter(item["job_role"] for item in hierarchies)
    thinking = Counter(item["thinking_style"] for item in hierarchies)

    print("SPACE CONTEXT SEED")
    print(f"loop: {summary['loop_id']}")
    print(f"logical kind: {summary['logical_kind']}")
    print(f"candidate records: {summary['candidates']}")
    print(f"model calls: {summary['model_calls']}")
    print(f"manifest: {result.manifest['content_digest_sha256'][:16]}")

    print("\nROLE COVERAGE")
    for role, count in sorted(roles.items()):
        print(f"  {role}: {count}")

    print("\nTHINKING STYLES")
    for style, count in sorted(thinking.items()):
        print(f"  {style}: {count}")

    print("\nSAMPLE CANDIDATES")
    for record in result.candidates[:6]:
        hierarchy = record.body["classification"]["context_hierarchy"]
        print(f"  [{hierarchy['thinking_style']}] {record.title}")

    print("\nQUESTIONS FOR A SOURCE-AWARE RESEARCH LOOP")
    for question in result.research_questions:
        print(f"  - {question}")

    print("\nNo person, organization, standard, or fact was invented. A separate "
          "research loop must answer those questions with sources before review.")


if __name__ == "__main__":
    main()
