"""Inspect a threejs_modules package without running JavaScript (standard library only).

    python3 inspect_module.py [PACKAGE_FOLDER]      prints a JSON report and exits 1 when it finds a problem

The inspector reads the package's component.json and its files as text:

- every file matches its SHA-256 in the card, and the package keeps to the review bounds (256 KiB a file, 2 MiB and
  64 files a package);
- the item's root ES module exports exactly the contract's names, each with the declared kind, through
  ``export function``, ``export class`` or ``export const`` declarations only;
- the module and its demo import nothing and use no network, storage, code-evaluation, worker, process or page-global
  API, so they run the same in a page, a worker or Node with three.js passed in;
- every export is named in the item's own node tests (which import the module) and in the README, the README has its
  sections, and the demo exports its declared function;
- every uniform the contract declares is declared in the module's GLSL text with its type.

It reports problems; it never changes a file. The node tests (test_*.mjs) are what run the module itself.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

MAXIMUM_FILE_BYTES = 256 * 1024
MAXIMUM_PACKAGE_BYTES = 2 * 1024 * 1024
MAXIMUM_PACKAGE_FILES = 64
CARD_NAME = "component.json"
README_NAME = "README.md"
#: Files every package of the family carries; the item's own node tests are the other root test_*.mjs files.
SHARED_FILES = frozenset({"test_contract.mjs", "test_package.py", "inspect_module.py"})
README_SECTIONS = ("## When to use it", "## Use it", "## Exports", "## Checks", "## Limits")
KINDS = {"function": "function", "class": "class", "const": "constant"}
EXPORT_DECLARATION = re.compile(r"^export\s+(?:async\s+)?(function|class|const)\s*\*?\s*([A-Za-z_$][\w$]*)",
                                re.MULTILINE)
EXPORT_ANY = re.compile(r"^export\b", re.MULTILINE)
UNIFORM = re.compile(r"\buniform\s+(?:(?:lowp|mediump|highp)\s+)?([A-Za-z_]\w*)\s+([A-Za-z_]\w*)\s*(?:\[[^\]]+\])?\s*;")
FORBIDDEN = (
    ("imports another module", re.compile(r"^\s*import\b|\bimport\s*\(|\brequire\s*\(", re.MULTILINE)),
    ("uses the network", re.compile(r"\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\b|\bEventSource\b|\bsendBeacon\b")),
    ("uses browser storage", re.compile(r"\blocalStorage\b|\bsessionStorage\b|\bindexedDB\b|\bdocument\.cookie\b")),
    ("evaluates code", re.compile(r"\beval\s*\(|\bnew\s+Function\s*\(")),
    ("starts a worker", re.compile(r"\bnew\s+(?:Shared)?Worker\s*\(|\bimportScripts\s*\(")),
    ("touches a process or host runtime", re.compile(r"\bprocess\.[a-z]|\bchild_process\b|\bDeno\.[a-z]|\bBun\.[a-z]")),
    ("touches page globals", re.compile(r"\b(?:window|document|globalThis|self)\.[A-Za-z_$]")),
)


def module_exports(text: str) -> tuple:
    """(name -> kind, problems): the module's export declarations; any other export form is a problem."""
    found, problems = {}, []
    declarations = EXPORT_DECLARATION.findall(text)
    for keyword, name in declarations:
        if name in found:
            problems.append(f"{name} is exported twice")
        found[name] = KINDS[keyword]
    if len(EXPORT_ANY.findall(text)) != len(declarations):
        problems.append("only export function, export class and export const declarations are allowed")
    return found, problems


def export_problems(text: str, contract: dict) -> list:
    found, problems = module_exports(text)
    declared = {row["name"]: row["kind"] for row in contract["exports"]}
    problems += [f"{name} is declared but not exported" for name in sorted(set(declared) - set(found))]
    problems += [f"{name} is exported but not declared" for name in sorted(set(found) - set(declared))]
    problems += [f"{name} is a {found[name]}, declared as a {declared[name]}"
                 for name in sorted(set(found) & set(declared)) if found[name] != declared[name]]
    return problems


def forbidden_problems(text: str) -> list:
    return [reason for reason, pattern in FORBIDDEN if pattern.search(text)]


def uniform_problems(text: str, contract: dict) -> list:
    """Contract uniforms the module's text does not declare with the same type."""
    declared = set(UNIFORM.findall(text))
    return [f"uniform {row['type']} {row['name']} is not declared in the module"
            for row in contract.get("uniforms", []) if (row["type"], row["name"]) not in declared]


def coverage_problems(test_texts: list, module: str, names: list) -> list:
    if not test_texts:
        return ["the item has no node test of its own"]
    problems = [] if any(f"./{module}" in text for text in test_texts) else [f"no item test imports ./{module}"]
    joined = "\n".join(test_texts)
    problems += [f"{name} is never named in the item's tests" for name in names
                 if not re.search(rf"\b{re.escape(name)}\b", joined)]
    return problems


def readme_problems(text: str, title: str, names: list) -> list:
    problems = [] if text.startswith(f"# {title}\n") else ["the README does not start with the title"]
    problems += [f"the README has no '{section}' section" for section in README_SECTIONS
                 if not re.search(rf"^{re.escape(section)}\s*$", text, re.MULTILINE)]
    problems += [f"the README never names {name}" for name in names if f"`{name}" not in text]
    return problems


def demo_problems(text: str, export: str) -> list:
    problems = forbidden_problems(text)
    if not re.search(rf"^export\s+(?:async\s+)?function\s+{re.escape(export)}\s*\(", text, re.MULTILINE):
        problems.append(f"the demo does not export function {export}")
    return problems


def digest_problems(card: dict, root: Path) -> list:
    problems = []
    for row in card["files"]:
        path = Path(root) / row["path"]
        if not path.is_file():
            problems.append(f"{row['path']} is missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            problems.append(f"{row['path']} differs from its digest")
    return problems


def bound_problems(root: Path) -> list:
    sizes = {path.relative_to(root).as_posix(): path.stat().st_size for path in Path(root).rglob("*")
             if path.is_file() and "__pycache__" not in path.parts}
    problems = [f"{name} is larger than {MAXIMUM_FILE_BYTES} bytes" for name, size in sorted(sizes.items())
                if size > MAXIMUM_FILE_BYTES]
    if sum(sizes.values()) > MAXIMUM_PACKAGE_BYTES:
        problems.append(f"the package is larger than {MAXIMUM_PACKAGE_BYTES} bytes")
    if len(sizes) > MAXIMUM_PACKAGE_FILES:
        problems.append(f"the package holds more than {MAXIMUM_PACKAGE_FILES} files")
    return problems


def item_tests(root: Path) -> list:
    return sorted(path for path in Path(root).glob("test_*.mjs") if path.name not in SHARED_FILES)


def inspect_package(root: Path) -> dict:
    """Every problem the inspector finds in the package folder, by area, and the export table it read."""
    root = Path(root)
    card = json.loads((root / CARD_NAME).read_text(encoding="utf-8"))
    contract = card["contract"]
    module_text = (root / contract["module"]).read_text(encoding="utf-8")
    names = [row["name"] for row in contract["exports"]]
    tests = item_tests(root)
    report = {
        "files": digest_problems(card, root) + bound_problems(root),
        "exports": export_problems(module_text, contract),
        "standalone": forbidden_problems(module_text),
        "uniforms": uniform_problems(module_text, contract),
        "tests": ([] if [path.name for path in tests] == sorted(contract["tests"])
                  else [f"the item tests are {[path.name for path in tests]}, the contract lists {contract['tests']}"])
                 + coverage_problems([path.read_text(encoding="utf-8") for path in tests], contract["module"], names),
        "readme": readme_problems((root / README_NAME).read_text(encoding="utf-8"), card["title"], names),
        "demo": demo_problems((root / contract["demo"]["file"]).read_text(encoding="utf-8"),
                              contract["demo"]["export"]),
    }
    return {"module": contract["module"], "exports": module_exports(module_text)[0], "problems": report,
            "passed": not any(report.values())}


def main(argv=None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    report = inspect_package(Path(arguments[0]) if arguments else Path(__file__).resolve().parent)
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
