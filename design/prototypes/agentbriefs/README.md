# AgentBriefs local design prototype

Review an executive decision workspace without connecting a company account.
The overview, CompanyDNA intake, example brief, evidence ledger and Decision
Memory run in the browser. All examples are fictional. Thresholds filter
three built-in scenarios; they do not discover opportunities or authorize work.

This directory is design material, not a registered service brand. It is not
packaged into the application, routed on Fly or published to a domain. The
selected name is AgentBriefs; ownership of `agentbriefs.si` remains unverified.
There is no price, signup, connector, upload, API call or experiment runner.

## Review locally

From this directory, run:

```bash
python3 serve_preview.py --port 0
```

Open the printed `http://127.0.0.1:PORT` address on the same computer. The
server binds only to loopback and serves four exact addresses for three files.
It does not expose the checkout, accept submissions or list directories.
Stop it with Ctrl+C when finished.

Use invented details in CompanyDNA. Applying a change updates browser memory
only. Reload resets the profile, thresholds and decisions. The fixed example
brief remains bound to its original context version; changing the profile
does not pretend to rerun research. A discussion or dismissal entry records
both the current review context and that original brief context.

## Independent presentation, shared backend

The navy workspace, navigation, copy and attention controls belong to
AgentBriefs. Baltor is not its navigation destination or umbrella interface.
The footer names the common operator, Baltor.AI. The design follows the
[owner decision](../../../docs/architecture/OWNER-DECISIONS.md#agentbriefs-executive-intelligence-proposal)
and the
[existing composition plan](../../../docs/architecture/CURRENT-ARCHITECTURE-MAP.md#proposed-agentbriefs-decision-support-composition).

Production integration must extend the existing owners below. These are
binding targets, not claims that AgentBriefs endpoints exist today.

| View or action | Shared owner and current contract | Missing binding and activation gate |
| --- | --- | --- |
| CompanyDNA intake | `RecordOperationService`, `record_operation_request/v1`, immutable `managed_record_revision/v1`; existing tenant access | Define the private company-context schema, namespace policy, source provenance, expected-version updates and retention. Enforce tenant ownership server-side. Review new personal-data uses before importing or retaining real context. |
| Evidence ledger | AgentFeeds source contracts, `tools/knowledge_radar`, managed research records and existing artifact stores | Bind observations to exact source, time, digest, access and company-context version. Separate source failure from an empty result. Quarantined newsletter content cannot become instructions or public material. |
| Candidate decisions | Typed decision engines in `core/decisions`, evaluation and acceptance contracts | Define category-specific evidence requirements, materiality, freshness and attention limits. Keep scores distinct from probability and measured benefit. Version policies and retain suppressed candidates for audit. |
| Decision brief | Existing artifact, evaluation and acceptance boundaries; managed revisions | Bind sources, assumptions, alternatives, uncertainty and next permitted action. A strategic development can be useful without code. An experimental-fit claim needs a baseline, tested conditions, artifacts and all attempts. |
| Proof of concept | Canonical Loop execution, existing task and solution-graph owners, `ModelGateway` and qualified sandbox profiles | Approve exact data, model access, resources, effects and acceptance checks separately. Record measured usage and unknown outcomes. The unreviewed Gemini portable-worker and reactive queue candidates are excluded. |
| Review actions and Decision Memory | `RecordOperationService`, `RunHistory`, `ProductOutcomeRef` and user-feedback owners | Create immutable, linked decisions and corrections under the tenant. Preserve original evidence. Later customer-reported benefit needs conditions and provenance; it is not an independently verified experiment. No fifth intelligence layer or second history store. |
| Notifications | Existing account access and permitted delivery boundaries | Add explicit recipient consent, deduplication, category and evidence gates, freshness and attention budgets. A score or company upload grants no permission to contact anyone. This prototype sends nothing. |
| Future account and service access | `ServiceHttpConfiguration`, `service_brand_profile/v1`, shared service/account/entitlement stores and OAuth boundary | Only after hostname ownership, explicit brand admission and per-origin qualification. Retain a separate issuer, MCP resource, return URLs and browser state over shared accounts. Shared backend does not mean cross-brand token reuse. |

Reference owners:

- [Managed records](../../../docs/components/managed-records/README.md)
- [Service presentation and access](../../../docs/components/service-runtime/README.md)
- [Typed contract index](../../../docs/contracts/README.md)
- [Canonical architecture map](../../../docs/architecture/CURRENT-ARCHITECTURE-MAP.md)

## Evidence and effects

The two fictional source references in the first brief share a publisher.
They are not independent corroboration. The scenario's importance numbers
are explicit design inputs, not performance measurements or success odds.
The experimental candidate has no result. Realized benefit stays unmeasured.

The local threshold evaluator is presentation logic. A production decision
edge needs a fixed typed, versioned contract and conforming engines in the
existing engine-slot registry. Language, execution runtime and placement are
separate choices. Every executable graph vertex remains a Loop; a UI card or
passive record is not another runtime.

Before backend activation, qualify one authorized company context and one
decision family end to end. Include a useful brief, a plausible unsupported
candidate that must stay withheld, a source outage, a failed experiment,
revoked access, tenant isolation, an unknown write outcome and a later
correction. Neither login nor a company subscription supplies model access,
connector permission or experiment authority. No ChatGPT plan entitlement is
assumed for this proposed service.

## Checks

The browser check starts its own loopback server and closes it afterwards.
It uses an existing Playwright installation and Chrome. It installs nothing.
From this directory:

```bash
node check.mjs /absolute/path/to/playwright-core/index.mjs /absolute/new/evidence-directory
```

The check covers desktop, tablet and phone layouts, visible headings, labels,
touch targets, keyboard focus, contrast, threshold behavior, missing-name
validation, markup injection, context-version disclosure, duplicate review
actions, reload reset and empty browser storage. It refuses off-origin
requests and checks that the app contains no outbound request or storage
API. This design has one light appearance. It is not a full
assistive-technology audit, real company workflow, backend integration test
or public deployment qualification.

The Sites skill supplied the local-only preview and teardown workflow. The
humanizer and project writing context informed the neutral executive copy
and the explicit evidence labels. No Sites project or hosting resource was
created.
