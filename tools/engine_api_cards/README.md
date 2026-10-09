# Engine API contract cards

Kind: tool component. One small, version-pinned card per class of a pinned
engine release: the class's exact surface, its own reference text and the
renames from the previous major version, in a file a harness loads instead of
guessing. Coding agents keep writing Godot 3 code against Godot 4
(`KinematicBody` for `CharacterBody3D`, `yield` for `await`, old method
names); a card for the class answers that from the engine itself. The owner
asked on October 9, 2026 for far more harness component files, "more atomic",
and said a model "doesn't need to reread the entire code if it knows the inputs
and outputs and functions and basic docstrings".

The supply line is [`engine_api_cards`](../supply_lines/engine_api_cards.py)
(command `engine-api-cards` of
[`tools/build_library_supply.py`](../build_library_supply.py)). Each card is a
review candidate; qualification and the ongoing independent review decide what
is served.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A card run is a Starting Practitioner task of the code execution profile that
an operator starts; it runs deterministically and calls no model. The engine
adapters, the BBCode converter, the card writer and the native verifier are
adapters the run uses: none is a graph vertex, a role, a mode or a runtime
type, and none grants authority.

## One card format, one adapter per engine

```text
engine_api_surface/v1 (api.json) and engine_api_card/v1 (component.json): the fixed edge
├── godot adapter: Godot 4.7.2-stable (godot_reference.py, godot_renames.py, godot_native.py,
│   godot_verify.gd, and the fact reading in ../supply_lines/engine_api_cards.py), syntax "godot"
└── a further adapter writes the same two records, with its own reader, text interface, syntax (when its
    declarations read differently) and native check; the card writer, checker and packaging stay as they are
```

An adapter gives the card writer its text through one interface (`markdown`, `title`, `address`: the
BBCode converter's `Context` for Godot), and says in its `EngineRelease` where the
surface was read, the format and licence of the text, and which classes exist only in an editor.

A card is the same files whatever the engine: `README.md` (and `members-2.md`,
`members-3.md`, ... for a class past 240,000 bytes), `api.json`,
`component.json`, the shared checker `api_card.py` and its test
`test_api_card.py` (the same bytes in every card, in
[`card_files/`](card_files/)), `verification/native.json`, `LICENSE` (Baltor's
MIT, for the generated files), `UPSTREAM-LICENSE` (the engine's licence text,
verbatim) and `ATTRIBUTION.md`. Every heading the card checks is written from
`api.json` by the shipped `api_card.py` itself, so the writer and the checker
cannot disagree about the format; the package test fails when the documents
lose, add, reorder or change an item, and the qualification mutation check
makes sure that test can fail.

## The Godot adapter

```text
Godot 4.7.2-stable
├── surface: the official Linux x86_64 build (SHA-256 8d106cbe...), run headless with an isolated HOME:
│   --doctool dumps 1,076 classes (1,036 ClassDB classes, 38 Variant types, @GlobalScope, @GDScript) in
│   about 1.5 s, with no description text
├── build identity: its version string names commit ed1daf0bf, which the tag 4.7.2-stable points at; the
│   release asset Godot_v4.7.2-stable_linux.x86_64.zip matches GitHub's published SHA-256 and holds the
│   build byte for byte (streamed once, then cached by digest)
├── text: the class reference XML of the repository at the tag (doc/classes, modules/*/doc_classes,
│   platform/*/doc_classes), each file proven by git blob identity; its structure must equal the dump's
│   (it did for all 1,076 classes), then the descriptions are converted from BBCode to Markdown
├── renames: editor/project_upgrade/renames_map_3_to_4.cpp at the tag (godot_renames.py)
└── native check: one run of the same build over every card (godot_verify.gd), about 2 s
```

### Why the text is MIT, and the documentation site is never read

The class reference text lives in the engine repository, not only on
docs.godotengine.org. Read on October 9, 2026 at commit `ed1daf0bf`:

- `LICENSE.txt` is the MIT licence, copyright "2014-present Godot Engine
  contributors (see AUTHORS.md)" and "2007-2014 Juan Linietsky, Ariel Manzur".
- `COPYRIGHT.txt` (the Debian machine-readable format) gives `Files: *` the
  licence Expat (MIT); a later, more specific stanza decides a file it names.
  The line parses every stanza and refuses a file whose last matching stanza is
  not Expat: no stanza names `doc/`, `modules/*/doc_classes`,
  `platform/*/doc_classes` or `editor/project_upgrade`, so every file read is
  MIT (`copyright_stanzas` and `governing_licence`, tested with a known-wrong
  stanza).
- The documentation site is built from godotengine/godot-docs, whose
  `LICENSE.txt` is CC BY 3.0 Unported, which is not on the owner's allowlist.
  Its own README says the exception: "the files in the classes/ folder are
  derived from Godot's main source repository and are distributed under the
  MIT license". The line therefore reads the engine repository's XML at the
  tag, the source those pages are generated from, and never the site.

GitHub's licence interface answers `NOASSERTION` for godotengine/godot at any
commit ref and `MIT` at its default branch, for the same `LICENSE.txt` blob
(`0e3ba08d`). The shared decision (`supply_lines/licences.py`) needs the
interface and the text to agree, so the line asks the default branch only when
the commit's answer names nothing, and accepts that answer only when the
default branch's licence file has the commit's own blob identity
(`tag_licence`, basis
`github_licence_of_the_same_blob_at_the_default_branch_and_text_agree`).

### What the native check asks the build

| Kind | Checks |
|---|---|
| ClassDB class | the class exists; its parent is the expected one; every listed method, signal, integer constant and enumeration is the class's own; every property is its own, an element of one of its arrays (`point_{index}/position`), a per-child property of a container holding one child (`tab_{index}/title`), or a setting its settings object holds (ProjectSettings, EditorSettings); a property that overrides an ancestor's default is looked up with inheritance |
| Variant type | the type exists; every method is callable on a value of the type (`Callable.create(value, name).is_valid()`); every member can be read from one |
| Global scope | every function compiles in a script, with untyped arguments, one more for a variadic call, or constants of the declared types (`preload` needs a constant path); every member is an engine singleton (no reflection could fail to know a global scope, so no check claims it) |

The record binds the card digest (every card file but `component.json`, the
record itself and the attribution), names the build and carries no time stamp.
A class whose record is missing, stale, invalid or failed is refused by name.

The first full run (October 9, 2026) refused 22 classes this way, each for a
reason the engine itself explains: the export options of the 7
`EditorExportPlatform*` classes (only `create_preset()` reaches them, and it
crashed the 4.7.2 build in a script run), the import options of the 14
`ResourceImporter*` classes (no script interface lists them), and 3 `.NET`
settings of `ProjectSettings` that a standard build defines only for the
doctool (`main/main.cpp`: "Hack to define .NET-specific project settings even
on non-.NET builds, so that we don't lose their descriptions and default values
in DocTools"). `Variant` has no surface and is refused as `no_api_surface`.

### What a reader sees, and what it cannot

A card never holds a character a reader cannot see, nor an HTML comment opener: the qualification safety
rules refuse both, and the 4.7.2 reference has both in four classes (a zero-width joiner inside the emoji
strings of TextServer, TextEdit and LineEdit; XMLParser's `<!--A comment-->`), which the first full run lost
for it. Such a character is now written visibly with the same meaning: a numeric character reference in prose,
an HTML code element in inline code (rendered as the same code span), and a `\u` escape in a code block, where
the reference has them only inside string literals that GDScript and C# read the same way. The safety rule's
own definition of an invisible character decides (`bbcode.invisible`).

A class of the `editor` api type (82 in 4.7.2) says so in its header: it exists in the editor, for editor
plugins and `@tool` scripts, and an exported project does not have it.

### Renames

A rename reaches a card only where the map says so: the GDScript tables for
classes, built-in types, methods, properties, signals, constants and
enumerations, named colours and project settings, attributed to the classes
its comment names before its note (a Godot 3 class name mapped through the
class table, `Area(2D/3D)` read as both) or to the class a comment line names
above its block (`// @GlobalScope`). An entry commented out is disabled in the
converter and never read. A rename is kept only when its new name is on the
class's surface at the tag, its own or an ancestor's; the others are counted in
the run summary. `instance()` to `instantiate()` and `yield` to `await` are
custom rules of the converter, not map entries, so no card lists them.

## Commands

```bash
PYTHONPATH=src:tools python tools/build_library_supply.py engine-api-cards [--engine godot] \
  --run-folder RUN --authorize-network-reads [--authorize-store-writes --store-root STORE] \
  [--materialize] [--class Node --class Vector3] [--godot PATH] [--workers 8]
PYTHONPATH=src:tools python -m unittest tools.test_engine_api_cards tools.test_engine_api_cards_line
```

The run folder keeps every fetched fact (cached by address), the dump, the
evidence records (`evidence/godot/<Class>.json`), `summary.json` and the
refusals.

## Existing work: adopted, adapted and rejected

| Project | Decision and reason |
|---|---|
| The engine's `--doctool` | Adopted as the surface: the build's own reflection, in the same XML shape as the class reference, so the text attaches by structure and the two are compared exactly. |
| The engine's `doc/tools/make_rst.py` | Adopted as the meaning of every BBCode tag (cross-references, code blocks, `[br]` as a paragraph break, `$DOCS_URL`); adapted to write Markdown instead of reStructuredText. |
| `--dump-extension-api` (extension_api.json) | Rejected as the surface: it carries no description text, and its shape is not the class reference's, so the text could not be attached by an exact structure comparison. |
| godot-docs `classes/*.rst` | Rejected: generated from the same XML, so it adds nothing but the documentation site's formatting, and the repository's own licence statement is the one to rely on. |
| `tools/creative_originals/engines.py` | Adopted to locate and run the pinned build. Repaired here: it probed the user service manager with the caller's environment and launched without the session bus, so every engine run of a session with a user bus failed; the launcher now gets the bus and the engine, started by `env -i`, gets only the isolated environment. |
| `supply_lines` reading, packaging, records and licences | Adopted: FactReader, pinned files by blob identity, the shared packaging and the licence decision, with the same-blob rule above. |

## Limits

- The surface is the official Linux x86_64 editor build's. A class, member or
  setting that only another platform, a .NET build or a module this build
  lacks registers is not listed (`CSharpScript` and `TextServerFallback` have
  class reference files and no class in this build).
- The text is converted from BBCode as the engine's generator reads it; a
  reference to another class is its name, not a link, and an unknown tag is
  kept as written.
- Theme items, constructors and operators are listed from the build's dump;
  the native check does not ask the running engine about them.
- The renames are the map's GDScript renames that hold on the surface; the C#
  tables and the converter's custom rules are not read.
- Nothing here was loaded by a harness.
