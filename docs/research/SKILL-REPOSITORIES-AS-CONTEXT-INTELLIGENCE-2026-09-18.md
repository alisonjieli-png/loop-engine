# Skill repositories as Context Intelligence

Date: 2026-09-18. The owner shared a list titled "awesome-claude-skills" with
twelve entries and asked whether the skills in those repositories could be
added as Context Intelligence. This record resolves the entries as far as the
public evidence allows, states what each repository actually holds, separates
the parts that are Context Intelligence from the parts that are Code
Intelligence, quotes the license of each source, and describes what an import
path would look like as roadmap work. The record decides nothing. The owner
decides.

Every fact below carries the source and the date it was read. Facts that could
not be confirmed are marked unverified. No star count and no license
identifier in this record was invented.

## How the twelve entries were resolved

Observed on 2026-09-18. All twelve LinkedIn short links supplied with the list
fail to resolve. Eleven of them answer an HTTP 404 status on the first
request. The body of each is the LinkedIn page that reads "Page not found".
One link, the one given for entry 3, answers an HTTP 301 redirect to a
LinkedIn hiring page for a video introduction, which has no connection to any
software repository. No interstitial page showing a destination address was
returned for any of the twelve.

The short links therefore supply no destination. Every repository named below
was found by searching GitHub for the entry name together with the words
"claude" and "skill", and then confirming the repository contents directly
through the GitHub programming interface and through
raw.githubusercontent.com. Each resolution is marked inferred, with the reason
stated. Two entries stayed unresolved and are recorded as unresolved.

| Entry | Name on the owner's list | Resolution | Status |
|---|---|---|---|
| 1 | Superpowers | <https://github.com/obra/superpowers> | inferred, high confidence |
| 2 | Matt Pocock Skills | <https://github.com/mattpocock/skills> | inferred, high confidence |
| 3 | UI/UX Pro Max, for user interface and user experience | <https://github.com/nextlevelbuilder/ui-ux-pro-max-skill> | inferred, high confidence |
| 4 | Caveman | <https://github.com/JuliusBrussee/caveman> | inferred, high confidence |
| 5 | Humanizer | <https://github.com/blader/humanizer> | inferred, high confidence |
| 6 | Find Skills | <https://github.com/vercel-labs/skills> | inferred, medium confidence |
| 7 | Deploy to Vercel | not resolved | unresolved |
| 8 | Brainstorming | <https://github.com/obra/superpowers>, folder skills/brainstorming | inferred, medium confidence |
| 9 | TDD, the short form the owner's list uses for test-driven development | <https://github.com/obra/superpowers>, folder skills/test-driven-development | inferred, low confidence |
| 10 | Excalidraw | <https://github.com/coleam00/excalidraw-diagram-skill> | inferred, medium confidence |
| 11 | Remotion | not resolved | unresolved |
| 12 | Web Quality | <https://github.com/addyosmani/web-quality-skills> | inferred, high confidence |

Reasons for each inference, all read on 2026-09-18:

- Entry 1. A GitHub repository search for "superpowers claude skills" returns
  obra/superpowers first among the repositories whose own description calls it
  an agentic skills framework. Two related repositories by the same account,
  obra/superpowers-skills and obra/superpowers-lab, exist, but the plain name
  "Superpowers" matches the main one.
- Entry 2. mattpocock/skills is the only repository owned by the account
  `mattpocock` that holds skill folders. Its description states that the
  skills come from that author's own agent directory. Several translated
  copies by other accounts exist and are not the source.
- Entry 3. nextlevelbuilder/ui-ux-pro-max-skill holds a skill folder whose
  front matter name is exactly `ui-ux-pro-max`. No other repository with that
  name holds the skill itself.
- Entry 4. JuliusBrussee/caveman holds a skill folder whose front matter name
  is exactly `caveman` and whose description matches the token reduction idea
  in the entry name. Several smaller repositories with similar names exist and
  are later copies or variants by other accounts.
- Entry 5. The most starred repository named after this idea,
  op7418/Humanizer-zh, states in its own README file that it is the translated
  version of <https://github.com/blader/humanizer>. blader/humanizer holds a
  SKILL.md file whose front matter name is exactly `humanizer`.
- Entry 6. vercel-labs/skills holds exactly one skill folder,
  `skills/find-skills`, whose front matter name is exactly `find-skills`. The
  confidence is medium because a separate list, BehiSecc/awesome-claude-skills,
  points a skill of the same name at <https://github.com/agentbay-ai/agentbay-skills>
  instead. That second repository has 50 stars, no license file, and was last
  pushed on 2026-02-12, so it is the weaker candidate for a widely shared list.
- Entry 7. No single repository stands out. A GitHub code search for a SKILL.md
  file whose front matter name is `deploy-to-vercel` returns at least six
  repositories, including midudev/autoskills (6877 stars, license reported as
  NOASSERTION), Kilo-Org/kilo-marketplace, sickn33/agentic-awesome-skills, and
  lovstudio/deploy-to-vercel-skill (0 stars, no license file). Naming one of
  them would be a guess, so the entry stays unresolved.
- Entry 8. The folder `skills/brainstorming` exists inside obra/superpowers and
  its front matter name is exactly `brainstorming`. Confidence is medium
  because the entry may point at a different repository that holds a skill of
  the same common name.
- Entry 9. Two strong candidates hold a test-driven development skill. The
  owner's list gives the short form used by both. obra/superpowers holds
  `skills/test-driven-development` and mattpocock/skills holds
  `skills/engineering/tdd`. Because entries 1 and 2 already name both
  repositories, neither can be preferred on evidence. Confidence is low.
- Entry 10. coleam00/excalidraw-diagram-skill holds one SKILL.md file whose
  front matter name is `excalidraw-diagram`, and it is the most starred
  standalone repository for this purpose. Confidence is medium because other
  repositories offer the same capability, including axtonliu/axton-obsidian-visual-skills
  and yctimlin/mcp_excalidraw.
- Entry 11. No single repository stands out. Candidates found by search are
  Vincentwei1021/video-shotcraft (8948 stars, Apache-2.0),
  wshuyi/remotion-video-skill (377 stars, no license file), and
  haidrrrry/claude-remotion-skill (168 stars, MIT). The plain entry name
  "Remotion" matches none of these better than the others, so the entry stays
  unresolved.
- Entry 12. addyosmani/web-quality-skills holds a skill folder whose front
  matter name is exactly `web-quality-audit`, together with five more quality
  skills. It is the clear match for the entry name.

## What each resolved repository holds

All values in this table were read on 2026-09-18 through
`gh api repos/<owner>/<repo>` and `gh api repos/<owner>/<repo>/git/trees/main?recursive=1`.
The license column gives the value of the `.license.spdx_id` field exactly as
GitHub reports it. "none stated" means the repository has no license file that
GitHub can serve; the license programming interface answers 404 for those.
The count of skills is the number of files named SKILL.md in the default
branch tree, which was not truncated for any of these repositories.

| Repository | License identifier | Stars on 2026-09-18 | SKILL.md files | Head commit read |
|---|---|---|---|---|
| obra/superpowers | MIT | 288546 | 14 | b36e0829c6d0140e93cfef2ca599b1b07d4a7797 |
| mattpocock/skills | MIT | 265259 | 38 | c55ee46073ed923f86ce59a5eb3b6d895095d1b7 |
| nextlevelbuilder/ui-ux-pro-max-skill | MIT | 128827 | 13 | 15de38fb70bc80ae9276fa7703b48ae861a672e6 |
| JuliusBrussee/caveman | NOASSERTION | 106596 | 24 | 542442bab314973709f95b85b1ac0b3f6f5b5dc6 |
| blader/humanizer | MIT | 49929 | 1 | 9862685f575c65a8247f90369951df1b3416e3d6 |
| vercel-labs/skills | MIT | 31967 | 1 | 7407f3893ad4dceab546ac002c3ef806e4000c73 |
| coleam00/excalidraw-diagram-skill | none stated | 4811 | 1 | 8646fcc9f74f38539c6cdb4c969723336a96ddcd |
| addyosmani/web-quality-skills | MIT | 2803 | 6 | afa8da942115f2961fdbfa80807ea0b232ff6c00 |

The star count for blader/humanizer was read twice on the same day, first as
49928 and then as 49929. Star counts move continuously and are only a
measurement at the moment of reading.

### Executable content and requested tool permissions

Observed. Every SKILL.md file in all eight repositories was fetched and its
front matter read. Not one of them carries an `allowed-tools` field. Every
skill in this set states only a name and a description, and in two cases a
license and a metadata block. No skill in this set asks for tool permissions
through the front matter.

Executable files inside skill folders, by contrast, are common.

| Repository | Executable content inside skill folders | Examples observed |
|---|---|---|
| obra/superpowers | yes | skills/brainstorming/scripts/server.cjs, skills/brainstorming/scripts/start-server.sh, skills/systematic-debugging/find-polluter.sh, skills/writing-skills/render-graphs.js |
| mattpocock/skills | yes | skills/engineering/diagnosing-bugs/scripts/hitl-loop.template.sh, skills/engineering/wizard/template.sh, skills/misc/git-guardrails-claude-code/scripts/block-dangerous-git.sh |
| nextlevelbuilder/ui-ux-pro-max-skill | yes, extensively | .claude/skills/brand/scripts/extract-colors.cjs, .claude/skills/design-system/scripts/generate-slide.py; 194 paths in the tree sit under a scripts folder |
| JuliusBrussee/caveman | yes | plugins/caveman/skills/caveman-compress/scripts/cli.py, skills/compile.mjs, skills/verbs-gate.mjs |
| blader/humanizer | one file | scripts/validate-package.py, which sits inside the skill root because the SKILL.md file is at the repository root |
| vercel-labs/skills | no | the skills/find-skills folder holds only SKILL.md; the installer itself is a command line program under src/ and bin/ |
| coleam00/excalidraw-diagram-skill | no | SKILL.md plus a references folder only |
| addyosmani/web-quality-skills | yes | skills/web-quality-audit/scripts/analyze.sh |

### What each skill teaches

One sentence each, from the SKILL.md file read on 2026-09-18.

| Skill and repository | What it teaches |
|---|---|
| skills/test-driven-development in obra/superpowers | Write the failing test first, watch it fail, write the smallest code that passes, and treat a test you never watched fail as unproven. |
| skills/brainstorming in obra/superpowers | Turn a rough idea into a design through structured questions, and hold a hard gate that forbids writing code before a person approves the intent. |
| skills/engineering/tdd in mattpocock/skills | Run the red then green loop so that the tests it leaves behind verify behavior at public boundaries rather than internal structure. |
| .claude/skills/ui-ux-pro-max in nextlevelbuilder/ui-ux-pro-max-skill | Apply a local searchable body of interface design guidance, stated by the skill as 79 styles, 192 palettes, 74 font pairings, 119 guidelines, 105 icons, 25 chart types, and 22 technology stacks. |
| skills/caveman in JuliusBrussee/caveman | Answer in an ultra-compressed style that keeps the technical substance and drops the filler, held for a whole session until the person asks for normal replies. |
| SKILL.md in blader/humanizer | Rewrite text that sounds machine-written so it reads like the writer, by naming the specific patterns that produce that sound and removing them without changing the meaning. |
| skills/find-skills in vercel-labs/skills | Recognize when a person is asking for a capability that already exists as an installable skill, then search the open skill ecosystem and install it. |
| SKILL.md in coleam00/excalidraw-diagram-skill | Produce Excalidraw diagram files that make a visual argument rather than only displaying information, with all color choices kept in one editable reference file. |
| skills/web-quality-audit in addyosmani/web-quality-skills | Run an evidence-led site audit across performance, accessibility, search visibility, and best practices, keeping measured findings separate from guesses read out of the source code. |

### Format claims, observed rather than assumed

Every SKILL.md file quoted above was fetched from raw.githubusercontent.com and
its opening lines read. The format matches the description in the request. Each
file opens with a line containing three hyphens, then a YAML block, then a
closing line of three hyphens, then a Markdown body. Each YAML block carries
`name` and `description`. Two of the nine also carry `license` and a `metadata`
block: blader/humanizer states `license: MIT` and `metadata.version: "3.0.0"`,
and the web-quality-audit skill states `license: MIT` with a metadata block
holding an author and a version. Supporting material sits beside the SKILL.md
file as further Markdown files, a references folder, a data folder, or a
scripts folder.

## The Loop Engine rules that govern any import

Read on 2026-09-18 in this repository.

From `AGENTS.md`, the Intelligence rules. There are four persistent
intelligence layers: Context Intelligence, Code Intelligence, Runtime History
and Solution Intelligence, and User Feedback Intelligence. Source formats such
as Markdown, skills, repositories, packages, transcripts, and vectors do not
define new layers, so a skill repository is material for an existing layer and
never a fifth layer. Imported and self-generated intelligence remains candidate
only until an independent process approves it. Promotion is never inferred from
retrieval, execution, a good score, or model confidence. Code Intelligence must
carry an immutable source identity, provenance, license state, version,
dependency information, a typed contract, effects, tests, independent
verification, and a digest before it is active. Search returns small typed
references, and a large body is loaded only after selection and permission
checks. Nothing executable runs from file presence.

From `src/loop_engine/core/skill_registry.py`, the module docstring and three
members.

- The module docstring states that discovery parses only the SKILL.md front
  matter as semantic metadata, that it reads skill file bytes to compute exact
  references and digests but does not return their bodies, that loading the
  full instructions is a separate deterministic Loop, and that imported skills
  enter as candidate Context Intelligence and never become active intelligence,
  executable Code Intelligence, or approved effects by being discovered. It
  states that task use requires a digest-bound `SkillAdmissionRecord` that names
  an external reviewer and evidence, that the registry validates the record but
  does not perform or prove that review, and that discovery cannot create the
  admission. It states that scripts, templates, references, and assets remain
  files behind bounded paths and that the module does not execute them.
- `SkillManifest` is the small searchable card. It holds the skill identifier,
  title, description, version, root path, manifest digest, a tuple of file
  references with a digest and a size for each, a lifecycle value, the declared
  license text, a compatibility string, a metadata mapping, the requested
  tools, and the instruction size in bytes and lines. It does not hold the
  instructions. The allowed front matter fields are exactly `name`,
  `description`, `license`, `compatibility`, `metadata`, and `allowed-tools`,
  with three further legacy fields tolerated under a named legacy policy.
- `SkillAdmissionRecord` binds one admission decision to one skill identifier,
  one version, and one manifest digest, and requires a reviewer identifier,
  unique evidence references, and an evidence digest. It refuses a reviewer
  whose identifier equals the skill identifier, so a skill cannot approve
  itself. The record carries its own digest and refuses to deserialize if the
  digest does not match.
- `SkillManifest.as_context_candidate` returns a `StoreRecord` with the record
  identifier `skill.<identifier>.<version>`, the kind `strategy`, the tags
  `context_intelligence` and `agent_skill` plus the skill's own tags, and the
  tier `experimental`. Its body carries the description, the context type
  `skill`, the source kind, the root path, the manifest digest, the list of
  file paths, the lifecycle, the license, the compatibility, the metadata, and
  the requested tools together with the explicit field
  `requested_tools_grant_authority` set to false. A comment in the source states
  the reason: a skill can state what it expects, and only Loop authority can
  make a tool or effect available at execution time.

From `src/loop_engine/skills/README.md`: the packaged skill directories are
source-format candidates for the registry, discovery does not activate them,
and task use requires independent digest-bound admission.

From `src/loop_engine/intelligence/README.md`: the four layers sit at rest in
this folder, each split into core, learned, and plugin provenance. The folder
allows only records and one README file. It forbids runtime Loop instances,
provider credentials, and Python modules of any kind. Context Intelligence is
implemented by `core.intelligence_layers`, `core.retrieval`, `core.store_serve`,
`strings.question_engine`, `core.temporal_facts`, and the catalog adapters.

From `docs/guides/seeded-intelligence-from-occupations.md`: the existing
pattern for turning an outside source into candidate intelligence. An
occupation record carries a code, a title, a description, task statements, a
domain, a source, a license, and a version. Seeds are staged through a store
contract, as candidates, never as a file. The guide also states plainly that
the reuse terms of one outside source, the ESCO occupation table, should be
confirmed before any seed derived from it is redistributed. The function
`stage_seeds` writes one record per seed with the lifecycle value candidate and
returns a report of the counts.

## Which parts are Context Intelligence and which are Code Intelligence

| Part of a skill | Layer | What it must carry | What it must never do |
|---|---|---|---|
| The Markdown body of SKILL.md: instructions, procedures, checklists, rubrics, personas, and style rules | Context Intelligence, staged as a candidate record | Provenance as the source repository full name, the exact source commit digest, the SKILL.md file digest, the manifest digest, the declared license identifier, the resolved version, and the date read | Become active, retrievable for task use, or preferred over the engine's own text without a separate admission decision |
| Reference Markdown files beside SKILL.md, such as writing-good-tests.md, mocking.md, tests.md, and color-palette.md | Context Intelligence, same treatment, retrieved only after selection | The same provenance fields, plus its own file digest | Be loaded in full during discovery; search returns the small card, and the body is loaded after selection and permission checks |
| Passive data files, such as the palette, font pairing, icon, and chart tables inside the ui-ux-pro-max skill | Context Intelligence as passive typed material | The same provenance fields and a declared shape | Be treated as code because it is machine-readable |
| The `scripts/` folder, hooks, and any template that is executed, such as server.cjs, start-server.sh, analyze.sh, cli.py, compile.mjs, and verbs-gate.mjs | Code Intelligence | Immutable source identity, provenance, license state, version, dependency information, a typed contract, declared effects, tests, independent verification, and a digest before it is active | Run because the file is present, because a Markdown body says to run it, or because the skill was admitted as Context Intelligence |
| The `allowed-tools` front matter field, when a skill carries one | Recorded request, neither layer | The literal requested tool names, stored with `requested_tools_grant_authority` set to false | Grant any tool, file, network, secret, model, spending, or external effect authority |
| An installer that fetches and writes files, such as the command line program in vercel-labs/skills | Code Intelligence with file write and network effects | The full code admission list plus an explicit typed effect authority and a path-confined workspace | Be imported at all as part of a Context Intelligence staging pass |

The split is not a matter of file extension. The deciding question is whether
the material is read as instruction by a model or run as a program. The
Markdown body of the caveman skill is Context Intelligence even though the
repository around it is mostly a compression program, and the Python file
inside the caveman-compress skill folder is Code Intelligence even though it
sits inside a skill.

Two observed frictions matter for any importer.

First, the manifest builder requires that the front matter `name` match the
name of the folder that holds the SKILL.md file. Observed: the SKILL.md file in
coleam00/excalidraw-diagram-skill states the name `excalidraw-diagram` while the
repository folder is named `excalidraw-diagram-skill`. A clone of that
repository under its default folder name would be refused by the current
registry. The same risk applies to blader/humanizer, whose SKILL.md file is at
the repository root, although the default clone name there does match.

Second, the manifest builder walks every file under the skill root and hashes
it. When the skill root is a repository root, as it is for blader/humanizer and
coleam00/excalidraw-diagram-skill, the manifest would include the license file,
the README file, the continuous integration configuration, and every script.
That is correct behavior for a digest, and it means an importer should choose
the skill root deliberately rather than pointing at a whole clone.

## Overlap with what Loop Engine already holds

| Outside skill | Loop Engine equivalent already in the repository | Relationship | Status |
|---|---|---|---|
| blader/humanizer | `humanizer-context.md` at the repository root, which states the reader, the voice, and the writing rules for public Markdown | Same purpose, different rule set. The outside skill names patterns to remove; the local file states a voice to write in. | Observed |
| skills/caveman in JuliusBrussee/caveman | `src/loop_engine/core/prompt_elements.py`, which declares response style as one of two grid axes with the values `concise`, `only_what_was_asked`, and `full` | The caveman skill is a candidate value for an axis the engine already declares, not a new mechanism. The module docstring states that style is a configuration choice a grid can vary and the evaluation product can measure. | Observed |
| skills/test-driven-development in obra/superpowers and skills/engineering/tdd in mattpocock/skills | `src/loop_engine/skills/software-tdd-red-green-refactor/SKILL.md`, the packaged test-driven development skill | Same procedure. The packaged version adds the parts the engine needs: a requirement verification contract, a confined workspace, a permitted write scope, a registered test capability, and a refusal to mark completion from test text alone. | Observed |
| skills/find-skills in vercel-labs/skills | `SkillRegistry.search` and `SkillRegistry.discovery_projection` in `src/loop_engine/core/skill_registry.py` | Same purpose. The engine already ranks candidate skill cards against a query inside a byte envelope. The outside skill additionally installs, which the engine deliberately does not do without an admission decision. | Observed |
| skills/brainstorming in obra/superpowers | `strings.question_engine`, named in `src/loop_engine/intelligence/README.md` as the implementation of question forms for Context Intelligence | Partial. Both turn an unclear request into structured questions. Whether the coverage overlaps in detail was not compared. | Inferred |
| .claude/skills/ui-ux-pro-max, skills/web-quality-audit, the Excalidraw diagram skill, and the unresolved Remotion and Deploy to Vercel entries | No equivalent found | These are domain capabilities the engine does not hold. | Missing |

The three observed overlaps are the reason this question needs an answer
rather than an import. Where the engine already holds a rule, an imported skill
is an alternative to compare, not a replacement to install. The prompt element
module and the evaluation product already give the means to compare them.

## What each license allows

The identifier in the first column is the value of the `.license.spdx_id`
field returned by GitHub on 2026-09-18.

| Repository | License identifier | Packaging inside the engine | Serving from a hosted tier |
|---|---|---|---|
| obra/superpowers | MIT | Permitted, with the copyright notice and the license text carried with the copy | Permitted on the same condition |
| mattpocock/skills | MIT | Permitted, same condition | Permitted, same condition |
| nextlevelbuilder/ui-ux-pro-max-skill | MIT | Permitted, same condition | Permitted, same condition |
| blader/humanizer | MIT | Permitted, same condition | Permitted, same condition |
| vercel-labs/skills | MIT | Permitted, same condition | Permitted, same condition |
| addyosmani/web-quality-skills | MIT | Permitted, same condition | Permitted, same condition |
| JuliusBrussee/caveman | NOASSERTION | Split. See below. | Split. See below. |
| coleam00/excalidraw-diagram-skill | none stated | Not permitted | Not permitted |

Two of these need the plain statement.

JuliusBrussee/caveman reports NOASSERTION, which means GitHub found a license
file but could not identify it as one standard license. The repository holds
three files: LICENSE, LICENSE.BSL, and LICENSING.md. The file LICENSING.md,
read on 2026-09-18, states a split model. It states that the public repository
identity stays MIT for the caveman skill and the adoption surfaces, and that
the compression engine and the Go binaries that embed it use Business Source
License 1.1 with an additional use grant. That grant, as the file states,
permits first-party self-hosted production use and requires a commercial
license for third-party hosted, managed, or embedded services. Its per-directory
table assigns the `skills/` folder to MIT. So the Markdown body of the caveman
skill may be packaged under MIT terms, while the compression engine may not be
served from a hosted, managed, or embedded commercial tier without a separate
commercial license. Because an automatic check reads NOASSERTION and not the
per-directory table, an importer must refuse this repository by default and
require an explicit recorded decision.

coleam00/excalidraw-diagram-skill states no license. The license programming
interface answers 404 for it and the repository tree holds no license file.
That means no permission to redistribute. Reading the repository is fine and
learning from it is fine. Copying its text into a package that Loop Engine
ships, or serving that text from a hosted tier, is not permitted unless the
owner of that repository grants it. The same applies to agentbay-ai/agentbay-skills
and wshuyi/remotion-video-skill, both of which also state no license.

## What an import path would look like as roadmap work

This section is a proposal. Nothing in it is implemented. It is written so
that it could become steps in `docs/roadmap/FABRIC-ROADMAP-2026-09-18.md` and
`docs/roadmap/roadmap.yaml` if the owner chooses.

A skill pack importer, staging Context Intelligence only:

1. Take a repository reference, an exact commit digest, and a list of skill
   root paths within that repository. Refuse a reference that names a branch
   without a commit digest, because a branch is not an immutable source
   identity.
2. Fetch into a path-confined workspace. Refuse path traversal, symlink
   escape, and unsafe overwrite, as the effects rules in `AGENTS.md` already
   require.
3. Read the license state first. Refuse to stage anything when the license is
   absent, when the identifier is NOASSERTION, or when the repository states a
   split model, and return a typed refusal that names the repository and the
   observed license state. A refusal is the correct result, not a failure. The
   record may still be created as a reference holding only the address and the
   date read.
4. For each skill root, call the existing discovery so that only the SKILL.md
   front matter is parsed and every file is hashed. Do not write a second
   parser.
5. Stage each candidate through the store contract, the way `stage_seeds`
   stages occupation seeds. Never write into `src/loop_engine/intelligence/`
   directly, because that folder allows records and one README file only, and
   because the storage direction recorded on 2026-09-18 refuses direct writes
   to intelligence files.
6. Record on every candidate: the source repository full name, the exact
   source commit digest, the skill file digest, the manifest digest, the
   declared license identifier, the resolved version, the date read, and the
   lifecycle value candidate. The existing `as_context_candidate` already
   carries the license, the manifest digest, the file list, and the lifecycle.
   The source repository, the source commit, and the date read are the fields
   that would need to be added.
7. Repair or refuse the folder name mismatch explicitly. When the front matter
   name does not match the folder name, either accept an explicit mapping
   supplied by the operator and record it, or refuse with the exact mismatch
   named. Do not rename silently.
8. Record `allowed-tools` as a request with `requested_tools_grant_authority`
   set to false, which the existing code already does. None of the twelve
   entries exercises this path, so it stays untested against them.
9. Deduplicate against what the engine already holds. When a candidate covers
   the same ground as the packaged test-driven development skill, the writing
   context file, or the declared response style values, record it as an
   alternative with a link to the local equivalent. Do not replace the local
   text.

A separate code admission path, for scripts and hooks:

1. Never carried by the same operation that stages the Markdown body. The two
   results must be separately visible, so that a staged skill body cannot be
   read as an approval of the scripts beside it.
2. Each script enters through the reusable capability records and the
   admission ladder with the full list from `AGENTS.md`: immutable source
   identity, provenance, license state, version, dependency information, a
   typed contract, declared effects, tests, independent verification, and a
   digest.
3. A script that has not passed that ladder is recorded as present and not
   admitted. It is never invoked, and the Markdown body that refers to it must
   be staged with that gap recorded, so a later reader does not follow an
   instruction that points at an unqualified program.
4. The sandbox, resource, and network rules apply unchanged. Several of the
   observed scripts start a local server, install packages, or modify a
   repository's version control behavior, which are exactly the effects that
   need typed authority.

Admission stays what it already is. A `SkillAdmissionRecord` names an external
reviewer, cites evidence, and is bound to one manifest digest. Neither the
importer nor the skill can create it.

## Observed, inferred, assumed, and missing

Observed. All twelve short links fail to resolve on 2026-09-18. The eight
repositories named above exist, and their license identifiers, star counts,
head commits, and SKILL.md counts are as tabled. No SKILL.md file in those
eight repositories carries an `allowed-tools` field. Six of the eight carry
executable files inside skill folders. Six of the eight state MIT, one states
NOASSERTION with a split model documented in its own LICENSING.md file, and one
states no license at all. The Loop Engine skill registry already parses only
front matter, hashes every file, keeps every discovered skill a candidate, and
refuses task use without a digest-bound admission record that names an external
reviewer. Loop Engine already holds a packaged test-driven development skill, a
writing context file, a declared response style axis, and a skill search
projection.

Inferred. The mapping from each list entry to a repository, with the confidence
stated per entry in the resolution table. The overlap between the brainstorming
skill and the question forms in `strings.question_engine`, which was read from
the component table rather than compared line by line.

Assumed. That the owner's list refers to publicly readable GitHub repositories
rather than to a private collection or to a vendor marketplace listing. That
the twelve entries name skills rather than twelve distinct repositories, which
is why entries 1, 8, and 9 can point at one repository.

Missing. The destination of entry 7 and entry 11. The original short link
targets, which cannot be recovered from LinkedIn. Any measurement of whether
any of these skills improves a verified outcome in Loop Engine. Any comparison
between the imported text and the engine's own text on the same task. Any
review of the scripts inside these repositories for what they actually do. Any
statement from the repository owners about reuse beyond the license file. The
reuse terms of the repositories that state no license.

Unverified. The relationship between the owner's list and any of the public
lists found during this search. Three lists named awesome-claude-skills were
read and none of them holds these exact twelve entries in this order. Whether
any repository named here is the one the owner's link pointed at cannot be
confirmed, because the links do not resolve.

## Open questions for the owner

1. Are entries 7 and 11 worth resolving, and if so, can the owner supply the
   working addresses from the original post.
2. For entry 9, is the intended source obra/superpowers or mattpocock/skills.
3. Should an importer be built at all before a comparison shows that an
   outside skill body beats the engine's own text on a measured task, or should
   the first step be the comparison.
4. For the repositories that state no license, should Loop Engine record them
   as references with an address only, or leave them out entirely.

## Sources read on 2026-09-18

Outside sources, all read on 2026-09-18:

- <https://lnkd.in/dKp8VwQa>
- <https://lnkd.in/dR3n-Tzb>
- <https://lnkd.in/dW9cYmFv>
- <https://lnkd.in/dh6SgUeq>
- <https://lnkd.in/dN2xLrPk>
- <https://lnkd.in/dZ4bHjWm>
- <https://lnkd.in/dC7tQaNs>
- <https://lnkd.in/dJ5_PvXr>
- <https://lnkd.in/dB8mKdTy>
- <https://lnkd.in/dY1fRcHu>
- <https://lnkd.in/dS6wNbGe>
- <https://lnkd.in/dE0zMqLj>
- <https://github.com/obra/superpowers>
- <https://raw.githubusercontent.com/obra/superpowers/main/skills/test-driven-development/SKILL.md>
- <https://raw.githubusercontent.com/obra/superpowers/main/skills/brainstorming/SKILL.md>
- <https://github.com/mattpocock/skills>
- <https://raw.githubusercontent.com/mattpocock/skills/main/skills/engineering/tdd/SKILL.md>
- <https://github.com/nextlevelbuilder/ui-ux-pro-max-skill>
- <https://raw.githubusercontent.com/nextlevelbuilder/ui-ux-pro-max-skill/main/.claude/skills/ui-ux-pro-max/SKILL.md>
- <https://github.com/JuliusBrussee/caveman>
- <https://raw.githubusercontent.com/JuliusBrussee/caveman/main/skills/caveman/SKILL.md>
- <https://raw.githubusercontent.com/JuliusBrussee/caveman/main/LICENSING.md>
- <https://github.com/blader/humanizer>
- <https://raw.githubusercontent.com/blader/humanizer/main/SKILL.md>
- <https://github.com/op7418/Humanizer-zh>
- <https://raw.githubusercontent.com/op7418/Humanizer-zh/main/README.md>
- <https://github.com/vercel-labs/skills>
- <https://raw.githubusercontent.com/vercel-labs/skills/main/skills/find-skills/SKILL.md>
- <https://github.com/coleam00/excalidraw-diagram-skill>
- <https://raw.githubusercontent.com/coleam00/excalidraw-diagram-skill/main/SKILL.md>
- <https://github.com/addyosmani/web-quality-skills>
- <https://raw.githubusercontent.com/addyosmani/web-quality-skills/main/skills/web-quality-audit/SKILL.md>
- <https://github.com/agentbay-ai/agentbay-skills>
- <https://github.com/midudev/autoskills>
- <https://github.com/Vincentwei1021/video-shotcraft>
- <https://github.com/wshuyi/remotion-video-skill>
- <https://github.com/haidrrrry/claude-remotion-skill>
- <https://github.com/travisvn/awesome-claude-skills>
- <https://raw.githubusercontent.com/travisvn/awesome-claude-skills/main/README.md>
- <https://github.com/BehiSecc/awesome-claude-skills>
- <https://raw.githubusercontent.com/BehiSecc/awesome-claude-skills/main/README.md>
- <https://github.com/ComposioHQ/awesome-claude-skills>
- <https://api.github.com/search/repositories> (repository search, twelve queries by entry name)
- <https://api.github.com/search/code> (code search for SKILL.md files named deploy-to-vercel and remotion)

Loop Engine sources read on 2026-09-18:

- /home/username/loop-engine/AGENTS.md
- /home/username/loop-engine/ASTRA.md
- /home/username/loop-engine/humanizer-context.md
- /home/username/loop-engine/src/loop_engine/core/skill_registry.py
- /home/username/loop-engine/src/loop_engine/core/prompt_elements.py
- /home/username/loop-engine/src/loop_engine/skills/README.md
- /home/username/loop-engine/src/loop_engine/skills/software-tdd-red-green-refactor/SKILL.md
- /home/username/loop-engine/src/loop_engine/intelligence/README.md
- /home/username/loop-engine/docs/guides/seeded-intelligence-from-occupations.md
