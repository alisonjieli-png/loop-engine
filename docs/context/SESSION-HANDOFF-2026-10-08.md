# Baltor engineering and account handoff

Kind: October 8, 2026 continuation checkpoint. The
[roadmap](../roadmap/roadmap.yaml) owns task status, the
[delivery plan](../roadmap/DELIVERY-SEQUENCE.md) orders the work, and
[AGENTS.md](../../AGENTS.md#commit-push-and-release-authority) owns authority.
The owner is moving to another OpenAI account and wants the project, provider
setup, decisions and unfinished work to remain usable from local files.

## Read this first

The public service remains release 78 from `f9dbb3d3`. A later main commit
does not imply a later deployment. The
[current deployment record](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
owns source, image, rollback and host verification.

The live library has 1,353,029 distinct files. The 10-million target and the
request for one million additional files are unfinished. Public Good has
448 groups and 1,128 useful files across all 17 goals. All nine product
hostnames use the Cloudflare edge. File-body delivery and custom search still
run on Fly; customer identity still uses Supabase.

The owner-workstation pointer `/home/username/START-HERE-BALTOR.md` names the
private handoff, exact source/evidence paths and closing checkpoint. Open it
before touching the shared checkout. Its private research lineage and staged
work are not the public integration tree. No private transcript or credential
value belongs in this public record.

## Account and provider continuity

Use the same local files and OS keyring after changing OpenAI accounts.
Recheck access to cloud workspaces and connected apps on the new account.
Do not assume chats or provider connections migrate between accounts.

The installed CLI supports `codex login status`, `codex logout`,
`codex login` and `codex login --device-auth`. Finish or checkpoint other
Codex sessions before changing the shared login. Subscription sign-in and
OpenAI API-key billing are separate.
[Official authentication guide](https://learn.chatgpt.com/docs/auth)

From a reviewed checkout, run this non-secret inventory:

```bash
/usr/bin/python3 tools/operator_credentials.py inventory
```

It reports references, presence and format, not live API entitlement.
Ollama Cloud, Kaggle, Brave, Exa, Tavily, Serper, Jina, OpenAlex, Hugging Face
and the existing infrastructure references are available locally. The
Reddit34 alias exposes the pre-existing keyring item to the same inventory.
Anthropic and optional OpenCode Zen references are prepared but require keys.
The installed OpenCode has a saved Go connection; Go and Zen are distinct.

To supply a missing credential from the owner's interactive terminal:

```bash
/usr/bin/python3 tools/operator_credentials.py store --ref anthropic-model-primary
```

The prompt hides the value, stores it in Secret Service and refuses to overwrite
an existing item. Use `opencode-zen-primary` only for a separately selected
Zen credential. Existing Ollama and Kaggle access should be reused. No purchase,
automatic top-up or new model allowance follows from a reference declaration.
Claude Code sign-in does not establish direct Claude API access.

## Recovered engineering work

The frozen atomic factory ended at 08:48 UTC, 04:48 Eastern. Its journal
records 42 completed and five held cohorts; systemd reports exit 2. Earlier
notes saying the factory is active are stale. Preserve its v1 journal and
original limits. The repaired v2 runner must not resume that journal.

The morning lineage audit completed all 47 cohorts and verified 31,474
candidate records with no reported lineage findings. Exact comparison found
120,131 distinct payloads, of which 120,090 are absent from the current live
library. That includes 31,474 schema files, 25,666 distinct case files and
supporting documentation, attribution and shared files; it is not 120,090
independently different methods. The audit rechecked sources and candidate
bytes. All 31,474 candidates then passed seven prechecks, 220,318 checks in
total, across a completed 43-cohort slice and four-cohort continuation.
The earlier import-path failure and fifteen-minute timeout are retained.
Semantic comparison, generated-test execution, content admission and
publication remain separate. The 266,797
reported placements are not a served-file increment.

The constraint-case feature and its accounting/path repair are integrated into
the current candidate. The prior independent review approved code integration,
not candidate admission. Its fresh sample contains 1,131 distinct case files.
The preserved queue repair reserves remaining call allocations durably before
dispatch, refuses allowance resets and holds unknown outcomes.
The [queue procedure](../../tools/OVERNIGHT-QUEUE.md) explains status, interruption
and evidence-bound reconciliation. Its 26 focused checks passed in this session.
No model-driven overnight result follows from those tests.

## Website readers and social sources

`tools/read_trendshift.py` provides effect-free planning and an explicitly
authorized one-read operation. Public mode reads current daily structured
metadata; Signal mode needs its own existing subscription. Neither publishes
raw observations or installs a schedule.
[Trendshift Signal](https://trendshift.io/signal)

The October 8 18:02 UTC public CLI probe returned HTTP 200 after one GET and
parsed five of 25 rows. Its source-period date remained unknown. It published
nothing and sent no outreach. This proves the bounded direct reader, not the
Signal subscription or a generic browser bridge.

The existing Reddit34 reader has observed requests and private research-work
orders. Start by qualifying this integration's quota and source coverage.
RapidAPI app keys can separate analytics; subscriptions and usage are
account-wide. Qualify the exact product, host, endpoint, allowance and content
rights for each additional social source.
[RapidAPI key model](https://docs.rapidapi.com/docs/keys-and-key-rotation)

OpenCLI is a candidate for converting permitted browser reads into repeatable
commands. Its browser-backed adapters need the browser bridge and a usable
site session. Pin and inspect its source and licence, qualify a read-only
adapter and keep it behind the existing research edge. A generated adapter
is not evidence of a successful live read.
[OpenCLI source](https://github.com/jackwener/OpenCLI)

## Product decisions and remaining work

Keep Agent Feeds at the owner-set $4.99/month standard price, free through
December 31, 2026 Eastern, with paid enrollment opt-in. Agent Feeds supplies
dated decision material; the existing $29/month Agent Feeds + Harness Files
plan adds reusable working files. Use files in customer quantity language.
Retain group identities internally for dependencies and complete downloads.

Hosted feed customization needs saved topics, exclusions, source selection,
cadence, format, snapshot history, per-agent access and independent cursors.
Local profiles exist; customer-hosted settings and push delivery are unfinished.

Supervised Runs remains a proposed third offering. Pilot hosted coordination
with a paired worker, customer-held model access, bounded recovery and morning
reports. Prove interruption, duplicate delivery, isolation and revocation
before pricing. A cloud worker cannot directly use a customer's localhost.

Move verified body delivery to R2 after its customer canary. Evaluate
Workflows/Queues for collection and coordination, and D1 for bounded metadata.
Keep custom retrieval and accounting on their existing typed edges while
comparing alternatives. Cloudflare Access is suitable for operator access;
customer signup migration has separate identity and recovery requirements.
[Cloudflare Access](https://developers.cloudflare.com/learning-paths/clientless-access/access-application/create-access-app/)

TensorArt history, images/video/mesh workflows, editable marketing renders,
native OpenCode customer execution, matched benefit comparisons, wider source
feeds, funding material and the recent-session semantic review remain in the
delivery plan. Replit is optional for an isolated demonstration; it has no
measured advantage for the current production migration.

## Procedures and release evidence

Follow the existing
[working cycle](TAKEOVER-CHECKPOINT-2026-09-20.md#working-cycle).
For every batch, record exact source, attempts, failures, accepted outputs,
provider usage and remaining limits. Check the committed revision's CI before
deployment. Read one-shot operation records before retrying an uncertain effect.

The private closing checkpoint states this session's final Git and deployment
outcome. It also records the recent-context review's actual time window and
coverage. Do not describe the complete backlog, ten-million target or native
overnight proof as finished.
