# Questions to ask before starting work

A short set of questions that lower the risk of a wrong result before any effort is spent. Each one has a fixed form, so it can be asked of a person, of a model or of yourself.

## When to use it

Use it after the task is understood and before the first real action, above all when the work is costly, hard to undo or new to you.

## Steps

1. Definition of done: state the exact observable condition that proves the work is complete, before starting.
2. Rejection test: state what a result would have to show for it to be rejected as wrong or incomplete.
3. Ambiguous words: name the words in the goal that are ambiguous and the exact meaning that success requires for each.
4. Unknowns: list every fact that is missing before it is safe to act, and rank which unknown blocks the most.
5. Assumptions: list every assumption that the current plan silently makes, and name the one that was examined least.
6. Cheapest check: name the cheapest single check that would most reduce the risk of a wrong result.
7. Smallest first step: name the smallest action that produces real evidence about feasibility before the full approach is committed.
8. Failure map: list the distinct ways the work could fail that would each need a different fix.
9. Reversibility: name the actions that are hard to undo when they turn out wrong, and the smaller reversible step that replaces each.
10. Resources: state the time, access, data and budget that each approach requires, and where the estimate is least certain.
11. Consumer: state who or what consumes the result, and what would make it useless to them.
12. Second order: state the new problem that success would create, and the further work that it forces.
13. Constraints: ask which stated constraint is actually optional and which unstated constraint binds hardest.

## Checks

- The definition of done and the rejection test are written down before the first action.
- Every question has an answer or is marked as unknown. None is skipped.
- At least one answer changed the plan. When none did, ask whether the answers were honest.

## Known-wrong example

An agent is asked to speed up a report. It spends a day rewriting queries and makes the report 30 percent faster. Nobody had written a definition of done. The person wanted the report before 8 in the morning, and a change of the schedule would have done it. The consumer question and the constraint question cost five minutes and would have found this.

## What to record

- The answers, with the time at which they were written.
- The definition of done and the rejection test, word for word.
- The changes that the answers made to the plan.

## Source

- `src/loop_engine/strings/question_engine.py`: the general purpose question forms, among them `done_definition`, `acceptance_inversion`, `definition_check`, `state_the_unknowns`, `assumption_audit`, `cheapest_check`, `smallest_first_step`, `failure_mode_map`, `reversibility`, `resource_horizon`, `stakeholder_view`, `second_order` and `constraint_inversion`.

Licence: MIT. Compiled from revision 7ed4e85.
