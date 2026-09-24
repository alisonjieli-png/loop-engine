# Cap tool calls at a declared budget

## What is active

This step has a fixed number of tool calls, set in `.baltor/step/cap-tool-call-budget.json` as `max_tool_calls`. A hook counts every tool call. When the count reaches the limit, the hook refuses further calls. Only reads and writes of the handoff file named there as `handoff_path` still work, a few times.

Plan for the limit. Prefer one larger call to many small ones, and keep a few calls for your handoff. Each refused call is counted too, and after a few of them the hook may end the session.

## If something is refused

1. Stop new work at once. Do not retry the refused call.
2. Write the handoff file in one write: what is done, what is not done, and the exact next action.
3. Finish.
4. If the handoff write is also refused, finish and put the same three items in your final message.
