# Harness package interoperability research

Research and no-model observations from September 23, 2026. These files add
no approved intelligence packages, install no customer plugin and qualify no
complete task. The existing roadmap remains the task authority.

Start with the [main comparison and implementation decisions](../../docs/research/TASK-PACKAGE-INTEROPERABILITY-AND-QUALIFICATION-2026-09-23.md).
It links detailed standards, editor and open-harness reports.

## New native observations

- [Initial Codex observations](codex-delivery-20260923T134822.json): seven
  prompt-construction cases, all expectations observed.
- [Hardened successor](codex-delivery-20260923T135708.json): the same seven
  cases, with the externally held fixture binding checked through the existing
  packet verifier and unchanged project files required for success.
- [Independent Codex review](standards/CODEX-DELIVERY-INDEPENDENT-REVIEW-2026-09-23.md):
  reproduced all seven initial cases, retained raw prompt output and warnings,
  and independently reproduced four native schema digests.
- [Corrected schema extraction](codex-native-schema-observation-2.json):
  resolves the input type through the generated schema's `definitions` field.
  The predecessor used `$defs` and recorded an empty extracted object; that
  was an extraction error, not an empty native input contract.
- [Pi loader observation](open-harnesses/pi-loader-observation-2026-09-23.json):
  seven direct loader cases against the installed 0.73.1 package. The linked
  open-harness report distinguishes this from current upstream 0.87.1.

The Codex controls demonstrate override shadowing, combined-budget loss,
missing import expansion, explicit task input and the difference between
skill metadata and body text. A loose Python source body was absent from
initial context; this observation alone is not a complete tool-registration
audit. The Pi checks demonstrate version-specific precedence, ancestor
discovery and duplicate-skill behavior.

These are separate debug processes or direct loader calls, not running
conversations. The no-model classification follows those selected interfaces;
no provider transport monitor was installed. Closed proxy variables do not
constitute an operating-system network sandbox. The preserved Codex warnings
concern helper PATH aliases under temporary directories.

## Reproduce the Codex controls

Use the repository environment containing the current Loop Engine package:

```bash
PYTHONPATH=src .venv/bin/python \
  artifacts/harness-package-interoperability-2026-09-23/probe_codex_delivery.py
```

The probe verifies the frozen earlier packet and its verifier before copying
it into temporary workspaces. It writes a new timestamped report and leaves
old reports intact. It never runs `codex exec`, invokes a provider, installs a
plugin or modifies real user configuration. It uses synthetic fixture text
as debug command arguments; production task text should use standard input
or a protocol transport.

The initial script is retained under `predecessors/`. Requalification is
required if the trusted fixture binding, renderer or native version changes.
The hard-coded fixture hashes are research experiment controls, not production
approval records.

## Sources and existing boundaries

The [standards source inventory](standards/sources.json),
[editor source inventory](claude-editors-source-records.json) and
[open-source manifest](open-harnesses/source-manifest.json) record the sources.
Third-party source snapshots are research input, not generated or admitted
library content. Source reviews and documentation do not establish behavior
in every released binary.

Integrate the findings through the existing instruction composer, prompt
resource contracts, catalogue package/body store, selected-material installer,
harness executor and trusted state. Required components need explicit native
activation and capability checks. New research tooling must not become a
second runtime, package registry or task-state store.
