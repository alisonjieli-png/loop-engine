# Candidate review: define-time-zone-reporting-window

Status: candidate only. The exact `packages/data/define-time-zone-reporting-window/SKILL.md` bytes need independent review before admission.

- Original authoring and source basis: Written for this batch by a Codex research subagent. The [Agent Skills specification](https://agentskills.io/specification) informed the file structure. [Python's `zoneinfo` documentation](https://docs.python.org/3/library/zoneinfo.html) confirms named-zone offset transitions and ambiguous local times; [IANA](https://www.iana.org/time-zones) provides the underlying time zone database. No external prose was copied. License and originality remain review decisions.
- Applicability facets: time-series reporting, usage billing analysis, operations dashboards, local business-day metrics; any geography with named-zone reporting.
- Search phrasings (author-supplied discovery aids, not evaluation queries): "How many signups belong to our New York business day when the clocks change?"; "Why do adjacent hourly reports both count the event at the boundary?"
- Typed input and output concept: Inputs are `LocalWindow`, boundary inclusion rules, `NamedZone`, `TimestampSemantics` including precision, and `AmbiguityPolicy`. Output is `ResolvedWindow` with absolute boundaries, event classifications, and elapsed duration.
- Declared effects: read-only analysis. The skill neither changes events nor fetches a time zone database.
- Known-good example: A half-open reporting day spanning an autumn offset change resolves its two local midnights independently. The resulting absolute interval can contain 25 elapsed hours, and an event exactly at the ending midnight is excluded under the supplied rule.
- Known-wrong example: Compute the second boundary by adding 24 hours to the first absolute boundary, losing one local hour on that day.
- Overlap search: Starter `design_a_request_and_response_contract.md` says to state a time zone; `build_an_incident_timeline_from_evidence.md` fixes one time zone for a timeline. Neither resolves reporting boundaries or tests daylight saving transitions.
- Limitations to check: The actual zone database version may be unavailable; an ambiguous input without a supplied policy must remain unresolved. Reviewers should test both autumn and spring transitions, a supplied inclusive end, and timestamps whose unknown precision prevents exact boundary classification.
