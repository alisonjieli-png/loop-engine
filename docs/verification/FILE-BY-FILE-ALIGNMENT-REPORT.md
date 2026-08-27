# File-by-file alignment report

## Current state

`NOT YET PROVEN` for Checkpoint -0.5.

The initial Repository Alignment Practitioner ran through the canonical `Loop`
runtime with profile `practitioner.verifier`.

| Measure | Current value |
|---|---:|
| Files inventoried | 1,200 |
| Files with current static findings | 80 |
| Exact findings | 175 |
| Runtime type used by the audit | `Loop` |
| Separate audit runtime | none |
| Approved parameter exceptions | 0 |

The complete per-file baseline is
`artifacts/architecture/alignment_results.jsonl`. A record marked
`VERIFIED_BY_CURRENT_GATES` has passed the checks implemented today; it is not
a claim that the later symbol, string/blob, folder-owner, and generalization
questions have all been completed.

## Next audit command

```bash
PYTHONPATH=devtools/src:src python -m loop_engine_devtools.cli \
  --assurance --scope full --json
```

The next session must add the full symbol inventory, folder semantic map,
string/blob findings, ProcedureDefinition and ProcedureStepSpec model, and the
twenty-configuration proof before marking Checkpoint -0.5 complete.
