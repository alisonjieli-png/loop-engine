# Takeover checkpoint: September 20, 2026

Kind: development checkpoint written by Claude Code after it took over from
the previous developer session. It records what was checked, what changed and
how work continues. It does not close a launch gate or grant authority. The
machine-readable work authority is [roadmap.yaml](../roadmap/roadmap.yaml).

The previous developer session (OpenAI Codex, working as Astra) ran from
September 19 at 09:49 to September 20 at 15:25 local time and stopped at its
usage limit while it prepared a release. Its own records are the
[September 20 checkpoint](DEVELOPMENT-CHECKPOINT-2026-09-20.md) and the
[Fable 5.1 handoff](FABLE-5-1-HANDOFF-2026-09-20.md). Both remain valid as
dated snapshots. This document corrects and extends them.

**Forward pointer, September 21, 2026 (added after):** the harness-first owner
decision postdates this checkpoint. The live serving state it describes
predates the family policy. For state after September 21 read
[the day handoff](SESSION-HANDOFF-2026-09-21.md) and its
[evening addendum](SESSION-HANDOFF-2026-09-21-EVENING.md), which record the
harness-only serving policy, the intelligence layers as open folders, and the
checkpoint branch resting at revision `a3bd0f1`.

## What was checked

Observed by read-only queries and by an isolated rerun of the check suites.

| Subject | Result |
|---|---|
| Running release at takeover | Fly release 7, image `sha256:7b45d327faba2e65829230e8ee4f91109207183b4575cdab08c545aae6af55e8`, one Machine in `iad`, one encrypted 1 GB volume with daily snapshots kept for five days. |
| Running release now | Release 8, image `sha256:a2d31be073025fcc4f6f0ad86ef743eeffbd36d8d65671855d7298260862ce0a`, built by the guarded workflow from revision `e63f614` after its continuous integration run passed. See the [release record](../../artifacts/architecture-audit-2026-09-19/pilot-release-8.json). |
| Live capabilities | Operator-issued keys only. Browser sign-in, registration, billing webhook, checkout and portal are off. Search is text search over granted items. The catalogue holds one diagnostic record. |
| Hostnames | `baltor.ai`, `www.baltor.ai`, `app.baltor.ai` and `baltor-pilot.fly.dev` serve the same release with valid certificates. Cloudflare answers the zone and records are not proxied. |
| Providers | Resend sender `auth.baltor.ai` is partially verified. The Supabase project has no tables, migrations or buckets. Nothing has been created in the Stripe sandbox. The GitHub `pilot` environment exists with deployment switched off. |
| Public language | No forbidden term appears on the live homepage, How it works page or footer. Runtime terms appear only in the Documentation view. |
| Source control | Until this takeover nothing from September 19 and 20 was committed. Releases one to seven were built from an uncommitted working tree on one workstation. |
| Previous developer's commands | No git write command and no destructive delete in any of its four project sessions. |
| Secrets | No credential value in the repository, including ignored folders. |
| Check suites | 30 of 30 conformance gates, 5,990 self-test checks, 206 tool tests, 336 focused checks with five of five removed-guard controls, 131 browser checks and 156 service checks passed. Two suites failed; see the next section. |

The earlier code review found no loosened gate. The 566 changed lines in
`forbidden_paths.json` are a reformat plus exact network registrations, and
the earlier allowlist additions are exact entries.

## What was wrong and what changed

Each repair has a check that fails when the repair is removed.

| Finding | Repair | Evidence |
|---|---|---|
| The release candidate stored personal client keys under the first key record version. After a rollback, release 7 would keep honoring a key whose owner's sign-in was disabled. | Personal keys use an owner-bound record version that an older release refuses. The current release refuses a mismatch between version and profile. | `tools/check_rollback_key_version.py` ran the real release 7 image against both states: [rollback drill](../../artifacts/architecture-audit-2026-09-19/rollback-key-version-1.json). Seven new access checks. |
| A forged sign-in token with an unknown key identifier forced one read of the identity provider's keys for each request, inside a pool of eight workers. | Reads are paused between attempts and never wait on each other. Key rotation still recovers after the pause. | `forged_key_identifiers_cannot_force_a_key_set_read_per_request` and its removed-pause control. |
| The subscription reader sent the payment secret through any proxy named in the environment. Every other client ignored such settings. | The reader now ignores them too. | Two provider checks, one of them the known-wrong default. |
| A durable write that contained a tuple was committed and then reported as an unknown outcome, on SQLite and DuckDB. | The confirmation compares stored forms. | New durable checks in `catalog/versioning.py` and `core/shared_memory_scopes.py`. |
| Two negative controls for exported solutions no longer failed when their guard was removed. | Direct controls for the content scan and for the strict isolated interpreter. | Both mutants now fail a named check. |
| The rewritten coding-agent route dropped the link to the dimension discovery addendum, which a test protects. | Link restored. | Embodiment suite, 106 tests. |
| 120 hardcoding findings in new files were not registered, so continuous integration would fail. | 116 exact entries with reasons, three literals repaired in source, and one exclusion bound to the contents of the packaged browser library. | The gate exits with success; the tool's own canaries pass. |
| The packaged browser library was served without its licence terms. | The notices are served and linked from the footer. | `packaged_browser_library_is_served_with_its_licence_terms`. |
| One network registration granted nothing. | Removed. | Conformance scan stays clean. |
| Roadmap notes contradicted each other about whether the account code was deployed, and two blocked steps named accounts that now exist. | Notes reconciled with the observed state. A recorded rule about reason assignments was changed on September 19 without a record; the change and its reason are now recorded in step S-2.37. | [Generated status](../roadmap/CONTINUATION-STATUS.md). |

## Known open findings

These are not repaired yet. Each belongs to an existing roadmap step.

| Finding | Owning work |
|---|---|
| The hosted service and the local solving path are not joined. No client has been observed loading a retrieved body. | D-06 and D-17 |
| The catalogue has one diagnostic record. The packaged records are mostly one sentence long and use internal vocabulary. | S-6.10 and D-17 |
| The serving path does not refuse an item without a known licence. | D-17 |
| There is no request limit for each address. | D-13 and D-17 |
| A monitoring-only DMARC record was added on September 20 ([record](../../artifacts/architecture-audit-2026-09-19/domain-mail-policy-1.json)). The bare domain still has no sender policy, the DMARC policy should be tightened only after sending is verified, and two of the sender's four records were still pending at the mail provider. | D-02 |
| A model-judged guardrail rule at provisioning time refuses with no path to resolve it. | S-6.2 |
| Derived training rows are kept only inside the outcome document. | S-6.3 |
| A subscription event removes paid access until the provider's current state is read again, so a short provider outage during a renewal interrupts a paying customer. This is a product decision to make before billing opens. | D-04 |
| The browser keeps its session in page memory without refresh, so a reload or the one-hour token lifetime signs a person out. | D-10 |
| The administrator key expires on October 20, 2026. | D-15 |
| Two self-test checks need name resolution for `example.com`, and the self-test summary prints a fixed count of provider calls instead of a measured one. | S-6.27 |
| The generated status reports no next eligible work because its selection rule needs verified dependencies. | S-6.17 |
| The previous developer's session records hold credentials that the owner pasted into that conversation, and those files are readable by other local accounts. They are outside this repository. | Owner decision |

## Private beta

No earlier document defined the beta. Package D-17 in the roadmap now does.

An invited person signs in to a personal account, creates and revokes
personal client keys, connects a supported client with copied settings, finds
and downloads useful starter material, and sees usage. The operator invites,
disables and restores. There is no payment, no public registration and no
model call by the service.

```text
Private beta path
├── Done
│   ├── Live pilot on three hostnames
│   ├── Operator-issued keys, tenant separation, revocation and usage records
│   ├── Account and personal-key code, checked against the real identity provider
│   └── Release blockers from this checkpoint
├── Engineering next
│   ├── Release 8 from a committed revision
│   ├── Browser sign-in for prepared accounts, registration closed
│   ├── Invitation command that returns a single-use password link
│   ├── Starter catalogue compiled into skill-sized, licensed items
│   ├── Request limit for each address
│   └── One native client that demonstrably loads selected material
└── Needs the owner
    ├── Approval of each starter item before publication
    ├── The first invited people and a support contact
    ├── A short privacy statement and beta terms
    └── Model-call authority for one checked task, when that proof is wanted
```

Payments, PostgreSQL, private file storage, learned search and outgoing email
are not needed for the beta. They remain required for a paid public launch.

## Working cycle

One cycle serves development, checkpoints and releases. A later stage never
replaces an earlier one.

```text
Cycle
├── 1. Change
│   ├── Read the owning component guide and the roadmap step
│   ├── Write the check for the known-wrong case first
│   └── Run the smallest owning check, then the owning suite
├── 2. Test
│   ├── Focused: service smoke, owning self-tests, tool tests
│   ├── Gates: conformance, hardcoding audit, embodiment suite
│   ├── Full: self-test, examples, clean installation, browser checks
│   └── A removed guard must fail a named check
├── 3. Checkpoint
│   ├── Update roadmap.yaml and regenerate the status file
│   ├── Save each report under a new name; never overwrite a failed attempt
│   ├── Commit to main with the checks named in the message
│   └── Confirm that continuous integration passed for that revision
└── 4. Release
    ├── Only from a committed revision whose checks passed
    ├── Build the image from an export of that revision
    ├── Run the container checks and the rollback drill against the running release
    ├── Deploy by image digest, then run the hosted checks on every hostname
    └── Record the release, its revision and its digests; keep the previous image
```

Commands, run from the repository root:

```bash
PYTHONPATH=src .venv/bin/python -m loop_engine service smoke
PYTHONPATH=src .venv/bin/python -m loop_engine --conformance
PYTHONPATH=src .venv/bin/python -m loop_engine --self-test
PYTHONPATH=src:tools .venv/bin/python -m unittest discover -s tools -p 'test_*.py'
PYTHONPATH=src:devtools .venv/bin/python -m unittest discover -s devtools/embodiment_lab/tests
PYTHONPATH=devtools/src .venv/bin/python -m loop_engine_devtools.cli --hardcoding-audit \
  --allowlist devtools/hardcoding-allowlist.yaml \
  --baseline devtools/hardcoding-ci-baseline.json --fail-on-new high
PYTHONPATH=src:tools .venv/bin/python tools/build_continuation_status.py --check
.venv/bin/python tools/check_rollback_key_version.py \
  --older-image IMAGE_OF_THE_RUNNING_RELEASE --output NEW_REPORT_PATH
```

The conformance and self-test commands rewrite
`src/loop_engine/architecture_conformance.json` and one context manifest.
The rewrite is identical when nothing changed. Commit the rewritten files
with the change that caused them.

To see what a running release contains, extract it from its image. Git could
not answer this for releases one to seven:

```bash
docker create --name inspect-release IMAGE
docker cp inspect-release:/usr/local/lib/python3.12/site-packages/loop_engine/core/service_runtime ./release
docker rm inspect-release
```

## Credentials

The [credential handoff](../guides/developer-credential-handoff.md) stays in
force. Credential values live in the workstation keyring and in provider
authorization stores, never in the repository. The reference manifest is
[operator_credentials.json](../../tools/operator_credentials.json). Provider
secrets for the running service are environment references in the host
configuration on the volume; the platform's secret list is empty today
because no provider integration is switched on.

The session that continues this work can destroy the application, its only
volume and the domain's name server delegation through the prepared
connections. Treat every destroy, delete, secret and name server operation as
needing the owner's confirmation in the current conversation.

## Next steps in order

1. Done: the reviewed work is on `main` and continuous integration passes.
2. Done: release 8 was built from that revision by the guarded workflow and
   passes the hosted checks on all four hostnames.
3. Switch on browser sign-in for prepared accounts and add the invitation
   command. Keep registration closed.
4. Compile the starter catalogue as candidates and ask the owner to approve
   each item.
5. Add the request limit for each address and the licence refusal.
6. Prove native loading with one client, then run the invited-user journey.
7. Add the DMARC record and finish the sender checks, so that email sign-up
   can follow the beta.
