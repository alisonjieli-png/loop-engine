# Agent stack landscape evidence, September 24 and 25, 2026

Evidence for [the agent stack landscape record](../../docs/research/AGENT-STACK-LANDSCAPE-2026-09-24.md).
Nothing here is runtime input, and nothing here approves material or adopts
an engine.

| File | What it holds |
|---|---|
| `catalogue-2026-09-24.json` | The 57 entries of the owner's input with check state, Baltor engine slots, decision, what was observed, the question before adoption and source addresses |
| `source-register-2026-09-25.json` | Every address fetched on September 25, 2026 with status, final address, byte count and SHA-256 prefix; GitHub metadata for 48 repositories; PyPI and npm metadata for 30 packages; the Agent Client Protocol registry count; the Agent Skills client list |
| `e01/pilot_e01.py` | Experiment E01 pilot: two packages, five placement engines, Claude Code and Codex layouts, two fresh roots, offline first |
| `e01/native_place.py` | Baltor's confined writer (`tools/install_selected_material.py`) looped over a package folder for the pilot |
| `e01/listing_probe.py` | The no-model listing probe: `codex debug prompt-input` and a local capture server for Claude Code |
| `e01/listing_controls.py` | The two known-wrong controls for the probe: an empty project and a wrong root |
| `e01/e01-pilot-result-2026-09-25.json` | The pilot result, with local paths replaced by `<work>`, `<tools>`, `<repo>` and `<home>` |
| `e01/e01-listing-probe-2026-09-25.json` | The probe result for all 20 placements |
| `e01/e01-listing-probe-controls-2026-09-25.json` | The control results |

No model was called. The capture server answers HTTP 400 to every request and
the key it receives is the literal `not-a-real-key`.

## Rerun

```text
mkdir -p "$E01_TOOLS/npmtools" && cd "$E01_TOOLS/npmtools" && npm init -y \
  && npm install @sentry/dotagents@3.1.0 opkg@0.11.3 rulesync@18.0.0
python3 -m venv "$E01_TOOLS/apmvenv" && "$E01_TOOLS/apmvenv/bin/pip" install apm-cli==0.31.0
export E01_WORK="$HOME/e01-work-$(date +%Y%m%d%H%M)"   # an empty folder outside the repository
mkdir -p "$E01_WORK"
python3 e01/pilot_e01.py        # about 2 minutes; writes about 21 MB under E01_WORK
python3 e01/listing_probe.py    # needs codex and claude on the path; no model call
python3 e01/listing_controls.py # exits 1 if a control is listed
```

The September 25 results came from two sessions: the first ran the same logic
from a scratch folder, the second ran these committed scripts. The per-engine
outcomes and the normalized trees were identical across both sessions.
