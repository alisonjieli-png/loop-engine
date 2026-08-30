import csv
from pathlib import Path
source = Path("inputs/inventory.csv")
with source.open(newline="") as stream:
    rows = list(csv.DictReader(stream))
for row in rows:
    row["product_name"] = " ".join(row["product_name"].split()).title()
    row["low_stock"] = "yes" if int(row["quantity"]) <= 5 else "no"
with Path("cleaned.csv").open("w", newline="") as stream:
    writer = csv.DictWriter(stream, fieldnames=[*rows[0].keys()])
    writer.writeheader(); writer.writerows(rows)
low = [row for row in rows if row["low_stock"] == "yes"]
Path("summary.md").write_text(f"# Inventory summary\n\nRows: {len(rows)}\n\nLow stock: {len(low)}\n")
