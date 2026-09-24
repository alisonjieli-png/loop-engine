"""Tests for scripts/detect_text_tool_calls.py. Effects: starts the script as a subprocess with synthetic session logs on standard input; writes no files.

The log shapes follow the key structure of session files observed for Claude Code,
Codex and Pi, and the documented shapes of OpenAI-compatible chat, Gemini contents
and an OpenCode export. Every conversation here is synthetic.
"""
import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "detect_text_tool_calls.py"


def jsonl(rows):
    return "\n".join(json.dumps(row) for row in rows) + "\n"


def call_text(name, arguments, fence=False):
    body = json.dumps({"name": name, "arguments": arguments})
    return f"```json\n{body}\n```" if fence else body


PI_TEXT_ONLY = jsonl([
    {"type": "session", "version": 3, "id": "s1", "timestamp": "2026-09-22T23:40:00Z", "cwd": "/work/step"},
    {"type": "message", "id": "m1", "parentId": None, "message": {
        "role": "user", "content": [{"type": "text", "text": "Normalize the phone numbers in input.csv."}]}},
    {"type": "message", "id": "m2", "parentId": "m1", "message": {
        "role": "assistant", "content": [{"type": "text", "text": call_text("read", {"path": "input.csv"})}],
        "stopReason": "stop"}},
])

PI_MIXED = jsonl([
    {"type": "session", "version": 3, "id": "s2"},
    {"type": "message", "message": {"role": "user", "content": [{"type": "text", "text": "Clean input.csv."}]}},
    {"type": "message", "message": {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "I should read it first."},
        {"type": "toolCall", "id": "c1", "name": "read", "arguments": {"path": "input.csv"}}], "stopReason": "toolUse"}},
    {"type": "message", "message": {"role": "toolResult", "toolCallId": "c1", "toolName": "read",
                                    "content": [{"type": "text", "text": "phone"}], "isError": False}},
    {"type": "message", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "Now I write the file:\n" + call_text("write", {"path": "out.csv", "content": "x"}, True)}],
        "stopReason": "stop"}},
])

CLAUDE_CODE = jsonl([
    {"type": "user", "uuid": "u1", "sessionId": "s", "message": {"role": "user", "content": "Run the tests"}},
    {"type": "assistant", "uuid": "a1", "sessionId": "s", "message": {
        "id": "msg_1", "role": "assistant", "content": [{"type": "thinking", "thinking": "plan"}]}},
    {"type": "assistant", "uuid": "a2", "sessionId": "s", "message": {
        "id": "msg_1", "role": "assistant", "content": [
            {"type": "text", "text": "Config I will use: " + json.dumps({"name": "pytest", "args": ["-q"]})}]}},
    {"type": "assistant", "uuid": "a3", "sessionId": "s", "message": {
        "id": "msg_1", "role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "pytest -q"}}]}},
    {"type": "user", "uuid": "u2", "sessionId": "s", "message": {
        "role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "2 passed"}]}},
    {"type": "assistant", "uuid": "a4", "sessionId": "s", "message": {
        "id": "msg_2", "role": "assistant", "content": [
            {"type": "text", "text": "<tool_call>\n" + call_text("Bash", {"command": "git status"}) + "\n</tool_call>"}]}},
])

CODEX = jsonl([
    {"type": "session_meta", "payload": {"id": "x", "cwd": "/work"}},
    {"type": "response_item", "payload": {"type": "message", "role": "user",
                                          "content": [{"type": "input_text", "text": "Fix the failing test"}]}},
    {"type": "response_item", "payload": {"type": "reasoning", "summary": []}},
    {"type": "response_item", "payload": {"type": "message", "role": "assistant",
                                          "content": [{"type": "output_text", "text": "Running the tests first."}]}},
    {"type": "response_item", "payload": {"type": "function_call", "name": "shell", "call_id": "c1",
                                          "arguments": json.dumps({"command": ["pytest", "-q"]})}},
    {"type": "response_item", "payload": {"type": "function_call_output", "call_id": "c1", "output": "1 failed"}},
    {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [
        {"type": "output_text", "text": call_text("shell", {"command": ["pytest", "-x"]})}]}},
])

OPENAI = json.dumps({"model": "small-local-model", "tools": [
    {"type": "function", "function": {"name": "read_file", "parameters": {"type": "object"}}}], "messages": [
    {"role": "system", "content": "You can call tools."},
    {"role": "user", "content": "Read a.csv"},
    {"role": "assistant", "content": call_text("read_file", {"path": "a.csv"}, True)},
    {"role": "user", "content": "Use the tool."},
    {"role": "assistant", "content": None, "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "read_file", "arguments": "{\"path\": \"a.csv\"}"}}]}]})

OPENAI_EXCHANGES = jsonl([
    {"request": {"tools": [{"type": "function", "function": {"name": "write_file"}}], "messages": []},
     "response": {"choices": [{"message": {"role": "assistant", "content": [
         {"type": "text", "text": json.dumps([{"function": {"name": "write_file", "arguments": "{}"}}])}]}}]}},
    {"request": {"messages": []}, "response": {"choices": [{"message": {"role": "assistant", "content": None,
        "tool_calls": [{"type": "function", "function": {"name": "write_file", "arguments": "{}"}}]}}]}},
])

GEMINI = json.dumps([
    {"role": "user", "parts": [{"text": "Summarize data.csv"}]},
    {"role": "model", "parts": [{"functionCall": {"name": "read_file", "args": {"path": "data.csv"}}}]},
    {"role": "user", "parts": [{"functionResponse": {"name": "read_file", "response": {"content": "a,b"}}}]},
    {"role": "model", "parts": [{"text": "hidden plan", "thought": True},
                                {"text": json.dumps({"tool": "read_file", "parameters": {"path": "other.csv"}})}]},
])

OPENCODE = json.dumps({"info": {"id": "ses_1"}, "messages": [
    {"info": {"role": "user"}, "parts": [{"type": "text", "text": "Fix it"}]},
    {"info": {"role": "assistant"}, "parts": [
        {"type": "step-start"}, {"type": "text", "text": "Reading."},
        {"type": "tool", "tool": "read", "callID": "c1", "state": {}}, {"type": "step-finish"},
        {"type": "step-start"}, {"type": "text", "text": call_text("edit", {"path": "a.py"}, True)},
        {"type": "step-finish"}]}]})

GUARDED = json.dumps({"tools": ["write"], "turns": [
    {"role": "user", "text": "Write the config."},
    {"role": "assistant", "text": "Writing it.", "tool_calls": ["write"]},
    {"role": "tool", "text": "ok"},
    {"role": "assistant", "text": "Done. The file holds:\n```json\n" + json.dumps({"name": "shop", "version": "1.0"})
     + "\n```\nSome models wrap calls in a <tool_call> tag; this one did not."}]})

PROSE = json.dumps({"tools": ["read"], "turns": [
    {"role": "user", "text": "Open data.csv"},
    {"role": "assistant", "text": "I will use the read tool to open data.csv."}]})

# Pi JSON event output. The reply names a tool and then gives its arguments as JSON with
# typographic quotes, a shape a small local model produced in the September 22 study.
OPEN_QUOTE, CLOSE_QUOTE = "“", "”"
NAME_FIRST_REPLY = ("write {" + OPEN_QUOTE + "path" + CLOSE_QUOTE + ": " + OPEN_QUOTE + "output.csv" + CLOSE_QUOTE
                    + ", " + OPEN_QUOTE + "content" + CLOSE_QUOTE + ": " + OPEN_QUOTE + "id\\n" + CLOSE_QUOTE
                    + "}\n\nread {\"path\": \"input.csv\"}")
PI_EVENTS_TEXT_ONLY = jsonl([
    {"type": "message_end", "message": {"role": "user", "content": [
        {"type": "text", "text": "Clean input.csv into output.csv."}]}},
    {"type": "message_end", "message": {"role": "assistant", "content": [{"type": "text", "text": NAME_FIRST_REPLY}],
                                        "usage": {"input": 900, "output": 60}}},
])

PI_EVENTS_WORKING = jsonl([
    {"type": "message_end", "message": {"role": "user", "content": [{"type": "text", "text": "Count the rows."}]}},
    {"type": "message_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "Reading it."}]}},
    {"type": "tool_execution_start", "toolName": "read", "args": {"path": "input.csv"}},
    {"type": "tool_execution_end", "toolName": "read", "isError": False},
    {"type": "message_end", "message": {"role": "toolResult", "content": [{"type": "text", "text": "id\n1\n"}]}},
    {"type": "message_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "One row."}]}},
])

def stream(pieces, calls=()):
    """A captured OpenAI-compatible stream: one data: line per chunk, then [DONE]."""
    lines = [{"id": "chunk-1", "object": "chat.completion.chunk", "model": "small-local-model",
              "choices": [{"index": 0, "delta": {"role": "assistant", "content": piece}, "finish_reason": None}]}
             for piece in pieces]
    for name in calls:
        lines.append({"id": "chunk-1", "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {
            "tool_calls": [{"index": 0, "id": "c1", "type": "function",
                            "function": {"name": name, "arguments": "{\"path\": \"input.csv\"}"}}]},
            "finish_reason": None}]})
    lines.append({"id": "chunk-1", "object": "chat.completion.chunk",
                  "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls" if calls else "stop"}]})
    return "".join(f"data: {json.dumps(line)}\n\n" for line in lines) + "data: [DONE]\n\n"


# The reply arrives in small pieces that only form a call written as text once joined.
STREAM_TEXT_CALL = stream(["write", " {\"", "path", "\": \"", "output.csv", "\", \"", "content",
                           "\": \"", "phone\\n", "\"}"])
STREAM_REAL_CALL = stream(["Reading the file first."], calls=["read"])

CUT_OFF = json.dumps({"tools": ["bash"], "turns": [
    {"role": "user", "text": "Deduplicate the rows."},
    {"role": "assistant", "text": "```json\n{\"name\": \"bash\", \"arguments\": {\"command\": \"python3 - <<EOF\\nimport csv"}]})


class DetectTextToolCalls(unittest.TestCase):
    def run_script(self, data, *arguments):
        done = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *arguments],
                              input=data.encode("utf-8") if isinstance(data, str) else data,
                              capture_output=True, cwd=str(PAYLOAD), timeout=60)
        return done.returncode, json.loads(done.stdout.decode("utf-8"))

    def test_known_wrong_every_reply_is_a_text_call(self):
        code, result = self.run_script(PI_TEXT_ONLY)
        self.assertEqual((code, result["status"], result["format"]), (1, "text_calls_detected", "pi"))
        self.assertEqual((result["assistant_turns"], result["text_call_turns"], result["rate"]), (1, 1, 1.0))
        self.assertTrue(result["last_turn_flagged"])
        self.assertEqual(result["turns_with_structured_calls"], 0)
        self.assertEqual(result["flagged"][0]["tool"], "read")
        self.assertIsNone(result["flagged"][0]["known_tool"])
        self.assertNotIn("excerpt", result["flagged"][0])

    def test_pi_mixed_session_with_a_fenced_call(self):
        code, result = self.run_script(PI_MIXED)
        self.assertEqual((code, result["rate"]), (1, 0.5))
        flagged = result["flagged"][0]
        self.assertEqual((flagged["kind"], flagged["in_fence"], flagged["tool"]), ("json_text", True, "write"))
        self.assertEqual(flagged["argument_keys"], ["content", "path"])
        self.assertEqual(result["kinds"]["json_text_in_fence"], 1)
        self.assertNotIn("I should read it first", json.dumps(result))

    def test_claude_code_lines_of_one_reply_form_one_turn(self):
        code, result = self.run_script(CLAUDE_CODE)
        self.assertEqual(result["format"], "claude_code")
        self.assertEqual((result["assistant_turns"], result["turns_with_structured_calls"]), (2, 1))
        flagged = result["flagged"]
        self.assertEqual(len(flagged), 1)
        self.assertEqual((flagged[0]["kind"], flagged[0]["tool"], flagged[0]["known_tool"]), ("tagged_text", "Bash", True))
        self.assertEqual(flagged[0]["line"], 6)

    def test_codex_rollout(self):
        code, result = self.run_script(CODEX)
        self.assertEqual((code, result["format"], result["assistant_turns"]), (1, "codex", 2))
        self.assertEqual(result["flagged"][0]["tool"], "shell")

    def test_openai_chat_with_declared_tools(self):
        code, result = self.run_script(OPENAI)
        self.assertEqual((result["format"], result["assistant_turns"], result["text_call_turns"]), ("openai_chat", 2, 1))
        self.assertEqual(result["known_tools"], ["read_file"])
        self.assertTrue(result["flagged"][0]["known_tool"])

    def test_openai_request_and_response_lines(self):
        code, result = self.run_script(OPENAI_EXCHANGES)
        self.assertEqual((result["assistant_turns"], result["text_call_turns"]), (2, 1))
        self.assertEqual(result["flagged"][0]["tool"], "write_file")

    def test_gemini_contents_skip_thought_text(self):
        code, result = self.run_script(GEMINI)
        self.assertEqual((result["format"], result["assistant_turns"], result["text_call_turns"]), ("gemini", 2, 1))
        self.assertNotIn("hidden plan", json.dumps(result))

    def test_opencode_export_steps(self):
        code, result = self.run_script(OPENCODE)
        self.assertEqual((result["format"], result["assistant_turns"]), ("opencode", 2))
        self.assertEqual(result["flagged"][0]["tool"], "edit")

    def test_example_matches_the_example_output(self):
        code, result = self.run_script("", "examples/generic-session.json", "--root", ".")
        expected = json.loads((PAYLOAD / "examples" / "scan-output.json").read_text(encoding="utf-8"))
        self.assertEqual((code, result), (1, expected))

    def test_configuration_json_and_tag_names_in_prose_are_not_calls(self):
        code, result = self.run_script(GUARDED)
        self.assertEqual((code, result["status"], result["flagged"]), (0, "structured_calls_work", []))

    def test_prose_mentions_are_low_confidence(self):
        code, result = self.run_script(PROSE)
        self.assertEqual((code, result["status"], result["low_confidence_turns"]), (0, "no_tool_calls", 1))
        code, result = self.run_script(PROSE, "--count-low-confidence")
        self.assertEqual((code, result["rate"]), (1, 1.0))
        code, result = self.run_script(PROSE, "--expect-calls")
        self.assertEqual((code, result["status"]), (1, "no_structured_calls"))

    def test_pi_event_output_with_a_tool_name_before_json(self):
        code, result = self.run_script(PI_EVENTS_TEXT_ONLY, "--tool", "read", "--tool", "write", "--expect-calls")
        self.assertEqual((code, result["status"], result["format"]), (1, "text_calls_detected", "pi_events"))
        flagged = result["flagged"][0]
        self.assertEqual((flagged["kind"], flagged["confidence"], flagged["tool"]), ("name_then_json", "high", "write"))
        self.assertEqual((flagged["argument_keys"], flagged["known_tool"]), (["content", "path"], True))
        self.assertTrue(result["last_turn_flagged"])
        self.assertNotIn("output.csv", json.dumps(result))

    def test_unknown_name_before_json_is_low_confidence(self):
        code, result = self.run_script(PI_EVENTS_TEXT_ONLY)
        self.assertEqual((code, result["status"], result["rate"]), (0, "no_tool_calls", 0.0))
        self.assertEqual((result["flagged"][0]["kind"], result["flagged"][0]["counted"]),
                         ("unknown_name_then_json", False))
        code, result = self.run_script(PI_EVENTS_TEXT_ONLY, "--expect-calls")
        self.assertEqual((code, result["status"]), (1, "no_structured_calls"))

    def test_pi_event_output_credits_the_executed_tool(self):
        code, result = self.run_script(PI_EVENTS_WORKING)
        self.assertEqual((code, result["status"]), (0, "structured_calls_work"))
        self.assertEqual((result["assistant_turns"], result["turns_with_structured_calls"]), (2, 1))
        self.assertEqual(result["known_tools"], ["read"])

    def test_captured_stream_joins_pieces_before_scanning(self):
        code, result = self.run_script(STREAM_TEXT_CALL, "--tool", "write", "--tool", "read", "--expect-calls")
        self.assertEqual((code, result["status"], result["format"]), (1, "text_calls_detected", "openai_stream"))
        self.assertEqual(result["flagged"][0]["kind"], "name_then_json")
        self.assertEqual(result["flagged"][0]["argument_keys"], ["content", "path"])
        code, result = self.run_script(STREAM_REAL_CALL, "--expect-calls")
        self.assertEqual((code, result["status"], result["turns_with_structured_calls"]),
                         (0, "structured_calls_work", 1))

    def test_cut_off_call_json_is_still_counted(self):
        code, result = self.run_script(CUT_OFF)
        self.assertEqual((code, result["status"]), (1, "text_calls_detected"))
        self.assertEqual((result["flagged"][0]["kind"], result["flagged"][0]["tool"]), ("broken_json_text", "bash"))

    def test_threshold_and_excerpts(self):
        code, result = self.run_script(PI_MIXED, "--max-rate", "0.5", "--excerpts")
        self.assertEqual((code, result["status"]), (0, "structured_calls_work"))
        self.assertIn("write", result["flagged"][0]["excerpt"])

    def test_refused_inputs(self):
        cases = [("", ()), ("not json\nat all\n", ()), (PI_MIXED, ("--max-rate", "2")),
                 (json.dumps({"turns": []}), ()), ("", ("../session.jsonl",)), (b"\xff\xfe", ()),
                 (PI_MIXED, ("--max-bytes", "10"))]
        for data, arguments in cases:
            with self.subTest(arguments=arguments):
                code, result = self.run_script(data, *arguments)
                self.assertEqual((code, result["status"]), (2, "refused"))

    def test_reference_lists_every_log_shape_the_script_reads(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        formats = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                       and any(isinstance(target, ast.Name) and target.id == "FORMATS" for target in node.targets))
        reference = (PAYLOAD / "references" / "log-formats.md").read_text(encoding="utf-8")
        for name in formats:
            if name != "auto":
                with self.subTest(format=name):
                    self.assertIn(f"| `{name}` |", reference)

    def test_skill_file_names_this_script(self):
        text = (PAYLOAD / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("scripts/detect_text_tool_calls.py", text)
        self.assertIn("examples/generic-session.json", text)


if __name__ == "__main__":
    unittest.main()
