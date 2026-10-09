"""The three.js adapter of the engine API cards: the JSDoc reader, the entry's exports, the JavaScript signatures, the
Node check, and the reader and line end to end against a fake registry and repository, through every qualification
check on the stored bytes (sandbox and mutation when bubblewrap is available; the Node check when Node is installed).

Known-wrong controls: a member tagged @private, an undocumented member and a JSDoc @static that the code contradicts
are not listed; Node refuses a method and a property the module does not have and a wrong parent; a package built
from another commit, a tarball whose integrity differs and a class whose published source differs from the tag's are
refused by name; a card whose test cannot fail is refused by mutation.
"""
from __future__ import annotations

import base64
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

from engine_api_cards import cards, jsdoc_reference, node_native  # noqa: E402
from engine_api_cards.jsdoc_reference import module_exports, parse_block, parameter, read_classes  # noqa: E402
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
COMMIT = "9b4a2ac29c63ccb43fd51c5661f2f873ac2c39b8"

VECTOR = """import { clamp } from './MathUtils.js';

/**
 * Class representing a vector, wrapped
 * over two lines.
 *
 * Use it with {@link Thing} or {@link Thing#move the move method}.
 */
class Vector {

	static {

		/**
		 * This flag can be used for type testing.
		 *
		 * @type {boolean}
		 * @readonly
		 * @default true
		 */
		Vector.prototype.isVector = true;

	}

	/**
	 * Constructs a new vector.
	 *
	 * @param {number} [x=0] - The x value.
	 * @param {number} [y] - The y value.
	 * @param {Object} [options] - Options.
	 * @param {number} [options.scale=1] - A field of the options, not a parameter.
	 */
	constructor( x = 0, y, options = {} ) {

		/**
		 * The x value.
		 *
		 * @type {number}
		 */
		this.x = x;

		this._hidden = 1;

		/**
		 * Internal.
		 *
		 * @private
		 * @type {number}
		 */
		this.secret = 2;

		/**
		 * Doubles the vector in place.
		 *
		 * @return {Vector} This vector.
		 */
		this.double = function () {

			return this;

		};

	}

	/**
	 * The length of the vector.
	 *
	 * @type {number}
	 */
	get length() {

		return 1;

	}

	/**
	 * The label of the vector.
	 *
	 * @type {string}
	 */
	get label() {

		return '';

	}

	set label( value ) {}

	/**
	 * Adds a vector.
	 *
	 * @param {{x: number, y: number}} v - The vector to add.
	 * @return {Vector} A reference to this vector.
	 */
	add( v ) {

		return this;

	}

	/**
	 * Wrongly documented as static: the code decides.
	 *
	 * @static
	 * @return {number} One.
	 */
	one() {

		return 1;

	}

	/**
	 * Creates a vector from an array.
	 *
	 * @param {Array<number>} array - The array.
	 * @return {Vector} The new vector.
	 */
	static fromArray( array ) {

		return new Vector();

	}

	/**
	 * Loads asynchronously.
	 *
	 * @deprecated Use add() instead.
	 * @return {Promise<Vector>} A promise.
	 */
	async load() {

		return this;

	}

	undocumented() {}

}

export { Vector };
"""
THING = """/**
 * A thing that moves.
 */
class Thing {

	/**
	 * Constructs a thing; it needs a name.
	 *
	 * @param {string} name - The name.
	 */
	constructor( name ) {

		if ( name === undefined ) throw new Error( 'a thing needs a name' );

		/**
		 * The name.
		 *
		 * @type {string}
		 */
		this.name = name;

	}

	/**
	 * Moves the thing.
	 *
	 * @param {number} distance - How far.
	 */
	move( distance ) {}

}

/**
 * A faster thing.
 *
 * @augments Thing
 */
class FastThing extends Thing {

	/**
	 * Moves the thing twice.
	 *
	 * @param {number} distance - How far.
	 */
	sprint( distance ) {}

}

export { Thing, FastThing };
"""
ENTRY = "export * from './Core.js';\nexport { Vector } from './math/Vector.js';\n"
CORE = "import { Thing, FastThing } from './Thing.js';\nexport { Thing, FastThing as Runner };\nexport const VERSION = 1;\n"
LICENSE = (ROOT / "LICENSE").read_bytes()
SOURCES = {"src/Three.js": ENTRY, "src/Core.js": CORE, "src/math/Vector.js": VECTOR, "src/Thing.js": THING}


def module(sources=SOURCES) -> str:
    """One ES module holding every class, the way the built module bundles them."""
    body = [text for path, text in sorted(sources.items()) if path.endswith(("Vector.js", "Thing.js"))]
    return "\n".join(part.replace("import { clamp } from './MathUtils.js';\n", "").split("export {")[0]
                     for part in body) + "\nexport { Vector, Thing, FastThing as Runner };\n"


class JsDocReaderTests(unittest.TestCase):
    def test_blocks_parameters_and_returns(self):
        block = parse_block("/**\n * Text.\n *\n * @param {number} [x=0] - The x.\n *   More.\n * @return {A} The a.\n */")
        self.assertEqual(block.description, "Text.")
        self.assertEqual(block.tags, [("param", "{number} [x=0] - The x.\n  More."), ("return", "{A} The a.")])
        self.assertEqual(parameter("{number} [x=0] - The x."),
                         {"name": "x", "type": "number", "optional": True, "default": "0", "description": "The x."})
        self.assertEqual(parameter("{{x: number}} v - A record."),
                         {"name": "v", "type": "{x: number}", "description": "A record."})
        self.assertIsNone(parameter("{number} [options.scale=1] - A field, not a parameter."))

    def test_a_class_is_read_with_its_documented_public_members_and_the_code_decides_static(self):
        (name, parent, reference), = read_classes(VECTOR)
        self.assertEqual((name, parent), ("Vector", None))
        self.assertEqual(reference.documentation["brief"], "Class representing a vector, wrapped over two lines.")
        sections = reference.sections
        self.assertEqual(sections["constructors"], [{"name": "Vector", "params": [
            {"name": "x", "type": "number", "optional": True, "default": "0"},
            {"name": "y", "type": "number", "optional": True}, {"name": "options", "type": "Object", "optional": True}]}])
        self.assertEqual([(row["name"], row.get("qualifiers", [])) for row in sections["methods"]],
                         [("double", []), ("add", []), ("one", []), ("fromArray", ["static"]), ("load", ["async"])])
        self.assertEqual([(row["name"], row["type"], row.get("default"), row.get("qualifiers", []))
                          for row in sections["members"]],
                         [("isVector", "boolean", "true", ["readonly"]), ("x", "number", None, []),
                          ("length", "number", None, ["readonly"]), ("label", "string", None, [])])
        self.assertEqual(sections["methods"][1]["params"], [{"name": "v", "type": "{x: number, y: number}"}])
        documented = reference.documentation["items"]["methods"][4]
        self.assertEqual(documented["deprecated"], "Use add() instead.")
        self.assertIn("Returns: A promise.", documented["description"])
        # Known wrong: neither the private, the underscored nor the undocumented member is listed.
        names = {row["name"] for section in sections.values() for row in section}
        self.assertFalse(names & {"secret", "_hidden", "undocumented"})

    def test_a_fence_left_open_is_closed_and_a_type_across_lines_is_one_declaration(self):
        opened = "Represents audio.\n\n```js\nconst sound = new Audio( listener );"
        self.assertEqual(jsdoc_reference.jsdoc_markdown(opened, CARD.code), opened + "\n```")
        closed = "Text.\n\n```js\nconst a = 1;\n```\n\nMore."
        self.assertEqual(jsdoc_reference.jsdoc_markdown(closed, CARD.code), closed)
        block = parse_block("/**\n * Gets a range.\n *\n * @return {{\n * \tstart:number,\n * \tcount:number\n * }} The range.\n */")
        self.assertEqual(jsdoc_reference.returned(block), ({"type": "{ start:number, count:number }"}, "The range."))

    def test_links_become_code_and_inheritance_is_read(self):
        text = jsdoc_reference.jsdoc_markdown("See {@link Thing}, {@link Thing#move the move method} and "
                                              "{@link https://example.org the site}.", CARD.code)
        self.assertEqual(text, "See `Thing`, `Thing.move` (the move method) and [the site](https://example.org).")
        classes = {name: parent for name, parent, _reference in read_classes(THING)}
        self.assertEqual(classes, {"Thing": None, "FastThing": "Thing"})

    def test_the_entry_exports_are_followed_to_where_each_class_is_declared(self):
        exports = module_exports("src/Three.js", SOURCES.get)
        self.assertEqual(exports["Vector"], ("src/math/Vector.js", "Vector"))
        self.assertEqual(exports["Thing"], ("src/Thing.js", "Thing"))
        self.assertEqual(exports["Runner"], ("src/Thing.js", "FastThing"))
        self.assertEqual(exports["VERSION"], ("src/Core.js", "VERSION"))


class JavaScriptSyntaxTests(unittest.TestCase):
    def test_signatures_are_written_in_typescript_notation(self):
        cases = [("constructors", {"name": "Vector", "params": [{"name": "x", "type": "number", "optional": True,
                                                                  "default": "0"}]}, "new Vector(x: number = 0)"),
                 ("methods", {"name": "load", "params": [{"name": "url", "type": "string"},
                                                         {"name": "onLoad", "type": "function", "optional": True}],
                              "returns": {"type": "Promise<Vector>"}, "qualifiers": ["static", "async"]},
                  "static async load(url: string, onLoad?: function): Promise<Vector>"),
                 ("methods", {"name": "dispose", "params": [], "returns": None}, "dispose(): void"),
                 ("members", {"name": "isVector", "type": "boolean", "default": "true", "qualifiers": ["readonly"]},
                  "readonly isVector: boolean = true")]
        for section, item, expected in cases:
            self.assertEqual(CARD.signature(section, item, CARD.JAVASCRIPT_SYNTAX), expected)
        self.assertEqual(CARD.item_line("members", cases[3][1], CARD.JAVASCRIPT_SYNTAX),
                         "`readonly isVector: boolean = true`")


def release(**changes):
    values = dict(name="threejs", title="three.js", release="r186", version="0.186.1", api_version="r186",
                  repository="mrdoob/three.js", commit=COMMIT, binary_name="three-0.186.1.tgz",
                  binary_sha256="8" * 64, binary_version="0.186.1", docs_address="https://threejs.org/docs/",
                  syntax=CARD.JAVASCRIPT_SYNTAX, surface_source="read from the JSDoc of `three@0.186.1`",
                  surface_phrase="the surface the library's own JSDoc declares", text_format="JSDoc")
    values.update(changes)
    return cards.EngineRelease(**values)


def tarball(sources=SOURCES, extra=None) -> bytes:
    files = {f"package/{path}": text.encode() for path, text in sources.items()}
    files["package/build/three.module.js"] = module(sources).encode()
    files["package/LICENSE"] = LICENSE
    files["package/package.json"] = json.dumps({"name": "three", "version": "0.186.1", "license": "MIT"}).encode()
    files.update(extra or {})
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


class FakeReader:
    """The registry, GitHub and the tarball as the three.js reader reads them, all from fixtures."""

    def __init__(self, root: Path, *, git_head=COMMIT, integrity=None, repository_sources=SOURCES):
        self.root, self.data = root, tarball()
        self.integrity = integrity or "sha512-" + base64.b64encode(hashlib.sha512(self.data).digest()).decode()
        self.record = json.dumps({"gitHead": git_head, "license": "MIT", "dist": {
            "tarball": "https://registry.npmjs.org/three/-/three-0.186.1.tgz", "integrity": self.integrity}}).encode()
        self.files = {path: text.encode() for path, text in repository_sources.items()}
        self.files["LICENSE"] = LICENSE

    def answer(self, url, status, body):
        return Fetched(url, status, body, hashlib.sha256(body).hexdigest(), "2026-10-09T00:00:00Z", False)

    def get(self, url):
        if url.endswith("/three/0.186.1"):
            return self.answer(url, 200, self.record)
        path = url.split(f"/{COMMIT}/", 1)[-1]
        return self.answer(url, 200 if path in self.files else 404, self.files.get(path, b""))

    def github(self, path):
        if path.endswith("/commits/r186") or path.endswith(f"/commits/{COMMIT}"):
            return self.answer(path, 200, json.dumps({"sha": COMMIT}).encode())
        if "/git/trees/" in path:
            tree = [{"path": name, "type": "blob", "sha": git_blob_identity(data)} for name, data in self.files.items()]
            return self.answer(path, 200, json.dumps({"tree": tree}).encode())
        if path.endswith("/license"):
            return self.answer(path, 200, json.dumps({"sha": git_blob_identity(LICENSE), "path": "LICENSE",
                                                      "license": {"spdx_id": "MIT"}}).encode())
        return self.answer(path, 404, b"")

    def licence_text(self, repository, commit):
        return "LICENSE", LICENSE, "MIT"

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

    def read(self, **reader):
        return line.read_threejs(FakeReader(self.root, **reader), self.root / "workspace")

    def test_the_reader_pins_the_package_the_licence_and_every_exported_class(self):
        sources = self.read()
        self.assertEqual(sorted(sources.references), ["Runner", "Thing", "Vector"])
        self.assertEqual(sources.references["Runner"].parent, "Thing")
        self.assertEqual(sources.reference_paths["Runner"], "src/Thing.js")
        self.assertEqual((sources.release.commit, sources.release.syntax, sources.state_scope),
                         (COMMIT, CARD.JAVASCRIPT_SYNTAX, line.THREEJS_STATE_SCOPE))
        self.assertEqual(sources.licence["basis"], line.LICENCE_AT_THE_TAG)
        self.assertEqual(sources.refusals, [])

    def test_known_wrong_releases_are_stopped_and_a_differing_source_is_refused_by_name(self):
        with self.assertRaises(line.LineStopped) as other_commit:
            self.read(git_head="0" * 40)
        self.assertEqual(other_commit.exception.reason, "engine_binary_unverified")
        with self.assertRaises(line.LineStopped) as other_bytes:
            self.read(integrity="sha512-" + base64.b64encode(b"x" * 64).decode())
        self.assertEqual(other_bytes.exception.reason, "engine_binary_unverified")
        sources = self.read(repository_sources={**SOURCES, "src/math/Vector.js": VECTOR.replace("vector", "arrow")})
        self.assertEqual([(row["reason"], row["subject"]) for row in sources.refusals],
                         [("published_source_differs", "Vector")])
        self.assertNotIn("Vector", sources.references)

    def generate(self, verifier):
        sources = self.read()
        return line.generate(sources, verifier=verifier, code_revision=REVISION,
                             licence_text=(ROOT / "LICENSE").read_bytes(), generated_on="2026-10-09",
                             staging=self.root / "staging", workers=2)

    def fake_verifier(self, engine):
        def verify(prepared):
            records = {}
            for name, card in prepared.items():
                answer = {"known": True, "parent": (card.api["inherits"] or [""])[0], "missing": {
                    "methods": [], "members": []}}
                records[name] = line.godot_native.evidence_bytes(node_native.evidence(engine, card.api, answer,
                                                                                      card.digest))
            return records
        return verify

    def component(self, built):
        payload, bodies = built
        folder = self.root / "package" / payload["record_id"]
        for entry in payload["package"]["files"]:
            target = folder / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bodies[entry["digest"]])
        (folder / "candidate.json").write_text(json.dumps(payload), encoding="utf-8")
        return components.from_folder(folder)

    def test_cards_are_packaged_and_pass_every_static_check_on_the_stored_bytes(self):
        engine = node_native.NodeEngine("/usr/bin/node", "v22", "1" * 64, "build/three.module.js", "2" * 64)
        built, refusals, _facts, summary = self.generate(self.fake_verifier(engine))
        self.assertEqual(refusals, [])
        self.assertEqual(sorted(payload["repository"]["class"] for payload, _bodies in built),
                         ["Runner", "Thing", "Vector"])
        payload = next(payload for payload, _bodies in built if payload["repository"]["class"] == "Vector")
        self.assertEqual([fact["role"] for fact in payload["provenance"]["facts"]],
                         ["licence_text", "data_source", "package_metadata", "release"])
        population = [self.component(row) for row in built]
        context = checks.QualificationContext.load(ROOT)
        context.duplicates = checks.duplicate_findings(population, context.policy)
        for component in population:
            for check in checks.CHECKS:
                if check.check_id in ("sandbox", "mutation"):
                    continue
                result = check.run(component, context)
                self.assertEqual(result.status, checks.PASSED, (component.identity, check.check_id, result.findings))
        readme = population[[row[0]["repository"]["class"] for row in built].index("Vector")].text("README.md")
        for expected in ("# Vector (three.js r186)", "### `new Vector(x: number = 0, y?: number, options?: Object)`",
                         "### `add(v: {x: number, y: number}): Vector`", "### `static fromArray(array: Array<number>): "
                         "Vector`", "### `async load(): Promise<Vector>`", "### `readonly isVector: boolean = true`",
                         "**Deprecated:** Use add() instead.", "Use it with `Thing` or `Thing.move` (the move method)."):
            self.assertIn(expected, readme)
        if HAS_SANDBOX:
            work = checks.QualificationContext.load(ROOT, sandbox_settings=SANDBOX, work_root=self.root / "work")
            by_id = {check.check_id: check for check in checks.CHECKS}
            vector = population[[row[0]["repository"]["class"] for row in built].index("Vector")]
            self.assertEqual(by_id["sandbox"].run(vector, work).status, checks.PASSED)
            self.assertEqual(by_id["mutation"].run(vector, work).status, checks.PASSED)
            weak = vector.replaced(payloads={**vector.payloads, "test_api_card.py": (
                b"import unittest\nimport api_card\n\n\nclass T(unittest.TestCase):\n    def test_nothing(self):\n"
                b"        self.assertTrue(True)\n")})
            self.assertEqual(by_id["mutation"].run(weak, work).status, checks.REFUSED)

    @unittest.skipUnless(HAS_NODE, "node is needed for the native check")
    def test_node_confirms_the_cards_and_refuses_what_the_module_lacks(self):
        sources = self.read()
        module_file = self.root / "workspace" / line.PACKAGE_FOLDER / line.THREEJS_MODULE
        engine = node_native.locate(line.THREEJS_MODULE, hashlib.sha256(module_file.read_bytes()).hexdigest())
        built, refusals, _facts, _summary = line.generate(
            sources, verifier=lambda prepared: line.node_evidence(engine, module_file, prepared, self.root / "verify"),
            code_revision=REVISION, licence_text=(ROOT / "LICENSE").read_bytes(), generated_on="2026-10-09",
            staging=self.root / "staging", workers=2)
        self.assertEqual(refusals, [])
        self.assertEqual(len(built), 3)
        files = {payload["repository"]["class"]: {entry["path"]: bodies[entry["digest"]]
                                                  for entry in payload["package"]["files"]}
                 for payload, bodies in built}
        # Thing cannot be made without a name: its property is confirmed in the class's own source text.
        self.assertEqual(json.loads(files["Thing"]["verification/native.json"])["state"], "passed")
        # Known wrong: a method and a property the module lacks, and another parent, are each refused.
        api = json.loads(files["Runner"]["api.json"])
        api["sections"]["methods"].append({"name": "teleport", "params": [], "returns": None})
        api["sections"]["members"].append({"name": "wings", "type": "number"})
        api["inherits"] = ["Vector"]
        answers = node_native.verify(engine, module_file, [api], self.root / "verify-wrong")
        failed = node_native.evidence(engine, api, answers["Runner"], "a" * 64)
        self.assertEqual(failed["state"], "failed")
        details = {check["name"]: check["detail"] for check in failed["checks"]}
        self.assertEqual(details["methods_callable"]["missing"], ["teleport"])
        self.assertEqual(details["properties_present"]["missing"], ["wings"])
        self.assertEqual(details["parent_matches"], {"expected": "Vector", "found": "Thing"})


if __name__ == "__main__":
    unittest.main()
