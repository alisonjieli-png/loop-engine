import csv
from pathlib import Path
with Path("cleaned.csv").open(newline="") as stream:
    rows = list(csv.DictReader(stream))
assert len(rows) == 3
assert rows[0]["product_name"] == "Blue Widget"
assert [row["low_stock"] for row in rows] == ["yes", "no", "yes"]
assert "Low stock: 2" in Path("summary.md").read_text()
print("inventory verified")
