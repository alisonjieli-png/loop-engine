"""The Babylon.js adapter of the engine API cards: the TypeScript declaration reader, the observation that marks a
property the published module does not hold, the Node check, and the reader and line end to end against a fake
registry and repository, through every qualification check on the stored bytes (sandbox and mutation when bubblewrap
is available; the Node checks when Node is installed).

Known-wrong controls: private, protected, internal and underscored members and index signatures are not listed; a
generic constraint is not read as the parent; a declaration's own "declare" is not taken as the observation; Node
refuses a method the module lacks, a property the card does not mark declare that the module lacks, and one the card
marks declare that the module holds; a package built from another commit, a notice file that is not the tag's and a
package whose licence field disagrees are each stopped by name.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from engine_api_cards import cards, node_native  # noqa: E402
from engine_api_cards.typescript_declarations import mark_declared, parameters, read_declarations  # noqa: E402
from loop_engine.core.library_ingestion.record_rules import git_blob_identity  # noqa: E402
from supply_lines import engine_api_cards as line  # noqa: E402
from supply_lines.reading import Digested, Fetched  # noqa: E402
from tools.component_qualification import checks, components  # noqa: E402
from tools.component_qualification.sandbox import SandboxSettings  # noqa: E402

REVISION = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
SANDBOX = SandboxSettings()
HAS_SANDBOX = bool(REVISION) and SANDBOX.works()
HAS_NODE = shutil.which("node") is not None
CARD = cards.card_module()
COMMIT = "b248b370267f13bfaf5b2a0f8fd525bad7c99b52"
APACHE = (ROOT / "tools/fixtures/licence-texts/apache-2.0-canonical.txt").read_bytes()
NOTICE = b"Babylon.js\nCopyright 2023 The Babylon.js team\n\nmeshoptimizer\nCopyright (c) 2016-2026 Arseny Kapoulkine\n"

DECLARATIONS = """import { Base } from "./base.js";
/**
 * A vector of the fixture.
 *
 * It shows every kind of member.
 */
export declare abstract class Vec extends Base {
    private _secret;
    /** @internal */
    _cache: number;
    /** A guarded value. */
    protected guard: number;
    /** A callback a caller assigns. */
    onDone: (task: Vec) => void;
    /** A count the class sets. */
    count: number;
    /** A table every vector shares. */
    static Shared: number;
    [key: string]: any;
    /** Gets or sets x. */
    get x(): number;
    set x(value: number);
    /** The length, read only. */
    get length(): number;
    /**
     * Creates a vector.
     * @param x defines the x value
     */
    constructor(x?: number);
    /**
     * Adds a vector.
     * @param other defines the other vector
     * @returns this vector
     */
    add(other: Vec): this;
    /** Scales by a number. */
    scale(factor: number): Vec;
    /** Scales by a vector. */
    scale(factor: Vec): Vec;
    /** Clones the vector. */
    clone<T extends Vec>(): T;
    /**
     * Creates a vector from an array.
     * @deprecated Use the constructor.
     */
    static FromArray(array: ArrayLike<number>, offset?: number): Vec;
    /** Each subclass draws. */
    abstract draw(): void;
    /** Sets options. */
    setOptions(options: {
        a: number;
        b?: string;
    }, ...rest: Map<string, number>[]): void;
    /** Gets or sets the size; the declaration writes the setter first. */
    set size(value: number);
    get size(): number;
    reset(): void;
}
/** Inputs of a camera. */
export declare class Inputs<T extends Vec> {
    /** The attached vector. */
    attached: T;
}
"""
COMPILED = """import { Base } from "./base.js";
export class Vec extends Base {
    constructor(x) {
        super();
        this.count = 0;
        this._cache = 0;
        this._x = x;
    }
    get x() { return this._x; }
    set x(value) { this._x = value; }
    get length() { return 1; }
    add(other) { return this; }
    scale(factor) { return this; }
    clone() { return this; }
    static FromArray(array, offset) { return new Vec(); }
    setOptions(options, ...rest) { }
    set size(value) { this._size = value; }
    get size() { return this._size; }
    reset() { }
}
Vec.Shared = 1;
export class Inputs {
    constructor() {
        this.attached = null;
    }
}
"""
BASE_DECLARATIONS = "/** The base. */\nexport declare class Base {\n    /** Disposes. */\n    dispose(): void;\n}\n"
BASE_COMPILED = "export class Base {\n    dispose() { }\n}\n"
INDEX = 'export * from "./vec.js";\nexport * from "./base.js";\n'


class DeclarationReaderTests(unittest.TestCase):
    def setUp(self):
        self.classes = {name: (parent, reference) for name, parent, reference in read_declarations(DECLARATIONS)}

    def test_parameters_are_split_outside_brackets_and_type_arguments(self):
        self.assertEqual(parameters("a: Map<string, number>, b?: (x: number, y: number) => void, ...rest: T[]"), [
            {"name": "a", "type": "Map<string, number>"},
            {"name": "b", "type": "(x: number, y: number) => void", "optional": True},
            {"name": "...rest", "type": "T[]"}])

    def test_the_public_surface_is_read_with_its_qualifiers_and_overloads(self):
        parent, reference = self.classes["Vec"]
        self.assertEqual(parent, "Base")
        sections = reference.sections
        self.assertEqual(sections["constructors"], [{"name": "Vec", "params": [
            {"name": "x", "type": "number", "optional": True}]}])
        self.assertEqual([(row["name"], row.get("qualifiers", []), row["returns"]) for row in sections["methods"]], [
            ("add", [], {"type": "this"}), ("scale", [], {"type": "Vec"}), ("scale", [], {"type": "Vec"}),
            ("clone", [], {"type": "T"}), ("FromArray", ["static"], {"type": "Vec"}),
            ("draw", ["abstract"], {"type": "void"}), ("setOptions", [], {"type": "void"}),
            ("reset", [], {"type": "void"})])
        self.assertEqual(sections["methods"][6]["params"], [{"name": "options", "type": "{ a: number; b?: string; }"},
                                                            {"name": "...rest", "type": "Map<string, number>[]"}])
        self.assertEqual([(row["name"], row["type"], row.get("qualifiers", [])) for row in sections["members"]], [
            ("onDone", "(task: Vec) => void", []), ("count", "number", []),
            ("Shared", "number", ["static"]), ("x", "number", []), ("length", "number", ["readonly"]),
            ("size", "number", [])])
        documentation = reference.documentation
        # Known answers: the setter-first property is writable with its text; the undocumented method is listed.
        self.assertEqual(documentation["items"]["members"][5]["description"],
                         "Gets or sets the size; the declaration writes the setter first.")
        self.assertEqual(documentation["items"]["methods"][7], {"description": ""})
        self.assertEqual(documentation["brief"], "A vector of the fixture.")
        self.assertIn("- `other`: defines the other vector", documentation["items"]["methods"][0]["description"])
        self.assertIn("Returns: this vector", documentation["items"]["methods"][0]["description"])
        self.assertEqual(documentation["items"]["methods"][4]["deprecated"], "Use the constructor.")
        # Known wrong: neither private, protected, internal, underscored nor index members are listed.
        names = {row["name"] for section in sections.values() for row in section}
        self.assertFalse(names & {"_secret", "guard", "_cache", "key"})

    def test_a_generic_constraint_is_not_the_parent_and_a_declaration_cannot_mark_declare_itself(self):
        self.assertIsNone(self.classes["Inputs"][0])
        _name, _parent, reference = read_declarations(
            "/** A. */\nexport declare class A {\n    /** x. */\n    declare x: number;\n}\n")[0]
        self.assertEqual(reference.sections["members"], [{"name": "x", "type": "number"}])

    def test_accessors_in_either_order_an_internal_pair_and_a_static_twin(self):
        _name, _parent, reference = read_declarations(
            "/** A. */\nexport declare class A {\n"
            "    get first(): number;\n    /** Lent by the setter. */\n    set first(value: number);\n"
            "    /** @internal */\n    get hidden(): number;\n    set hidden(value: number);\n"
            "    /** The instance one. */\n    get twin(): string;\n"
            "    /** The static one. */\n    static set twin(value: number);\n    static get twin(): number;\n}\n")[0]
        self.assertEqual(reference.sections["members"], [
            {"name": "first", "type": "number"}, {"name": "twin", "type": "string", "qualifiers": ["readonly"]},
            {"name": "twin", "type": "number", "qualifiers": ["static"]}])
        self.assertEqual([row["description"] for row in reference.documentation["items"]["members"]],
                         ["Lent by the setter.", "The instance one.", "The static one."])

    def test_the_observation_marks_declare_and_leaves_an_ambiguous_name_alone(self):
        references = {name: reference for name, (_parent, reference) in self.classes.items()}
        self.assertEqual(mark_declared(references, {"Vec": ["onDone", "draw"], "Inputs": []}), 1)
        self.assertEqual(mark_declared(references, {"Vec": ["onDone"]}), 0)  # already marked
        sections = references["Vec"].sections
        self.assertEqual(sections["members"][0]["qualifiers"], ["declare"])
        self.assertEqual(sections["methods"][5]["qualifiers"], ["abstract"])  # a method is never marked
        twins = read_declarations("/** T. */\nexport declare class T {\n    /** a. */\n    static a: number;\n"
                                  "    /** a. */\n    a: number;\n}\n")[0][2]
        self.assertEqual(mark_declared({"T": twins}, {"T": ["a"]}), 0)

    def test_the_cards_write_the_declarations_in_typescript_notation(self):
        references = {name: reference for name, (_parent, reference) in self.classes.items()}
        mark_declared(references, {"Vec": ["onDone"]})
        sections = references["Vec"].sections
        self.assertEqual(CARD.item_line("members", sections["members"][0], CARD.JAVASCRIPT_SYNTAX),
                         "`declare onDone: (task: Vec) => void`")
        self.assertEqual(CARD.item_line("methods", sections["methods"][5], CARD.JAVASCRIPT_SYNTAX),
                         "`abstract draw(): void`")
        # Every property is asked, the declared one too (the check holds it to the observation); abstract is not.
        self.assertEqual(node_native.expectation({"class": "Vec", "sections": sections}),
                         {"name": "Vec", "methods": [{"name": row["name"], "static": row["name"] == "FromArray"}
                                                     for row in sections["methods"] if row["name"] != "draw"],
                          "members": [{"name": name, "static": name == "Shared"}
                                      for name in ("onDone", "count", "Shared", "x", "length", "size")]})


def tarball(files) -> bytes:
    """The package as npm would serve it, the same bytes every time (no gzip time stamp)."""
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", mtime=0) as compressed, \
            tarfile.open(fileobj=compressed, mode="w") as archive:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(f"package/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


PACKAGE = {"index.js": INDEX.encode(), "index.d.ts": INDEX.encode(), "vec.js": COMPILED.encode(),
           "vec.d.ts": DECLARATIONS.encode(), "base.js": BASE_COMPILED.encode(),
           "base.d.ts": BASE_DECLARATIONS.encode(), "license.md": APACHE, "NOTICE.md": NOTICE,
           "package.json": json.dumps({"name": "@babylonjs/core", "version": "9.30.0", "license": "Apache-2.0",
                                       "type": "module"}).encode()}


class FakeReader:
    """The registry, GitHub and the tarball as the Babylon.js reader reads them, all from fixtures."""

    def __init__(self, root: Path, *, git_head=COMMIT, package=None, repository_notice=NOTICE):
        self.root, self.data = root, tarball(package or PACKAGE)
        self.integrity = "sha512-" + base64.b64encode(hashlib.sha512(self.data).digest()).decode()
        self.record = json.dumps({"gitHead": git_head, "license": "Apache-2.0", "dist": {
            "tarball": "https://registry.npmjs.org/@babylonjs/core/-/core-9.30.0.tgz",
            "integrity": self.integrity}}).encode()
        self.files = {"license.md": APACHE, "packages/public/@babylonjs/core/NOTICE.md": repository_notice}

    def answer(self, url, status, body):
        return Fetched(url, status, body, hashlib.sha256(body).hexdigest(), "2026-10-09T00:00:00Z", False)

    def get(self, url):
        return self.answer(url, 200 if url.endswith("/@babylonjs/core/9.30.0") else 404,
                           self.record if url.endswith("/@babylonjs/core/9.30.0") else b"")

    def github(self, path):
        if path.endswith("/commits/9.30.0"):
            return self.answer(path, 200, json.dumps({"sha": COMMIT}).encode())
        if path.endswith("/license"):
            return self.answer(path, 200, json.dumps({"sha": git_blob_identity(APACHE), "path": "license.md",
                                                      "license": {"spdx_id": "Apache-2.0"}}).encode())
        return self.answer(path, 404, b"")

    def licence_text(self, repository, commit):
        return "license.md", APACHE, "Apache-2.0"

    def pinned_file(self, repository, branch, path):
        if path not in self.files:
            raise LookupError(path)
        data = self.files[path]
        return {"repository": repository, "commit": COMMIT, "path": path, "blob": git_blob_identity(data),
                "url": f"https://raw.githubusercontent.com/{repository}/{COMMIT}/{path}", "bytes": data,
                "sha256": hashlib.sha256(data).hexdigest(), "retrieved_at": "2026-10-09T00:00:00Z"}

    def digest(self, url, *, published=None, maximum_bytes=0, inspect=None, use_cache=True):
        temporary = self.root / "download.tgz"
        temporary.write_bytes(self.data)
        inspected = inspect(temporary) if inspect else None
        return Digested(url, url, 200, hashlib.sha256(self.data).hexdigest(), "", len(self.data),
                        "2026-10-09T00:00:00Z", False, inspected)


class ReaderAndLineTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.root)

    def read(self, observe=None, **reader):
        return line.read_babylon(FakeReader(self.root, **reader), self.root / "workspace", observe=observe)

    def test_the_reader_pins_the_package_its_licence_and_notice_and_every_exported_class(self):
        sources = self.read()
        self.assertEqual(sorted(sources.references), ["Base", "Inputs", "Vec"])
        self.assertEqual(sources.reference_paths["Vec"], "vec.d.ts")
        self.assertEqual(sources.licence_expression, "MIT AND Apache-2.0")
        self.assertEqual([notice["path"] for notice in sources.notices], ["packages/public/@babylonjs/core/NOTICE.md"])
        self.assertEqual(sources.copyright_text, b"Copyright 2023 The Babylon.js team")
        self.assertEqual((sources.state_scope, sources.release.api_version), (line.BABYLONJS_STATE_SCOPE, "9.30"))
        self.assertEqual(sources.summary["declared_properties"], 0)  # nothing observed, nothing marked

    def test_known_wrong_releases_are_stopped_by_name(self):
        cases = ((dict(git_head="0" * 40), "engine_binary_unverified"),
                 (dict(repository_notice=b"another notice\n"), "published_source_differs"),
                 (dict(package={**PACKAGE, "package.json": json.dumps({"license": "MIT"}).encode()}),
                  "licence_signals_disagree"))
        for changes, reason in cases:
            with self.assertRaises(line.LineStopped) as stopped:
                self.read(**changes)
            self.assertEqual(stopped.exception.reason, reason, changes)

    def component(self, built):
        payload, bodies = built
        folder = self.root / "package" / payload["record_id"]
        for entry in payload["package"]["files"]:
            target = folder / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bodies[entry["digest"]])
        (folder / "candidate.json").write_text(json.dumps(payload), encoding="utf-8")
        return components.from_folder(folder)

    @unittest.skipUnless(HAS_NODE, "node is needed for the native check")
    def test_node_checks_the_held_surface_and_the_cards_pass_every_check_on_the_stored_bytes(self):
        sources = self.read(observe=line.node_observer(line.BABYLONJS_MODULE, self.root / "workspace"))
        # Node finds count (this.count), Shared (assigned after the class), x and length (prototype accessors) and
        # attached; only onDone is held by no part of the module.
        self.assertEqual(sources.summary["declared_properties"], 1)
        module_file = self.root / "workspace" / line.PACKAGE_FOLDER / line.BABYLONJS_MODULE
        engine = node_native.locate(line.BABYLONJS_MODULE, hashlib.sha256(module_file.read_bytes()).hexdigest())
        built, refusals, facts, _summary = line.generate(
            sources, verifier=lambda prepared: line.node_evidence(engine, module_file, prepared, self.root / "verify"),
            code_revision=REVISION, licence_text=(ROOT / "LICENSE").read_bytes(), generated_on="2026-10-09",
            staging=self.root / "staging", workers=2)
        self.assertEqual(refusals, [])
        # The store keeps the bytes of the licence, the notice and the registry record the packages name; the
        # tarball is named by digest and size only.
        record = FakeReader(self.root).record
        self.assertEqual(set(facts), {hashlib.sha256(data).hexdigest() for data in (APACHE, NOTICE, record)})
        self.assertTrue(all(hashlib.sha256(data).hexdigest() == digest for digest, data in facts.items()))
        files = {payload["repository"]["class"]: {entry["path"]: bodies[entry["digest"]]
                                                  for entry in payload["package"]["files"]}
                 for payload, bodies in built}
        evidence = json.loads(files["Vec"]["verification/native.json"])
        self.assertEqual(evidence["state"], "passed")
        details = {check["name"]: check["detail"] for check in evidence["checks"]}
        self.assertEqual(details["methods_callable"], {"checked": 7, "abstract": 1, "missing": []})
        self.assertEqual(details["properties_present"], {"checked": 6, "abstract": 0, "missing": [], "declared": 1,
                                                         "held_although_declared": []})
        readme = files["Vec"]["README.md"].decode()
        for expected in ("# Vec (Babylon.js 9.30)", "### `declare onDone: (task: Vec) => void`",
                         "### `abstract draw(): void`", "### `static FromArray(array: ArrayLike<number>, offset?: "
                         "number): Vec`", "Copyright 2023 The Babylon.js team. Apache-2.0, see `UPSTREAM-LICENSE` "
                         "and `UPSTREAM-NOTICE`.", "### `reset(): void`\n\n" + cards.NO_DESCRIPTION):
            self.assertIn(expected, readme)
        self.assertEqual(files["Vec"]["UPSTREAM-NOTICE"], NOTICE)
        population = [self.component(row) for row in built]
        context = checks.QualificationContext.load(ROOT)
        context.duplicates = checks.duplicate_findings(population, context.policy)
        for component in population:
            for check in checks.CHECKS:
                if check.check_id in ("sandbox", "mutation"):
                    continue
                result = check.run(component, context)
                self.assertEqual(result.status, checks.PASSED, (component.identity, check.check_id, result.findings))
        if HAS_SANDBOX:
            work = checks.QualificationContext.load(ROOT, sandbox_settings=SANDBOX, work_root=self.root / "work")
            by_id = {check.check_id: check for check in checks.CHECKS}
            vec = next(component for component in population if component.text("README.md").startswith("# Vec "))
            self.assertEqual(by_id["sandbox"].run(vec, work).status, checks.PASSED)
            self.assertEqual(by_id["mutation"].run(vec, work).status, checks.PASSED)
        # Known wrong: a method the module lacks, a property it lacks that the card does not mark declare, and a
        # property the card marks declare that the module holds are each refused.
        vec = json.loads(files["Vec"]["api.json"])

        def wrong(change, *, failing):
            api = json.loads(json.dumps(vec))
            change(api["sections"])
            answer = node_native.verify(engine, module_file, [api], self.root / "verify-wrong")["Vec"]
            failed = node_native.evidence(engine, api, answer, "a" * 64)
            self.assertEqual(failed["state"], "failed", failing)
            self.assertEqual([check["name"] for check in failed["checks"] if check["state"] == "failed"], [failing])
            return {check["name"]: check["detail"] for check in failed["checks"]}[failing]

        detail = wrong(lambda sections: sections["methods"].append({"name": "teleport", "params": [],
                                                                    "returns": None}), failing="methods_callable")
        self.assertEqual(detail["missing"], ["teleport"])
        detail = wrong(lambda sections: sections["members"][0].pop("qualifiers"), failing="properties_present")
        self.assertEqual((detail["missing"], detail["held_although_declared"]), (["onDone"], []))
        detail = wrong(lambda sections: sections["members"][1].update(qualifiers=["declare"]),
                       failing="properties_present")
        self.assertEqual((detail["missing"], detail["held_although_declared"]), ([], ["count"]))


if __name__ == "__main__":
    unittest.main()
