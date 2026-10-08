# Kaggle metadata CLI qualification

October 8, 2026. The bounded CLI has read real competition, published-page
and notebook-list metadata into private records. It has not joined a
competition, accepted rules, submitted work, executed a notebook, downloaded
source/data/weights, published intelligence or started a schedule.

## Contract and existing implementation

The installed Kaggle distribution is 2.2.3 and its `kagglesdk` is 0.1.30 under
Python 3.14. Their local source was inspected before calling the service.
The [official repository README](https://github.com/Kaggle/kaggle-cli),
[user documentation](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md)
and [notebook commands](https://github.com/Kaggle/kaggle-cli/blob/main/docs/kernels.md)
were also read. This qualifies the inspected wheel contracts, not an invented
upstream Git revision or every command in the SDK.

The SDK uses fixed service POST routes on `api.kaggle.com/v1`. The implemented
read operations are `ListCompetitions`, `GetCompetition`,
`ListCompetitionPages`, `ListKernels` and `IntrospectToken`. Their enum names
and JSON field casing come from the installed generated types. The ordinary
SDK authentication path performs its own introspection; it was not invoked
implicitly by this adapter. That keeps the physical request count visible.

The native adapter reuses the existing query request/result and transport
boundary, canonical Loop and private CommunityStore. It creates no alternate
runtime, registry or queue. It is explicitly selected by the CLI, not added
to bulk query plans that would preserve raw source responses. Raw notebook
code and source-page prose do not enter the stored observations.

## Authentication proof and read population

The root session's initial legacy competition-list GET returned HTTP 200 and
an empty list. That established transport, not identity. A later documented
introspection POST returned `active: true` and an associated account name,
matching the SDK's own validity criterion. Only the boolean proof was
retained. The token, request body, account name, user identifier, scopes and
identity-bearing response bytes or digest were not stored.

The full qualification population contains fourteen physical read attempts
under a twenty-request ceiling, including that first root request. Calls were
serial, spaced at least one second apart, bounded to one MiB and did not
retry or follow redirects.

| Phase | Reads | Outcome |
| --- | ---: | --- |
| Root legacy list probe | 1 | HTTP 200, empty result, authentication unproved |
| Official documentation | 3 | HTTP 200, complete bounded text |
| Explicit token introspection | 1 | HTTP 200, active account token; identity discarded |
| Authenticated API qualification | 5 | Competition, search, pages and two notebook ordering probes answered 200 |
| Separate anonymous notebook control | 1 | HTTP 401; not retried |
| Implemented CLI acceptance reads | 3 | HTTP 200 for notebook metadata, pages and one competition |

The anonymous refusal did not show that the authenticated public-list results
were private. The SDK defines `EVERYONE` separately from its mixed
`PUBLIC_AND_USERS_PRIVATE` view. The caller authorized that documented view
for private discovery while retaining missing per-row evidence. The refusal
and the earlier overly strict projections remain in the private attempt
history. No anonymous fallback or repeated anonymous request was made.

The current API observed
[the Gemma 4 Good competition](https://www.kaggle.com/competitions/gemma-4-good-hackathon)
as identifier 134561, with deadline `2026-05-18T23:59:00Z`. The deadline has
passed. The documented all-competition search returned this competition and
one related community competition; that does not prove why the earlier
legacy query was empty.

The implemented CLI saved twenty-one unapproved metadata records: ten
notebooks, ten published page entries and the competition record. The ten
pages belong to one competition, not ten independent confirmations. Page
names do not establish a specific website permalink. Notebook rows provided
references, titles, last-run timestamps and sometimes vote counts, but no
per-row visibility or licence field. Those absences remain explicit. Votes
do not qualify quality, adoption or a reusable implementation.

## Rights, safety and remaining work

All results remain private discovery leads. A supplied licence label is a
lead, not a verified grant. Unknown notebook licences and repository revisions
must be resolved before any code reuse. The CLI has no source download,
public export, account mutation or notebook-execution operation. Source
content cannot change those capabilities or approve itself.

Offline checks cover strict selection, fixed method/host/path/body binding,
unknown versus explicit-private visibility, typed empty/failure/partial
results, bounded metadata projection, credential reflection, discarded
account fields, shared quotas, unknown-reset holds and compiler compatibility.
Removed-hold controls expose an extra dispatch, demonstrating that the guards
detect the fault. These checks are not a complete Kaggle integration test or
an independent review of the discovered projects.

Remaining work is source and licence review of selected private leads,
qualified adapter changes if the SDK contract changes, and an explicit
ongoing request allowance before a recurring discovery schedule. None of
these leads increases the served component-file count by itself.

## Exact local contract evidence

The installed source paths below are relative to their distribution roots.
Hashes identify the code inspected; no upstream implementation was copied.

| Source | SHA-256 |
| --- | --- |
| `kaggle/api/kaggle_api_extended.py` | `ba0cbbcfcbce9b7b42997de0b3ffa759144d95110cb073483a64e6b7d2fa4c96` |
| `kagglesdk/kaggle_http_client.py` | `45cc19fcb49e6ee0e5657019fff05c086f4ad0b43c071884d475f7335ae27054` |
| `kagglesdk/competitions/types/competition_api_service.py` | `cc40527dc138f7a8c1858c7eac9bd747cb0e57c64cd327b61b31f0f8bfc41cec` |
| `kagglesdk/kernels/types/kernels_api_service.py` | `976e21f945d85ef1787268d3b8099520755b8fef5718daadf279e97acf5d392a` |
| `kagglesdk/security/types/oauth_service.py` | `da147669309073590a60f6dbae75b1c4a1f345206acf497d73ff2140cc75b79d` |
