# Ownership component probes

Date: 2026-09-23. Upstream: madebywild/agent-harness, commit
`2ecf44f97ab6ffd76f5c1a58ac57b930e2ccfa17`, tag v2.1.0, MIT.

Files:

- `source-inventory.json`: audited source URLs, digests and execution scope.
- `build-probe.mjs`: exact-source transpiler and explicitly documented wrappers.
- `component-source-fingerprints.json`: original and compiled module digests.
- `probe.mjs`: fifteen checked fixture observations.
- `component-probe-results.json`: successful isolated run results.
- `UPSTREAM-LICENSE`: attribution for derived source fragments.

This is a component experiment, not the complete upstream test suite or CLI.
The native renderer is a fixture returning controlled artifacts. The writer's
exact apply method consumes injected plans. The registry clone argument builder
is exercised without running Git. Private helpers are copied from exact source
slices and exported. Types and import locations are transformed; the tested
logic is not repaired. The inherited-property behavior was measured using
Zod 4.4.3 and YAML 2.8.2, not every supported parser dependency version.

Dependencies were installed by the parent session in a separate scratch prefix,
with package scripts disabled. Required Node modules are TypeScript 5.9.3,
Zod 4.4.3 and YAML 2.8.2. No project dependencies or scripts were installed or
executed. The host Node build could not use built-in TypeScript stripping; this
successful method uses TypeScript explicitly. No model calls or network fetches
occur during the probe itself.

Reproduce with paths to an exact detached upstream clone, a new module output
directory, isolated dependencies, and a new writable scratch directory:

```sh
node build-probe.mjs "$UPSTREAM_CLONE" "$PROBE_ROOT/modules" "$PROBE_DEPENDENCIES/node_modules"
bwrap --unshare-net --die-with-parent --ro-bind / / \
  --bind "$PROBE_ROOT" "$PROBE_ROOT" --clearenv --setenv PATH /usr/bin:/bin \
  --proc /proc --dev /dev \
  /usr/bin/timeout 30 /usr/bin/node --max-old-space-size=128 \
  "$EVIDENCE_ROOT/probe.mjs" "$PROBE_ROOT/modules" "$PROBE_ROOT/run-new"
```

Use a new run directory; fixtures deliberately retain their final state. The
probe writes only below that directory. The symlink case connects two disposable
siblings there. The delete-error case intercepts only removal of one exact
fixture path and restores the original filesystem method in a finally block.
No real credential is used; the clone argument contains a synthetic canary.
