"""Hold the customer service pages to the exact service source.

Kind: development check. It reads the customer-facing service pages, takes
every checkable fact out of their code spans, fenced blocks and refusal tables,
and refuses any fact that the service source does not contain. A command, an
address, a record type, a scope, a field name or a refusal code that is renamed
or removed in the source makes this check fail, so the pages cannot drift
silently away from the service a paying customer actually meets.

A refusal table also states the status a client will see. That status is not
restated here. The transport decides it in one function, and this check
compiles that function out of the source under test and asks it, so changing
the status a refusal answers with changes what every page must say.

It reads files. It starts no server, opens no connection and needs no
credential. It is not a runtime boundary and grants no authority.

Run it directly for a report:

    PYTHONPATH=src python tools/check_service_documentation.py --repository .

The exit status is zero when every documented fact exists in the source.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPORT_VERSION = "service_documentation_check/v1"

#: The customer pages this check owns. Each one is held to the service source.
DOCUMENTED_PAGES = (
    "docs/guides/service-getting-set-up.md",
    "docs/guides/service-searching-and-retrieving.md",
    "docs/guides/service-serving-and-connections.md",
    "docs/guides/service-troubleshooting.md",
    "docs/guides/service-what-baltor-is.md",
    "docs/guides/service-your-account.md",
    "docs/guides/service-usage-and-what-you-pay-for.md",
)

#: The service surface a customer meets. A documented name must exist in one of
#: these files. Unrelated repository modules do not make a name real.
SERVICE_SOURCES = (
    "src/loop_engine/core/service_runtime",
    "src/loop_engine/core/provisioning_server.py",
    "src/loop_engine/core/provisioning_mcp.py",
    "src/loop_engine/core/harness_intelligence.py",
    "src/loop_engine/core/retrieval.py",
    "src/loop_engine/service_cli.py",
)
RECIPES = "src/loop_engine/core/service_runtime/web_assets/client-recipes.json"
HTTP_MODULE = "src/loop_engine/core/service_runtime/http.py"
#: The website address table moved out of the transport module on September
#: 21, 2026. The addresses it serves are read from here as well.
PAGES_MODULE = "src/loop_engine/core/service_runtime/web_pages.py"
RECORDS_MODULE = "src/loop_engine/core/service_runtime/records.py"
ENTRYPOINT_MODULE = "src/loop_engine/core/service_runtime/http_entrypoint.py"
CLI_HELP_MODULE = "src/loop_engine/cli_help.py"

#: Error classes whose named argument is the stable refusal code a client reads,
#: mapped to the position of that argument.
REFUSAL_CLASSES = {"ServiceHttpError": 0, "ServiceRuntimeError": 0, "ServiceError": 1,
                   "HttpAuthenticationError": 0, "BillingSessionError": 0, "ProvisioningError": 1}
#: The code each class uses when the call names none.
REFUSAL_DEFAULTS = {"HttpAuthenticationError": "unauthorized", "ProvisioningError": "invalid_request",
                    "ServiceError": "invalid_request"}
#: The transport function that decides one status for one refusal code. It is
#: compiled from the source under test and asked, never restated here.
STATUS_FUNCTION = "_status"
#: The one refusal class that carries its own status. Every other class leaves
#: the status to the transport function above.
TRANSPORT_REFUSAL = "ServiceHttpError"

RECORD_TYPE = re.compile(r"^[a-z][a-z0-9_]*/v[0-9]+$")
SCOPE = re.compile(r"^(?:provisioning|usage|billing|access):[a-z_]+$")
NAME_TOKEN = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
#: A refusal code is one lowercase word, with or without underscores.
CODE_TOKEN = re.compile(r"^[a-z][a-z0-9_]*$")
ADDRESS = re.compile(r"^/(?:mcp|api/[A-Za-z0-9/_.-]*|\.well-known/[A-Za-z0-9/_.-]*"
                     r"|assets/[A-Za-z0-9._-]+|[a-z][a-z0-9-]*)$")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
FENCE = re.compile(r"^```([A-Za-z0-9+-]*)\s*$")
TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
#: Programs whose command lines this check verifies.
CHECKED_PROGRAMS = ("loop-engine", "codex", "opencode", "claude")


class DocumentationDrift(Exception):
    """One or more documented facts are absent from the service source."""


def _python_files(root: Path):
    for entry in SERVICE_SOURCES:
        path = root / entry
        if path.is_dir():
            yield from sorted(path.glob("*.py"))
        elif path.is_file():
            yield path


def _raised_status(node):
    """The status a transport refusal names, positionally or as a keyword.

    None means the call named none, so the class default applies. Reading both
    forms keeps a later `status=` keyword from silently resolving to that
    default and making every page that states the real status fail.
    """
    if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
        return node.args[1].value
    for keyword in node.keywords:
        if keyword.arg == "status" and isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return None


def _status_resolver(http_tree):
    """Compile the transport's own status function, with stand-in refusal classes.

    The function reads only the class of a refusal and its code, and for a
    transport refusal the status it was raised with. Each stand-in carries
    exactly that much, and the default status is read from the class in the
    source rather than written here, so a change to either is a change to what
    the pages must say.
    """
    default_status = None
    for node in ast.walk(http_tree):
        if isinstance(node, ast.ClassDef) and node.name == TRANSPORT_REFUSAL:
            for item in node.body:
                if not isinstance(item, ast.FunctionDef) or item.name != "__init__":
                    continue
                named = [argument.arg for argument in item.args.args]
                for argument, value in zip(named[len(named) - len(item.args.defaults):],
                                           item.args.defaults):
                    if argument == "status" and isinstance(value, ast.Constant):
                        default_status = value.value
    if not isinstance(default_status, int):
        raise DocumentationDrift("the transport refusal declares no default status")

    class ServiceError(ValueError):
        pass

    class ServiceHttpError(ValueError):
        def __init__(self, code, status=default_status, **_unused):
            self.code, self.status = code, status

    class HttpAuthenticationError(ValueError):
        def __init__(self, code="unauthorized"):
            self.code = code

    class ServiceRuntimeError(ValueError):
        def __init__(self, code, message=""):
            self.code = code

    class BillingSessionError(ServiceRuntimeError):
        pass

    class ProvisioningError(ServiceError):
        def __init__(self, message, code="invalid_request"):
            self.code = code

    namespace = {"ServiceError": ServiceError, "ServiceHttpError": ServiceHttpError,
                 "HttpAuthenticationError": HttpAuthenticationError,
                 "ServiceRuntimeError": ServiceRuntimeError,
                 "BillingSessionError": BillingSessionError,
                 "ProvisioningError": ProvisioningError}
    for node in http_tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == STATUS_FUNCTION:
            # Only this one function is compiled, out of the repository's own
            # transport module, and it is given nothing but the stand-in
            # classes above. Restating its rules here instead would create a
            # second copy of the status table, which is the drift this check
            # exists to catch.
            module = ast.Module(body=[node], type_ignores=[])
            exec(compile(module, "<transport status>", "exec"), namespace)  # noqa: S102
            return namespace
    raise DocumentationDrift(f"the transport module defines no {STATUS_FUNCTION} function")


def _refusal_statuses(http_tree, raise_sites) -> dict:
    """Ask the transport what each refusal code answers with, by raise site."""
    namespace = _status_resolver(http_tree)
    decide, statuses = namespace[STATUS_FUNCTION], {}
    for code, target, raised_status in raise_sites:
        build = namespace[target]
        if target == TRANSPORT_REFUSAL:
            error = build(code) if raised_status is None else build(code, raised_status)
        elif target == "ProvisioningError":
            error = build("", code)
        else:
            error = build(code)
        statuses.setdefault(code, set()).add(decide(error)[0])
    return statuses


def source_facts(root: Path) -> dict:
    """Collect, from the service source alone, every fact the pages may state."""
    files = list(_python_files(root))
    if not files:
        raise DocumentationDrift("the service source was not found under " + str(root))
    trees = {path: ast.parse(path.read_text(encoding="utf-8")) for path in files}
    constants: dict[str, str] = {}
    for tree in trees.values():
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                    and isinstance(node.value.value, str)):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.isupper():
                        constants[target.id] = node.value.value

    def literal(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id in constants:
            return constants[node.id]
        return None

    strings, names, refusals, raise_sites = set(), set(), set(), []
    for tree in trees.values():
        # A module-local helper may forward its code argument to a known
        # refusal class. Follow only that explicit raising implementation;
        # a function with the same name that merely returns is not evidence.
        helpers = {}
        for function in tree.body:
            if not isinstance(function, ast.FunctionDef):
                continue
            arguments = [argument.arg for argument in function.args.args]
            bindings = set()
            for raised in ast.walk(function):
                call = raised.exc if isinstance(raised, ast.Raise) else None
                if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
                    continue
                target = call.func.id
                if target not in REFUSAL_CLASSES or target == TRANSPORT_REFUSAL:
                    continue
                index = REFUSAL_CLASSES[target]
                if (len(call.args) > index and isinstance(call.args[index], ast.Name)
                        and call.args[index].id in arguments):
                    bindings.add((target, arguments.index(call.args[index].id)))
            if len(bindings) == 1:
                helpers[function.name] = next(iter(bindings))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                strings.add(node.value)
            elif isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.arg) or isinstance(node, ast.keyword) and node.arg:
                names.add(node.arg)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            if isinstance(node, ast.Call):
                target, index = None, 0
                if isinstance(node.func, ast.Name) and node.func.id in REFUSAL_CLASSES:
                    target, index = node.func.id, REFUSAL_CLASSES[node.func.id]
                elif isinstance(node.func, ast.Name) and node.func.id in helpers:
                    target, index = helpers[node.func.id]
                elif (isinstance(node.func, ast.Attribute) and node.func.attr == "__init__"
                      and isinstance(node.func.value, ast.Call)
                      and isinstance(node.func.value.func, ast.Name)
                      and node.func.value.func.id == "super"):
                    # A refusal subclass names its own code through super().
                    target, index = "ServiceRuntimeError", 0
                if target is not None:
                    value = literal(node.args[index]) if len(node.args) > index else REFUSAL_DEFAULTS.get(target)
                    if value and CODE_TOKEN.match(value):
                        refusals.add(value)
                        # A transport refusal carries its own status; every
                        # other class leaves the status to the transport.
                        raise_sites.append((value, target, _raised_status(node)
                                            if target == TRANSPORT_REFUSAL else None))
    refusals.update(value for name, value in constants.items()
                    if name.endswith("_CODE") and NAME_TOKEN.match(value))
    # A refusal code may reach the caller through a named constant that a
    # policy returns, rather than as a literal inside the raise. Those
    # constants are refusal codes too, so a rename must fail this check.
    for tree in trees.values():
        for node in ast.walk(tree):
            if isinstance(node, ast.Return) and node.value is not None:
                for inner in ast.walk(node.value):
                    if (isinstance(inner, ast.Name) and inner.id in constants
                            and NAME_TOKEN.match(constants[inner.id])):
                        refusals.add(constants[inner.id])

    addresses = {"/mcp"}
    for module in (HTTP_MODULE, PAGES_MODULE):
        for node in ast.walk(trees[root / module]):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("/"):
                addresses.add(node.value)
    addresses.update(value for value in constants.values() if value.startswith("/"))

    scopes = set()
    for node in ast.walk(trees[root / RECORDS_MODULE]):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and SCOPE.match(node.value):
            scopes.add(node.value)

    service_commands = set()
    entrypoint_tree = trees[root / ENTRYPOINT_MODULE]
    # The command choices may be written in place or named once as a module
    # tuple, such as SERVICE_COMMANDS, which the help check compares with.
    named_tuples = {target.id: node.value for node in entrypoint_tree.body
                    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Tuple)
                    for target in node.targets if isinstance(target, ast.Name)}
    for node in ast.walk(entrypoint_tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "add_argument"):
            for keyword in node.keywords:
                choices = keyword.value
                if isinstance(choices, ast.Name):
                    choices = named_tuples.get(choices.id)
                if keyword.arg == "choices" and isinstance(choices, ast.Tuple):
                    values = [literal(item) for item in choices.elts]
                    if all(value and value.isalpha() or value and "-" in value for value in values):
                        service_commands.update(value for value in values if value)
                    break

    root_commands = set()
    help_tree = ast.parse((root / CLI_HELP_MODULE).read_text(encoding="utf-8"))
    for node in ast.walk(help_tree):
        if isinstance(node, ast.Dict):
            for key in node.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    root_commands.add(key.value.split()[0])

    recipes = json.loads((root / RECIPES).read_text(encoding="utf-8"))

    def collect(value):
        """Every key and text value a served recipe publishes is a real name."""
        if isinstance(value, dict):
            for key, item in value.items():
                strings.add(key)
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, str):
            strings.add(value)
            strings.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", value))

    collect(recipes)
    record_types = {value for value in strings if RECORD_TYPE.match(value)}
    record_types.add(recipes["record_type"])
    http_tree = trees[root / HTTP_MODULE]
    return {"refusal_codes": refusals, "addresses": addresses, "scopes": scopes,
            "refusal_statuses": _refusal_statuses(http_tree, raise_sites),
            "record_types": record_types, "strings": strings, "names": names,
            "service_commands": service_commands, "root_commands": root_commands,
            "recipe_commands": {row["verification_command"]: row["id"] for row in recipes["recipes"]},
            "recipe_ids": {row["id"] for row in recipes["recipes"]},
            "credential_variable": recipes["credential_variable"]}


def page_facts(text: str) -> dict:
    """Take every checkable fact out of one page's code spans, blocks and tables."""
    spans, commands, refusal_rows, status_rows = [], [], [], []
    inside, language, header = False, "", None
    for line in text.splitlines():
        fence = FENCE.match(line)
        if fence:
            inside, language = (not inside), (fence.group(1) if not inside else "")
            header = None
            continue
        if inside:
            spans.extend(re.findall(r"[^\s\"'`,;()\[\]{}<>]+", line))
            if language == "bash":
                stripped = line.strip()
                if stripped.split(" ")[:1] and stripped.split(" ")[0] in CHECKED_PROGRAMS:
                    commands.append(stripped)
            continue
        spans.extend(INLINE_CODE.findall(line))
        # Public same-origin page links are service facts too, not just code spans.
        spans.extend(re.findall(r"\]\(https://(?:app\.)?baltor\.ai(/[^)#?\s]*)(?:[?#][^)]*)?\)", line))
        row = TABLE_ROW.match(line.strip())
        if row:
            cells = [cell.strip() for cell in row.group(1).split("|")]
            if header is None:
                header = cells
            elif set("".join(cells)) <= set("-: "):
                continue
            elif header and header[0].strip("` ").lower() == "code" and cells:
                refusal_rows.append(cells[0].strip("` "))
                # A second cell holding only digits is the status the page
                # promises a client will see for that refusal.
                if len(cells) > 1 and cells[1].strip("` ").isdigit():
                    status_rows.append((cells[0].strip("` "), int(cells[1].strip("` "))))
        else:
            header = None
    return {"tokens": [value.strip("`.,").rstrip(":;") for value in spans], "commands": commands,
            "refusal_codes": refusal_rows, "refusal_statuses": status_rows}


def check(root: Path, pages=DOCUMENTED_PAGES) -> dict:
    """Return one report; every finding names the page, the fact and its kind."""
    facts = source_facts(root)
    findings, checked = [], 0
    documented_recipes = set()

    def refuse(page, kind, value, note):
        findings.append({"page": page, "kind": kind, "value": value, "note": note})

    for page in pages:
        path = root / page
        if not path.is_file():
            refuse(page, "page", page, "the documented page is missing")
            continue
        found = page_facts(path.read_text(encoding="utf-8"))
        for value in found["refusal_codes"]:
            checked += 1
            if value not in facts["refusal_codes"]:
                refuse(page, "refusal_code", value, "no service refusal raises this code")
        for value, status in found["refusal_statuses"]:
            checked += 1
            answered = facts["refusal_statuses"].get(value)
            if not answered:
                refuse(page, "refusal_status_unknown", f"{value} {status}",
                       "the page promises a status for a refusal whose raise site this check "
                       "cannot find, so the promise cannot be held to the source")
            elif status not in answered:
                refuse(page, "refusal_status", f"{value} {status}",
                       "the service answers this refusal with {}".format(" or ".join(str(number) for number in sorted(answered))))
        for token in found["tokens"]:
            if RECORD_TYPE.match(token):
                checked += 1
                if token not in facts["record_types"]:
                    refuse(page, "record_type", token, "no service record declares this version")
            elif SCOPE.match(token):
                checked += 1
                if token not in facts["scopes"]:
                    refuse(page, "scope", token, "this scope is not in the service vocabulary")
            elif ADDRESS.match(token):
                checked += 1
                if token not in facts["addresses"]:
                    refuse(page, "address", token, "the service serves no such address")
            elif NAME_TOKEN.match(token):
                checked += 1
                if token not in facts["strings"] and token not in facts["names"]:
                    refuse(page, "name", token, "no service field, record key or identifier uses this name")
        for command in found["commands"]:
            checked += 1
            words = command.split()
            if words[0] == "loop-engine":
                if len(words) < 2 or words[1] not in facts["root_commands"]:
                    refuse(page, "command", command, "the command line interface has no such command")
                elif words[1] == "service" and (len(words) < 3 or words[2] not in facts["service_commands"]):
                    refuse(page, "command", command, "the service command accepts no such operation")
            elif command not in facts["recipe_commands"]:
                refuse(page, "command", command, "no client recipe publishes this verification command")
            else:
                documented_recipes.add(facts["recipe_commands"][command])

    checked += 1
    for recipe in sorted(facts["recipe_ids"] - documented_recipes):
        refuse(DOCUMENTED_PAGES[0], "recipe", recipe,
               "the service serves this client recipe and no page shows how to confirm it")
    return {"record_type": REPORT_VERSION, "repository": str(root), "pages": list(pages),
            "facts_checked": checked, "findings": findings, "passed": not findings}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repository", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--json", action="store_true", help="print the whole typed report")
    arguments = parser.parse_args(argv)
    report = check(Path(arguments.repository).resolve())
    if arguments.json:
        print(json.dumps(report, indent=1, sort_keys=True))
    else:
        for finding in report["findings"]:
            print("{page}: {kind} {value!r}: {note}".format(**finding))
        print("checked {facts_checked} documented facts; {result}".format(
            facts_checked=report["facts_checked"],
            result="all exist in the service source" if report["passed"]
            else f"{len(report['findings'])} absent from the service source"))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
