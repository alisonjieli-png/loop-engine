# Independent review of consolidated hardcoding exceptions

Date: September 23, 2026. **GO for the scoped exception additions and prompt/credential
abstraction.** Integration source, allowlist and generator were read only. This review
adds only its own report and evidence. It ran no provider/model calls or browser journey.

## Inventory and unchanged gate

The initial triage contains **139 distinct finding IDs**, reconciled exactly as:

| Treatment | Initial high findings | Mechanism |
|---|---:|---|
| Exact allowances | 35 | Individual finding IDs with matching source owner/classification and dated rationale |
| Frozen website evidence | 101 | Two exact JSON paths, each pinned to its reviewed SHA-256 |
| Actual abstraction | 3 | Inline prompt, deployment lookup and credential reference in the native generator |

The resulting governed prompt resource adds the 36th exact allowance. During this
review, the parent added one separate signup/browser finding, making the final scope
**37 new exact allowances and two digest-bound exclusions**. The original 139-row
triage remains accurate and unchanged; the later signup finding is recorded separately.

All pre-existing allowances/exclusions remain unchanged. The baseline is byte-identical
to HEAD, SHA-256 `09f46c9ae19407c648d145977ee9b87291e23dac93663aca5a9ea35dee87f255`.
The audit implementation and CI's `--fail-on-new high` gate are unchanged. There is no
wildcard exception or newly excluded directory. All additions expire September 23, 2027.

The independent focused scan covers all 18 paths implicated in the original triage and
new prompt resource. It reports **zero new high/critical blockers, zero allowlist
problems, and 36 suppressed findings**. Its **183 new medium findings remain visible**.
A separate scan of the signup browser tool finds the 37th allowance correctly bound
and no new high blocker. This is not a claim that all hardcoding findings disappeared.

## Source review

| Addition group | Independent observation |
|---|---|
| Role and status discriminants | Eleven role branches use values from the existing `CataloguePackage.FILE_ROLES`; the twelfth controlled-vocabulary allowance is the generator's `candidate_prepared` journal state. Placement/effect guards remain enforced. These are schema/control values, not configurable permissions or producer approval claims. |
| JSON Schema identifiers | Ten frozen control schemas and the validator name the supported 2020-12 dialect. The validator uses its local implementation and refuses non-local `$ref`/`$dynamicRef`; these identifiers do not select a network service. |
| URL syntax and documentary links | HTTP/HTTPS prefixes distinguish external citations from package-local links. The documentation origin rewrite requires the exact origin plus slash and a served-page path. It is a first-party link normalization rule, not a credential/provider route. |
| Historical website inspector | Four exact public URL findings belong to the saved read-only observation program. Its browser restricts requests to GET on the observed public origin; asset requests also name that fixed public host. It is not imported by service routing. |
| Browser negative controls | Three `.invalid` addresses are deliberately bad index/body/link fixtures. The browser tool blocks non-fixture origins and checks refusal; they are not deployment defaults. |
| Later signup finding | `hardcoding.b8c2de715f0926b6fb499569` checks the generated link starts with `https://checkout.stripe.com/`. It does not follow that link. The scenario runs against `stripe_session_checks.fixture`, whose injected `LocalStripeSessionTransport` supplies Stripe-shaped records; the browser also applies its local-only route guard. This is a provider-specific destination assertion, not a real checkout/charge or runtime routing exception. |

The 35 original exact allowances match their triage owners and classifications. The
new prompt-resource allowance and later signup allowance also match the actual scanned
finding identities. The evidence JSON digests match both exclusions. The audit's own
credential-shaped-value detector finds no such values in either excluded file; their
contents are public-site observation data, not active credentials or deployment policy.

## Genuine abstraction in the generator

The generation instructions now live in `original-native-generation-prompt-v1.json`
and pass through the existing `PromptResourceBundle` owner. The loader validates the
record, bundle and version identities, bounds the file, refuses secret-shaped content,
and renders the bundle. Run v4 records both resource-byte and rendered-text digests,
as well as implementation source. It uses the rendered text as the model system
instruction. This is an active abstraction, not a detached file added only to satisfy
an audit. A resource-only byte change refuses resume before a fixture gateway call.

Credential presence is delegated to the selected Ollama adapter's existing local
`load_api_key` resolver. The generator does not name/read the credential environment
variable, serialize its value, call provider verification or list models for this check.
A missing key or unsupported provider is refused. This remains an Ollama-only generation
lane; the exception does not authorize or pretend to implement another provider.

Five focused tests passed: exact old prompt text preserved, changed resource blocks
resume, unsupported resource version blocks before output/call, credential presence
delegates to the adapter, and missing credentials refuse without provider verification.

## Controls against weakening

Using the original HEAD allowlist against the current scoped source restores **137
high blockers**. Their ID set equals the initial 139 minus the three genuinely
abstracted source findings plus the new governed-resource finding. This exactly
accounts for the source changes and exemptions without changing the baseline.

A second canary changes one excluded evidence file's read bytes by a trailing newline
in memory only. The audit reports `excluded_path_content_changed`, scans the file
instead of skipping it, and rejects verification. No repository file was changed.

The preserved `focused-successor.json` is an intermediate failed audit with the new
prompt resource still blocking; it has not been rewritten into a success. Current
independent results and hashes are in the
[evidence index](../../artifacts/hardcoding-exceptions-independent-qa-2026-09-23/README.md).
No material issue was found within this classification/abstraction scope. Admission,
provider availability, live signup behavior and launch readiness require their own
existing checks.
