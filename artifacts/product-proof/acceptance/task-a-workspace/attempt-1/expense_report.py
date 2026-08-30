import argparse
import json
from collections import defaultdict
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("output")
    args = parser.parse_args()
    rows = json.loads(Path(args.input).read_text())
    totals = defaultdict(float)
    for row in rows:
        totals[str(row["category"])] += float(row["amount"])
    lines = ["# Expense report", ""]
    lines += [f"- {name}: {totals[name]:.2f}" for name in sorted(totals)]
    Path(args.output).write_text("\n".join(lines) + "\n")

if __name__ == "__main__":
    main()
