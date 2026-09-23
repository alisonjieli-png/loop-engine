# Generator prompt and provider-boundary repair evidence

September 23, 2026. No model or provider calls; no approval or publication.

- `known-wrong-before.txt`: five new checks fail on the copied predecessor.
- `tests-after-1.txt`: all 33 generator checks pass after the repair.
- `source-bindings.json`: copied integration baseline and final changed source hashes.
- `summary.json`: exact original/rendered prompt hash, resource binding and scope.

The first prompt resource preserves all 1,076 prior system-prompt bytes. The
resource is loaded through the existing prompt-bundle owner and bound into run
version 4. The credential-presence check uses the selected Ollama adapter's
local-only resolver and performs no verification/listing request. Fixture runs
remain visibly marked and do not become live provider qualification.

Reproduce from the repository root with the qualified repository environment:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src python -m unittest \
  tools.test_generate_original_native_candidates -q
```

The generator's CLI remains Ollama-only. The resource must travel with the
operator tool in its checkout; this change does not make the operator command a
new hosted service endpoint.
