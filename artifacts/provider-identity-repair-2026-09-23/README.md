# Provider answering-model identity repair

Date: September 23, 2026. Base: `9f7cd804`. No provider call was made.

The initial tests reproduced seven failing subcases: missing, null and empty
gateway identity were replaced with the requested route model; Ollama also
accepted an absent, null, empty or wrong response model. The
`known-wrong-before.txt` report preserves them.

The repair keeps missing identity as an empty string, which the existing
`model_identity_mismatch` classification refuses. Requested model identity
remains in the route and `GatewayAttempt.expected_model`. Provider usage is
preserved on these failures. Matching explicit identity still succeeds.

Checks: the new tests plus candidate-review engine tests pass, 26 total.
The owning gateway self-test passes 22 checks, and the Ollama client self-test
passes 12. These are injected transports and synthetic responses, not live
provider qualification. Exact reports are beside this file.
Two removed-guard controls independently restore the Ollama and gateway
identity failures and are detected by the named checks.

Independent review also found that an Ollama JSON error body discarded its
explicit input/output token counts. The successor extracts those counters
before the error return and preserves unknown answering identity. The new
known-wrong case and its passing successor are in the generation evidence
directory and the provider test module. Gateway 22/22 and Ollama 12/12 owning
checks still pass after that change.

Final independent review found more unanswered branches that still copied the
request model: malformed responses, transport failures, preflight refusals and
a gateway adapter exception. They now keep the actual model unknown. The
route and attempt's expected-model field retain the request. Preflight refusals
that open no request explicitly report zero physical requests. The named
regressions were recorded first in `unanswered-identity-before.txt` and pass
after repair. No live call was needed.

The small provider repair is exported separately from the native generation
command and its factory dependency so the integrating session can review and
commit the prerequisite independently.
