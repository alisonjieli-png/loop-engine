# Review note: Changelog writer

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a05_focused_subagents, model family anthropic, repaired on September 24, 2026 by the a05 repairer of the same family after the a05 critic's review. This note is never delivered to a customer.

## Method

A subagent definition for a narrow writer that runs after a fix has passed its checks. Its first action looks for news fragment setups: `towncrier.toml`, `.changeset/config.json`, the folders `changelog.d`, `newsfragments` and `releasenotes/notes`, and `towncrier` in `pyproject.toml`. Any of them means a tool builds the changelog from fragment files, so the helper refuses instead of editing the generated file; it also refuses a changelog that says it is generated. Otherwise it searches the changelog with line numbers for Unreleased and version headings and reads about 30 lines around the Unreleased heading or the newest version heading, which in a changelog ordered oldest first is the last one. It adds one entry of one to three lines under the Unreleased heading, adding that heading at the same level where the next version heading would go when there is none, searches the documentation pages for the passage that describes the old behavior, edits only that passage, and rereads both places.

It returns one JSON object: the changelog path, the section heading it wrote under, the line and the entry, and either the updated page with its line and the replaced text (`before`) or `no_passage_found`. The changed files are exactly the changelog and, when updated, that page; the first draft's separate `files_changed` list was removed, so the reply can no longer name a file that disagrees with the rest of it. It refuses without evidence that names a command with exit status 0.

## Authoring basis and sources

Original text written for this wave from ordinary release practice. No outside text was copied. Sources at revision a1fc7432:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the file contract this package follows.
- `docs/guides/native-client-material-loading.md`: records the OpenCode project agent folder `.opencode/agents/<name>.md` as documented and observed with version 1.18.31.

Harness facts were read from the installed Claude Code 2.1.281 and OpenCode 1.18.32 program text, which was not run, and from GitHub's custom agents documentation, read on September 24, 2026 (docs.github.com/en/copilot/reference/custom-agents-configuration).

## Inputs and outputs

Input: a short summary of what changed for users, the passing check command with exit status 0, the changelog path, the documentation page if known, and an optional ticket key. Output: one JSON object matching `contracts/reply.schema.json`, or `{"refused": "..."}`. During the repair the schema was checked with the `jsonschema` library: the body example, the no-passage form, a refusal, a bracketed `[Unreleased]` heading and a reStructuredText page validate, and ten known-wrong replies are rejected, among them the old `files_changed` field, an entry under the section `2.3.0`, an updated passage without `before`, the no-passage form naming a page, a changelog or page inside a folder whose name starts with a dot, `AGENTS.md`, a nested `CLAUDE.md` and a Python file as the page. Each of seven schema rules, removed on its own, let at least one of those replies through.

## Effects

`reads_fs` and `writes_fs`. The helper reads the changelog, documentation pages and a few setup files, and edits at most two existing files. It runs no command and uses no network.

What each harness enforces, corrected in the repair. The first draft said that Claude Code's Edit tool cannot create files. That was wrong: in the installed Claude Code 2.1.281 program text, Edit accepts an empty `old_string` for a file that does not exist, passes validation and is labelled Create, so Edit can create a new changelog or page. In the installed OpenCode 1.18.32 program text, the `write` and `apply_patch` tools ask the same `edit` permission as `edit`, so an allowed pattern also permits creating, overwriting, moving or deleting matching files; for a move, `apply_patch` checks the edit permission against the old path only, so a deny rule does not stop a move into a denied folder (read, not run). GitHub documents that the Copilot `edit` alias covers Write as well as Edit. So "never create a file" and "edit only these two files" are instructions in all three harnesses. The OpenCode rules narrow which paths may change; nothing in the package enforces the rest. Real limits need a settings rule that denies edits outside documentation paths, a write guard hook such as wave 5 `guard_workspace_file_writes` (a04) with protected paths, and a diff check afterwards such as wave 5 `check_diff_allowed_paths` (a12).

The OpenCode rules, last match winning: deny everything, allow `*.md`, `*.rst` and changelog names (`*CHANGELOG`, `*CHANGELOG.*`, `*CHANGES`, `*CHANGES.*`, `*changelog.*`), then deny any path that starts with a dot or passes through a folder whose name starts with a dot (`.*` and `*/.*`), and deny `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`, `GEMINI.md` and `SKILL.md` anywhere. With a copy of the matcher read from that program text (special characters escaped, `*` for any characters including `/`, case-sensitive, anchored), 24 sample paths gave the intended decision; the first draft's rules allowed `.agents/skills/a/references/b.md`, `.clinerules/rules.md`, `.gemini/styleguide.md`, `.pi/notes.md`, `CLAUDE.local.md`, `src/CHANGELOG_parser.py` and `docs/.drafts/uploads.md`, and the new rules deny all seven.

## Closest existing items

- No served, starter or first-party candidate writes a changelog entry; the scout inventory search for changelog, release note and documentation update found none.
- Starter `run_a_release_check_list_before_deploying` mentions release notes as a check before deploying. It does not write them.
- Wave 5 `ticket_fix_verification_packet` (a09) writes a change summary and a proposed commit message, and `write_step_handoff` (a06) writes a handoff. This helper writes the customer-facing record and the one documentation passage, and nothing else.
- Wave 5 `check_diff_allowed_paths` (a12) refuses a diff outside allowed paths, and `guard_workspace_file_writes` (a04) refuses writes to protected paths. They can enforce this helper's limits; this package does not restate them. Wave 5 `generated_files_stay_unedited` (a08) is a rule against editing generated output, which covers a changelog that a tool builds.

## Positive example

Summary: "Upload retries now stop after 5 attempts." Evidence: `python3 -m pytest -q tests/test_uploads.py`, exit status 0. No fragment setup exists. The helper adds `- Upload retries now stop after 5 attempts (TICKET-12).` under `## Unreleased` in `CHANGELOG.md`, changes the sentence in `docs/uploads.md` that said uploads retry until they succeed, and returns the section `Unreleased`, both lines and the replaced sentence.

## Known-wrong example

The changelog has no unreleased section, and a small model appends the entry under the newest released version, `## 2.3.0`. That rewrites a published release. The body tells it to add an Unreleased heading, and the schema rejects a reply whose `section` is `2.3.0`. A second case: no page mentions retries, and the model writes a new `docs/retries.md`. The body forbids a new file and asks for `no_passage_found`; an updated page must carry the replaced text, which a caller can look for in the previous version of the page, and a new file shows as added in a diff check. A third: the repository keeps `newsfragments/` for towncrier, and the model edits `CHANGELOG.md` by hand; the first action finds the folder and refuses.

## Harness placement and verification state

- Claude Code: variant to `.claude/agents/changelog-writer.md`. Documented folder; keys checked against the agent parser in the installed Claude Code 2.1.281 program text, read and not run. Discovery of this file and the effect of the tools line were not observed. This variant does not set `omitClaudeMd`, unlike the four read-only a05 helpers: a writer should see project rules in CLAUDE.md, for example a rule to add news fragments instead of editing the changelog.
- OpenCode: variant to `.opencode/agents/changelog-writer.md`. The wave specification names `.opencode/agent/` as unverified; the plural folder is recorded as documented and observed in the guide above, and the installed OpenCode program text (it embeds version 1.18.32) scans both. The rule behavior above was read and simulated, not run. Unverified.
- Copilot: variant to `.github/agents/changelog-writer.agent.md`. GitHub documents the path and the `read`, `search` and `edit` aliases; `edit` includes Write, so Copilot can create files, and there is no path limit in this variant. Discovery was not observed. Unverified.
- `contracts/reply.schema.json` and `LICENSE` go under `.baltor/changelog-writer/`.

## Customer requests

- "The fix passed, add a changelog line and update the docs that describe it."
- "Write the release note for this bug fix, docs only."
- "Update CHANGELOG.md for ticket 12 without touching any code."

## Limits

The helper trusts the evidence it is given and does not rerun checks; it can only refuse evidence that names no command or a status other than 0, and it cannot judge whether the evidence belongs to the summarized change. It finds the passage by words from the summary, so a page that describes the behavior in other words may be missed and reported as not found. The fragment check covers towncrier, changesets and reno in their default places; other generators are caught only when the changelog says it is generated. Changelog formats vary; the helper copies the format it reads. The purpose no longer says "limited to documentation paths", because only OpenCode enforces a path limit. The first body draft had 379 words and was shortened to 345 words before the first package check.

The September 24 repair answered the a05 critic: the false claim about Claude Code's Edit tool and the OpenCode write tools was corrected, the fragment check and refusal were added, the OpenCode denials now cover every folder whose name starts with a dot and more instruction file names, the rule about a summary that disagrees with the evidence was replaced by the checkable rule above, the schema now rejects the critic's two inconsistent replies, and the first read finds the newest section of a changelog ordered oldest first. The body is 349 words after the repair.
