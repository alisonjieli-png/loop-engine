# Custom endpoint reported identity repair

Date: September 23, 2026. Local source base: `9c57c9a4c813578bffa504108ef9d785b308bb86`.
This isolated change affects `core.custom_endpoint` and its owning offline controls.
It complements the separate ModelGateway identity repair; it does not replace it.
No model, provider generation, installation, credential transmission, or approval occurred.

## Reproduced defect

The custom adapter used the requested model as the answering model when a buffered
response omitted `model`. Both OpenAI-compatible SSE and Ollama NDJSON initialized
stream identity from that request. A later stream chunk could overwrite an earlier
conflicting identity. Consequently downstream exact-model checks could receive an
invented matching identity. Ollama streaming also changed missing final token counts
to zero.

The named negative checks were written first: **30 assertions failed before repair**.
The failure report is retained in
[`checks-before-repair.json`](../../artifacts/custom-endpoint-reported-identity-2026-09-23/checks-before-repair.json).

## Repair

- A reported identity must be a nonempty string from the response. No coercion or
  fallback fills it from configuration. A different reported model is retained and
  refused; absent or malformed identity remains the empty unknown representation.
- A stream may name its model once before later usage-only chunks. Every supplied
  model identity must be well formed and agree. Conflicts and malformed identities
  remain failures even if later chunks name the requested model.
- The adapter refuses an answer with an absent, malformed, conflicting, or unexpected
  identity, independently of the ModelGateway guard. Buffered provider refusal errors
  retain their existing classification without inventing an answering model.
- Transport and preflight failures carry no answering model. Capacity and retry
  preflight refusals report zero physical requests. A received response is still a
  physical request even when its identity fails.
- Absent streamed usage remains unknown. Explicit zero counts remain zero.

Two existing framing/completion fixtures now include a genuine response model so
those tests continue to isolate framing and completion rather than missing identity.
No serialized contract shape changed; no old record is reinterpreted. Generator
resume must continue binding the adapter source digest.

## Verification and limits

The owning endpoint checks pass **22/22**, and expanded custom adapter checks pass
**70/70**. Adjacent gateway and accounting checks pass **22/22 and 33/33** on this
isolated base. Seven in-memory guard mutations are all detected. Existing-file Ruff
findings remain 9 and 3 respectively, with zero introduced findings; the new mutation
runner is clean. Source diff whitespace checks pass. All fixtures replace the opener
and never open a socket.

Evidence lives in
[`custom-endpoint-reported-identity-2026-09-23`](../../artifacts/custom-endpoint-reported-identity-2026-09-23/README.md).
These are offline boundary checks. They do not qualify Tactical's live endpoint,
model identity, capacity, or generated intelligence.
