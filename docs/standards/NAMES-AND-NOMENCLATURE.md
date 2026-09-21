# Names and nomenclature

Kind: engineering standard. It describes the names that the code and the
documents use today. It renames nothing.

Two documents own the vocabulary. This standard links to them and does not
repeat them.

- [terminology.yaml](../../terminology.yaml) is the machine-readable list of
  canonical terms, forbidden class names, deprecated terms and semantic
  categories. The conformance gates read it.
- The table
  [Names and where they may appear](../guides/product-style-guide.md#names-and-where-they-may-appear)
  in the product style guide says where each public and technical name may
  appear, and which identifiers wait for an owner decision.

## Baltor and Loop Engine

Baltor is the public brand: the product, the website and the hosted service as
a customer sees them. Loop Engine is the repository, the Python distribution
and command `loop-engine`, and the Python import `loop_engine`
([pyproject.toml](../../pyproject.toml)).

- Never use Baltor in place of a code identifier, a package name, a record
  type or a contract field.
- Some customer-visible identifiers carry the engine name, for example the key
  prefix `le_` (`issue_key` in
  [runtime.py](../../src/loop_engine/core/service_runtime/runtime.py)) and the
  response header `X-Loop-Engine-Record-Type`
  ([http.py](../../src/loop_engine/core/service_runtime/http.py)). Their
  renaming is an open owner decision. Do not rename them.

## Public words and technical words

The homepage, the How it works view and their shared footer use plain words:
task, each step, information, tools, model, checks and results. They never
show Loop, Loop node, Loop Engine, runtime classification or role profiles.
Technical documents, the Documentation view, GitHub and source code use the
exact runtime terms. The check
`live_public_explanation_avoids_internal_runtime_names` in
`tools/check_hosted_website.mjs` reads the live How it works view and footer.

In technical prose:

- Repeat the exact technical term. A synonym can change the meaning.
- Do not introduce an abbreviated alias. Write Model Context Protocol and
  continuous integration in full.
- Keep the full phrase "discrete cognitive or act step Loop node" together
  with its [complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation).
- Do not use dash punctuation. The rule `.vale/styles/LoopEngine/NoDashes.yml`
  refuses it, and two more rules in the same folder refuse retired terms.
  Those three rules are not the whole vocabulary gate. A separate step in
  continuous integration refuses a family of retired phrases that the vale
  folder does not carry. Read
  [the four document gates](CHECKS-AND-EVIDENCE.md#what-each-gate-covers)
  before you write.

## Runtime terms

The only operational runtime type is `Loop`. Everything else in this tree is a
separate field of a Loop, not a new type. Use these exact words, and start
from the complete tree before you write about one branch.

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

The same tree, with the meaning of each word, is in
[AGENTS.md](../../AGENTS.md#required-architecture-trees). Do not create a
class whose name ends in `Node`; `forbidden_class_names` in terminology.yaml
lists the refused names.

## The four persistent intelligence layers and Runtime Memory

Use these names exactly, with capital letters:

1. Context Intelligence
2. Code Intelligence
3. Runtime History and Solution Intelligence
4. User Feedback Intelligence

Runtime Memory is separate, temporary and scoped to one run. It is not a
fifth layer. A source format such as Markdown, a skill, a repository or a
vector index does not define a layer. The owning guide is
[Intelligence layers](../components/intelligence-layers/README.md).

## Record types and versions

A record type is lower-case words joined by underscores, then a slash, then
`v` and a whole number: `service_key/v2`, `service_http_result/v1`,
`rollback_key_version_drill/v1`. The field that carries it is `record_type`.

| Convention | Example in the code |
|---|---|
| A module constant holds the string. Its name ends in `_VERSION`, `_SCHEMA` or `_RECORD_TYPE`. | `CONFIG_VERSION`, `OWNER_BOUND_KEY_SCHEMA`, `HTTP_CONFIGURATION_RECORD_TYPE` in `src/loop_engine/core/service_runtime/` |
| Request and result records of one operation share a stem. | `service_access_request/v1` and `service_access_result/v1` in `access.py` |
| A report written by a tool has its own record type. | `REPORT_VERSION` in [check_rollback_key_version.py](../../tools/check_rollback_key_version.py) |
| Profiles use a dotted name and a semantic version. | `practitioner.code_execution@1.0.0` in `http.py` |

Never compare a record type by prefix and never guess a version. See
[Records, versions and compatibility](RECORDS-VERSIONS-AND-COMPATIBILITY.md).

## Scopes

A service scope is `area:action` in lower case: `provisioning:metadata`,
`provisioning:read`, `usage:read`, `billing:manage`, `access:manage`. The
closed list is `SCOPES` in
[records.py](../../src/loop_engine/core/service_runtime/records.py). A value
outside that list is refused.

## Stable error codes

An error code is a short lower-case phrase joined by underscores, for example
`unauthorized`, `unsupported_version`, `scope_escalation_refused`,
`commit_unknown` and `request_limit_exceeded`.

- The code is the contract. `ServiceRuntimeError` and `ServiceHttpError` carry
  it in the attribute `code`. The function `_status` in `http.py` maps each
  code to one HTTP status.
- A client and a check compare the code, never the message text.
- Name the code after the refused condition, not after the function that
  found it. Do not reuse a code for a different condition.
- Do not rename a code that a release already returns. Add a new code.

## Check names written as sentences

A check name is a full statement of the expected behavior, in lower case and
joined by underscores. A reader of a report must understand the claim without
opening the source.

| Good, from the code | Why |
|---|---|
| `customer_key_uses_the_owner_bound_record_version` | States the subject and the expected fact. |
| `forged_key_identifiers_cannot_force_a_key_set_read_per_request` | States the known-wrong case that is refused. |
| `removed_key_version_change_is_detected` | Names the mutant control and what it must notice. |

Avoid names such as `test_key_2` or `version_check`. They say nothing when
they fail.

## Files and folders

- Python modules and packages: lower case with underscores. A checks module
  sits beside its subject and ends in `_checks.py`, for example `access.py`
  and `access_checks.py`.
- Guides are undated and use `kebab-case.md`
  ([guides index](../guides/README.md)). A dated record ends in the date, for
  example `TAKEOVER-CHECKPOINT-2026-09-20.md`.
- A saved report ends in a number that rises with each attempt, for example
  `rollback-key-version-1.json`. See
  [Checks and evidence](CHECKS-AND-EVIDENCE.md).
- A new top-level folder needs the steps in
  [AGENTS.md](../../AGENTS.md#one-loop-runtime). Every folder under `docs/`
  needs a README that states its kind.
