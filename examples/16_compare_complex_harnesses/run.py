"""Validate and account for source-backed published harness evidence."""

import json

from loop_engine.code_nodes.complex_task_benchmark import (
    default_published_catalog_path,
    load_published_evidence,
)


def main():
    catalog = load_published_evidence(default_published_catalog_path())
    print(json.dumps(catalog.accounting(), indent=2))


if __name__ == "__main__":
    main()
