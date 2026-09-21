# Developer language

Kind: operating guide. It is the one place a new developer or a new coding
agent learns the words this repository uses, where each word may appear and
which words were retired. It renames nothing.

Written on September 21, 2026.

## The one source is terminology.yaml

[terminology.yaml](../../terminology.yaml) is the single structured source for
the vocabulary. Every term in it carries five facts:

```text
One term in terminology.yaml
├── kind          what sort of name it is
├── definition    what it means, in one or two sentences
├── may_appear    the surfaces where a writer may use it
├── must_not_appear   the surfaces that refuse it
└── status        current, retired, an owner decision or an open decision
```

Read the file before you invent a name. Every other document points here
instead of repeating the list:

| Document | What it still owns |
|---|---|
| [terminology.yaml](../../terminology.yaml) | Every term, its definition, its placement and its status. |
| [product style guide](product-style-guide.md) | How to write product prose, and the difference between marketing language and a factual claim. |
| [humanizer-context.md](../../humanizer-context.md) | The voice, the punctuation and the reference style for public prose. |
| [names and nomenclature](../standards/NAMES-AND-NOMENCLATURE.md) | The shapes of record types, scopes, error codes, check names, files and folders. |
| [product nomenclature](../reference/PRODUCT-NOMENCLATURE.md) | The longer explanations of the architecture terms and the step profile labels. |
| [glossary](../architecture/GLOSSARY.md) | How similar sounding components differ from each other. |

## The surfaces

A surface is a place a reader meets a word. terminology.yaml declares six of
them and says for each one whether a check reads it.

```text
Surfaces
├── public_website_pages          checked
│   └── the homepage, the How it works view and the shared footer
├── website_documentation_view    declared only
│   └── the Documentation view and the runtime vocabulary it shows
├── website_application_views     declared only
│   └── sign in, registration, workspace, account, administration,
│       client connection, the first example, access and data
├── technical_documents           checked
│   └── Markdown under docs and the instruction files in the repository root
├── source_code                   declared only
│   └── Python, JavaScript, YAML and JSON under src, tools and devtools
├── command_output                declared only
│   └── what the installed loop-engine command prints
└── customer_configuration        declared only
    └── copied client settings, environment variable names, issued keys
```

A checked surface has a file mapping that the gate reads. A surface marked
declared only has no file mapping, so the rule is written down for a person
and no check enforces it. Do not read a declared-only surface as an enforced
one.

The served website is one HTML page with several views inside it. The gate
splits that page by the exact markers the page already uses, so a placement
rule can name one view:

```text
src/loop_engine/core/service_runtime/web_assets/index.html
├── header
├── view:home        the homepage
├── view:about       How it works
├── view:docs        Documentation
├── view:login, view:signup, view:workspace, view:account, view:admin,
│   view:setup, view:examples, view:security
├── footer           the shared footer
└── template:runtime-vocabulary-template
```

If you rename or reindent one of those sections, the gate reports
`declared_surface_region_missing` instead of passing in silence. Update the
`html_regions` list in terminology.yaml in the same change.

## The words a customer page uses

Baltor is the public brand. On the homepage, the How it works view and the
shared footer, describe the work with these words only: task, each step,
information, tools, model, checks, results and reusable solution. The four
persistent intelligence layer names are public as well, because a customer
reads them on the homepage today.

The owner chose the category line **harness and agent optimized operation**.
Because of that line, harness and agent are customer words and may appear on
a public page. They were previously refused there. The owner's decision of
September 20, 2026 is the reason, and terminology.yaml records it as the
status of both words.

## The words a technical document uses

Loop Engine is the repository, the Python distribution and command
`loop-engine`, and the Python import `loop_engine`. Technical documents, the
Documentation view, GitHub, source code and command output keep the exact
runtime terms. None of them appears on a public website page.

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

Write the full descriptive term every time. Do not introduce a shorthand, an
acronym or an abbreviated alias for any term, not even after you have defined
it once. Write Model Context Protocol, continuous integration and Runtime
History and Solution Intelligence in full. Repeating the full term is what
keeps the meaning stable between sessions and between agents.

## The phrase that must stay whole

A **discrete cognitive or act step Loop node** is an independently governed
instance of the Loop runtime responsible for one clearly defined cognitive
step or action. Write the phrase in full. Do not shorten it, do not remove
the word node, do not substitute an acronym and do not replace its
explanation with a label.

The phrase never travels without its complete behavioral explanation. The
explanation is in
[ASTRA.md](../../ASTRA.md#complete-behavioral-explanation) and in
[the session handoff](../context/DISCRETE-COGNITIVE-OR-ACT-STEP-LOOP-NODE-HANDOFF-2026-09-12.md).
Read both before you describe one. The explanation must keep the narrowly
scoped assignment, the selected context and resources, the separately
initialized harnesses, the permitted harness changes, the expectation checks,
the repetition until the declared completion conditions are satisfied, the
continued production of alternative outputs, and the protection against
repeated external effects. Publishing an output is separate from finishing
the assignment.

The phrase describes an executable graph vertex implemented by the canonical
`Loop`. It does not introduce a runtime class, a role or a mode.

## Three settings a developer confuses on the first day

These are three separate fields. Using one word for two of them is the most
common naming mistake in this repository.

| Write this | The code field | What it bounds |
|---|---|---|
| role profile | `LoopProfileSpec` | The versioned purpose, required fields, capabilities and supported modes. |
| step profile | `framework` and `custom_steps` | The number, order and repetition of the steps. |
| effort setting | `LoopConfig.power`, values light, standard, deep and max | The work limits of one Loop. |
| thinking power | `llm_thinking_power`, values small, medium, high, max and specialized | The model effort a provider is asked for. |
| operating settings | `OperatingProfile` | Permissions, access, providers and optimization preferences. |

Write effort setting, not effort budget and not the bare word power. Write
thinking power for the model effort. The two share the word power in the
code and mean different things, so the prose has to separate them.

## Two views over the four intelligence layers

The four persistent intelligence layers are Context Intelligence, Code
Intelligence, Runtime History and Solution Intelligence, and User Feedback
Intelligence. Runtime Memory is separate, temporary and scoped to one run. It
is not a fifth layer.

Two different names describe a view across those layers. They are not
interchangeable:

```text
The four persistent intelligence layers
├── Intelligence Library
│   └── one searchable view every Loop uses, served by query_intelligence
└── Harness Intelligence
    └── one provisioning view that serves authorized material to a single
        harness assignment
```

Neither is a store and neither is a fifth layer.

## Retired words

This guide does not list the retired words, and no other current document
should. Every one of them carries `status: retired` in terminology.yaml,
beside the `replacement` field that names the word to write instead. Read
that file when a reviewer tells you a word was retired, or when you inherit
old prose and need to know what replaced it.

The reason for keeping the list in one machine-readable file is that four
separate gates refuse these words in current prose. A document that spelled
them out would fail its own advice.

A retired class name and a retired serialized record spelling are different,
and terminology.yaml marks them `retired_identifier` and
`retired_record_spelling`. A document may name those, because the version
policy needs documents that state exactly what the gate refuses. The
class-name rule in `forbidden_class_names` and the record rule in
`legacy_serialized_terms` keep them out of running code. A prose rule does
not.

A fenced code block is not prose, so a retired word inside one is not
reported. An inline code span is prose, because that is how a retired
configuration name comes back into a set of instructions. When a document
truly has to quote a retired name inside a sentence, add the file to that
term's `quotation_exceptions` and write a `quotation_reason` that says why a
reader needs the old name.

## Renaming something

A rename of an identifier is a contract change, not a copy change. Prefer
changing prose. When the code name is genuinely wrong, record it under
`proposed_renames` in terminology.yaml with its current names, the proposed
name, the reason, the owning contract and why it was not performed. Do not
perform it in the same change that records it.

A performed rename needs a new explicit version, updated callers and checks
in the same change, and an explicit refusal of the old form where the
[version policy](../architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md)
requires one.

## The check

The gate `undefined_terms_retired_names_and_misplaced_words` runs inside
`python -m loop_engine --conformance`. It reads terminology.yaml and reports:

1. `term_without_definition`, when a term carries no definition.
2. `term_without_placement`, when a term has no `may_appear`,
   `must_not_appear` or `status` and its kind has no entry in
   `placement_defaults`.
3. `term_names_an_undeclared_surface`, when a placement names a surface that
   `surfaces` does not declare.
4. `term_pattern_is_not_an_expression`, when a term's `pattern` does not
   compile.
5. `retired_name_in_document`, when a retired word appears in the prose of a
   document on a checked surface.
6. `forbidden_term_on_surface`, when a term appears on a checked surface that
   its `must_not_appear` refuses.
7. `declared_surface_region_missing` and `declared_surface_page_missing`,
   when the page a surface names no longer has the region it declares.

Every rule has a known-wrong case in
`loop_engine.nomenclature_conformance.self_test`, and the live contract has
its own control in `loop_engine.conformance_report.self_test`. Run the module
self test first, then the full conformance scan.
