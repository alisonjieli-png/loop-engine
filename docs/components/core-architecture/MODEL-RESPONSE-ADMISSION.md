# Model Response Admission

Model Response Admission is the deterministic trust boundary between the
Model Gateway and a semantic consumer. It treats every provider response as
untrusted text until a canonical validator Loop admits a typed value.

```text
Operational runtime type
└── Loop
    └── Solution role
        └── solution.validator profile
            ├── deterministic envelope normalization
            ├── JSON and optional schema validation
            └── typed admission or rejection
```

The validator defaults to deterministic mode, performs no model call, and has
no external effects. If it rejects a response, the owning semantic Loop may
request another response through the existing Model Gateway. The validator
does not become hybrid and does not grant itself repair authority.

## Current deterministic strategies

- Parse strict JSON.
- Remove one exact Markdown JSON fence.
- Remove an approved non-semantic JSON preamble such as `Here is the JSON:`.
- Unwrap one safely double-encoded JSON string.
- Require an object at the response root.
- Validate an optional JSON Schema Draft 2020-12 contract.
- Reject arbitrary surrounding prose rather than extracting a convenient
  object from unknown text.

No strategy may invent a field, rename a field, coerce a semantic value, add
permission, or change an effect declaration.

## Repair flow

```text
raw provider text
    -> deterministic admission Loop
        -> admitted typed object
        -> or typed rejection with response digest and failure code
            -> owning Loop requests format repair through Model Gateway
                -> deterministic admission runs again
                    -> admit
                    -> or stop when an invalid-output digest repeats
```

Formatting repair, schema repair, semantic repair, transport retry, provider
failover, and task replanning remain separate decisions. A network failure is
not classified as malformed JSON.

## Evidence and privacy

The admission record includes the contract identity, response digest,
normalization strategy, schema failures, transformation names, Loop ID, and
model-call count. It does not include the raw response body. The raw text
remains an untrusted run-scoped value.

## Planned extensions

- Provider finish-reason and truncation checks.
- Typed tool-call argument admission.
- Streaming incomplete-response detection.
- Explicit field-alias and value-coercion policies.
- Secret and private-data screening.
- Consumer-specific evidence and abstention requirements.
- Command-level progress events for long deterministic execution.
