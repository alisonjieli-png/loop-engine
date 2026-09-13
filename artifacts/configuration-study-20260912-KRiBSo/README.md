# Tactical configuration study, 2026-09-12

The [verification report](../../docs/verification/CONFIGURATION-AND-NATIVE-INITIALIZATION-2026-09-12.md)
describes the completed study and preserves the full terminology explanation.
All artifacts in this directory are local. The derived DuckDB projections do
not replace canonical Run History or managed records.

The study made 70 real Tactical calls. All 244 saved histories verify, and the
physical-call totals reconcile. Usage is 137,960 input tokens and 7,828 output
tokens, with complete accounting and unknown monetary cost.

| Location | Evidence |
|---|---|
| [authority.json](authority.json) | Exact endpoint, model, scope, allocations, and provider policy |
| [preflight](preflight/) | Four initial packet checks, including three strict-admission failures |
| [admission comparison](admission-773aac4a092e/summary.json) | Eight matched response-policy cells |
| [repair matrix](resource-matrix-58d076930cf8/summary.json) | Forty cells and 159/160 independent case passes |
| [skill review](resource-matrix-58d076930cf8/skill-review.json) | Independent review before local task-use admission |
| [native initialization](native-initialization-5298291c2c2b/summary.json) | Nine positive and negative controls, all passing |
| [native requirements](native-requirements-c9c8133729b1/report.json) | Current adapter requirements and configuration-loader refusals |
| [first diagnostic setup failure](native-requirements-ba6010ebd0ce/report.json) | Missing output role, zero model calls |
| [second diagnostic setup failure](native-requirements-f0a006fd64c8/report.json) | Request-authority construction refusal, zero model calls |
| [reconciled audit](audit-74761d89b3fd/summary.json) | Counts, tokens, histories, per-cell outcomes, and retained failures |
| [physical calls](audit-74761d89b3fd/physical-calls.json) | Provider-reported usage linked to exact events |
| [application checks](qa/summary.json) | 32/32 tests, with no real provider calls |

The phase directories preserve immutable source archives or pinned bootstrap
and software identities. Each live attempt has a separate directory. The
summary views are derived from their own projection databases. Existing
studies were not overwritten.

The source applications create a fresh phase when invoked again:

```bash
PYTHONPATH=src:devtools .venv/bin/python -m embodiment_lab.configuration_study \
  --root /home/username/loop-engine/.loop-engine-dev/configuration-study-20260912-KRiBSo

PYTHONPATH=src:devtools .venv/bin/python -m embodiment_lab.configuration_matrix \
  --root /home/username/loop-engine/.loop-engine-dev/configuration-study-20260912-KRiBSo
```

Those commands make new real provider calls. Running
[summarize_study.py](summarize_study.py) instead creates a fresh read-only audit
of retained evidence and makes no model calls. It refuses to overwrite an
existing audit artifact.

The [native initialization driver](test_native_initialization.py) registers
the [pinned initializer](native_bootstrap.py) through existing harness
configuration fields. It does not edit the original Pi, OpenCode, or Codex
configuration. Its controls enable only native Markdown visibility; tools and
plugins retain the original denial policy.
