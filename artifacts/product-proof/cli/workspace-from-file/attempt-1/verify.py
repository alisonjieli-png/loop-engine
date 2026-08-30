import json
import subprocess
import sys
from pathlib import Path
rows = [{"category": "Food", "amount": 12.5}, {"category": "Travel", "amount": 8}, {"category": "Food", "amount": 2.5}]
Path("sample.json").write_text(json.dumps(rows))
subprocess.run([sys.executable, "expense_report.py", "sample.json", "report.md"], check=True)
report = Path("report.md").read_text()
assert "Food: 15.00" in report and "Travel: 8.00" in report
print("expense report verified")
