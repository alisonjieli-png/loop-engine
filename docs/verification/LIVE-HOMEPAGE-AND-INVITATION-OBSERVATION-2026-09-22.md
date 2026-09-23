# Live homepage and invitation observation

Kind: read-only public-site observation. Checked September 22, 2026 at
23:45 to 23:52 UTC and again September 23 at 00:09 UTC. This is a
point-in-time result for S-6.33 and S-6.35
in the [roadmap](../roadmap/roadmap.yaml), not a deployment change or a
claim about Claude Code's pending release. No account, credential, form
submission or paid operation was used.

## Method and result

An unauthenticated HTTP client fetched `https://baltor.ai/`,
`https://baltor.ai/signup`, and
`https://app.baltor.ai/api/v1/capabilities`. It also sent one `HEAD` to the
root hostname. The website checks used a fixed read-only user agent and did
not run browser JavaScript. The initial root and signup GET responses were
both HTTP 200 and had the same 69,778-byte HTML body with SHA-256 digest
`19e76cc9d76ebd5f63d367cc37876ae1d2f30781a6c50d3064998aff764a469c`.
The live root `HEAD` returned HTTP 404. The single-page application may
render different views after JavaScript routing; equal initial HTML bodies
alone do not prove the visible pages are the same.

The live HTML still contains the right-hand `solution-preview` aside headed
“Example workflow.” At the initial check, local main was `d66e892` and its
[homepage source](../../src/loop_engine/core/service_runtime/web_assets/index.html)
had SHA-256 digest
`742cceb7188cf8930b113e9e2ebf9e63402f637ded5d221e873496c92a46660f`
and contained no `solution-preview` or “Example workflow.” During this
research, main fast-forwarded to `9cdf99e`; its source digest became
`0b391835c462f03bfbd33cf4ddd2f4fc4f51a1aeb31ff94e9da428d93a2afa36`
and still has no old aside. It includes a conditional waiting-list form,
which is not proof the form is deployed or enabled. The 00:09 UTC live root recheck returned the
same 69,778-byte body and digest, so the repair had not reached that public
response by the later observation either.

The live hero, pricing and closing calls to action say “Join the waiting
list” and point to `/signup#waiting-list`. The served signup markup says the
waiting-list form is still being built and that it does not collect an email
address. A separate email signup form exists in the HTML but is initially
hidden. The live unauthenticated
[capabilities response](https://app.baltor.ai/api/v1/capabilities) reported
`website.registration_available: false` and
`website.access_profile: operator_provisioned`. The 00:09 UTC capabilities
recheck still reported those values and no `waitlist_available` field.
Together these observations
support a present invitation dead end for an unaffiliated visitor, not a
claim that no operator can invite anyone.

## Consequence and next check

S-6.33 owns the real invitation request and page flow. S-6.35 owns a checked
release and public hostname verification. After a committed, checked release,
repeat the GET, HEAD and browser journey on every live hostname. The known
wrong case is a homepage that promises a waiting list while the next page
collects no request, or a live page that still contains the old aside after
the repaired source was deployed. Record the deployed revision and image
digest with the result. Do not count a click on the current invitation link
as a submitted lead, and do not send paid traffic to that path until an
outside visitor can actually submit and receive confirmation.
