# OpenMuse source audit evidence

September 23, 2026. Commit `bb7ce4e1c6e523bf282a655c63621e3ed9e75150`.
See the source inventory for inspected files, hashes and URLs.

`probe.mjs` transpiles the exact configuration module and disabled OpenBot
adapter. The only import rewrite binds Zod to a separately installed analysis
dependency. It checks configuration construction and injects a synthetic
transport returning controlled Responses. No global fetch is used. No upstream
application, model SDK, database, browser, Docker worker or lifecycle script runs.

Dependencies were reused from the parent session's analysis-only prefix:
TypeScript 5.9.3, Zod 4.4.3; Node 22.22.1. This does not reproduce the whole
upstream lockfile. The app's recommended Node version is 24 LTS; its package
engine accepts Node >=22. No claim about full application compatibility follows.

The successful results have seven observations. They are component fixtures,
not live-service acceptance. All key values were harmless synthetic text and
the source configuration only tested their presence, not validity.

Reproduction, with a new writable scratch directory and an exact detached
clone:

```sh
bwrap --unshare-net --die-with-parent --ro-bind / / \
  --bind "$PROBE_ROOT" "$PROBE_ROOT" --chdir "$PROBE_ROOT" \
  --clearenv --setenv PATH /usr/bin:/bin --proc /proc --dev /dev \
  /usr/bin/timeout 30 /usr/bin/node --max-old-space-size=128 \
  "$EVIDENCE_ROOT/probe.mjs" "$UPSTREAM_CLONE" "$PROBE_ROOT" \
  "$PROBE_DEPENDENCIES/node_modules"
```

The scratch working directory must contain no `.env` file. The root filesystem
is read-only; only scratch is writable. Network is unshared. Preserve the
upstream MIT notice with any reused source fragments.
