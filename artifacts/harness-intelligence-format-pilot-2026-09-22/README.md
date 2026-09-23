# Mixed-format harness intelligence candidates

Kind: isolated, candidate-only file-format experiment, September 22,
2026. The owner clarified that harness intelligence includes any file or
package a selected harness can natively discover, load or invoke. The
earlier [68 candidate skills](../first-party-harness-candidates-2026-09-22/README.md)
exercise one class. This pilot adds root instruction files and bundled
deterministic code, with connection/configuration candidates assessed
separately. No file here is approved, released, granted to a customer, or
qualified to improve a task.

The [file-kind research](../../docs/research/HARNESS-INTELLIGENCE-FILE-KINDS-AND-ADMISSION-2026-09-22.md)
distinguishes presence, native discovery, load, use and verified benefit.
The [placement report](../../docs/research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
maps client-specific directories. A filename is not a permission grant,
and a tool script is not automatically callable just because it is on
disk.

```text
Mixed-format candidate pilot
├── context/       step instruction files in separate client layout examples
├── tools/         skill packages containing real Python scripts and tests
├── connections/   local protocol/configuration candidates, if qualified
├── manifest.json  exact bytes of every candidate source file
└── README.md      this boundary and handoff
```

Instruction candidates must be rendered with actual task identity,
workspace paths, authority and acceptance conditions before native
loading. A `CODEX.md` file is not a Codex default instruction file;
Codex 0.155.1 uses `AGENTS.md` by default and accepts additional fallback
names only under an explicit configuration. Client-specific layouts are
alternatives for one step, not files to install simultaneously in every
compatibility directory.

The code candidates are read-only utilities. Their script tests establish
bounded behavior on stated fixtures, not permission to run them on a
customer's filesystem. Claude Code must independently review the exact
multi-file package, source rights, dependencies, effects and native
invocation before it enters the active catalogue. A review of `SKILL.md`
alone cannot approve a script hidden beside it.

The [logical candidate catalogue](candidate-items.json) records **six
packages**: two instruction templates, three skills with tested Python
tools, and one local protocol connection package. The
[exact-file manifest](manifest.json) currently binds 52 physical source,
rendering and review files. Those counts answer different questions;
tests and client renderings are not extra intelligence methods. The
[mixed-format search](search_format_candidates.py) checks both records
before returning metadata and digests. With `--client codex`, it shows
only the Codex delivery variant, while an unfiltered card requires a
client choice before any file can be installed. It is local reviewer
search, with no customer grant or approval state.

```bash
python3 artifacts/harness-intelligence-format-pilot-2026-09-22/make_format_manifest.py --check
python3 -B artifacts/harness-intelligence-format-pilot-2026-09-22/test_make_format_manifest.py
python3 -B artifacts/harness-intelligence-format-pilot-2026-09-22/test_search_format_candidates.py
python3 artifacts/harness-intelligence-format-pilot-2026-09-22/search_format_candidates.py \
  --id baltor.connection.json-shape-stdio.v1 --client codex
```

The connection [review](connections/json-shape-stdio/REVIEW.md) preserves a
clean-home failure of its canonical `python3` configuration and a
successor local OpenCode connection using a separately provisioned
interpreter. It is qualified only for the recorded legacy protocol probe,
not installed into any customer's harness. The three tool packages have
40 focused tests. An independent rereview replayed the earlier path,
number, privacy, FIFO and resource failures against the repaired exact
bytes and found no new blocker for retaining them as candidates. Runtime
authority, mount provenance, concurrent snapshot consistency and native
invocation remain separate gates.
