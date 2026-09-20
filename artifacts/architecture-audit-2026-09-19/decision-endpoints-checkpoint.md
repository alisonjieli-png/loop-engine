# Configured external decision endpoints

Date: September 19, 2026. This checkpoint records local implementation and
testing, not model quality or a paid release.

## Ownership and generalization

| Responsibility | Owner | Boundary |
|---|---|---|
| Endpoint, model, locality, provenance, credential reference and ordered route selection | Host configuration | `core/decisions/configuration.py` compiles shipped adapter profiles into the existing ModelGateway |
| Input and output meaning | Shared contracts | `contracts.py` and `wire.py`; provider names do not change caller logic |
| Credential lookup | Shared resolver | `credentials.py`; discovery does not resolve keys |
| One bounded external request | Transport adapter | `http_transport.py`; no redirects, proxy inheritance, automatic retry or model-server launch |
| Provider-specific restrictions | Adapter configuration | Jev uses its fixed vendor endpoint; Circuit and compatible services use a declared endpoint |
| Call allowance, route policy and history | Existing runtime | ModelExecutionSession, ModelGateway and the owning canonical Loop |
| Direct and harness-tool access | Application adapter | `decision_cli.py` and `code_nodes/decision_tools.py` |

The configuration contract is `decision_host_configuration/v2`. It accepts
named `jev`, `circuit` and `system_one` profiles. Circuit and `system_one` share
one wire implementation. Changing a route changes configuration, not the
requesting code. Incompatible protocols need a tested adapter; arbitrary
module imports and silent response guessing are not supported.

No inheritance hierarchy or second provider registry was added. Import-boundary
checks keep shared serialization and credentials independent of provider code,
and keep configuration and adapters free of HTTP clients and process launchers.
Two conformance entries allow only URL parsing in configuration; the import
tests prohibit actual network clients there.

## Operator responsibility

The owner clarified that users provide existing endpoints and authentication.
A newly drafted optional Circuit launcher was removed before adoption. No
existing user files were removed. No weights, Ollama server, Jev interface or
Circuit process are installed, downloaded, launched or managed by these adapters.

HTTPS is required except for explicitly authorized numeric loopback HTTP.
Different provider origins require different credential references. Exact model
identity and response admission are checked. Context coverage, actual deployment
provenance and model quality remain unqualified. Byte ceilings do not establish
token capacities. A custom-trained model needs its declared training-record
digest; the adapter cannot replace it with a made-up default.

## Local evidence

`decision-endpoints-verification-3.json` records 228 passing focused checks and
five detected removed-guard controls with unchanged source. The checks include
real loopback HTTP for configured Circuit and compatible endpoints, an official
Model Context Protocol client, disabled discovery, request and response bounds,
wrong model identity, fake output, redirects, authentication failure and shared
session limits. Configured failover reaches a second endpoint only when
authorized, and retains both physical attempts in the same allowance.

The earlier full exported source passed 5,872 checks. Subsequent provenance
work exposed a missing required training digest in the custom-model path;
the invariant refused that configuration rather than silently inventing
provenance. The repair passes the digest through to the existing ontology and
adds a negative case. The final `verification-decision-endpoints-attempt-3.json`
records 5,876 of 5,876 executed checks passing, with 15 optional checks untested
and unchanged frozen source. Its full package identity matches the working
tree: `aeef37d57bc243ebd4d8d4f309e3455843b35db275cc6f188a3e55e7338612d9`.
The failed second capture is retained with its module-collection failure.

The development report has fifteen owner preparation tasks, phased instructions,
non-secret handoff fields and full embedded guides. Checkmarks are browser-local
notes bound to instruction digests. They do not change roadmap status, satisfy
release gates or grant any authority. Unknown or changed imported marks are
ignored. The failed browser attempt after changing the default page is retained:
its copied-file check waited for a diagram before opening Architecture. The
test now explicitly selects that view and still checks its rendered result.

## Known boundaries still open

SemIf's inspected release has a different record shape and no declared hosted
decision route. It also returns explicitly uncalibrated scores, while our
current Choice and Score records require a confidence scalar. Its future
adapter needs an honest confidence-basis contract, not a fabricated scalar.
See the embedded research review before claiming support.

SoL-Pi is an optional Pi extension-profile candidate. Our current Pi process
recipe disables extensions. Its admission, actual feature loading, nested
model accounting and composed safety behavior remain work. Neither research
item changes independent task acceptance or introduces another Loop runtime.

No real provider calls, payments, deployments, commits or pushes occurred.
