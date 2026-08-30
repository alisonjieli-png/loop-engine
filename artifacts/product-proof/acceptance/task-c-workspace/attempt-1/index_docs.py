from pathlib import Path
root = Path("inputs/docs")
sections = ["# Document index", ""]
for path in sorted(root.glob("*.md")):
    text = path.read_text()
    lines = text.splitlines()
    title = next((line[2:] for line in lines if line.startswith("# ")), path.stem)
    headings = [line.lstrip("# ") for line in lines if line.startswith("## ")]
    paragraphs = [line for line in lines if line and not line.startswith("#")]
    summary = paragraphs[0] if paragraphs else "No summary available."
    sections += [f"## {title}", "", f"Path: {path.as_posix()}", "", f"Headings: {', '.join(headings)}", "", f"Summary: {summary}", ""]
Path("index.md").write_text("\n".join(sections))
