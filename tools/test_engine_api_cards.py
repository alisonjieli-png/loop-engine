"""Engine API cards: BBCode conversion, the class reference reader, the renames map, the card format and its checker,
and the native evidence (with the pinned Godot build when it is present).

Known-wrong controls: a removed item, a changed default, an extra item, a lost heading and items out of order are each
reported by the card's checker; a class reference with another structure differs from the build's; a rename whose new
name is not on the class's surface is not attached; stale, failed and unanswered native evidence is refused; the
pinned build refuses a method it does not have.
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tools", ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from engine_api_cards import bbcode, cards, godot_native, godot_renames  # noqa: E402
from engine_api_cards.godot_reference import ClassKind, ReferenceError, inheritance, read_reference  # noqa: E402

CARD = cards.card_module()
COMMIT = "ed1daf0bf001b61586d9930840f2f1394092c079"
DOCS = "https://docs.godotengine.org/en/4.7"

BODY_DUMP = """<?xml version="1.0" encoding="UTF-8" ?>
<class name="Body" inherits="Thing" api_type="core">
	<brief_description>
	</brief_description>
	<description>
	</description>
	<tutorials>
	</tutorials>
	<methods>
		<method name="get_mode" qualifiers="const">
			<return type="int" enum="Body.Mode" />
			<description>
			</description>
		</method>
		<method name="move" qualifiers="vararg">
			<return type="bool" />
			<param index="1" name="speed" type="float" default="1.0" />
			<param index="0" name="direction" type="Vector3" />
			<description>
			</description>
		</method>
	</methods>
	<members>
		<member name="mode" type="int" setter="set_mode" getter="get_mode" enum="Body.Mode" default="0">
		</member>
		<member name="visible" type="bool" setter="set_visible" getter="is_visible" overrides="Thing" default="false" />
	</members>
	<signals>
		<signal name="moved">
			<param index="0" name="distance" type="float" />
			<description>
			</description>
		</signal>
	</signals>
	<constants>
		<constant name="MODE_STILL" value="0" enum="Mode">
		</constant>
		<constant name="MODE_MOVING" value="1" enum="Mode">
		</constant>
		<constant name="FLAG_A" value="1" enum="Flags" is_bitfield="true">
		</constant>
		<constant name="LIMIT" value="8">
		</constant>
	</constants>
	<theme_items>
		<theme_item name="tint" data_type="color" type="Color" default="Color(1, 1, 1, 1)">
		</theme_item>
	</theme_items>
</class>
"""
BODY_TEXT = {
    "<brief_description>\n\t</brief_description>": "<brief_description>\n\t\tA thing that [b]moves[/b].\n"
                                                   "\t</brief_description>",
    "<description>\n\t</description>\n\t<tutorials>": "<description>\n\t\tUse [method move] with [param direction]"
                                                      " on a [Body]; see [url=$DOCS_URL/body.html]the guide[/url].\n"
                                                      "\t\t[codeblocks]\n\t\t[gdscript]\n\t\tfunc _ready():\n"
                                                      "\t\t\tmove(Vector3.UP)\n\t\t[/gdscript]\n\t\t[csharp]\n"
                                                      "\t\tMove(Vector3.Up);\n\t\t[/csharp]\n\t\t[/codeblocks]\n"
                                                      "\t</description>\n\t<tutorials>\n\t\t<link title=\"Guide\">"
                                                      "$DOCS_URL/guide.html</link>",
}
THING_DUMP = """<?xml version="1.0" encoding="UTF-8" ?>
<class name="Thing" inherits="Object" api_type="core">
	<brief_description>
	</brief_description>
	<description>
	</description>
	<tutorials>
	</tutorials>
	<members>
		<member name="visible" type="bool" setter="set_visible" getter="is_visible" default="true">
		</member>
	</members>
</class>
"""
OBJECT_DUMP = """<?xml version="1.0" encoding="UTF-8" ?>
<class name="Object" api_type="core">
	<brief_description>
	</brief_description>
	<description>
	</description>
	<tutorials>
	</tutorials>
	<methods>
		<method name="free">
			<return type="void" />
			<description>
			</description>
		</method>
	</methods>
</class>
"""
VECTOR_DUMP = """<?xml version="1.0" encoding="UTF-8" ?>
<class name="Vector3">
	<brief_description>
	</brief_description>
	<description>
	</description>
	<tutorials>
	</tutorials>
	<constructors>
		<constructor name="Vector3">
			<return type="Vector3" />
			<param index="0" name="x" type="float" />
			<description>
			</description>
		</constructor>
	</constructors>
	<methods>
		<method name="lerp" qualifiers="const">
			<return type="Vector3" />
			<param index="0" name="to" type="Vector3" />
			<param index="1" name="weight" type="float" />
			<description>
			</description>
		</method>
	</methods>
	<members>
		<member name="x" type="float" setter="" getter="" default="0.0">
		</member>
	</members>
	<constants>
		<constant name="UP" value="Vector3(0, 1, 0)">
		</constant>
	</constants>
	<operators>
		<operator name="operator ==">
			<return type="bool" />
			<param index="0" name="right" type="Vector3" />
			<description>
			</description>
		</operator>
	</operators>
</class>
"""
GLOBAL_DUMP = """<?xml version="1.0" encoding="UTF-8" ?>
<class name="@GDScript">
	<brief_description>
	</brief_description>
	<description>
	</description>
	<tutorials>
	</tutorials>
	<methods>
		<method name="len">
			<return type="int" />
			<param index="0" name="var" type="Variant" />
			<description>
			</description>
		</method>
	</methods>
	<annotations>
		<annotation name="@export_range" qualifiers="vararg">
			<return type="void" />
			<param index="0" name="min" type="float" />
			<description>
			</description>
		</annotation>
	</annotations>
</class>
"""
VARIANT_DUMP = """<?xml version="1.0" encoding="UTF-8" ?>
<class name="Variant">
	<brief_description>
	</brief_description>
	<description>
	</description>
	<tutorials>
	</tutorials>
</class>
"""
RENAMES_MAP = """// header
const char *RenamesMap3To4::enum_renames[][2] = {
	// @GDScript
	{ "OLD_LIMIT", "LIMIT" },

	{ "MODE_STAY", "MODE_STILL" }, // Body
	{ nullptr, nullptr },
};

const char *RenamesMap3To4::gdscript_function_renames[][2] = {
	// { "walk", "move" }, // Body -- disabled in the converter
	{ "go", "move" }, // Body -- Breaks Other.
	{ "fly", "glide" }, // Body
	{ "mover", "move" }, // Kinetic
	{ "nowhere", "move" },
	{ "liner", "lerp" }, // Thing(2D/3D), Vector3

	// @GDScript
	{ "lenght", "len" },
	{ nullptr, nullptr },
};

const char *RenamesMap3To4::gdscript_properties_renames[][2] = {
	{ "shown", "visible" }, // Body
	{ nullptr, nullptr },
};

const char *RenamesMap3To4::gdscript_signals_renames[][2] = {
	{ "moved_by", "moved" }, // Body
	{ nullptr, nullptr },
};

const char *RenamesMap3To4::project_settings_renames[][2] = {
	{ nullptr, nullptr },
};

const char *RenamesMap3To4::builtin_types_renames[][2] = {
	{ "Vec3", "Vector3" },
	{ nullptr, nullptr },
};

const char *RenamesMap3To4::class_renames[][2] = {
	{ "Kinetic", "Body" }, // Was 2D and 3D.
	{ "Gone", "Missing" },
	{ nullptr, nullptr },
};

const char *RenamesMap3To4::color_renames[][2] = {
	{ nullptr, nullptr },
};
"""


def documented(dump: str, replacements: dict) -> str:
    for old, new in replacements.items():
        dump = dump.replace(old, new)
    return dump


def references(*texts):
    found = {}
    for text in texts:
        reference = read_reference(text.encode("utf-8"))
        found[reference.name] = reference
    return found


class BBCodeTests(unittest.TestCase):
    def context(self, current="Body"):
        return bbcode.Context(frozenset({"Body", "Node", "Vector3", "int"}), current, DOCS)

    def convert(self, text, current="Body"):
        return bbcode.to_markdown(text, self.context(current))

    def test_known_answers(self):
        cases = {
            "[b]Note:[/b] Use [method move] on [Body] and [int].": "**Note:** Use `move()` on `Body` and `int`.",
            "See [method Node.add_child] and [member Node.name].": "See `Node.add_child()` and `Node.name`.",
            "Call [method Body.move] with [param direction].": "Call `move()` with `direction`.",
            "[enum Node.ProcessMode], [constant Vector3.UP], [signal moved].":
                "`ProcessMode`, `Vector3.UP`, `moved`.",
            "[code]a[b]b[/b][/code] and [kbd]Ctrl + C[/kbd]": "`a[b]b[/b]` and `Ctrl + C`",
            "[code]x`y[/code]": "`` x`y ``",
            "[url=$DOCS_URL/a.html]Doc[/url] and [url]https://example.org[/url]":
                f"[Doc]({DOCS}/a.html) and <https://example.org>",
            "array[lb]0[rb] is [i]first[/i][u][/u]": "array\\[0\\] is *first*",
            "a * b, _private, snake_case and <div>": "a \\* b, \\_private, snake_case and \\<div>",
            "# Not a heading": "\\# Not a heading",
            "1. Not a list": "1\\. Not a list",
            "3.14 stays": "3.14 stays",
        }
        for source, expected in cases.items():
            self.assertEqual(self.convert(source), expected, source)

    def test_lines_are_paragraphs_and_br_breaks_one(self):
        self.assertEqual(self.convert("\t\tFirst line.\n\t\tSecond[br] third."), "First line.\n\nSecond\n\nthird.")

    def test_code_blocks_keep_their_relative_indentation_and_language(self):
        text = ("\t\t[codeblocks]\n\t\t[gdscript]\n\t\tfunc f():\n\t\t\treturn 1\n\t\t[/gdscript]\n\t\t[csharp]\n"
                "\t\tint F() => 1;\n\t\t[/csharp]\n\t\t[/codeblocks]\n\t\t[codeblock lang=text]\n\t\tplain\n"
                "\t\t[/codeblock]\n\t\t[codeblock]\n\t\tvar a = [b]1[/b]\n\t\t[/codeblock]")
        self.assertEqual(self.convert(text), "```gdscript\nfunc f():\n\treturn 1\n```\n\n```csharp\nint F() => 1;\n```"
                                             "\n\n```text\nplain\n```\n\n```gdscript\nvar a = [b]1[/b]\n```")

    def test_known_wrong_an_unknown_tag_is_kept_escaped_and_reported(self):
        context = self.context()
        self.assertEqual(bbcode.to_markdown("A [foo] tag.", context), "A \\[foo\\] tag.")
        self.assertEqual(context.unresolved, ["foo"])


class ReferenceTests(unittest.TestCase):
    def test_the_dump_is_read_into_sections(self):
        body = read_reference(BODY_DUMP.encode())
        self.assertEqual((body.name, body.parent, body.api_type, body.kind), ("Body", "Thing", "core",
                                                                                 ClassKind.OBJECT_CLASS))
        move = body.sections["methods"][1]
        self.assertEqual([row["name"] for row in move["params"]], ["direction", "speed"])
        self.assertEqual(move["qualifiers"], ["vararg"])
        self.assertEqual(body.sections["enums"], [
            {"name": "Mode", "is_bitfield": False, "values": [{"name": "MODE_STILL", "value": "0"},
                                                              {"name": "MODE_MOVING", "value": "1"}]},
            {"name": "Flags", "is_bitfield": True, "values": [{"name": "FLAG_A", "value": "1"}]}])
        self.assertEqual(body.sections["constants"], [{"name": "LIMIT", "value": "8"}])
        self.assertEqual(body.sections["members"][1]["overrides"], "Thing")
        self.assertEqual(read_reference(VECTOR_DUMP.encode()).kind, ClassKind.BUILTIN_TYPE)
        self.assertEqual(read_reference(GLOBAL_DUMP.encode()).kind, ClassKind.GLOBAL_SCOPE)
        self.assertTrue(read_reference(VARIANT_DUMP.encode()).is_empty)

    def test_the_documented_reference_has_the_dump_structure_and_the_text(self):
        dump = read_reference(BODY_DUMP.encode())
        text = read_reference(documented(BODY_DUMP, BODY_TEXT).encode())
        self.assertEqual(text.structure(), dump.structure())
        self.assertIn("[method move]", text.documentation["description"])
        self.assertEqual(text.documentation["tutorials"], [{"title": "Guide", "address": "$DOCS_URL/guide.html"}])
        # Known wrong: a reference with one more parameter has another structure.
        changed = BODY_DUMP.replace('<param index="0" name="distance"', '<param index="0" name="metres"')
        self.assertNotEqual(read_reference(changed.encode()).structure(), dump.structure())

    def test_inheritance_and_refused_documents(self):
        chains, children = inheritance(references(BODY_DUMP, THING_DUMP, OBJECT_DUMP))
        self.assertEqual(chains["Body"], ["Thing", "Object"])
        self.assertEqual(children["Object"], ["Thing"])
        for data, reason in ((b"<!DOCTYPE x><class name='A'/>", "reference_declaration_refused"),
                             (b"<class", "reference_unreadable"), (b"<other name='A'/>", "reference_not_a_class")):
            with self.assertRaises(ReferenceError) as caught:
                read_reference(data)
            self.assertEqual(caught.exception.reason, reason)


class RenamesTests(unittest.TestCase):
    def test_only_renames_the_map_attributes_and_the_surface_holds_are_attached(self):
        found = references(BODY_DUMP, THING_DUMP, OBJECT_DUMP, VECTOR_DUMP, GLOBAL_DUMP)
        chains, _children = inheritance(found)
        entries = godot_renames.read_map(RENAMES_MAP, set(found))
        self.assertNotIn("walk", [entry.old for entry in entries])  # a disabled entry is never read
        renames, outcomes = godot_renames.attach(entries, found, chains)
        self.assertEqual([(row["kind"], row["from"], row["to"]) for row in renames["Body"]], [
            ("class", "Kinetic", "Body"), ("method", "go", "move"), ("method", "mover", "move"),
            ("property", "shown", "visible"), ("signal", "moved_by", "moved"), ("constant", "MODE_STAY", "MODE_STILL")])
        self.assertEqual(renames["Body"][0]["note"], "Was 2D and 3D.")
        self.assertEqual([(row["kind"], row["from"]) for row in renames["Vector3"]],
                         [("class", "Vec3"), ("method", "liner")])
        self.assertEqual([(row["kind"], row["from"]) for row in renames["@GDScript"]], [("method", "lenght")])
        # Known wrong: "fly" -> "glide" names Body, which has no glide; "nowhere" names no class; the class renamed
        # to Missing does not exist at the tag; OLD_LIMIT's block names @GDScript, which has no LIMIT.
        self.assertEqual(outcomes["gdscript_function_renames"], {"attached": 4, "target_missing": 1,
                                                                 "unattributed": 1})
        self.assertEqual(outcomes["class_renames"], {"attached": 1, "unattributed": 1})
        self.assertEqual(outcomes["enum_renames"], {"attached": 1, "target_missing": 1})

    def test_a_comment_names_classes_before_its_note_and_both_dimensions(self):
        known = {"Area2D", "Area3D", "Camera3D", "Body"}
        self.assertEqual(godot_renames.comment_classes("Area(2D/3D)", known, {}), ["Area2D", "Area3D"])
        self.assertEqual(godot_renames.comment_classes("Camera -- Breaks Body", known, {"Camera": "Camera3D"}),
                         ["Camera3D"])
        with self.assertRaises(godot_renames.RenamesMapError):
            godot_renames.read_map("no tables here", known)


def release(**changes):
    values = dict(name="godot", title="Godot", release="4.7.2-stable", version="4.7.2", api_version="4.7",
                  repository="godotengine/godot", commit=COMMIT, binary_name="Godot_v4.7.2-stable_linux.x86_64",
                  binary_sha256="8" * 64, binary_version="4.7.2.stable.official.ed1daf0bf", docs_address=DOCS,
                  syntax=CARD.GODOT_SYNTAX, renames_from_version="3")
    values.update(changes)
    return cards.EngineRelease(**values)


def card_texts(maximum=cards.MAXIMUM_DOCUMENT_BYTES):
    found = references(BODY_DUMP, THING_DUMP, OBJECT_DUMP)
    chains, children = inheritance(found)
    documentation = read_reference(documented(BODY_DUMP, BODY_TEXT).encode())
    sources = cards.CardSources("doc/classes/Body.xml", "1" * 64, "doc/classes/Body.xml", "2" * 64,
                                godot_renames.MAP_PATH, "3" * 64)
    renames = [{"kind": "method", "from": "go", "to": "move"}]
    api = cards.surface_record(release(), found["Body"], chains["Body"], children["Body"], renames, sources)
    context = bbcode.Context(frozenset(found), "Body", DOCS, CARD.code)
    texts = cards.documents(api, release(), documentation, context, sources, ["Copyright (c) 2026 Example."],
                            maximum=maximum)
    return api, texts


class CardFormatTests(unittest.TestCase):
    def setUp(self):
        self.api, documents = card_texts()
        self.texts = [documents[name] for name in CARD.documents(documents)]

    def test_the_written_card_agrees_with_its_surface(self):
        self.assertEqual(CARD.disagreements(self.api, self.texts), [])
        readme = self.texts[0]
        self.assertTrue(readme.startswith("# Body (Godot 4.7)\n\nUse this card when writing or checking Godot 4.7 "
                                          "code that uses the class `Body`. Its role: A thing that **moves**."))
        for line in ("### `Body.Mode get_mode() const`", "### `bool move(direction: Vector3, speed: float = 1.0, ...)"
                     " vararg`", "### `Body.Mode mode = 0` setter `set_mode` getter `get_mode`",
                     "### `bool visible = false` setter `set_visible` getter `is_visible` overrides `Thing`",
                     "### `moved(distance: float)`", "### `enum Mode`", "#### `MODE_STILL = 0`", "### `flags Flags`",
                     "### `LIMIT = 8`", "### `Color tint = Color(1, 1, 1, 1)` (color)",
                     "- method `go()` → `move()`", "**Inherits:** `Thing` < `Object`",
                     f"- [Guide]({DOCS}/guide.html)", "```gdscript\nfunc _ready():\n\tmove(Vector3.UP)\n```"):
            self.assertIn(line, readme)

    def test_known_wrong_cards_that_differ_from_their_surface_are_reported(self):
        removed = copy.deepcopy(self.api)
        del removed["sections"]["methods"][0]
        changed = copy.deepcopy(self.api)
        changed["sections"]["members"][0]["default"] = "1"
        extra = copy.deepcopy(self.api)
        extra["sections"]["signals"].append({"name": "stopped", "params": []})
        renamed = copy.deepcopy(self.api)
        renamed["renames"]["entries"][0]["to"] = "walk"
        for wrong in (removed, changed, extra, renamed):
            self.assertTrue(CARD.disagreements(wrong, self.texts))
        lost = [self.texts[0].replace("### `moved(distance: float)`\n", "")]
        self.assertTrue(any(problem.startswith("missing") for problem in CARD.disagreements(self.api, lost)))
        first, second = (CARD.ITEM_PREFIX + CARD.item_line("methods", item) for item in self.api["sections"]["methods"])
        swapped = self.texts[0].replace(first, "@@").replace(second, first).replace("@@", second)
        problems = CARD.disagreements(self.api, [swapped])
        self.assertTrue(problems and problems[0].startswith("out of order"), problems)
        self.assertEqual(CARD.disagreements({**self.api, "syntax": "typescript"}, self.texts)[0][:18],
                         "api.json uses the ")

    def test_headings_inside_fenced_code_are_not_card_lines(self):
        fenced = self.texts[0] + "\n```gdscript\n### `not an item`\n## Methods\n```\n"
        self.assertEqual(CARD.disagreements(self.api, [fenced]), [])

    def test_a_large_card_continues_in_numbered_documents_that_agree_together(self):
        api, documents = card_texts(maximum=1800)
        names = CARD.documents(documents)
        self.assertGreater(len(names), 1)
        self.assertEqual(names[1], "members-2.md")
        texts = [documents[name] for name in names]
        self.assertEqual(CARD.disagreements(api, texts), [])
        self.assertIn("This card continues in `members-2.md`", texts[0])
        self.assertTrue(any(CARD.CONTINUED in text or "## " in text for text in texts[1:]))
        # Known wrong: a later document left out loses its items.
        self.assertTrue(CARD.disagreements(api, texts[:1]))

    def test_documents_are_read_in_number_order_and_code_spans_hold_backticks(self):
        self.assertEqual(CARD.documents(["members-10.md", "README.md", "members-2.md", "members-1.md", "x.md"]),
                         ["README.md", "members-2.md", "members-10.md"])
        self.assertEqual(CARD.code("a``b"), "``` a``b ```")


#: A stand-in for the pinned build in evidence records (no engine runs with it).
ENGINE = godot_native.engines.Engine("godot", "/x/godot", "4.7.2.stable.official.ed1daf0bf", "8" * 64)


class NativeEvidenceTests(unittest.TestCase):
    ENGINE = ENGINE

    def setUp(self):
        self.api, _documents = card_texts()

    def answer(self, **missing):
        empty = {key: [] for key in ("methods", "members", "overridden_members", "signals", "constants", "enums")}
        return {"known": True, "parent": "Thing", "missing": {**empty, **missing}}

    def test_expectations_name_every_item_the_engine_is_asked_about(self):
        asked = godot_native.expectation(self.api)
        self.assertEqual(asked["methods"], ["get_mode", "move"])
        self.assertEqual((asked["members"], asked["overridden_members"]), (["mode"], ["visible"]))
        self.assertEqual(asked["constants"], ["LIMIT", "MODE_STILL", "MODE_MOVING", "FLAG_A"])
        self.assertEqual(asked["enums"], ["Mode", "Flags"])
        vector = cards.surface_record(release(), read_reference(VECTOR_DUMP.encode()), [], [], [],
                                      cards.CardSources("a", "1" * 64, "b", "2" * 64))
        self.assertEqual(godot_native.expectation(vector), {"name": "Vector3", "kind": "builtin_type",
                                                             "methods": ["lerp"], "members": ["x"]})
        scope = cards.surface_record(release(), read_reference(GLOBAL_DUMP.encode()), [], [], [],
                                     cards.CardSources("a", "1" * 64, "b", "2" * 64))
        self.assertEqual(godot_native.expectation(scope)["functions"],
                         [{"name": "len", "params": [{"name": "var", "type": "Variant"}]}])

    def test_a_record_binds_the_card_digest_and_passes_only_when_every_check_does(self):
        record = godot_native.evidence(self.ENGINE, self.api, self.answer(), "a" * 64)
        self.assertEqual(record["state"], "passed")
        self.assertNotIn("time", json.dumps(record))
        data = godot_native.evidence_bytes(record)
        self.assertEqual(godot_native.read_evidence(data, self.api, "a" * 64)["class"], "Body")
        with self.assertRaises(godot_native.NativeError) as stale:
            godot_native.read_evidence(data, self.api, "b" * 64)
        self.assertEqual(stale.exception.reason, "evidence_stale")
        failed = godot_native.evidence(self.ENGINE, self.api, self.answer(methods=["move"]), "a" * 64)
        self.assertEqual(failed["state"], "failed")
        self.assertEqual([check["detail"] for check in failed["checks"] if check["name"] == "methods_known"],
                         [{"checked": 2, "missing": ["move"]}])
        with self.assertRaises(godot_native.NativeError) as refused:
            godot_native.read_evidence(godot_native.evidence_bytes(failed), self.api, "a" * 64)
        self.assertEqual(refused.exception.reason, "native_check_failed")
        wrong_parent = godot_native.evidence(self.ENGINE, self.api, dict(self.answer(), parent="Object"), "a" * 64)
        self.assertEqual(wrong_parent["state"], "failed")
        unanswered = godot_native.evidence(self.ENGINE, self.api, None, "a" * 64)
        self.assertEqual(unanswered["state"], "failed")
        with self.assertRaises(godot_native.NativeError) as invalid:
            godot_native.read_evidence(b'{"record_type": "other"}', self.api, "a" * 64)
        self.assertEqual(invalid.exception.reason, "evidence_invalid")


GODOT = None
try:
    GODOT = godot_native.locate()
except godot_native.NativeError:
    GODOT = None


@unittest.skipUnless(GODOT is not None and GODOT.sha256 == "8d106cbe6144c2dc7e881d61d2429c1a8a76e6b22ef48bd5e48dcf934953f71e",
                     "the pinned Godot 4.7.2 build is needed for the native check")
class RealEngineTests(unittest.TestCase):
    """One dump and one check of real classes by the pinned build, with a method it does not have as the control."""

    def test_the_build_confirms_real_cards_and_refuses_a_method_it_lacks(self):
        root = Path(tempfile.mkdtemp())
        try:
            dump = godot_native.dump(GODOT, root / "dump")
            found = {}
            for data in dump.values():
                reference = read_reference(data)
                found[reference.name] = reference
            chains, children = inheritance(found)
            apis = [cards.surface_record(release(binary_sha256=GODOT.sha256), found[name], chains[name],
                                         children[name], [], cards.CardSources("a", "1" * 64, "b", "2" * 64))
                    for name in ("CharacterBody3D", "Vector3", "@GlobalScope", "@GDScript", "Curve", "TabContainer")]
            wrong = copy.deepcopy(apis[0])
            wrong["class"] = "CharacterBody3D"
            wrong["sections"]["methods"].append({"name": "move_and_slide_with_snap", "returns": {"type": "bool"},
                                                 "params": []})
            answers = godot_native.verify(GODOT, apis, root / "verify")
            for api in apis:
                record = godot_native.evidence(GODOT, api, answers.get(api["class"]), "a" * 64)
                self.assertEqual(record["state"], "passed", (api["class"], record["checks"]))
            wrong_answer = godot_native.verify(GODOT, [wrong], root / "verify-wrong")
            record = godot_native.evidence(GODOT, wrong, wrong_answer["CharacterBody3D"], "a" * 64)
            self.assertEqual(record["state"], "failed")
            self.assertIn("move_and_slide_with_snap", json.dumps(record["checks"]))
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
