# Trae Agent adapter experiment

Trae Agent completed a scripted text roundtrip through an explicit modified
SDK profile. The profile calls the upstream `Agent.run()` and `execute_task()`
loop with `tool_names=[]`. It replaces the task-completion hook with an exact
text-submission condition: nonempty text, a normal stop, and no tool calls.
It supplies a text-only system prompt and returns a versioned result. The
upstream model client, step execution, trajectory recording, and tool executor
remain in use. Injected native tool requests and responses were refused.

The stock CLI does not meet this text-only contract. A task configured with `tools: []`
sent five native tool declarations. The broker refused that request before
calling a model. The CLI exited with code 0 while its execution summary said
the task failed. A successful process exit is not accepted output.

The [official repository](https://github.com/bytedance/trae-agent) is pinned at
`e839e559ac61bdd0e057c375dd1dee391fee797d`. Its Python package reports version
0.1.0 and its main license is MIT. The source includes separately attributed
Apache-2.0 material. The private runtime uses Python 3.12.13.

The initial base installation could not import the CLI because `docker` and
`pexpect` were missing. Installing those declared optional dependencies fixed
startup. Both the failed attempt and the successful startup are saved.

The attempted configuration disabled Lakeview and MCP, selected one step,
and used the upstream OpenRouter-compatible client with a private loopback
URL. This provider label selected a client protocol; no OpenRouter provider
was called. `TraeAgent.new_task()` replaces an empty tool list with its default
tools when the CLI supplies no explicit `tool_names`. Completion also requires
the native `task_done` protocol. The stock CLI remains unqualified; the named
`trae_text_submission/v1` SDK profile is qualified only by offline fixtures.

The [fixture records](../../artifacts/harness-expansion-20260909-DNMQ3Y/lightweight-recipes/)
preserve installation output, actual requests, refusals, and CLI output. The
first task probe also tested a very wide terminal setting; Rich expanded its
decorative borders to that width. That setting was removed from the proposed
Trae recipe, and the large original log remains saved.

No real model was called. No task completion, provider integration, or
full-system benchmark result is claimed.
