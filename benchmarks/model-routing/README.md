# Model-routing bootstrap benchmark

This frozen benchmark checks the deterministic selection contract before a
model call. It covers 14 cases and permits zero provider calls.

The population is
[`frozen-bootstrap-cases-v1.json`](frozen-bootstrap-cases-v1.json). It names the
expected contract assertion for each case. The package self-test owns the
executable synthetic routes, reviewed capability and suitability records,
current availability snapshots, and adapters that fail if touched.

## Run it

```bash
PYTHONPATH=src python3 -m \
  loop_engine.core.model_routing_intelligence_checks \
  benchmarks/model-routing/frozen-bootstrap-cases-v1.json
```

The result includes the SHA-256 digest of the exact fixture, the case
denominator, and the provider-call count.

## Cases

```text
Frozen model-routing population
├── portfolio uses the four existing intelligence layers
├── capability, suitability, and availability remain separate records
├── hard filtering runs before explainable ranking
├── deterministic evidence returns no_model_required
├── local-only policy excludes cloud routes
├── Practitioner, Intelligence, and Solution use the same route policy
├── short-task evidence does not transfer to repository architecture
├── deployment changes invalidate old suitability evidence
├── stale runtime availability is rejected
├── bootstrap selection makes zero adapter calls
├── a selected decision maps to ModelGatewayConfig
├── selection runs through a governed Loop with canonical events
├── missing token usage remains unknown
└── a producer cannot approve its own routing candidate
```

## Evidence boundary

This is an offline contract benchmark. All route performance values are
synthetic fixtures. The result is not evidence about provider uptime, model
quality, latency, cost, token accounting, a local Qwen deployment, or route
selection regret on a real task population.

Live measurements need an authorized provider run, a frozen real task
population, an independent evaluator, exact model and deployment identity, and
complete Run History.
