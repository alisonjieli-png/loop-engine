from pathlib import Path
text = Path("index.md").read_text()
for required in ("Alpha guide", "Beta notes", "Setup", "Verification", "inputs/docs/alpha.md", "inputs/docs/beta.md", "Summary:"):
    assert required in text, required
print("document index verified")
