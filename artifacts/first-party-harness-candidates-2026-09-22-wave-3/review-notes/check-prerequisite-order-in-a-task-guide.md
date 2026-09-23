# Candidate review: check prerequisite order in a task guide

Status: candidate only. No independent approval, native load, licence assignment, or measured benefit.

- Source and originality: Original procedure written for this batch. Need inspiration is task `27-3042.00 / 3966` in the pinned [O*NET® 31.0 Database inventory](../../occupation-grid-research-2026-09-22/README.md) by the U.S. Department of Labor, Employment and Training Administration, under [Creative Commons Attribution 4.0](https://www.onetcenter.org/license_db.html). No task prose or third-party skill text was copied; the agency did not approve or test this candidate.
- Facets: Technical writer, developer experience, support guide; reader's starting state and product revision matter more than company name.
- Typed input/output concept: `OrderedStep[]`, `ReaderStartingState`, `Prerequisite[]`, `EffectPermission[]` to `PrerequisiteOrderReport` and `RepairSuggestion[]`.
- Effects: Read-only guide analysis. No execution of guide steps, access grant or edit.
- Good fixture: A procedure asks for a scoped access reference in step 2 but does not provision or request it until step 5. The report identifies the backward dependency and recommends moving the prerequisite before first use.
- Known-wrong fixture: A review marks the guide usable because each command is syntactically correct, while a fresh reader cannot complete step 2 without a credential created later. The method must reject the usable-guide claim even though the commands themselves are valid.
- Search phrasings: “Will a new user have everything needed before each setup step?”; “This guide mentions an access key before it tells people how to obtain one.”
- Nearest overlap and distinction: Starter `hand_over_a_result_its_consumer_can_use` addresses a final handoff. The release-guide audit in this batch checks factual drift. This method checks temporal dependency order and recovery from a stated reader starting state, independent of release drift.
- Limits: It needs actual starting permissions and environment version. It cannot prove a guide works without a later authorized reader trial.
