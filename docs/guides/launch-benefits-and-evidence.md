# Launch benefits and evidence

Kind: proposed product messaging and publication checks. The owner requested
these themes on September 20, 2026. They are not claims of measured savings,
overnight completion or perfect context selection.

## Positioning

Keep the overall promise about reusable solutions:

> Turn complex problems into solutions you can use again.

The three supporting messages below describe the intended product. They can
guide implementation and customer research now. A live feature claim needs
the matching release evidence before publication.

| Draft benefit | Supporting explanation | Current limitation |
|---|---|---|
| Put your models to work overnight. | Give a complex task time to make progress with models running on your own machine, within the limits you set. | No overnight local-model task population has been qualified for this release. Completion by morning is not guaranteed. |
| Spend fewer tokens on repeated work. | Reuse suitable code and pass relevant information to each step instead of regenerating everything or resending the whole history. | Input and output savings have not been measured for the complete release. Some tasks need more context or verification. |
| Give each step the expertise it needs. | Select useful guidance, tools and past findings for the work at hand, and request more information when a gap appears. | Selection can miss or misunderstand material. Relevance and a downloaded file do not prove successful use. |

Do not substitute "always the right amount" or "significant savings" for
these drafts before evidence exists. The intent is not to weaken the benefit:
it is to make the promised behavior something the product can demonstrate.

Code reuse can reduce newly generated output. Context selection can reduce
repeated input. Those are different mechanisms and need separate accounting.
Local models still use time, memory, electricity and tokens, even without a
hosted model invoice. No API bill does not mean no cost.

## Public explanation

Use "each step" on How it works. Describe a concrete task, its selected
information, allowed tools and checked result. A reader should not need to
understand agents, harnesses, graphs, runtime types or internal role names.

The technical documentation and GitHub explain exact architecture, contracts
and configuration. Keep the complete runtime definitions there. This is a
separation of audiences, not a change to implementation names or semantics.
The current technical route is `/docs`; a documentation subdomain is planned,
not deployed. Do not send readers to a nonexistent hostname.

## Evidence required for the overnight message

Choose a declared population of real, bounded tasks before a run. Include
work that should finish, work that must request information, and work that
must refuse an effect. Record exact model identity, hardware, memory limits,
task inputs, permitted network access, evaluator and intended run duration.

Test real elapsed overnight operation separately from accelerated lifecycle
checks. Cover process crash, computer restart, sleep, provider unavailability,
expired credentials, full disk, cancellation and a result that fails review.
Never repeat an uncertain external action after restart. Persist remaining
limits, partial files, failures and the exact point of resumption.

The morning report should distinguish accepted results, useful unfinished
work, required decisions and exhausted limits. Report all attempted tasks
and their outcomes, not only completed examples. Do not claim local inference
if any model call silently used a remote provider.

## Evidence required for the token message

Freeze the baseline, task population, model and provider, evaluation checks,
quality tolerance and allowed effects before comparing configurations. Use
paired trials and enough repetitions to describe variability. Keep a final
evaluation set out of optimization and preserve all excluded and failed runs.

Count every physical call, including selection, embedding, reranking,
delegated work, repair and verification. Report input, cached input, output
and provider-reported reasoning usage separately when available. Do not add
overlapping categories twice. Missing usage remains unknown, never zero.

Compare task acceptance as well as tokens, cost, elapsed time, memory and
retrieval overhead. Show aggregate results and task-level regressions. A
cheaper unfinished answer is not a successful optimization. Any percentage
belongs to the exact measured population, model and release, not all tasks.

## Evidence required for the expertise message

Define the supported domains and independently reviewed material first.
Test permission filtering, license state, source age, conflicting guidance,
compatible code dependencies and missing required resources. Record material
that was retrieved, selected, loaded, used and helpful as different findings.

Compare useful context against absent, excessive, stale and misleading
context. Include a task that benefits from adding material, not just removing
it. Measure independently checked task success, retrieval coverage, loading
failures and cost. A high similarity score is not an expertise certificate.

## Publication decision

The existing roadmap owns the work and the main HTML displays these drafts.
An independently reviewed report and exact release binding must support any
stronger public wording. Without that report, retain a clearly described
product direction and the actual private-pilot capabilities.

Keep useful examples and customer evidence ahead of more slogans. Do not
claim to replace every specialist, solve any problem, optimize every model
choice or improve every day merely because the architecture allows trials.
