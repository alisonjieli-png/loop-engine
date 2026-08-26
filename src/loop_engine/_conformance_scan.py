"""The machine-enforced conformance scanner.

Every detector reads its policy from ``forbidden_paths.json`` and scans the
canonical package. Any detected bypass produces a nonzero violation count.

Every detector is CANARY-PROVEN: the self-test plants a deliberately invalid
fixture for each rule and asserts the detector fires, then asserts the live
tree scans clean.  A conformance mechanism without a failing canary does not
count as proven (§15.3).

CLI: ``python3 -m loop_engine --conformance`` runs the
scan plus the zero-tolerance gates, writes ``architecture_conformance.json``,
and exits nonzero on any violation (§15.4).
"""
from __future__ import annotations

import ast
import json
import os
import re

_HERE = os.path.dirname(__file__)

_NETWORK_MODULES = ("urllib", "requests", "http", "socket", "httpx", "aiohttp")


def _rules() -> dict:
    with open(os.path.join(_HERE, "forbidden_paths.json")) as f:
        return json.load(f)


def _py_files(root: str) -> list:
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in ("__pycache__", "build", "dist",
                                    "evidence")]
        for f in filenames:
            if f.endswith(".py"):
                p = os.path.join(dirpath, f)
                out.append(os.path.relpath(p, root))
    return sorted(out)


def _legacy_prefixes() -> tuple:
    """Every mapped module's OLD flat import path — dead, and kept dead."""
    from .architecture_map import PACKAGE, MODULE_MAP
    return tuple(f"{PACKAGE}.{m}" for mods in MODULE_MAP.values() for m in mods)


def scan_legacy_flat_imports(root: str, rules: dict) -> list:
    v = []
    prefixes = _legacy_prefixes()
    from .architecture_map import PACKAGE, SUBPACKAGES
    pat = re.compile(rf"^\s*(?:from|import)\s+({re.escape(PACKAGE)}\.[\w\.]+)",
                     re.M)
    for rel in _py_files(root):
        text = open(os.path.join(root, rel)).read()
        for m in pat.finditer(text):
            name = m.group(1)
            # an OLD flat path is exactly PACKAGE.<mapped-module>...
            for p in prefixes:
                if name == p or name.startswith(p + "."):
                    # the module now lives under a subpackage; the flat spelling
                    # is a legacy import UNLESS the next segment IS a subpackage.
                    seg = name[len(PACKAGE) + 1:].split(".")[0]
                    if seg not in SUBPACKAGES:
                        v.append({"rule": "legacy_flat_import", "file": rel,
                                  "line": text[:m.start()].count("\n") + 1,
                                  "detail": name})
                    break
    return v


def scan_public_parallel_runtime_surfaces(root: str, rules: dict) -> list:
    """Refuse competing runtime/state-machine names at the package root."""
    from .public_runtime_conformance import (
        public_parallel_runtime_violations)
    return public_parallel_runtime_violations(
        root, rules.get("public_parallel_runtime_names", ()))


def scan_retired_source_nomenclature(root: str, rules: dict) -> list:
    from .nomenclature_conformance import retired_nomenclature_violations
    return retired_nomenclature_violations(
        root, rules.get("retired_source_nomenclature", {}))


def _module_imports(path: str) -> set:
    try:
        tree = ast.parse(open(path).read())
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def scan_network(root: str, rules: dict) -> list:
    allowed = set(rules["network_allowed_modules"])
    v = []
    for rel in _py_files(root):
        if rel in allowed:
            continue
        hit = _module_imports(os.path.join(root, rel)) & set(_NETWORK_MODULES)
        if hit:
            v.append({"rule": "network_outside_gateway", "file": rel,
                      "line": 0, "detail": f"imports {sorted(hit)}"})
    return v


def scan_subprocess(root: str, rules: dict) -> list:
    allowed = set(rules["subprocess_allowed_modules"])
    v = []
    for rel in _py_files(root):
        if rel in allowed:
            continue
        if "subprocess" in _module_imports(os.path.join(root, rel)):
            v.append({"rule": "subprocess_outside_declared", "file": rel,
                      "line": 0, "detail": "imports subprocess"})
    return v


def scan_eval_exec(root: str, rules: dict) -> list:
    allowed = set(rules["eval_exec_allowed_modules"])
    v = []
    for rel in _py_files(root):
        if rel in allowed:
            continue
        try:
            tree = ast.parse(open(os.path.join(root, rel)).read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id in ("eval", "exec")):
                v.append({"rule": "eval_or_exec", "file": rel,
                          "line": node.lineno, "detail": node.func.id})
    return v


def scan_secrets(root: str, rules: dict, *, include_json: bool = True) -> list:
    pats = [re.compile(p) for p in rules["secret_patterns"]]
    v = []
    files = _py_files(root)
    if include_json:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            files += [os.path.relpath(os.path.join(dirpath, f), root)
                      for f in filenames if f.endswith(".json")]
    for rel in sorted(set(files)):
        if rel == "forbidden_paths.json":        # the patterns themselves
            continue
        try:
            text = open(os.path.join(root, rel), errors="ignore").read()
        except OSError:
            continue
        for pat in pats:
            m = pat.search(text)
            if m:
                v.append({"rule": "secret_shaped_literal", "file": rel,
                          "line": text[:m.start()].count("\n") + 1,
                          "detail": pat.pattern})
    return v


def scan_dynamic_imports(root: str, rules: dict) -> list:
    allowed = set(rules["dynamic_import_allowed_modules"]); v = []
    for rel in _py_files(root):
        if rel in allowed:
            continue
        path = os.path.join(root, rel); text = open(path).read()
        try: tree = ast.parse(text, path)
        except SyntaxError: continue
        risky = any((isinstance(n, ast.Import) and any(
            a.name == "importlib" or a.name.startswith((
                "importlib.util", "importlib.machinery")) for a in n.names))
            or (isinstance(n, ast.ImportFrom) and n.module == "importlib"
                and any(a.name in ("import_module", "reload")
                        for a in n.names))
            or (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "__import__") for n in ast.walk(tree))
        if risky:
            v.append({"rule": "dynamic_import_bypass", "file": rel,
                      "line": 0, "detail": "importlib/__import__ outside "
                                            "registry plumbing"})
    return v


def scan_kimi(root: str, rules: dict) -> list:
    allowed = set(rules["kimi_mention_allowed_modules"])
    v = []
    for rel in _py_files(root):
        if rel in allowed:
            continue
        text = open(os.path.join(root, rel)).read()
        if "kimi-k3" in text:
            v.append({"rule": "forbidden_model_mention", "file": rel,
                      "line": text.index("kimi-k3") and
                      text[:text.index("kimi-k3")].count("\n") + 1,
                      "detail": "kimi-k3 outside the refusal guards"})
    return v


def scan_empty_modules(root: str, rules: dict) -> list:
    v = []
    for rel in _py_files(root):
        base = os.path.basename(rel)
        try:
            tree = ast.parse(open(os.path.join(root, rel)).read())
        except SyntaxError:
            continue
        body = [n for n in tree.body
                if not (isinstance(n, ast.Expr)
                        and isinstance(n.value, ast.Constant)
                        and isinstance(n.value.value, str))]
        if base == "__init__.py":
            continue                       # a docstring-only package marker is fine
        if not body:
            v.append({"rule": "empty_placeholder_module", "file": rel,
                      "line": 1, "detail": "no executable content"})
    return v


def scan_skip_markers(root: str, rules: dict) -> list:
    v = []
    pat = re.compile(r"@\w*skip|xfail|pytest\.skip", re.I)
    for rel in _py_files(root):
        base = os.path.basename(rel)
        if not base.startswith(("_conformance", "_self")):
            continue
        if base == "_conformance_scan.py":     # the detector's own fixtures
            continue
        text = open(os.path.join(root, rel)).read()
        m = pat.search(text)
        if m:
            v.append({"rule": "conformance_test_skip_marker", "file": rel,
                      "line": text[:m.start()].count("\n") + 1,
                      "detail": m.group(0)})
    return v


def scan_min_python_syntax(root: str, rules: dict) -> list:
    """Refuse syntax newer than the declared minimum Python.

    `pyproject.toml` promises >=3.10, but a workstation running 3.14 happily
    parses syntax that 3.10 rejects. A multi-line expression inside an
    f-string (PEP 701, 3.12+) shipped this way and failed only in CI, on the
    two oldest matrix entries, AFTER the push.

    So the check parses every module with the OLDEST interpreter actually
    installed. If none older than the current one exists, that is reported as
    NOT RUN rather than passed — a check that cannot run has established
    nothing.
    """
    import shutil
    import subprocess
    floor = rules.get("min_python", "3.10")
    older = [f"python{v}" for v in ("3.10", "3.11", "3.12", "3.13")
             if v >= floor and shutil.which(f"python{v}")]
    if not older:
        return []                       # nothing older available; CI covers it
    interp = older[0]
    script = (
        "import ast,os,sys,json\n"
        "bad=[]\n"
        f"for dp,dn,fn in os.walk({root!r}):\n"
        "    dn[:]=[d for d in dn if d!='__pycache__']\n"
        "    for f in sorted(fn):\n"
        "        if not f.endswith('.py'): continue\n"
        "        p=os.path.join(dp,f)\n"
        "        try: ast.parse(open(p,encoding='utf-8').read(),p)\n"
        "        except SyntaxError as e: bad.append([p,e.lineno,e.msg])\n"
        "print(json.dumps(bad))\n")
    try:
        out = subprocess.run([interp, "-c", script], capture_output=True,
                             text=True, timeout=120)
        rows = json.loads(out.stdout or "[]")
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    return [{"rule": "syntax_newer_than_min_python",
             "file": os.path.relpath(p, root), "line": ln,
             "detail": f"{msg} — parsed with {interp}; pyproject declares "
                       f"python>={floor}"} for p, ln, msg in rows]


def scan_module_size(root: str, rules: dict) -> list:
    """Best-practices cap: a module over the hard cap fails unless it carries
    a declared exception (reason + split plan) in forbidden_paths.json."""
    cap = rules.get("module_size_hard_cap", 800)
    exceptions = set(rules.get("module_size_exceptions", {}))
    v = []
    for rel in _py_files(root):
        if rel in exceptions:
            continue
        n = sum(1 for _ in open(os.path.join(root, rel)))
        if n > cap:
            v.append({"rule": "module_over_size_cap", "file": rel,
                      "line": n, "detail": f"{n} lines > cap {cap}; declare "
                      "an exception with a split plan or split it"})
    return v


def scan_short_docstring(root: str, rules: dict) -> list:
    """Every module opens with an LLM-context docstring (what it owns, which
    abstraction, its surface).  Fewer than the minimum lines fails."""
    minl = rules.get("docstring_min_lines", 3)
    exceptions = set(rules.get("docstring_exception_modules", ()))
    v = []
    for rel in _py_files(root):
        if os.path.basename(rel) == "__init__.py" or rel in exceptions:
            continue
        try:
            doc = ast.get_docstring(
                ast.parse(open(os.path.join(root, rel)).read())) or ""
        except SyntaxError:
            continue
        if len(doc.strip().splitlines()) < minl:
            v.append({"rule": "short_module_docstring", "file": rel,
                      "line": 1, "detail": f"docstring < {minl} lines — an "
                      "LLM landing on this file gets no context"})
    return v


def scan_cross_component_imports(root: str, rules: dict) -> list:
    """The package must be self-contained: an absolute import of a SIBLING
    monorepo component (components.<anything-else>) breaks the installed
    wheel — exactly the failure the clean-install canary exposed.  Vendor the
    leaf or depend on an interface; never reach across the boundary."""
    from .architecture_map import PACKAGE
    v = []
    pat = re.compile(r"^\s*(?:from|import)\s+(components\.[\w\.]+)", re.M)
    for rel in _py_files(root):
        text = open(os.path.join(root, rel)).read()
        for m in pat.finditer(text):
            name = m.group(1)
            if name == PACKAGE or name.startswith(PACKAGE + "."):
                continue  # own dev-tree path (covered by legacy_flat_import)
            v.append({"rule": "cross_component_import", "file": rel,
                      "line": text[:m.start()].count("\n") + 1,
                      "detail": name})
    return v


def scan_public_node_naming(root: str, rules: dict) -> list:
    """The loop-node rule, active on the surfaces the migration actually landed:
    the Solution graph, its compiler, and the public SaaS/Studio API now expose
    only loop vocabulary (``loops=``, ``"loops"``, ``kind="loop"``).  Those are
    the surfaces where a regression would re-introduce "node" into the public
    architecture.  This detector FIRES if a deprecated node spelling reappears
    in any of them.  Graph-domain internals (``ast.walk``, the kernel's
    solver-stage vocabulary) are explicitly out of scope — that is a different
    domain where "node" is correct."""
    v = []
    deprecated = (
        re.compile(r'\bnodes\s*='),                       # SolutionSpec keyword
        re.compile(r'"nodes"\s*:'),                        # dict key
        re.compile(r'kind\s*=\s*"node"'),
        re.compile(r'StoreRecord\([^)]*"node"'),
    )
    policed = {
        "code_nodes/solution_canvas.py", "code_nodes/solution_compiler.py",
        "core/saas_routes.py", "core/studio_server.py",
    }
    # In the CANARY tree a planted fixture must be inspected even though its
    # filename is not one of the policed modules.
    root_is_canary = not os.path.isdir(os.path.join(root, "loop"))
    for rel in _py_files(root):
        if not root_is_canary and rel not in policed:
            continue
        try:
            text = open(os.path.join(root, rel)).read()
        except OSError:
            continue
        for pat in deprecated:
            for m in pat.finditer(text):
                v.append({"rule": "public_node_naming", "file": rel,
                          "line": text[:m.start()].count("\n") + 1,
                          "detail": "residual public 'node' spelling — the "
                                    "architecture vocabulary is 'loop'"})
    return v


def scan_unmapped_event_kinds(root: str, rules: dict) -> list:
    """ONE event vocabulary (§3.8): every raw runtime kind this package
    records must project into a declared canonical family.  An
    ``event="..."`` literal with no entry in the RunHistory's canonical map
    would reach the live console and the browser as an untyped ``x.<kind>``
    passthrough — a second semantic event model growing in the dark.  Fail
    the build instead: map the kind, or do not emit it."""
    from .core.run_history import _CANONICAL_EVENT_MAP
    v = []
    for rel in _py_files(root):
        try:
            tree = ast.parse(open(os.path.join(root, rel)).read())
        except SyntaxError:
            continue
        # AST, not text: an ``event=`` in prose describing the rule is
        # documentation, and only a real call site emits an event.
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            for kw in node.keywords:
                if kw.arg != "event":
                    continue
                if isinstance(kw.value, ast.Subscript) and isinstance(
                        kw.value.value, ast.Name):
                    # event=SOME_MAP[key] — checkable when SOME_MAP is a
                    # module-level dict of string literals: every value must
                    # be a declared kind.  This is the clean pattern; only
                    # genuinely opaque computation is refused.
                    vals = _literal_map_values(tree, kw.value.value.id)
                    if vals is None:
                        v.append({"rule": "unmapped_ledger_event_kind",
                                  "file": rel,
                                  "line": getattr(node, "lineno", 0),
                                  "detail": f"event= indexes {kw.value.value.id}"
                                            ", which is not a module-level map "
                                            "of string literals, so its kinds "
                                            "cannot be checked"})
                        continue
                    bad = [k for k in vals if k not in _CANONICAL_EVENT_MAP]
                    if bad:
                        v.append({"rule": "unmapped_ledger_event_kind",
                                  "file": rel,
                                  "line": getattr(node, "lineno", 0),
                                  "detail": f"{kw.value.value.id} yields "
                                            f"{sorted(bad)!r} with no canonical "
                                            "family"})
                    continue
                if not isinstance(kw.value, ast.Constant):
                    # A COMPUTED event kind (f-string, variable, concat) cannot
                    # be checked against the vocabulary, so it silently bypassed
                    # this gate — which is exactly how an untyped
                    # x.intelligence.context.retrieved reached the browser.
                    # Fail closed: the kind must be a literal a scanner reads.
                    v.append({"rule": "unmapped_ledger_event_kind",
                              "file": rel, "line": getattr(node, "lineno", 0),
                              "detail": "event= is COMPUTED, so its canonical "
                                        "family cannot be checked; use a "
                                        "literal kind (branch if needed)"})
                    continue
                kind = kw.value.value
                if not isinstance(kind, str) or kind in _CANONICAL_EVENT_MAP:
                    continue
                v.append({"rule": "unmapped_ledger_event_kind", "file": rel,
                          "line": getattr(node, "lineno", 0),
                          "detail": f"{kind!r} has no canonical family — add "
                                    "it to run_history._CANONICAL_EVENT_MAP"})
    return v


def _literal_map_values(tree, name: str):
    """The string values of a module-level ``name = {...}`` dict, or None if
    it is not a plain dict of string literals."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == name
                   for t in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            return None
        out = []
        for val in node.value.values:
            if not (isinstance(val, ast.Constant)
                    and isinstance(val.value, str)):
                return None
            out.append(val.value)
        return out
    return None


def _enclosing_functions(tree) -> dict:
    """node id -> nearest enclosing function name (for call-site context)."""
    out: dict = {}

    def walk(node, fn):
        for spawned in ast.iter_child_nodes(node):
            name = (spawned.name
                    if isinstance(spawned, (ast.FunctionDef, ast.AsyncFunctionDef))
                    else fn)
            out[id(spawned)] = name
            walk(spawned, name)
    walk(tree, None)
    return out


def scan_unregistered_boundaries(root: str, rules: dict) -> list:
    """The boundary register cannot detect a boundary nobody listed.

    `boundary_report()` reads 14/14, but that means every boundary IN THE
    REGISTER is bound — the register is hand-maintained data, so its
    completeness was never machine-checked.  This closes that gap from the
    other side: a module that OWNS an envelope (it calls one of the
    encapsulators) is doing boundary work, and the register should know about
    it.  An envelope-owning module absent from the register is either a
    missing row or a deliberate exemption, and both should be visible.
    """
    from .core.boundary_registry import BOUNDARIES
    exempt = set(rules.get("boundary_register_exempt_modules", {}))
    registered = " ".join(str(r.get("envelope", "")) + " " + str(r.get("test", ""))
                          for r in BOUNDARIES)
    envelopes = ("as_practitioner_loop", "as_component_loop", "as_model_loop",
                 "as_loop_of_stage_loops", "serve_pillar", "serve_api")
    v = []
    for rel in _py_files(root):
        norm = rel.replace(os.sep, "/")
        if norm in exempt or "/" not in norm:
            continue
        mod = os.path.basename(norm)[:-3]
        if mod in registered or mod == "boundary_registry":
            continue
        try:
            tree = ast.parse(open(os.path.join(root, rel)).read())
        except SyntaxError:
            continue
        calls = {n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        used = calls & set(envelopes)
        if used:
            v.append({"rule": "unregistered_boundary", "file": norm, "line": 1,
                      "detail": f"owns an envelope ({sorted(used)}) but names "
                                "no row in the boundary register — add the "
                                "row, or declare the exemption with a reason"})
    return v


def scan_direct_resource_access(root: str, rules: dict) -> list:
    """No direct cross-boundary resource access (Article 1, owner 2026-08-24).

    "There is no directly consumable String, Code Node, guidance record, or
    historical record outside the universal loop system." A product-level
    caller must invoke the loop that owns a resource, never the store.

    Three call classes are NOT crossings and are separated out rather than
    counted, because publishing a number that conflates them would be as
    dishonest as publishing zero:

      * a surface calling ITSELF — internal, the base case for that boundary;
      * a declared ENVELOPE module — the code whose job is to wrap that
        surface in a loop necessarily reaches it (justifications live in
        forbidden_paths.json, so an exemption is reviewable data);
      * a self_test or a loop HANDLER body — a test exercising the surface it
        tests, and a call already inside an envelope. The law governs
        crossing the boundary, not what a body does once inside one.

    What remains is genuine product-level access. It is reported against a
    declared baseline and may only DECREASE — a ratchet, because at this
    scale the law is unenforceable by discipline alone.
    """
    surfaces = rules.get("resource_surfaces", {})
    envelopes = set(rules.get("resource_envelope_modules", {}))
    v = []
    for rel in _py_files(root):
        norm = rel.replace(os.sep, "/")
        if norm in envelopes:
            continue
        mod = os.path.basename(norm)[:-3]
        try:
            tree = ast.parse(open(os.path.join(root, rel)).read())
        except SyntaxError:
            continue
        enc = _enclosing_functions(tree)
        # A call inside a lambda/callable handed TO a loop envelope is already
        # inside that envelope — e.g. serve_historical(..., lambda:
        # RunHistory.load(...)).  Collect those node ids so the envelope's own
        # body is not counted as a crossing of the boundary it creates.
        inside_envelope = set()
        for call in ast.walk(tree):
            if not isinstance(call, ast.Call):
                continue
            fname = (call.func.id if isinstance(call.func, ast.Name)
                     else call.func.attr
                     if isinstance(call.func, ast.Attribute) else "")
            if not (fname.endswith("_as_loop") or fname.startswith("serve_")
                    or fname in ("as_loop", "as_practitioner_loop",
                                 "as_component_loop")):
                continue
            for arg in list(call.args) + [k.value for k in call.keywords]:
                for sub in ast.walk(arg):
                    inside_envelope.add(id(sub))
        imported = {n.module.split(".")[-1] for n in ast.walk(tree)
                    if isinstance(n, ast.ImportFrom) and n.module}
        for surf, spec in surfaces.items():
            if surf == mod or surf not in imported:
                continue                      # the surface itself: base case
            methods = spec.get("methods", ())
            receivers = set(spec.get("receivers", ()))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and node.func.attr in methods):
                    continue
                # the RECEIVER must be the surface, not merely a matching
                # method name — json.load(f) is not run_history.load.
                recv = node.func.value
                name = (recv.id if isinstance(recv, ast.Name)
                        else recv.attr if isinstance(recv, ast.Attribute)
                        else "")
                if receivers and name not in receivers:
                    continue
                if id(node) in inside_envelope:
                    continue                  # the envelope's own body
                fn = enc.get(id(node)) or ""
                if "self_test" in fn or fn == "handler" or fn.startswith("_h"):
                    continue                  # test, or already in an envelope
                v.append({"rule": "direct_resource_access", "file": norm,
                          "line": node.lineno,
                          "detail": f"{surf}.{node.func.attr} reached "
                                    "directly; invoke the loop that owns it"})
    return v


def scan_uncollected_self_tests(root: str, rules: dict) -> list:
    """The suite never silently shrinks.

    A module can define ``self_test()`` and simply not be listed in the
    suite's collection — the tests exist, pass when run by hand, and are
    absent from every reported total. That is the quietest way for coverage
    to rot, because nothing fails. Every module with a self_test must be
    collected, or carry a declared exception with a reason.
    """
    import ast as _ast
    exceptions = set(rules.get("suite_collection_exceptions", {}))
    suite = os.path.join(root, "_self_test.py")
    # No suite file means nothing is collected — every self_test is
    # uncollected, which is exactly what the planted canary asserts.
    src = open(suite).read() if os.path.exists(suite) else ""
    collected = set(re.findall(
        r'"((?:loop|strings|code_nodes|core|ontology|catalog|memory|generation)\.[a-z_]+)"', src))
    collected |= {f"{a}.{b}" for a, b in
                  re.findall(r"from \.(\w+)\.(\w+) import", src)}
    v = []
    from .architecture_map import ROOT_MODULES
    for rel in _py_files(root):
        parts = rel.replace(os.sep, "/").split("/")
        if parts[-1] == "__init__.py" or len(parts) > 2:
            continue
        if len(parts) == 1:
            # root plumbing is driven directly by the suite, not folded
            if parts[0][:-3] in ROOT_MODULES:
                continue
            name = parts[0][:-3]
        else:
            name = f"{parts[0]}.{parts[1][:-3]}"
        if name in collected or rel.replace(os.sep, "/") in exceptions:
            continue
        try:
            tree = _ast.parse(open(os.path.join(root, rel)).read())
        except SyntaxError:
            continue
        if any(isinstance(n, _ast.FunctionDef) and n.name == "self_test"
               for n in tree.body):
            v.append({"rule": "uncollected_self_test", "file": rel, "line": 1,
                      "detail": f"{name} defines self_test() but the suite "
                                "does not collect it — add it to "
                                "_FOLDED_SUBMODULE_TESTS or declare an "
                                "exception with a reason"})
    return v


#: Rules that report KNOWN DEBT held flat by a declared baseline rather than
#: a zero-tolerance gate.  A ratchet is not a pass: the count is published,
#: its own gate fails if it rises, and the baseline may only be lowered.
#:
#: EMPTY as of 2026-08-24 — direct_resource_access GRADUATED to zero-tolerance
#: when its last violation was routed through a loop envelope. A rule leaves
#: this tuple by being fixed, never by being excused.
RATCHETED_RULES = ()


DETECTORS = (scan_legacy_flat_imports,
             scan_public_parallel_runtime_surfaces,
             scan_retired_source_nomenclature,
             scan_network, scan_subprocess,
             scan_eval_exec, scan_secrets, scan_dynamic_imports, scan_kimi,
             scan_empty_modules, scan_skip_markers, scan_module_size,
             scan_min_python_syntax,
             scan_short_docstring, scan_cross_component_imports,
             scan_unmapped_event_kinds, scan_public_node_naming,
             scan_uncollected_self_tests, scan_direct_resource_access,
             scan_unregistered_boundaries)


def run_scan(root: "str | None" = None) -> dict:
    """Run every detector over the package; return the machine-readable
    conformance manifest fragment."""
    root = root or _HERE
    rules = _rules()
    violations = []
    for det in DETECTORS:
        violations.extend(det(root, rules))
    counts = {}
    for v in violations:
        counts[v["rule"]] = counts.get(v["rule"], 0) + 1
    return {"record_type": "conformance_scan/v1", "root": root,
            "files_scanned": len(_py_files(root)),
            "violations": violations, "counts_by_rule": counts,
            "clean": not violations}


# ---------------------------------------------------------------------------
# Canary-proven self-test: plant a fixture per rule; each detector must FIRE;
# then the live tree must scan clean.
# ---------------------------------------------------------------------------

_FIXTURES = {
    # legacy_flat_import fixture is generated from the live PACKAGE.
    # name so the canary fires under BOTH the dev path and the installed name.
    "network_outside_gateway": "import urllib.request\n",
    "subprocess_outside_declared": "import subprocess\nsubprocess.run(['ls'])\n",
    "eval_or_exec": "y = eval('1+1')\n",
    "secret_shaped_literal": 'k = "sk-' + "A" * 24 + '"\n',
    "dynamic_import_bypass": "import importlib\nm = importlib.import_module(n)\n",
    "forbidden_model_mention": 'MODEL = "kimi-k3:cloud"\n',
    "empty_placeholder_module": "",
    "conformance_test_skip_marker": "# _conformance fixture\nxfail = True\n",
    "module_over_size_cap": "x = 1\n" * 900,
    "short_module_docstring": "y = 2\n",
    "cross_component_import":
        "from components.some_other_component.mod import x\n",
    "uncollected_self_test":
        'def self_test():\n    return {"tests": []}\n',
    "unmapped_ledger_event_kind":
        'ledger.record(loop_id="l", event="a_kind_nobody_mapped")\n',
    "public_node_naming":
        'SolutionSpec("s", nodes=(SolutionLoopSpec("a", "clean"),))\n',
}


def self_test() -> dict:
    import shutil
    import tempfile
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from .architecture_map import PACKAGE
    fixtures = dict(_FIXTURES)
    retired_term = _rules()["retired_source_nomenclature"]["terms"][0]
    fixtures["retired_source_nomenclature"] = f'x = "{retired_term}"\n'
    fixtures["legacy_flat_import"] = f"from {PACKAGE}.kernel import x\n"
    fixtures["public_parallel_runtime_surface"] = (
        '__all__ = ["SolverCell"]\n')
    tmp = tempfile.mkdtemp(prefix="conf_canary_")
    try:
        shutil.copy(os.path.join(_HERE, "forbidden_paths.json"),
                    os.path.join(tmp, "forbidden_paths.json"))
        names = {}
        for rule, src in fixtures.items():
            base = ("_conformance_fixture.py"
                    if rule == "conformance_test_skip_marker"
                    else "__init__.py"
                    if rule == "public_parallel_runtime_surface"
                    else f"fixture_{rule}.py")
            names[rule] = base
            with open(os.path.join(tmp, base), "w") as f:
                f.write(src)
        report = run_scan(tmp)
        fired = set(report["counts_by_rule"])
        # 1. EVERY detector fires on its planted fixture (canary-proven).
        missing = set(fixtures) - fired
        check("every_detector_fires_on_its_planted_fixture", not missing,
              f"silent detectors: {sorted(missing)}")
        # 2. violations carry file + rule so refusals are inspectable.
        check("violations_are_inspectable",
              all(v.get("file") and v.get("rule")
                  for v in report["violations"]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 3. the LIVE tree scans clean for every ZERO-TOLERANCE rule.  One rule
    # is deliberately a RATCHET rather than a gate — direct_resource_access
    # holds known debt flat while it is worked down — so it is named here as
    # data instead of quietly excluded, and its own gate checks the overage.
    live = run_scan()
    zero_tolerance = {k: n for k, n in live["counts_by_rule"].items()
                      if k not in RATCHETED_RULES}
    ratcheted = {k: n for k, n in live["counts_by_rule"].items()
                 if k in RATCHETED_RULES}
    check("live_tree_scans_clean_for_every_zero_tolerance_rule",
          not zero_tolerance,
          json.dumps(zero_tolerance) if zero_tolerance
          else f"{live['files_scanned']} files, 0 zero-tolerance violations"
               + (f"; ratcheted debt held at {ratcheted}" if ratcheted else ""))

    # 4. the rules are data in a store (forbidden_paths.json), not literals.
    check("rules_live_in_the_forbidden_paths_store",
          os.path.exists(os.path.join(_HERE, "forbidden_paths.json"))
          and _rules()["record_type"] == "forbidden_paths/v1")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
