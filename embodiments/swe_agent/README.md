# SWE-agent attempted integration

The official SWE-agent 1.1.0 source is installed at
`/home/username/loop-engine/embodiments/swe_agent/runtime/SWE-agent-SWE-agent-0f3acaf`.
Its wheel-only dependency environment is
`/home/username/loop-engine/embodiments/swe_agent/runtime/.venv`.
It includes SWE-ReX 1.4.0. The official project is
[SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent), under MIT.
The maintainers recommend mini-SWE-agent for new work; these remain distinct
projects, not two configurations of one project.

The real CLI help and run-help commands succeeded. A configured noninteractive
run proceeded to environment startup, then failed because the isolated
namespace deliberately has no Docker socket. No container was started, no
image was downloaded, and no model request occurred. Native SWE-ReX execution
needs a separately qualified service boundary; mounting the host Docker socket
would not satisfy the current confinement contract.

Evidence is under
`/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y/remaining-recipes/swe_agent/`:
`help-02.json`, `run-help-01.json`, `startup-01/result.json` and
`dependency-install.json`. `help-01.json` used an incorrect source-directory
suffix in the launcher and is excluded as a SWE-agent failure. The corrected
run uses the source path printed above.

The installed model configuration supports an OpenAI-compatible API base.
That establishes a possible broker endpoint, not a working tool-free semantic
profile. No live Ollama Cloud call or full-engine solve is claimed.
