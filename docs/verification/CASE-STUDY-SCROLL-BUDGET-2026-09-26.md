# Case-study scroll budget, September 26, 2026

Kind: scoped policy and verification record. Prepared in a detached worktree
from `13caeb20`; this record does not claim integration or deployment.

The owner approved longer pages: "We can increase our scroll length budget,
especially for pages like a case study." The three narrative case studies
now select a finite `case-study` budget in the site map: 6,000 pixels at
1440 by 900 and 11,253 pixels at 390 by 844. This gives the longest measured
study 880 desktop pixels for explanation and evidence. It is a deliberate
allowance, not the measured minimum.

The homepage and How it works retain their 4,000-pixel desktop limit;
ordinary pages retain 2,700. The detailed decision red-team report keeps its
existing documentation classification and introductory contents navigation.
No new unlimited category was added.

## Contract and implementation

The existing typed reader and the two browser consumers were reused. The
site map becomes `service_web_site_map/v3`, and the layout standard becomes
`service_web_layout_standard/v2`, with an explicit `case-study` enum value
and a required positive integer height. Earlier and future record versions
are refused. The old reader was also run against the new serialized records
and refused both versions.

Both browser consumers now calculate the phone limit as the desktop limit
divided by the desktop viewport height, multiplied by the phone screen
factor and phone viewport height, then rounded once. The showcase checker
previously rounded the number of desktop screens down first, disagreeing
with the layout checker and the written policy.

## Measurements and checks

Fresh local browser measurements used the service's current files, with no
CSS or JavaScript overrides, no real credentials, and no external requests.

| Page | Desktop height / limit | Phone height / limit |
|---|---:|---:|
| Homepage | 3,979 / 4,000 | 7,208 / 7,502 |
| Data cleanup study | 2,653 / 6,000 | 4,578 / 11,253 |
| Pi and Gemma 4 study | 2,351 / 6,000 | 3,258 / 11,253 |
| Sign-up protection study | 5,120 / 6,000 | 5,972 / 11,253 |

All eight measurements fit, with no document overflow or browser errors.
No case-study content was shortened.

The named regression
`test_case_studies_have_a_finite_budget_without_relaxing_the_homepage`
was added before the repair and failed because the budget was absent.
After the repair:

- `tools/test_website_site_map.py`: 17 tests passed.
- `tools/test_showcase_pages.py`: 6 tests passed.
- `tools/check_website_site_map.py`: 7 tests passed.
- The actual layout-checker decision functions passed all 11 known-wrong
  controls; both showcase budget checks passed.
- A case study one pixel over either limit was refused. Replacing its limit
  with a billion pixels, raising the homepage limit, or restoring the old
  phone rounding each failed a named regression check.
- JavaScript syntax checks, generated roadmap and tracker checks, and
  `git diff --check` passed.

Evidence, screenshots, failed attempts and the patch are kept together under
`/home/username/baltor-private/ui-deploy-20260926/case-study-budget-v1`.
The compatibility proof is `old-reader-refusals-v2.json`; the earlier attempt
used the transformed JavaScript record and is not the version-refusal proof.

## Deployment scope

This changes validation policy and packaged typed records. The runtime
site-map reader must move with its new record version, so it is not a
standalone edit to a development script. No served CSS or JavaScript asset
changed. Rendered HTML hashes are identical for all 56 site-map pages before
and after the change, including after regenerating public status data.

The current release and its validation export were not edited. There was no
push or deployment. The follow-up can be integrated after that release with
its normal exact-revision checks; it does not change the visitor interface.
