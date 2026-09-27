# Package activation and the failure laboratory

Kind: research record, September 26, 2026.

The question: how does Baltor know that a served package loads in a harness
and gives it something to use? Before this record, nothing checked it. The
review panel's prechecks refuse format, licence, safety, effect, secret and
duplicate faults; the daily release check downloads one item and compares its
digest. No check placed a package where a harness reads it.

This record compares ten verification approaches, chooses native activation
facts as the next layer, and reports the increment: a laboratory of twelve
fixture packages under `examples/31_failure_laboratory/packages/` and
`tools/check_package_activation.py`, run over every package of the served
bundle `daily-2026-09-26-10` (6,398 packages). The failing packages are
findings, not fixtures. A second, separate layer asks a real loader: OpenCode's
own skill listing, against an empty project as the no-extra-component
baseline, listed every one of the 2,249 skills the check passed.

## A. Current reality

| Part | Exists | Enabled | Deployed | Tested | Note |
|---|---|---|---|---|---|
| Review prechecks (`tools/candidate_review/native_prechecks.py`, `imported_prechecks.py`) | yes | yes, in the daily job | yes, before publication | yes, with mutants | read the record and the text; never place a file |
| Mutant controls in the check suites | yes | yes | not applicable | yes | remove a guard and confirm the check fails |
| Daily release live check | yes | yes | yes | yes | downloads one item and verifies its digest |
| Documented native layouts (`tools/licensed_import/harness_kinds.py`, `placements`) | yes | used at import | recorded on candidates | yes | every row says `support: unverified` |
| Client layout profiles (`tools/install_selected_material.py`) | yes | customer tool | shipped in the repository | yes | place single-file skills for OpenCode, Claude Code, Codex and Pi; observed client versions are recorded there |
| Activation check over served packages | no, before this record | | | | the gap this record fills |

The served bundle holds 6,398 packages: 2,796 skills, 1,023 subagents, 953
commands, 464 plugin manifests, 327 marketplaces, 490 instruction files, 219
rules files, 101 protocol server configurations and 25 contract schemas, as
counted from its `items.jsonl`.

## B. First principles

- The user outcome: a customer installs a package and the harness lists it,
  loads it and can follow it, with no fault the customer has to debug.
- The essential information: the bytes of each file and their digests, the
  file roles, the package kind and native format, and the documented layout
  of each harness.
- The required effects: file writes into a scratch folder only. No network,
  no model, no harness process. The optional loader listing adds one
  OpenCode listing process, run twice, which starts no model turn.
- The acceptance conditions: each fixture is refused with exactly the codes it
  names; each control activates; every served package gets one of four
  verdicts bound to its served digest; unknown is never counted as a pass.
- Is a model needed? No. Every activation fact is a parse, a path lookup or a
  digest comparison. A model is needed only for the later question of whether
  a package helps, which this record leaves to sandboxed trials.

## C. Alternatives

1. Schema and static checks, present today: fast and cheap, but they never
   place a file, so a missing script or a colliding path passes.
2. Native activation facts, chosen: place the package in each documented
   layout in a scratch folder and check what the harness reads first.
3. Real harness loaders: start Claude Code, Codex, OpenCode or Pi and read
   their own listing of what loaded. The strongest evidence of loading, but it
   needs installed clients, and only OpenCode offers a listing that starts no
   model turn (recorded in `install_selected_material.py`).
4. Unit tests shipped inside packages, as Homebrew's `test do` block does:
   strong for code modules, absent from nearly all imported material.
5. Property-based tests over the package model: generate packages and check
   invariants such as "an activating package never names a missing file".
6. Differential testing against the source project: install the package and
   the upstream folder side by side and compare what each harness loads.
7. Metamorphic tests: rename, reorder or add a notice file and require the
   same verdict.
8. Sandboxed task trials with a small model, with a baseline run that has no
   extra package: the only approach that measures usefulness.
9. Independent model review (the oracle) and human review: judge meaning and
   quality; neither observes a file placement.
10. Doing less: publish and rely on feedback withdrawal. Cheap, but every
    fault reaches a customer first.

## D. External research

These sources informed the documented layouts and the facts. The repository
records the layouts in `harness_kinds.py` and the client versions in
`install_selected_material.py`. The first three rows were read again on
September 26, 2026 for this record; the other rows state what the recorded
documentation was used for, not a new reading.

| Source | Version or date | Used for |
|---|---|---|
| [OpenCode skills](https://opencode.ai/docs/skills/) | page last updated September 26, 2026; read September 26, 2026 | the six skill folders OpenCode searches, the walk up to the git worktree, and the name rule: 1 to 64 lowercase letters and digits with single hyphens, matching the folder, or the skill "won't load" |
| [Agent Skills specification](https://agentskills.io/specification) | read September 26, 2026 | `name` required, at most 64 characters, no leading, trailing or double hyphen, matching the parent folder; `description` required, at most 1,024 characters; file references relative to the skill root |
| [Claude Code skills](https://code.claude.com/docs/en/skills) | read September 26, 2026 (the older address redirects there) | `name` is optional and defaults to the folder name; frontmatter is read only when `---` is the first line; `allowed-tools` takes a string or a list |
| [Claude Code slash commands](https://docs.claude.com/en/docs/claude-code/slash-commands) | as recorded in the repository, September 2026 | command frontmatter, `argument-hint`, `@` file references relative to the project |
| [Claude Code hooks](https://docs.claude.com/en/docs/claude-code/hooks) | as recorded in the repository, September 2026 | event names, handler types, `${CLAUDE_PLUGIN_ROOT}` |
| [Claude Code plugins reference](https://docs.claude.com/en/docs/claude-code/plugins-reference) | as recorded in the repository, September 2026 | `plugin.json` part fields and `./` relative paths |
| [Claude Code memory](https://docs.claude.com/en/docs/claude-code/memory) | as recorded in the repository, September 2026 | `@` imports in CLAUDE.md, code spans left out |
| [Gemini CLI custom commands](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/custom-commands.md) | as recorded in the repository, September 2026 | TOML commands with a required `prompt` |
| Observed clients in `install_selected_material.py` | Codex 0.155.1, Pi 0.73.1 | where each client reads project skills |
| OpenCode on this machine | 1.18.32, observed September 26, 2026 | the skill listing that starts no model turn, and what it lists in practice |

Limits: the documentation shows `argument-hint: [pr-number] [priority]`,
which strict YAML refuses, so a harness must read frontmatter more forgivingly
than a YAML parser. How each harness does so is not documented, which is why
the check reports such a file as unknown.

## E. Analogies

| Analogy | What transfers | What does not | Experiment that tests it |
|---|---|---|---|
| Debian lintian and autopkgtest | a static linter plus a test run against the installed package, with named tags per fault | Debian runs the installed program; a skill has no program to run | compare the refusal codes with a lintian-style tag list after one month of releases |
| Manufacturing incoming inspection with golden samples | a known-bad sample for each defect keeps the gauge honest; a gauge that passes a bad sample is recalibrated | parts do not change shape between lots; library material does | add a fixture for each new refusal code and require the laboratory to stay exact |
| Aviation preflight checklist | a short fixed list of facts that must hold before use, independent of the pilot's judgement | a checklist cannot say whether the flight was worth taking | measure how many refused packages the review panel had approved |

## F. Comparable products and projects

| Project | Journey | Evidence | Relevance |
|---|---|---|---|
| Homebrew (`brew audit`, `brew test`) | a formula ships its own test block, run after installation | documented behaviour | shipped tests suit code modules, not instruction files |
| Debian (lintian, autopkgtest) | static tags, then tests against the installed package | documented behaviour | the split between static facts and installed trials |
| Python packaging (`twine check`, `check-wheel-contents`) | checks that an archive's metadata and contents agree before upload | documented behaviour | the same idea as `file_claim_false` and `media_type_claim_false` |
| Visual Studio Code extensions (`vsce package`) | refuses a manifest that names missing parts | documented behaviour | the same fact as `manifest_part_missing` |
| Agent Skills reference validator | validates a skill folder's frontmatter | inferred from the specification's tooling; not run here | the same fact as the skill name and description checks |

Inference: none of these places material into several harness layouts at once
or checks two packages for the same path, which a harness library needs
because customers install many small packages side by side.

## G. Comparison and choice

| Approach | Catches placement faults | Needs a harness or model | Cost per package | Measures usefulness | Status |
|---|---|---|---|---|---|
| Schema and static prechecks | no | no | milliseconds | no | present |
| Native activation facts | yes | no | 8 to 40 milliseconds | no | built here |
| Real harness loaders | yes, for what the loader enforces | harness | one listing of about 20 seconds for 2,575 skills | no | built here for OpenCode skills; the other clients next |
| Shipped unit tests | for code only | runtime | seconds | partly | later, code modules |
| Property-based tests | of the checker | no | not per package | no | untouched |
| Differential against source | yes | harness | seconds | no | untouched |
| Metamorphic tests | of the checker | no | not per package | no | partly, in the unit tests |
| Sandboxed trials with baseline | indirectly | model | minutes | yes | next wave |
| Oracle and human review | no | model or person | seconds to minutes | partly | present |
| Doing less | no | no | none | no | refused |

Chosen: native activation facts now, because they catch the placement faults
that reach customers, need no model and run over the whole bundle in under a
minute when the machine is quiet. The one real loader that lists without a
model turn, OpenCode's, was added as a second, separate layer for skills,
against an empty-project baseline, because the documented rules and the
loader can disagree, and they did. Loaders for the other clients come next,
and trials with a no-extra-package baseline come after that, to measure
usefulness.

## H. The increment and what it found

### What was built

- `tools/check_package_activation.py` writes a `package_activation_report/v1`
  record with one `package_activation_result/v1` per package: the facts, the
  layouts written with read-back digests, and one of four verdicts:
  activates, refused, unresolved or no native activation.
- `examples/31_failure_laboratory/` holds twelve fixtures (three controls and
  nine faults) with a README each and a `run.py` added to the examples step of
  continuous integration.
- `--observe-listing` adds a `package_activation_listing/v1` record: OpenCode's
  own skill listing (`opencode debug skill --pure`, through the installer's
  `observe_client_listing`) in an empty project, the no-extra-component
  baseline, and in a project that holds only the placed skill folders, so no
  plugin or tool file is ever loaded as code. Each skill package gets a
  separate `listing` fact: reported at its exact path or not, and any extra
  component the loader lists from inside its folder. The static verdicts do
  not change.
- `tools/test_check_package_activation.py` holds 20 checks, including eleven
  mutants that each remove one guard and name the fixture or case that must
  then stop passing; one of them attributes the listing without the baseline.

Two design choices came from the first run. A notice file beside a command
was placed in the commands folder, where Claude Code lists it as a second
command; the first run counted 1,069 collisions in 300 packages, nearly all
`ATTRIBUTION.md` and `LICENSE`. Now only the entry goes into a single-file
slot and the other files wait in a side folder. And 17 commands of the first
300 were refused for frontmatter such as `argument-hint: [test-type]
[element-to-test]`, which the documentation's own example resembles; such a
file is now unknown, not refused.

### Observed results on `daily-2026-09-26-10`

| Package kind | Packages | Activates | Refused | Unresolved | No native activation |
|---|---|---|---|---|---|
| Skill | 2,796 | 2,460 | 336 | 0 | 0 |
| Subagent | 1,023 | 479 | 520 | 24 | 0 |
| Command | 953 | 825 | 62 | 66 | 0 |
| Plugin manifest | 464 | 212 | 252 | 0 | 0 |
| Marketplace | 327 | 86 | 241 | 0 | 0 |
| Instruction file | 490 | 473 | 1 | 16 | 0 |
| Rules | 219 | 177 | 0 | 42 | 0 |
| Protocol server configuration | 101 | 90 | 11 | 0 | 0 |
| Contract schema | 25 | 0 | 0 | 0 | 25 |
| All | 6,398 | 4,802 | 1,423 | 148 | 25 |

The refusal codes that account for most refusals (a package can carry more
than one):

| Code | Packages | Where | What it means |
|---|---|---|---|
| `authority_exceeds_declared_effects` | 509 | 455 subagents, 44 plugin manifests, 10 skills | the `tools`, `allowed-tools`, hooks or servers ask for effects the item record leaves undeclared: running a process 278 times, reading files 272, writing files 196, network 11 |
| `manifest_part_missing` | 454 | 238 marketplaces, 216 plugin manifests | the manifest names a plugin, command, skill or agent that the package does not carry |
| `referenced_path_escapes` | 350 | 273 skills, 43 commands, 33 subagents, 1 instruction file | a link or import climbs out of the package, so the harness cannot find its target |
| `skill_name_not_native` | 48 | skills | the frontmatter name breaks the lowercase, digits and hyphens rule |
| `referenced_file_missing` | 20 | 8 commands, 7 subagents, 5 skills | a linked file inside the package is absent |
| `subagent_name_missing` and `subagent_frontmatter_missing` | 37 | subagents | a Claude Code subagent without a name or without frontmatter |
| `command_format_mismatch` | 17 | commands | a TOML command placed where Markdown commands are read |

Unknown facts: 131 frontmatter blocks that only a forgiving reader accepts
(62 commands, 42 rules, 26 subagents, 1 instruction file), 21 imports of files
that the customer's project may hold, and 25 contract schemas with no file a
harness reads first. No served file broke its recorded digest, size or media
type.

Collisions: 1,035 packages in 656 pairs write different bytes to the same
named slot, 282 slots in the Claude Code layout alone (for example 40 files
into `.claude/skills/designlang-tokens` and 27 into
`.claude/skills/code-review`). Installed together, the later package replaces
the earlier one. 3,575 packages carry files, mostly licence and attribution
notices, that the check keeps in the side folder rather than beside a
command or rule.

The recorded run took 4 minutes 13 seconds and at most 251 megabytes of
memory, while another full run and the test suites ran beside it; an earlier
run of the same scope alone took 2 minutes 56 seconds, about 28 milliseconds
a package. All twelve laboratory fixtures passed. The check changed once more
after that run, so the same command ran again at 21:25 UTC: every verdict,
fact and collision was identical, and it took 52.6 seconds and at most 253
megabytes on a quieter machine, about 8 milliseconds a package.

### What a real loader reported

The run with `--observe-listing` started at 21:32 UTC. OpenCode 1.18.32 listed
its skills with `opencode debug skill --pure`, which starts no model turn,
first in an empty project and then in a project that held the 2,575 skill
folders the check had written; 221 skill packages found their slot already
held by another package and were not listed as their own. The whole run took
5 minutes 32 seconds and at most 549 megabytes while the machine's load
average stood near 50; the two listings and the copy took 49 seconds.

| Check verdict | Written | Listed by OpenCode | Not listed |
|---|---|---|---|
| Activates | 2,249 | 2,249 | 0 |
| Refused | 326 | 324 | 2 |

| Refusal code | Listed | Not listed | Reading |
|---|---|---|---|
| `frontmatter_unterminated` | 0 | 2 | a load fault: the loader drops the skill, as the check does |
| `referenced_path_escapes` | 263 | 0 | a use fault: the skill loads, and the link fails only when a model follows it |
| `skill_name_not_native` | 48 | 0 | the loader lists names such as `backend/api-development`, `pinecone:cli` and `stitch::code-to-design` from a folder whose name differs, although its documentation says such a skill "won't load" |
| `authority_exceeds_declared_effects` | 10 | 0 | a declaration fault, which no loader sees |
| `referenced_file_missing` | 5 | 0 | a use fault |

What this settles for OpenCode: every skill the check passes is listed, so
the check made no false pass for this loader, and the check is stricter than
the loader for 324 skills. Those are faults a customer meets later, such as a
link that leads nowhere, or rules that other harnesses and the Agent Skills
specification state. No skill folder added a second listed skill, and every
listed entry inside the project belonged to a written package.

The baseline is not a constant. It held 11 entries: one built-in skill and the
person's own global skills. Two synchronized folders hold skills of the same
names, and between two listings OpenCode chose a different folder for three
of them, so the check explains the entries outside the project by name, not
by location; no entry outside the project was left unexplained. In the
earlier hand-run probe of the same listing, two global skills, `pdf` and
`skill-creator`, were listed from the project instead once served skills of
the same names were in place: in OpenCode, a served skill replaces the
customer's own global skill of the same name.

The numbers file is
[activation-summary.json](../../artifacts/failure-laboratory-2026-09-26/activation-summary.json);
the non-activating packages with their facts and digests are in
[activation-findings.jsonl](../../artifacts/failure-laboratory-2026-09-26/activation-findings.jsonl).

### Next opportunities

1. Run the check in the daily release before publication and hold refused
   packages back, as the prechecks do, starting in report-only mode.
2. Settle the unknown facts with the other harnesses' own loaders, a
   scripted Codex, Claude Code and Pi session in a sandbox, and give each
   harness its own verdict, since OpenCode lists skills that the Agent Skills
   name rule refuses.
3. Warn a customer before a served skill takes the name of one of their own
   global skills, which OpenCode then stops listing.
4. Make the import carry the files a command, subagent or plugin names, or
   refuse it at import, since most refusals are missing parts.
5. Derive declared effects from `tools` and `allowed-tools` at import, which
   removes the largest refusal code.
6. Resolve same-name collisions before publication by renaming the slot.

## Untouched ideas

- Property-based generation of packages to test the checker itself.
- Differential installation against the upstream source folder.
- A loader listing for commands and subagents, and for the laboratory
  fixtures, beside the skill listing.
- A laboratory fixture for each unknown fact, with an expected unresolved
  verdict.
- Running the review prechecks over the laboratory to measure what they miss.
- Sandboxed task trials with a no-extra-package baseline, from the data
  cleanup case study's finding that library items did not help a small model.
