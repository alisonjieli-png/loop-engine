# Publication and architecture review

Date: September 19, 2026. Scope: the consolidated report, its embedded data,
current architecture claims, public-content suitability, naming, and a targeted
serving counterexample. This is not a security certification or a complete
semantic review of all 623 Python files.

Follow-up, September 19 at 22:30 UTC: the in-flight metadata finding below has
a local repair. Search binds the grant revision used for the initial listing
and revalidates it with the principal at completion. Revocation, replacing the
same grants, and entitlement changes refuse the pending response. The
204-check `launch-slice-verification-3.json` includes those checks and five
removed-guard controls, including this disclosure boundary. It does not recall
bytes already sent, qualify a cloud deployment, or supersede the other findings.

## Decision

Keep the complete HTML as an internal engineering artifact. Publish smaller,
reviewed pages from the same source facts after a release is selected. Do not
publish the internal file unchanged or describe the product as a qualified
hosted service yet.

The owner reports owning `baltor.ai`. Baltor is a public-brand candidate, not an
approved repository or runtime rename. Keep Loop Engine, `loop-engine`, and
`loop_engine` unchanged until the owner makes a deliberate naming decision.

## Findings

| Priority | Finding and evidence | Disposition |
|---|---|---|
| Publication blocker | The measured HTML is 23,524,034 bytes. It embeds 2,488 file records, internal work and owner setup notes, plus compressed inventory and graph archives that expand to about 103 and 76 million bytes. A collapsed panel is not an access boundary. | Keep internal. A public exporter needs an explicit content allowlist, release identity and disclosure review. No secret-free public-export claim is made. |
| High | A real loopback request returned two metadata references after the fixture revoked that tenant's grants during ranking. The next request returned zero. No body disclosure or cross-tenant access was reproduced. | Locally repaired in the follow-up above. The original probe and failing observation are retained. Hosted qualification remains separate. |
| High | The historical matrices use N for both undocumented and documented-absent features. Loop Engine's Y cells include features without live integration evidence. | Preserve as dated research in the internal artifact. Do not reuse them as a public superiority claim without a new cell-by-cell review and distinct unknown/absent states. |
| High | The harness layout creates instructions, assignment and provisioning records plus empty folders. `bodies_included` is false; file placement is not evidence that a native harness loaded it. | Public docs must show offered, fetched, placed, loaded, used and accepted as separate states. Avoid an all-harness support claim. |
| High | AutoRAG 2 has a documented candidate interface, not an installed Loop Engine adapter or measured learning gain. The local default vector path uses deterministic hashing rather than semantic embeddings. | Describe the current retrieval profile accurately. Keep self-improving retrieval and external engine replacement in the research/integration section. |
| Medium | The solid-line diagram caption could be read as a live trace or complete end-to-end evidence. Some connected components are only partly integrated. | Clarify that arrows describe software relationships and identify the tested local profile separately. |
| Medium | Embedded guides are displayed as raw Markdown. This is inspectable internally, but headings, code fences and relative links are not a suitable public documentation reading experience. | Use a sanitized documentation renderer and portable links for public pages. Do not insert untrusted raw HTML. |
| Medium | Responsive browser tests run in desktop Chromium at narrow widths. They do not establish real-phone performance for this large payload. | Test a much smaller public bundle on representative mobile hardware and slow connections. |
| Medium | The new service commands and source changes are still in the working tree. The GitHub revision alone does not identify those changes. | Publish instructions against a committed, installed and verified release; keep the current working-tree label. No push or deployment has occurred. |
| Naming decision | Existing products use Loop Engine, including a music product and the separate `@loop-engine/sdk` project. Balto also operates an AI software business, and other businesses use Baltor. | Prefer the owner-held domain for evaluation, but complete a naming/confusion and appropriate trademark review before a commercial brand commitment. This search is not legal clearance. |

## Counterexample scope

The metadata probe used the existing `HttpDomainFixture`, a temporary SQLite
store and a real loopback HTTP request. An in-memory wrapper around
`Retriever.search` revoked the authorized tenant's grants after computing
ranked results and before returning to the transport. The response was 200
with two references; a subsequent request was 200 with zero references.

At probe time, `ServiceHttpApplication._search` revalidated the principal after
ranking, but did not bind the response to the grant revision used for listing. The
body-serving boundary has separate authorization and digest checks. The
finding therefore concerned in-flight metadata consistency, not a demonstrated
ability to download an unauthorized body. The earlier passing suite did not
contain this counterexample. The later repair adds it explicitly.

## Evidence retained

- `verification-attempt-2.json`: 5,765 executed checks passed, 15 optional
  checks not tested, source unchanged; the working package identity matched.
- `system-map-browser-attempt-1.json`: eight initial layout failures retained.
- Later browser runs pass after the redraw repair. The checks include a copied
  offline file, filters, keyboard controls, embedded archive downloads, and
  deliberately broken overlap and clipping controls.
- The two compressed downloads were decoded and matched their raw generated
  JSON projections exactly. No remote resource tags were present.

Passing tests support their exact cases. The repaired metadata path does not
erase the original counterexample, establish native harness benefit, or qualify
provider accounts.

## Domain checks

Registration Data Access Protocol lookups used the registry endpoints selected
from the [IANA bootstrap](https://data.iana.org/rdap/dns.json). These checks did
not register, purchase, transfer or change a domain.

| Name | September 19 observation | Meaning |
|---|---|---|
| `baltor.ai` | Owner reports ownership; this review did not verify registrar control or hosting. | Candidate to use, with no new registration needed if ownership is confirmed. |
| `loopengine.com` | Registry returned a registration record, expiring March 28, 2028. | Registered, not ordinary new-registration availability. |
| `loopengine.dev` | Registry returned a registration record, expiring February 21, 2027. | Registered; ownership must not be inferred. |
| `getloopengine.com` | Registry returned 404. | No registration record found, not a guaranteed availability or price quote. |
| `useloopengine.com` | Registry returned 404. | No registration record found, not a purchase recommendation. |
| `loopengine.app` | Registry returned 404. | No registration record found; registrar confirmation still required. |
| `loopengine.io` | No endpoint was found in the downloaded bootstrap. | Inconclusive; no availability claim. |

The first `getloopengine.com` probe tried to parse a non-JSON response and was
inconclusive. A status-aware retry established the 404 above. Results can
change, and no registrar checkout price was verified.

Relevant naming sources are the [Boss Loops software package documentation](https://www.bossloops.io/docs/packages/sdk),
[W. A. Production's Loop Engine](https://www.waproduction.com/plugins/view/loop-engine-2),
[Balto's own AI product site](https://www.balto.ai/), and
[Baltor Systems](https://baltor.co.uk/contact-us/). These establish existing use,
not a conclusion about legal rights or likelihood of confusion.
