# Codex research and delivery checkpoint, September 23, 2026

This is a dated continuation record. The [roadmap](../roadmap/roadmap.yaml)
remains authoritative. The shared checkout has concurrent work. The assembled
Codex tree is `/home/username/.le-codex-build/integration`; recheck its revision,
dirty state and current checks before continuing.

## Terminology and architecture

The owner chose **Harness Working Directory Compiler**, using harness alone.
Use **Harness Working Directory Package** and **Harness Working Directory File**
for precise backend descriptions. Both glossary copies map these to existing
`CataloguePackage` and `CataloguePackageFile` contracts. Serialized identities
and `harness_local` remain unchanged. Compiler engines are implementations;
harness compatibility profiles are passive data.

- [Component design](../architecture/HARNESS-WORKING-DIRECTORY-COMPILER-2026-09-23.md)
- [Material hierarchy](../research/HARNESS-MATERIAL-HIERARCHY-AND-COMPILER-ENGINES-2026-09-23.md)
- [Profiles and handshakes](../research/HARNESS-AGENT-COMPILER-PROFILES-AND-HANDSHAKES-2026-09-23.md)

Two draft schemas and twelve synthetic fixtures extend existing record families.
They activate no compiler, registry or scheduled job. Path construction does
not prove native discovery. Known incompatible bindings must stop new starts;
active attempts follow supervisor policy. New semantics may require code.

## External research

- [Agent Harness compatibility](../research/MADEBYWILD-AGENT-HARNESS-COMPATIBILITY-AND-ADOPTION-2026-09-23.md): exact source, four-provider rendering, five Codex prompt cases and an isolated repeat.
- [Agent Harness ownership](../research/MADEBYWILD-AGENT-HARNESS-ARCHITECTURE-AND-OWNERSHIP-2026-09-23.md): fifteen bounded controls for drift, deletion, partial writes, binary conversion, inheritance and substitution.
- [OpenMuse](../research/OPENMUSE-COMPONENT-ENGINE-REUSE-2026-09-23.md): exact source and seven isolated checks. Sample mode now also requires CopilotKit Intelligence; generated-tool registry remains planned.
- [Ecosystem standards](../research/HARNESS-ECOSYSTEM-STANDARDS-AND-ENGINE-CHOICES-2026-09-23.md): packaging, protocols, provenance, evaluation, durability and presentation.

Correction to the first Agent Harness note: the lock does contain rendered
output hashes. It still needs independent post-write and native verification.
Prefer staged compilation through Baltor's confined writer. No upstream issue,
message or contribution was posted.

## Live deployment

Fly release 21 is complete from checked main
`1920296c00ced18e47992ae05237f4a2923666f0`, workflow 35888814908, image
`sha256:4c82835554d45d22efa6a56753da2039a51e34278f1e6e5c3408524984b56857`.
The deployment enable setting is false again. Release 20 remains the rollback
image. See the [release record](../../artifacts/architecture-audit-2026-09-19/pilot-release-21-codex.json).

The homepage pill is removed. Packaged assets have versioned direct references,
caching, ETags and HEAD support; HTML and dynamic responses remain no-store.
All eight hostnames passed read-only browser checks after the technical
hostname's exact-origin wording false positive was corrected. Catalogue checks
passed 6/6 and authenticated service checks 19/19. These bounded observations do
not establish load capacity.

Registration remains closed. Restored documentation and search effect selection
are assembled for the next checked release. The independently checked secure
signup flow is now integrated but remains disabled. The pure compiler is an
artifact-only prototype with sixteen tests and no active runtime registration.

## Generation and admission

The [Hermes plan](../../artifacts/original-native-generation-2026-09-23/hermes-hundred-file-plan.json)
has ten package requests and 100 planned payload paths. It passed existing plan
validation; it has not generated those files. Tactical's saved endpoint and
standard HTTPS port both fail hostname verification. No key was sent and no
Hermes call ran. The current endpoint question is pending. Exact model identity,
family and output capacity also need verification. See
[provider evidence](../verification/TACTICAL-HERMES-PROVIDER-BINDING-2026-09-23.md).

Earlier authorized Ollama generation made five physical requests and prepared
one seven-file MiniMax candidate. Four responses reported 39,465 tokens; timeout
usage and monetary cost remain unknown. Failures are preserved. The separate
repaired twelve-package cohort contains 96 payload paths and passed 302 independent
sandbox cases plus six contract replays. None is approved or added to the live
catalogue.

Whole-package preparation, review and calibration infrastructure is assembled.
Independent review repaired exclusion deletion, uncalibrated-reviewer eligibility
and exact-prompt binding defects. The real native pilot still needs applicable
benign-control loading evidence. Its tiny control set does not establish a
population error rate. See the [repair](../verification/CALIBRATION-EXPORT-ELIGIBILITY-REPAIR-2026-09-23.md)
and [independent review](../verification/NATIVE-REVIEW-CALIBRATION-INDEPENDENT-SUCCESSOR-QA-2026-09-23.md).

Do not publish the previously staged 114-item catalogue wholesale. Approval
conflicts and incorrect methods remain documented in the adjudication evidence.
Existing live approvals and newly generated candidates are separate counts.

Live signup readiness is now explicitly checked: Supabase public signup is
open, the live host lacks account-email configuration and its required secrets,
and password/sender qualification is incomplete. A Supabase integration was
found but is not connected here. No signup activation or email occurred. See
[the live readiness audit](../verification/SIGNUP-LIVE-READINESS-READONLY-2026-09-23.md).
