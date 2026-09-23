# Review of the new library-wave roadmap entries

Kind: dated research review for Claude Code. Read against main `0d1f883`
on September 22, 2026 local time after the owner described a 10,000-item
library, reviewer models, catalogue releases, account settings and original
rewrites. The [roadmap](../roadmap/roadmap.yaml) remains the only task
authority. This review does not change a status, model allowance, source
right, approval decision or live service.
After this review, the owner clarified that the first 10,000 should be
original first-party packages. The
[original-package report](FIRST-PARTY-TEN-THOUSAND-HARNESS-PACKAGES-2026-09-22.md)
and current roadmap update supersede the supply order and S-6.64 wording
described in this snapshot. The serving, review and rights findings below
still apply.

Main now assigns S-6.62 to catalogue releases and settings, S-6.63 to the
multi-model review panel, and S-6.64 to original rewrites. Earlier Codex
drafts briefly used S-6.62 for model-conditioned intelligence; that local
roadmap edit was removed before the main-line fast-forward to avoid a
duplicate identifier. The
[model-conditioned research](MODEL-CONDITIONED-HARNESS-INTELLIGENCE-2026-09-22.md)
remains a proposal for Claude to schedule under the existing materialization
edge after source approval. It is not implemented by current S-6.62.

## Preserve the distinction between discovery and admission

The [10,000-item serving audit](TEN-THOUSAND-SEARCHABLE-HARNESS-FILES-2026-09-22.md)
names independent gates for rights, safety, approval, indexing, grants,
body reads, relevance and release rollback. The
[million-scale review](MILLION-SCALE-HARNESS-INTELLIGENCE-ADMISSION-2026-09-22.md)
shows why a discovered file, registry server or model rendering cannot
inflate the count of distinct approved active packages. The standing rule
requires a decision by reviewers independent of the producer on exact
bytes. This report additionally recommends calibrating any automated
three-model policy by item class before using it at scale.

| Roadmap row at the reviewed revision | Specific issue to resolve before its stronger claim | Suggested next evidence |
|---|---|---|
| S-6.40 scheduled ingestion | Its acceptance still says reviewed licensed items arrive continuously “without manual work,” while exact independent approval is mandatory. A random batch sample can estimate defects or hold a batch but cannot approve unsampled bytes. The cited millions of GitHub files and registry entries are not rights-eligible supply counts. | State which bounded, low-risk class a separately qualified automated reviewer may approve, which cases require a person, and the measured joint false approvals and rights holds. Count discovered, candidate, approved, active, indexed and helpful separately. |
| S-6.62 catalogue release | “Grants follow the packaged manifest” can overwrite account-specific withdrawal or resurrect a bad item during rollback. The current manifest loader caps one JSON file at 2 MB; a same-shape 10,000-item manifest is about 14.8 MB. The body builder accepts one Markdown file per item and derives release paths from basenames. | Freeze one versioned release and sparse deny policy; test an old image against a new durable withdrawal version, same-basename bodies, full 10,000-item manifest load and a paying account's authorized access. An old binary must already refuse an incompatible record, or rollback across that withdrawal is unavailable. |
| S-6.63 review panel | Three approvals from different model families do not by themselves measure shared-error rate, even if those three agree. A model cannot determine a copyright grant from a root licence badge or mutable endpoint metadata. Scanner `CAUTION` and incomplete results can still have a successful default process exit. | Pilot on a frozen malicious/benign challenge set and blinded stratified human adjudication of random approvals and refusals. Save reviewer/model/prompt/item digests, disagreements, abstentions, physical calls, output capacity, cost or unknown cost and confidence intervals by risk class. Keep ambiguous rights and executable remote effects pending for a person. |
| S-6.64 original rewrites | Never showing the source text to the generator and checking similarity reduces copying risk but does not itself establish independent authorship or permission. An outline can carry protected expression; a similarity scanner can miss it. Some restricted sources must remain metadata-only or held. | Use factual, licensed or independently authored inputs; require source/right review and an independent exact-byte decision. Compare the original item only where evaluation use is permitted. Refuse a candidate whose expression or rights remain uncertain. |
| S-6.32 and S-6.39 serving | Current search rebuilds its index per request, list is unpaged, and the default configurable response cap is 262,144 bytes. A public no-bulk policy cannot absolutely prevent a customer granted all bodies from retrieving them over time. | Reusable grant-filtered index, bounded listing, metadata versus protected-body search, exact-ID read of every approved item in an isolated host, held-out no-answer queries, and published rate/body allowances. |

An exact wording change for S-6.64's acceptance would be: **“Original
authored candidates inspired by restricted sources may be considered only
after factual-source provenance, separate rights review and independent
approval of exact bytes; restricted or uncertain material stays link-only
or held.”** The earlier wording that material the library may not copy
“still reaches customers” was too absolute. The current roadmap records a
separate rights gate. This is research reasoning, not a legal determination.

## Safety and source checks for the first batch

[GitHub's licensing guide](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
does not turn a public repository into a redistribution grant. The
[Copyright Office](https://www.copyright.gov/help/faq/faq-general.html)
distinguishes facts and methods from protected expression. An actual public
[PDF skill licence](https://github.com/anthropics/skills/blob/main/skills/pdf/LICENSE.txt)
forbids copying and derivatives, illustrating why nested files matter.
[AgentSync's catalog](https://github.com/dallay/agentsync/blob/main/README.md)
contains outside providers whose rights need review separate from
AgentSync's own files. The
[Model Context Protocol Registry](https://modelcontextprotocol.io/registry/about)
includes closed-source servers and delegates code scanning. A reviewed
**link card**, a reviewed **configuration template**, and a qualified
**executable connection** are different states.

[NVIDIA SkillSpector](https://github.com/NVIDIA/SkillSpector) can triage,
but its default successful exit includes CAUTION, and even `--no-llm` can
send dependency coordinates to OSV. Record its exact findings,
completeness, scanner version and permitted network recipient. The
[Agent Skills validator](https://agentskills.io/specification) checks
format, not rights or prompt safety. A malicious body can pass syntax.
Three reviewer approvals should be tested against a planted prompt that
fools all three, not treated as safety by vote count.
The roadmap's first 30-item review-panel pilot can test integration,
cursoring and accounting; it is too small to establish a low false-approval
rate for rare attack classes. The larger 1,000-item stage needs the
separate challenge and sampled real-batch adjudication above.

The first 1,000 should report approved yield and calls per reviewed item.
The proposed following two weeks need about 643 new approvals per day to
reach 10,000 from 1,000. Three reviewers imply at least 1,929 review calls
per day if every candidate passes, before retries or rights holds. Use
measured throughput and defect rates to set a date; no schedule follows
from source counts alone.

## Website and model-variant implications

The [post-release public check](../verification/LIVE-WEBSITE-POST-RELEASE-13-CHECK-2026-09-22.md)
found the old homepage aside absent on all three tested public hostnames.
The public waiting-list capability remained false and root `HEAD` returned
404. A future hero with an example beside the headline should be inspected
visually on desktop and mobile against the owner's earlier complaint about
a right-hand reading break; a width check and real example items do not
settle that user preference.

When the library grows, a customer should search logical approved items,
select one permitted exact package, then optionally receive a **separately
qualified** rendering for the model and harness actually running the step.
The [variant research](MODEL-CONDITIONED-HARNESS-INTELLIGENCE-2026-09-22.md)
defines the source and derivative digests, model revision, rights, protected
obligations, cache cost and fallback checks. Ten renderings of one item
must not add ten to the public distinct-item count.
