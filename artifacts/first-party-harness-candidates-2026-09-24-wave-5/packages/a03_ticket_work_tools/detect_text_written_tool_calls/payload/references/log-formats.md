# Session log shapes the script reads

Read this file only when `--format auto` picks the wrong shape or refuses the log. Pass `--format NAME` to choose a shape yourself.

## Shapes

| `--format` | What the log looks like | Structured call | Visible text | Basis |
|---|---|---|---|---|
| `claude_code` | JSON Lines; lines with `type` `assistant` or `user` and a `message` object. One reply can span several lines with the same `message.id`. | `tool_use` block | `text` blocks; `thinking` is skipped | Read without error from Claude Code 2.1.280 session files on one machine |
| `codex` | JSON Lines; lines with `type` `response_item` and a `payload` object | `function_call`, `custom_tool_call`, `local_shell_call` and similar payloads | `output_text` parts of assistant `message` payloads; `reasoning` is skipped | Read without error from Codex 0.155.1 rollout files on one machine |
| `pi` | JSON Lines session file; lines with `type` `message` and a `message` object with `role` | `toolCall` block | `text` blocks; `thinking` is skipped | Read without error from Pi session files (session format 3) on one machine |
| `pi_events` | JSON Lines printed by Pi in JSON mode; whole messages arrive in `message_end` events | `toolCall` block, or a `tool_execution_start` event right after the reply | `text` blocks | The event fields a repository test runner read from Pi 0.73.1; a full event log was not replayed here |
| `openai_chat` | A request or response body, a list of messages, or JSON Lines of those, including lines with `request` and `response` objects | `tool_calls` or `function_call` on an assistant message | `content` as a string or text parts | Documented message shape; request bodies also give the declared tool names |
| `openai_stream` | Captured `data:` lines of a streamed response | `tool_calls` in the deltas | `content` in the deltas | Documented stream shape; not observed here |
| `gemini` | A list of contents with `role` `user` or `model` and `parts`, or an object with `contents` or `history` | `functionCall` part | `text` parts; parts marked `thought` are skipped | Documented contents shape; a saved Gemini CLI chat file was not observed |
| `opencode` | One object with `messages`, each with `info` and `parts` | `tool` part | `text` parts; each `step-start` begins a new turn | Built from OpenCode message and part records; an export file was not observed |
| `generic` | `{"tools": [...], "turns": [{"role": ..., "text": ..., "tool_calls": [...]}]}` | names in `tool_calls` | `text` | Defined by this package; convert any other log to it |

## Where harnesses keep their logs

These folders were seen on one Linux machine. They can differ by version and setting. Read a log only when the host or the task names it.

- Claude Code: `~/.claude/projects/<folder-name>/<session>.jsonl`
- Codex: `~/.codex/sessions/<year>/<month>/<day>/rollout-<time>-<id>.jsonl`
- Pi: `~/.pi/agent/sessions/<folder-name>/<time>_<id>.jsonl`; Pi in JSON mode prints events on standard output instead, and the host must save them
- OpenCode keeps sessions in a database, not in files; an export is needed. Unverified.
- Gemini CLI: unverified.

## What counts as a call written as text

A turn counts only when it made no structured call. The strongest sign in its visible text decides the kind. Typographic double quotes are read as plain quotes first.

High confidence, counted in `rate`:

- `json_text`: JSON with a tool name key (`name`, `tool`, `function_name`, `action`) and an argument key (`arguments`, `parameters`, `args`, `input`, `action_input`), or a `function` object with a `name`; inside a code fence or not.
- `broken_json_text`: the start of such JSON, `{"name": "...", "arguments":`, when the rest does not parse, for example because the reply was cut off.
- `tagged_text`: a `<tool_call>`, `<function_call>` or `<tool_use>` tag, or a `[TOOL_CALLS]` or `<|python_tag|>` marker, followed by such JSON; or a `<function=NAME>` or `<invoke name="NAME">` tag.
- `name_then_json`: a line that starts with a known tool name followed by a JSON object, such as `write {"path": "out.csv"}`.

Low confidence, left out of `rate` unless `--count-low-confidence` is given:

- `unknown_name_then_json`: the same line shape with a name that is not a known tool.
- `named_in_prose`: a known tool named in prose, such as "I will use the read tool", or written like a function call.

Known tools come from the log (declared tools and structured calls) and from each `--tool NAME`.
