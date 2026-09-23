# Candidate review: audit a published guide against a release

Status: candidate only. No independent approval, native load, licence assignment, or measured benefit.

- Source and originality: Original procedure written for this batch. Need inspiration is task `27-3042.00 / 3970` in the pinned [O*NET® 31.0 Database inventory](../../occupation-grid-research-2026-09-22/README.md) by the U.S. Department of Labor, Employment and Training Administration, under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). No task prose or third-party skill text was copied; the agency did not approve or test this candidate.
- Facets: Technical writer, release engineer, product documentation; shipped revision and reader environment are required inputs.
- Typed input/output concept: `GuideRevision`, `ReleaseArtifact[]`, `Example[]`, `Audience` to `SectionDriftReport` and `ProposedCorrection[]`.
- Effects: Read-only publication review. No command execution, production access, documentation edit or release.
- Good fixture: A guide's setup section claims a feature is enabled by default. The pinned release configuration disables it; the report labels that sentence stale, cites the release artifact, and proposes the exact correction for a human editor.
- Known-wrong fixture: The guide is declared current because every example passed on a development branch, even though one command is absent from the published release. The method must reject current-release status for that section.
- Search phrasings: “Does this how-to match what customers actually downloaded?”; “Our documentation examples work on main but fail against the released version.”
- Nearest overlap and distinction: Batch one `match-a-product-claim-to-verified-capability` checks a single public claim. This method reviews a multi-section procedural guide, prerequisite and worked examples against one exact shipped revision.
- Limits: Release evidence may be missing or private. The skill marks unknown and cannot itself certify the public website or edit a customer document.
