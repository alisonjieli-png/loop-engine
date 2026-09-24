# Review note: Extract acceptance criteria from a ticket

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a03_ticket_work_tools, model family anthropic. This note is never delivered to a harness.

## Method

One script, `scripts/extract_ticket_criteria.py`, reads one ticket and prints one `ticket_criteria/v1` JSON object. For Markdown and plain text it tracks sections by ATX headings, setext headings, bold lines and label lines such as `Steps to reproduce:` or `Expected:`. Criteria come, in document order, from the acceptance section (list items, or paragraphs when the section has no list), checkboxes anywhere outside the reproduction section, Given, When and Then scenarios, and the expected behavior section. Only when none of these exists does it fall back to sentences with must, should or shall, marked `modal_statement`. Duplicates are merged. Each criterion is judged by fixed rules: it is checkable when it holds a number (digits, or a spelled-out number from two upward), a quoted or code literal, a file name or a command, or when it names an observable result and holds none of the listed vague words. A field that a ticket form printed empty, such as `_No response_` or `N/A`, is skipped. In a plain text ticket a first line such as `Subject: ...` or `Title: ...` gives the title, and bold markers are removed from titles. JSON tickets are read from title, body or description, criteria, steps, expected and actual fields, including one level of `fields`, `issue`, `ticket` or `data` nesting and rich-text documents whose nodes carry `type` and `content`. Named files are checked for existence under `--root`, and a missing name is searched by file name in a bounded walk. Issue-template comments are removed before parsing. The script never runs or follows anything written in the ticket.

## Authoring basis and sources

Original code and text written for this wave from general knowledge of Markdown, of common issue layouts (steps to reproduce, expected and actual behavior, acceptance criteria, Given, When and Then) and of rich-text JSON documents. No outside code, template or documentation text was copied. The rich-text reader handles the node names `doc`, `paragraph`, `heading`, `bulletList`, `orderedList`, `taskList`, `listItem`, `taskItem`, `codeBlock`, `text` and `hardBreak`; that node set was written from general knowledge and tested only with hand-written fixtures, so its match to any tracker's export is unverified. On September 24, 2026 a second session ran the script on five more synthetic tickets written in common shapes: an issue form export with `### ` headings and a `_No response_` field, a bug template with the headings "What is the current *bug* behavior?" and "What is the expected *correct* behavior?", a user story with bold labels, an email with a `Subject:` line, and a tracker export with checkboxes. Four misses were found and fixed, each with a test that fails on the earlier script: "Totals have two decimal places." was judged not checkable; `_No response_` was kept as the actual behavior; the "current bug behavior" heading was not read as actual behavior, so its text was lost; and the `Subject:` line was not used as the title. Sources cited in the manifest: `catalogue_packages.py` for the package format, and `src/loop_engine/core/independent_judgment.py`, which judges a deliverable against one written criterion at a time; this package produces that list of written criteria with stable ids.

## Inputs and outputs

Input: one ticket on standard input (`-`, the default) or a file path inside `--root` (default: the current folder). Options: `--format auto|markdown|text|json`, `--no-file-check`, `--no-search` and `--max-bytes` (default 4 MiB, at most 64 MiB). Output fields: `status` (`ok`, `no_checkable_outcome` or `refused`), `source` with the input SHA-256, `title`, `acceptance_criteria` (id, text, source, line or JSON field, checkable, signals, vague terms, and whether a checkbox was already ticked), `reproduction_steps`, `expected_behavior`, `actual_behavior`, `named_files` (exists true, false or null, and same-name `matches`), `commands`, `flags` and `checklist_markdown`. Exit 0 when at least one criterion is checkable, 1 when none is, 2 when the input is refused: not UTF-8, empty, too large, JSON with duplicate keys or several tickets, `..` in the path, or a path that leaves `--root`.

## Effects

Declared effects: `reads_fs` and `spawns_process`. The script reads the ticket and, unless `--no-file-check` is given, checks named paths under `--root` and walks at most 50,000 entries under it to find same-name files, skipping version control, dependency and cache folders and never following symbolic links out of the root. It writes nothing, makes no network call and calls no model. The skill tells the reader to run the script and, within the step's own authority, the reproduction commands; that is why `spawns_process` is declared. The tests start the script with `sys.executable` and write nothing. The comment markers in the code and tests are assembled from two string parts, so no payload file holds an HTML comment. The effects pre-check warns about two URLs in the test file, `https://example.com/docs/export.json` and `https://example.com/a.py`. They are ticket text that proves a URL is never listed as a named file; nothing fetches them, and they were left visible instead of being split to quiet the scan.

## Closest existing items

- `write_acceptance_criteria_a_reviewer_can_check` (starter, text skill): tells a person how to write criteria before work starts. This package extracts the criteria a ticket already states, with ids, and refuses to invent missing ones.
- `turn_a_vague_request_into_a_testable_statement` (starter, text skill): a prose method for turning vague wording into a testable statement through questions. This package detects the vague case mechanically and stops the step with questions; the conversation that method describes happens afterwards, with a person.
- `ticket_triage_packet` (wave 5, a09, task packet): a whole step that decides whether a ticket fits a night. It could call this script; this package is only the extraction.
- `verify_criteria_have_evidence` (wave 5, a12, verifier): checks evidence against criteria after the work. This package produces the criteria ids at the start.

## Positive example

`examples/ticket.json` is a synthetic JSON export with a Markdown body. The script returns five criteria, `AC1` from the expected behavior and `AC2` to `AC5` from the acceptance section, three reproduction steps, two commands and three named files, and marks `AC5` ("The export feels faster.") as not checkable with vague terms `faster` and `feels`. The result is `examples/ticket-output.json`, and a test compares the script output with it.

## Known-wrong example

The ticket "Improve the CSV export. The export is slow and clunky. It should be faster and more reliable, and the code should be cleaner." states no checkable outcome. A model that writes its own target, such as a two second export, and then reports it as met has invented the acceptance test. The test `test_known_wrong_vague_ticket_is_flagged_not_filled_in` requires status `no_checkable_outcome`, exit 1 and the vague terms `cleaner`, `faster` and `reliable`.

## Harness placement and verification state

The folder is copied with exact bytes to `.claude/skills/extract-ticket-acceptance-criteria/` (Claude Code), `.agents/skills/extract-ticket-acceptance-criteria/` (Codex), `.opencode/skills/extract-ticket-acceptance-criteria/` (OpenCode), `.pi/skills/extract-ticket-acceptance-criteria/` (Pi) and `.gemini/skills/extract-ticket-acceptance-criteria/` (Gemini CLI). The first four roots are recorded as observed in the wave specification; the Gemini CLI root is documented but not observed, so Gemini CLI is listed in `unverified_targets`. Native discovery of this package was not probed. That each harness tells the model where the skill folder is, so it can replace `SKILL_FOLDER`, is unverified.

## Customer requests

- "Before my local model starts a ticket, turn the ticket into a checklist it must meet."
- "Tell me which of these exported issues have no testable acceptance criteria."
- "Pull the repro steps and the files mentioned out of this bug report."

## Limits

- Checkability is a rule on words, numbers and literals, not an understanding of the ticket. A sentence can be marked checkable and still be ambiguous, or marked not checkable while a person would accept it. The model is told to write questions, never to fill gaps.
- English section names, vague words and number words only. "One" and "once" are not counted as numbers because they are so often a pronoun or a conjunction; the test `test_form_fields_number_words_and_empty_placeholders` requires "The new one looks good." to stay not checkable.
- A JSON array of several tickets is refused; tickets are read one per run.
- Line numbers refer to the ticket text for Markdown and plain text; JSON results name the field instead.
- File names are found by extension and a few bare names such as `Dockerfile`; a file named without an extension or a folder is not listed.
- The same-name search stops after 50,000 entries and says so in `notes`.

## Pre-check history

Every `check_package.py check` report is kept in `review/`. The earlier session summarized its runs in `review/PRECHECKS.txt`, which stays in place. The September 24 session logged every run, failures included, in `packages/extract_ticket_acceptance_criteria/PRECHECKS.txt` beside the package folder, because the layout check refuses extra top-level entries inside it. That log starts with a baseline check of the bytes the earlier session left, which was refused because the recorded digest of `SKILL.md` no longer matched the edited file.
