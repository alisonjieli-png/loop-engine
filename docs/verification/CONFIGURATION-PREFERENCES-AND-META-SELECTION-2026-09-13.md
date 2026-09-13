# Configuration preference and meta-selection verification

The configuration extension supports sourced setting facts, atomic in-memory
dataclass changes, and advisory preference engines. A preference Loop can
choose another preference or search engine before configurations are ranked.
It does not automatically launch an optimal model and harness combination.

The [configuration preference guide](../guides/configuration-preferences-and-meta-selection.md)
describes the current interfaces and proposed extensions. The
[saved summary](../../artifacts/configuration-preferences-20260913-cjiFnr/summary.json)
and [source manifest](../../artifacts/configuration-preferences-20260913-cjiFnr/source-manifest.json)
identify this verification snapshot.

## Scope and source identity

The parent revision at publication was
`6251f89a14dd678beae14792fdc9a1a1fe821b23`. The extension was not yet committed
when the package was frozen. The source manifest binds the exact package,
build configuration, README, and license used for the clean installation.
Its wheel digest is
`226b11b115fa8b3bf1c4971bd7ee22fee410f5ad3095d7691a9249bfded6c25e`.

Another Claude session continued editing harness fallback and response
evaluation after the freeze. Those uncommitted edits are outside this
verification claim and outside this extension's publication scope. The
generated architecture report also changed when conformance ran. The owned
configuration source files still matched the frozen package at publication.

No live provider was called. No real task from the task database was executed.
The model invocation control uses a declared offline provider fixture.

## Results

| Check | Result |
|---|---|
| Setting capabilities and application | 38/38. |
| Preference and meta-selection | 31/31. |
| Existing parameter-resolution regression checks | 16/16. |
| Existing harness-selection checks | 31/31. |
| Existing model-routing checks | 14/14. |
| Boundary registry checks | 9/9. |
| Full source self-test | 4,539/4,539 reported suite records. |
| Clean-wheel self-test | 4,504/4,504 reported suite records. |
| Source and clean-wheel architecture conformance | 27/27 gates in each environment. |
| Repository conformance | Passed, 515 indexed source files, no reported problems. |
| Development laboratory | 48/48. |
| Selector-to-search composition | 6/6 corrected controls. |
| Installed optional optimizer controls | 15/15 with Optuna 5.0.0 and cmaes 0.12.0. |
| Edited documentation | Markdown checks and prose checks passed. |

Suite totals include explicit records for optional adapters that were not
exercised. The source suite did not install Optuna or cmaes. The base-wheel
environment also lacked the listed numerical, retrieval, telemetry, and
external-tool extras. The saved self-test summaries identify each missing
optional adapter. The separate optimizer controls exercised the installed
optimizer implementations; missing dependencies were not counted as model
or optimizer quality evidence.

The new checks cover explicit source precedence, zero, false, null, empty
values, stale target digests, unavailable and unqualified settings,
authority-bearing fields, phase and mode incompatibility, ordered alternatives,
atomic refusal, sensitive-value reports, and actual field propagation through
the existing gateway fixture. They also cover invalid and stale preference
proposals, unavailable engines, explicit fallback triggers, cycle refusal,
and hard-rejected harness choices.

The six search methods are exact enumeration, random search, vector warm
start, Bayesian search, evolutionary search, and covariance adaptation.
The controls explicitly choose each method and confirm that its proposals
come through the existing search boundary. They do not train a meta-selector
or compare task-solving quality.

## Failed controls and corrections

The first selector-to-search run passed five of six controls. The vector
fixture supplied only configurations already observed on the target task.
The search boundary correctly excluded them and returned no new proposal,
which failed the control's expectation of a nonempty result. The corrected
fixture supplied distinct candidate configurations. Both the
[first result](../../artifacts/configuration-preferences-20260913-cjiFnr/optimizer-composition-first.json)
and [corrected result](../../artifacts/configuration-preferences-20260913-cjiFnr/optimizer-composition.json)
remain available.

Early local checks exposed incomplete fixture interfaces, a comparison of
run-local Loop identifiers from separate runs, and a short module docstring.
The fixtures and shared-parent control were corrected before the final
verification. An initial development-laboratory command omitted its import
path; the recorded final command supplies `src:devtools` and passes.

Review also found two precedence defects. The existing parameter resolver
treated an explicit zero confidence threshold as if it were unspecified.
The new setter initially removed a repository default while considering a
lower-priority agent proposal. Both were corrected and have regression checks.

## Limits

Capability source references are host attestations. They do not autonomously
prove provider support, availability, or qualification. The embedding owner
must supply honest, current facts and construct an eligible candidate set
through the existing checks.

Custom preference callbacks are trusted deterministic host code. A supplied
agent proposal is data from a separate operation, not a hidden provider call.
Native file, environment, command, and remote configuration setters remain
unimplemented by this interface. Distributed commits, automatic joint model
and harness binding, and autonomous live selector portfolios remain open.

This report establishes neither broad grid coverage nor a generally superior
selector. It makes no new artificial general intelligence, live learning,
task-quality, or provider-performance claim. Those claims require frozen real
tasks, authorized execution, independently qualified evaluators, and complete
outcome and usage records.
