# Tactical Hermes discovery and generation binding proposal

Date: September 23, 2026. Discovery only; **zero model calls and zero credentials
sent**. The generator implementation inspected is the detached
`native-generation` checkout at `9f7cd80495e454ea6dac0a7ffafcf74a49113bd6`.

## Observed status

| Question | Evidence and result |
|---|---|
| Existing route | Tracked Tactical scripts and campaign defaults name `https://ai.tacticalengineering.net:6969/v1`. No different verified route or fingerprint trust contract was found in the inspected sources. |
| Active runtime settings | Neither repository `.loop-engine.yaml`, the normal user settings path, the settings environment override, nor the historical `/tmp/tactical-probe/tactical-settings.yaml` was available. `LOOP_ENGINE_ENDPOINTS` was absent. |
| Credential availability | `TACTICAL_API_KEY` was absent from this process. A single-token, mode-0600 file exists at `/home/username/.config/tactical_key.env`. Its contents were not printed, copied into artifacts, executed as shell, or sent. The existing operator credential reference manifest has no Tactical entry. |
| Initial metadata read | Existing `CustomEndpoint.live_model_listing` with normal TLS failed certificate verification. No HTTP response or model listing was obtained. |
| Scoped CA read | A public Cloudflare Origin RSA root downloaded from Cloudflare's official documentation was passed to the existing endpoint-only `ca_file` setting. Hostname verification then failed. No global trust settings changed. |
| Certificate identity | SANs name `*.iamretarded.net` and `iamretarded.net`; neither covers `ai.tacticalengineering.net`. The public leaf fingerprint is `0F:C6:9C:F1:C7:2A:BE:55:2E:9F:B3:CF:A9:6D:B9:97:4D:7B:D9:33:94:C2:0D:21:9D:4C:05:1A:1A:92:39:01`. No connection to those alternate names was attempted. |
| `/hermes` identity | Unknown. It may name a model or a route. A path fragment is not a qualified model identity. |
| Context/output capacity | Unknown for this requested model. Historical Gemma route evidence is not transferable. No old capacity number was reused. |

The CA source is the [Cloudflare Origin CA documentation](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/)
and its [published RSA root](https://developers.cloudflare.com/ssl/static/origin_ca_rsa_root.pem).
The downloaded public certificate has SHA-256
`91a8a5567efa6bf941162aa806b3ba476aaddf7867640e53053b35fb225a5dae`.
An initial download without a browser user agent returned HTTP 403; the succeeding
request is recorded. These observations are not authorization to disable TLS or
follow the certificate to another domain.

## Reuse decision

Use the existing `ProviderSettings`, `CustomEndpoint`,
`provider_spec_from_endpoint`, `ModelOutputCapability`, `ModelRoute`, and
`ModelGateway` contracts. Keep the current native generator, dispatch journal,
factory, package identity, quarantine, and independent review pipeline. No second
runtime, generation journal, catalogue, or approval store is needed.

Existing built-in generation defaults cannot safely be relabeled Tactical:

- The generator's family proof currently filters panel installations by
  `provider_id == ollama_cloud` and separately requires `OLLAMA_API_KEY`.
- Its `implementation_digests` handles module and instance adapters but treats a
  custom class adapter as `type`, whose file cannot be inspected. CustomEndpoint's
  factory returns a class. The source binding must explicitly support classes.
- The custom adapter and older gateway filled absent response model identities
  from requested identities. The separate gateway successor and
  [custom adapter repair](CUSTOM-ENDPOINT-REPORTED-IDENTITY-2026-09-23.md)
  are prerequisites for a credible reported-model claim.

## Proposed bounded implementation

This is the frozen design proposal; provider selection remains unimplemented here.
It does not authorize a model call.

1. **One explicit provider selection.** Add a generation-local immutable
   `GenerationProviderBinding` around an existing parsed `ProviderSettings`, the
   exact requested model, producer family, and source references. The binding has
   its own explicit version and digest. Prefer a small source-bound input record
   `original_native_generation_provider_binding/v1`; it is configuration for the
   existing generator, not a reviewer installation or new authority store. Reuse
   the settings loader's field/type validation. No raw credential field is allowed.
2. **Bind the actual family.** The record names a reviewed source for the exact
   provider/model-to-family relationship. Preserve the existing reviewed panel
   source for current Ollama models; custom producer bindings require their own
   explicit source rather than adding an unqualified reviewer to that panel.
   Unknown Hermes ancestry stays unqualified for independent-family counting.
   Provider ownership and model family are distinct fields.
3. **Resolve credentials through existing mechanisms.** Use a credential reference
   resolved in process immediately before building the provider; never put a key
   in run configuration, argv, source prompts, generated files, or event records.
   A Tactical reference may be added to the operator credential mechanism by the
   parent after the route is verified. The discovered file is not a reason to
   duplicate a secret-loading framework inside the generator.
4. **Verified endpoint and exact capacity.** Build the isolated ProviderSpec from
   that one endpoint and retain hostname validation. Record provider metadata or
   the reviewed provider configuration that supplies output capacity, its byte
   digest, retrieval date and exact model/endpoint binding. A successful model
   listing does not by itself establish capacity. Unknown capacity fails before
   dispatch under the existing generator policy. An explicit output allocation
   cannot manufacture a model maximum or token-count upper bound.
5. **Persist reproducibility.** Advance the existing generation run version when
   its active binding fields change, retaining historical files and rejecting old
   resume rather than inferring defaults. Save the binding digest, secret-free
   settings digest, CA digest if applicable, family evidence digest, exact model,
   capacity source, route, and implementation hashes. Resume refuses changes to
   any of these. Keep existing response, prepared-tree, and package digests.
6. **One bounded gateway attempt.** Construct ModelGateway with only the selected
   ProviderSpec and ModelRoute; failover off, one route attempt, transport retries
   off. Preserve unknown token usage and physical-call accounting. One sequential
   pilot attempt precedes a larger run; an unknown outcome, identity mismatch,
   authentication fault, or transport failure stops it with the saved evidence.
   There is no silent switch to Ollama.

The existing token bound resolver remains the contract for a strict total-token
ceiling. If the endpoint supplies no qualified bound, do not pretend an output
limit also bounds input. Any alternative use of the generator's explicitly
unbounded-total mode is a separate run-budget decision for the parent.

## Required checks before a pilot

| Known-wrong control | Expected behavior |
|---|---|
| Custom provider selected but only Ollama credential exists | No Ollama invocation; custom credential refusal before dispatch. |
| Bound settings, endpoint, CA or family source bytes change | Refuse preflight/resume before request. |
| Configured provider/model differs from binding | Refuse; no inferred alias normalization. |
| Unknown capacity, capacity from another model, or unjustified token bound | Refuse before request. |
| TLS hostname mismatch | No credential-bearing request; no automatic skip or alternate host. |
| Native class adapter rather than module adapter | Hash the owning adapter source and proceed through the same gateway fixture. |
| Response omits identity, changes it midstream, or reports another model | Preserve observed/unknown identity, save failure and usage, produce no candidate. |
| Provider omits usage or a dispatch is interrupted | Unknown remains unknown; stop with a reservation or unknown outcome, never claim zero cost. |
| Frozen binding is valid and fixture returns exact model and complete draft | Same native factory, package identity, quarantine and zero approvals. |
| Built-in Ollama fixture uses its reviewed binding | Continues through the same selection code without custom-provider exceptions. |

The first live run needs a verified current HTTPS route, exact `/hermes` model ID,
capacity evidence, frozen provider binding and package plan, then the parent's
bounded call authorization. The pending endpoint clarification does not block
package planning, offline generator adapter tests, or review calibration.
