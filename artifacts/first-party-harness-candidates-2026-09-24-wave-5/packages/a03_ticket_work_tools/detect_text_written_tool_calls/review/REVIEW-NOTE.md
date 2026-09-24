# Review note: Detect tool calls written as plain text

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a03_ticket_work_tools, model family anthropic. This note is never delivered to a harness.

## Method

One script, `scripts/detect_text_tool_calls.py`, reads one saved session log and prints one `text_tool_call_scan/v1` JSON object. It first turns the log into assistant turns. It reads nine shapes: Claude Code JSON Lines (the lines of one reply share `message.id`), Codex rollout JSON Lines, Pi session JSON Lines, Pi JSON event output, an OpenCode export, OpenAI-compatible chat JSON or JSON Lines (including lines that hold a `request` and a `response`), a captured OpenAI-compatible stream of `data:` lines (the pieces of one reply are joined before scanning), Gemini contents, and a generic `{"turns": [...]}` document. A turn that made a structured call is counted and not scanned. The visible text of every other turn is scanned; hidden reasoning is skipped. The strongest sign decides the kind of a finding: a tagged call, JSON with a tool name key and an argument key (inside a code fence or not), a known tool name followed by a JSON object, or the start of call-shaped JSON that does not parse because the reply was cut off. These count in `rate`. A tool named in prose, or an unknown name before JSON, is low confidence and counts only with `--count-low-confidence`. Known tool names come from the log and from `--tool`. The status is `text_calls_detected` when the rate is above `--max-rate` (default 0), `no_structured_calls` when `--expect-calls` is given and no turn made a structured call, `no_tool_calls` without that option, and `structured_calls_work` otherwise. By default the output names tools and argument keys and quotes no text from the log. The model only decides whether to continue; the counting is in the script.

## Authoring basis and sources

Original code and text written for this wave. No outside code or documentation text was copied. The Claude Code, Codex and Pi shapes were written from the key structure of session files on this machine. The Pi event, OpenAI-compatible, Gemini and OpenCode shapes were written from their documented or stored record shapes, as `references/log-formats.md` says for each; a saved OpenCode export and a saved Gemini CLI chat were not observed. Sources cited in the manifest: `catalogue_packages.py` for the package format; the case-study report `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md`, which records that the local model `qwen2.5-coder:7b` wrote tool calls as plain text and scored 0 in its steps; that study's recorded request and response bodies, `trials/request-bodies.tar.gz`, used for the check below; and `docs/verification/HARNESS-MODEL-USE-ONE-CALL-2026-09-22.md`, which records the same model writing an invented tool call as text under Claude Code and OpenCode.

Evidence gathered on September 24, 2026. First, the recorded bodies of the case study, byte for byte the file in the repository, 225 responses. Per response, 34 of the 37 small-model responses were flagged (21 as JSON, 10 as JSON in a code fence, 3 as cut-off JSON). The other 3 held no call of any kind: the text "DONE", once with a claim that an output file had been written. Each of those 3 steps made exactly one request, so the recordings differ from the report's statement that all 37 steps wrote their first tool call as text: 34 did, and 3 replied without any call. The outcome was the same, a step that ended with no output. This difference is recorded here as a disputed fact for the report's owner and is not corrected by this package. None of the 188 responses of the two cloud models was flagged. Per step, with the responses of each trial joined into one stream and `--expect-calls` given, all 37 small-model steps exited 1 (34 `text_calls_detected`, 3 `no_structured_calls`) and all 37 cloud-model steps exited 0 with `structured_calls_work`. One probe request that offered no tools exited 1 with `no_structured_calls`, as intended. Second, the newest 25 session files of each harness on this machine, counting only: Claude Code 15,485 assistant turns (14,722 with structured calls), Codex 4,708 turns (4,630 with structured calls) and Pi 21 turns in 21 files (no calls). No turn was flagged. All logs were read in about 24 seconds. These are observations on one machine, not a measured accuracy.

## Inputs and outputs

Input: one log file inside `--root`, or standard input. Options: `--format` (auto or one of the nine shapes), `--tool NAME` (repeatable), `--max-rate`, `--count-low-confidence`, `--expect-calls`, `--excerpts` (up to 160 characters per finding, off by default) and `--max-bytes` (default 64 MiB, at most 512 MiB). Output: `status`, `format`, `assistant_turns`, `turns_with_structured_calls`, `text_call_turns`, `rate`, `max_rate`, `kinds`, `low_confidence_turns`, `last_turn_flagged`, `known_tools`, `flagged` (kind, confidence, fence, tool, argument keys, known tool, turn, line, counted), `omitted_flagged` and `notes`. Exit 0 when the rate is at or below `--max-rate` and, with `--expect-calls`, a structured call exists; 1 otherwise; 2 for refused input, such as a path with `..`, a path that leaves the root, text that is not UTF-8 or a log with no assistant turn.

## Effects

Declared effects: `reads_fs` and `spawns_process`. The script reads standard input or one regular file below `--root`; it refuses `..` and paths that leave the root directly or through a symbolic link, and opens the file with no-follow and non-blocking flags before checking its type. It writes nothing, makes no network call and calls no model. The skill tells the reader to run the script, which starts a process. The tests pass synthetic logs on standard input, read this package's own files and write nothing. A session log can hold private text; the default output quotes none of it, and the skill tells the model not to open the log itself or to search private folders for one.

## Closest existing items

The scout found no existing item for this task; the roadmap evidence of September 23 records the failure mode. The nearest wave 5 packages:

- `night_preflight` (a06, command file): a go or no-go ritual before an unattended run whose first check is that the model makes structured tool calls. It can run this script on a probe step's log; this package is only the log scan, with exact counts.
- `log_tool_activity` (a04, hook): appends one line per tool call while a step runs. This package reads a finished log afterwards and looks at the turns that made no call at all, which a hook never sees.
- `test_run_summarizer` (a05, subagent) and `extract_test_failures` (a03): both summarize test output, not model behavior.

## Positive example

`examples/generic-session.json` holds two assistant turns: one made a structured `read` call; the other wrote `{"name": "write", "arguments": {...}}` inside a code fence. The script returns `text_calls_detected`, `rate` 0.5, one `json_text` finding in a fence for tool `write` with argument keys `content` and `path`, and `last_turn_flagged` true. The full result is `examples/scan-output.json`, and a test compares the script output with it.

## Known-wrong example

A log in which every assistant reply is a tool call written as JSON text, while no output file exists. Counting each reply as a finished step is wrong. The test `test_known_wrong_every_reply_is_a_text_call` requires `text_calls_detected`, exit 1 and rate 1.0 for a Pi session whose only reply is such text, and the case-study check above is the same case on real recordings. The opposite error is guarded too: `test_configuration_json_and_tag_names_in_prose_are_not_calls` requires that JSON configuration shown after a real call, and a mention of the `<tool_call>` tag in prose, are not flagged.

## Harness placement and verification state

The folder is copied with exact bytes to `.claude/skills/detect-text-written-tool-calls/` (Claude Code), `.agents/skills/detect-text-written-tool-calls/` (Codex), `.opencode/skills/detect-text-written-tool-calls/` (OpenCode), `.pi/skills/detect-text-written-tool-calls/` (Pi) and `.gemini/skills/detect-text-written-tool-calls/` (Gemini CLI). The first four roots are recorded as observed in the wave specification; the Gemini CLI root is documented but not observed, so Gemini CLI is listed in `unverified_targets`. Native discovery of this package was not probed. That each harness tells the model where the skill folder is, so it can replace `SKILL_FOLDER`, is unverified. The log folders listed in the reference file were seen on one Linux machine; OpenCode's session storage and Gemini CLI's saved chats are unverified.

## Customer requests

- "Before I leave my local model running tonight, check whether it really calls tools in this harness."
- "My Ollama model keeps printing JSON instead of running the tool. How often did that happen in this session?"
- "Scan last night's agent logs and tell me which runs stalled because the model wrote its calls as text."

## Limits

- Detection uses patterns on visible text. A reply that describes a call in free prose without a tool name, or in a shape not listed, is missed. A reply that shows call-shaped JSON on purpose, for example while explaining an interface, is flagged. No such false flag occurred in the local logs above, but those are one machine's sessions.
- The rate counts turns, not steps, so one bad turn in a long step gives a low rate; the default `--max-rate` of 0 treats any counted finding as a failure.
- Only the first 256 KiB of each turn is scanned, and a note says so.
- Log shapes change between harness versions. The reference file names the versions whose files were read.
- A turn with no call and no call-shaped text, such as "DONE", is not a call written as text. Only `--expect-calls` catches a log with no structured call at all, which is why the skill's first action uses it.

## Pre-check history

The earlier sessions wrote the payload but no `package.json` and no review note, and ran no check. A later session unpacked the case-study bodies and wrote validation drivers but recorded no result. The September 24 session reran those drivers and the local-log driver unchanged, and recorded the counts above. It also rewrote `SKILL.md` for a clearer first action, added tests for the captured stream shape and for the reference file listing every shape the script reads, wrote the manifest and this note, set every payload file to mode 0644 (they were 0664), and logged every run, failures included, in `packages/detect_text_written_tool_calls/PRECHECKS.txt` beside the package folder. Every `check_package.py check` report is kept in `review/`.
