# Package one skill as thin adapters for two coding harnesses

Publish the same skills for Claude Code and for Codex as thin adapters over one installed command line tool. The adapters hold instructions and metadata only. They hold no second engine, no credentials and no permission grants.

## When to use it

Use it when a command line tool should be usable from more than one coding harness and the behaviour must stay the same in all of them.

## Steps

1. Keep all behaviour in the installed tool. Let each skill say which command to run and what to report.
2. Create one folder for each harness. Put one folder for each skill inside it, with a `SKILL.md` file.
3. For Claude Code, start `SKILL.md` with front matter that holds `name`, `description` and `allowed-tools`. Add a plugin manifest and a marketplace file in the hidden plugin folder of the package.
4. For Codex, start `SKILL.md` with front matter that holds `name` and `description`. Add an `agents/openai.yaml` file with a display name and a short description. Add a plugin manifest that points to the skills folder, and a marketplace file that names the local plugin path.
5. Write the description as a trigger: say when the skill applies, for example when the person asks to build, solve, run, verify or resume work.
6. Give a skill that only inspects results the narrowest tools, and tell it not to start or repeat work for a request that only reads.
7. For a setup skill, switch off invocation by the model, so that only the person can start it. Tell it never to print keys and never to download models without being asked.
8. Make every skill pass on only the permissions and effects that the person supplied, and report blocked results and results without progress honestly.
9. Add a deterministic check that parses every manifest, counts the skills and refuses placeholder text and credential assignments inside a skill.

These file layouts are the ones in this repository at the cited revision. Check the current documentation of each harness before publishing.

## Checks

- The list of allowed contents is short: plugin manifests, marketplace metadata, thin skills and deterministic validation scripts.
- No adapter holds a second scheduler, provider credentials, permission grants or copied records of earlier work.
- The same skill names exist for both harnesses.
- The structure check passes.

## Known-wrong example

A team copies the planning logic of its tool into the skill text for one harness and adjusts it there. Two weeks later the tool and the skill disagree, and only one harness shows the new behaviour. A thin adapter cannot drift in this way, because it holds no behaviour of its own.

## What to record

- The version of the tool that each adapter was written for.
- The result of the structure check.
- The date on which each harness format was last checked against its documentation.

## Source

- `integrations/README.md`: the rule that host packages are thin adapters.
- `integrations/architecture.yaml`: the allowed and the forbidden contents.
- `integrations/tests/check_integrations.py`: the deterministic structure check.
- `integrations/claude-code/skills/loop-engine-setup/SKILL.md`: a setup skill with invocation by the model switched off.
- `integrations/claude-code/skills/loop-engine-inspect/SKILL.md`: a skill that only inspects, with narrow tools.
- `integrations/codex/plugins/loop-engine/skills/loop-engine-run/SKILL.md`: a run skill for Codex.
- `integrations/codex/plugins/loop-engine/skills/loop-engine-run/agents/openai.yaml`: the interface metadata for Codex.

Licence: MIT. Compiled from revision 9a483df. The plugin manifests sit in hidden folders beside these files.
