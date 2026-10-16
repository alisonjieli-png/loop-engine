# Engine framework

Kind: component folder for the shared engine framework (roadmap S-6.30).

This folder holds what every engine slot shares: the engine slot catalogue
and its joins, the engine records, selection, evidence and measurement.
Engines themselves stay in the registries and folders of their own
components. The design is
[Engines behind fixed edges](../../../../docs/architecture/ENGINES-BEHIND-FIXED-EDGES.md).

Naming rule: one module for each part of the framework, named without an
`engine_` prefix (`slots.py`, `slot_index.py`, `selection.py`). A factory
table module names engine classes and defines none; an engine module holds
exactly one engine and lives in the folder its slot names.

Version rule: every record is `name/vN`. Readers refuse unknown keys and
unsupported versions before any effect, and a record that an older release
must not honour gets a new version.

## Envelope layers

The envelope Loop of every functional component applies the same ordered
envelope layers between its edge contract and its engine slot. The
[envelope layer decision](../../../../docs/architecture/ADR-COMPONENT-ENVELOPE-LAYERS.md)
maps the owner's words to the layers, and section 14 of the
[functional component standard](../../../../docs/architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
states their rules.

| Module | What it holds |
|---|---|
| `envelope.py` | The layer order, `envelope_handshake_verdict/v1` and its negotiation, `envelope_refusal/v1`, the recovery policy and its shared allowance, the nesting frame with its depth bound, and `envelope_trace/v1` |
| `envelope_tracking.py` | `envelope_journal_entry/v1`, the journal decision (dispatch, answer from the first result, reconcile first) and the resync decision |
| `envelope_preflight.py` | Declared self-checks, declared self-repairs refused without their effect grant, and `envelope_preflight_report/v1` |
| `envelope_coverage.py` | What every slot declares for each layer in `data/component_envelope_coverage.yaml`, held to `data/component_envelope_coverage_baseline.yaml` |
| `envelope_checks.py` | The named checks, each with its known-wrong case |

These modules hold records and pure functions. They start, open, store and
schedule nothing, and no envelope record grants authority. After an
improvement, raise the slot's row in the baseline file to the new
declaration; a lowered row fails the coverage check.

```bash
PYTHONPATH=src python -c "from loop_engine.core.engines.envelope_checks import self_test; r = self_test(); print(r['passed'], r['total'])"
```

A folder grants nothing: no path implies access, authority or routing.
