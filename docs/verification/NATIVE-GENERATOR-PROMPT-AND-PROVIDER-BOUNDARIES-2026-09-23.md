# Native generator: prompt and provider ownership

September 23, 2026. Bounded repair of the inline system prompt and duplicated
credential lookup. No provider or model calls occurred. No approval, package
publication, provider expansion or hardcoding-allowlist change was made.

The generator's 1,076-byte system prompt now lives in the versioned
[`original_native_generation_prompt/v1` resource](../../tools/resources/original-native-generation-prompt-v1.json).
It renders through the existing `PromptResourceBundle` / `PromptResourceComponent`
owner with no slots. The rendered bytes remain exactly the old prompt, SHA-256
`02436f583453916c23f9ab7c19bd1cd5a27afeb0ec475116920b27e2ceb2fe87`.
This is a passive semantic resource with a version and digest-bound reader,
not a renamed inline constant.

`original_native_generation_run/v4` freezes the resource's exact byte digest,
bundle/render identity and rendered text digest. It also fingerprints the shared
prompt implementation alongside the existing controller, factory, gateway and
selected adapter sources. A resource-only whitespace change refuses resume
before another gateway call. Unsupported resource versions refuse before a run
output is created. One loaded render stays immutable in memory for the campaign.
Old runs remain historical; no compatibility reader or migration was added.

The generator no longer names or reads `OLLAMA_API_KEY`. It asks the selected
`ProviderSpec` adapter's existing `load_api_key` resolver for presence, reducing
the returned value immediately to a Boolean. The Ollama adapter remains the
single owner of environment/file lookup. Missing credentials retain the typed
`provider_credential_unavailable` refusal. The presence check does not verify
credential validity and deliberately calls neither `verify` nor `live_models`,
which could make unledgered provider requests.

That resolver is specific to the currently supported Ollama adapter. The
non-fixture generation path explicitly refuses other provider IDs. This repair
does not claim a universal credential-readiness protocol or activate Tactical
Engineering. Another provider requires its own qualified binding and authority.

The five new checks failed before the repair. All **33 generator checks pass**
after it, including prior resume/accounting/identity controls. New checks verify
exact prompt preservation, stored prompt/resource binding, changed-resource
resume refusal, unsupported resource version refusal, adapter-owned readiness
without the generator environment, missing-credential refusal and continued
Ollama-only scope. They use injected gateways/adapters only.

[Evidence](../../artifacts/generator-prompt-provider-boundaries-2026-09-23/README.md)
retains the initial failures, passing successor and source bindings. The narrow
patch is relative to the integrating session's copied source, including its
prior import-owner repair; unrelated provider/factory source copies are test
dependencies and are excluded from the delta. Final integration review and CI
remain the root session's responsibility.
