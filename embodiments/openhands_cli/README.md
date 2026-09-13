# OpenHands CLI attempted integration

The official OpenHands CLI 1.16.0 release executable is installed at
`/home/username/loop-engine/embodiments/openhands_cli/runtime/openhands`.
The project is [OpenHands/OpenHands-CLI](https://github.com/OpenHands/OpenHands-CLI),
under MIT. Its current README says it is no longer actively maintained and
recommends Agent Canvas. The CLI is distinct from that control-center project.

Actual help and version commands succeeded in a private network namespace.
The release binary reports OpenHands SDK 1.21.0 in its startup banner. Current
source metadata declares a newer SDK; those are not interchangeable evidence.

The installed headless command reached the local fixture broker through
`LLM_BASE_URL` and `--override-with-envs`. It included native tool schemas,
which the broker refused. The command returned exit code zero despite that
refusal. It is not a successful semantic invocation. Headless mode also
automatically approves native actions; an approval flag is not tool closure.

Records are under
`/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y/remaining-recipes/openhands_cli/`:
`help-01.json`, `version-01.json` and `text-01/result.json`.
The last record has one refused local POST and zero live calls. No candidate
was accepted. All source identities and download hashes are retained there.

An OpenAI-compatible endpoint is supported, but a tool-free CLI profile is not
qualified. A separately pinned SDK profile may be feasible; it would need its
own native-tool, discovery, lifecycle and semantic-packet checks. Do not expose
the host Docker socket or credentials to work around this refusal.
