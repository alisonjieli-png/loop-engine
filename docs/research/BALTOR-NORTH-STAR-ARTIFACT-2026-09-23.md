# Baltor north star: accepted work from focused harnesses

Kind: dated companion artifact for the Baltor System Handbook. Prepared
September 23, 2026. This page explains the owner's product direction; it is
not a second roadmap, a performance claim, or a replacement for the
[repository instructions](../../AGENTS.md) and
[architecture constitution](../architecture/CONSTITUTION.md). The
[roadmap](../roadmap/roadmap.yaml) owns task state.

## The goal

The owner's September 22 direction is to make coding harnesses and
multi-agent systems efficient enough to become a frontier harness, a frontier
multi-agent system, or a frontier fabric for unseen work. Each focused step
should receive the information, reusable code, tools, model capability, time,
and permissions it needs. A smaller or local model should be able to finish
more useful work, including bounded work left running overnight. The work may
be software, research, data analysis, or another task. Reusing a completed
solution is one benefit, not the goal itself. This is the intended destination,
not an achieved performance classification. See the
[owner's north star and current initiatives](../../AGENTS.md#north-star-and-current-initiatives).

**Success means work accepted by an independent task check within the
customer's declared limits.** Fewer tokens, model calls, steps, or dollars
are useful only if quality, authority, safety, and completion remain
acceptable. Some tasks need more context, more verification, or several model
calls. An honest no-answer or request for missing authority can be the
correct result. The [launch evidence guide](../guides/launch-benefits-and-evidence.md)
separates these hypotheses from measured benefits.

## The product in one customer sentence

Baltor helps a customer's own harness and models work through a task one
focused step at a time, supplying reviewed information, native files and
reusable code for that step, then checking what the step actually achieved.

The product has two sides:

```text
Baltor
├── Hosted intelligence service
│   ├── Search and retrieve approved, versioned packages
│   └── Control account access, releases, rights and withdrawal
└── Customer-side Loop Engine
    ├── Govern a task and its focused steps
    ├── Start a fresh, qualified harness for each step by default
    ├── Use the customer's selected model endpoints and allowed tools
    └── Verify results and retain scoped Run History
```

The hosted service does not need to hold the customer's provider keys or
reach a model at `127.0.0.1`. The customer-side engine owns those connections
and the task's effect authority. This split is documented in the
[client and server map](../architecture/MVP-CLIENT-SERVER.md) and the
[credential research](CUSTOMER-ENDPOINTS-AND-CREDENTIAL-DELEGATION-2026-09-22.md).

## Who uses it, and for what

| Customer | Concrete job | Result that matters |
|---|---|---|
| Individual developer | Leave a bounded issue or test repair running with a local model; inspect the morning result. | A patch and test result accepted under the developer's file, tool and spending limits, or a precise unresolved finding. |
| Engineering team | Reuse reviewed project guidance, code and tool connections across many focused assignments. | Less repeated setup with a traceable package version and clear ownership of edits and external effects. |
| Agentic system builder | Give a complex task to smaller models through separately governed steps. | More accepted tasks per declared resource budget without passing an entire history or credential set to every step. |
| Data or research practitioner | Apply a verified procedure to a bounded input, then request a new step when evidence is missing. | An independently checked artifact, with source, method and limits recorded. |

These are target jobs and acceptance examples, not customer testimonials or
reported outcomes. The [private beta definition](../../AGENTS.md#north-star-and-current-initiatives)
prioritizes developers, teams and agentic systems; the other row is an
application of the same architecture. The first demonstrations named by the
owner are overnight local-model work on tickets, a data-cleaning task, and a
data-science competition from task to submission.

## The operating principles

1. **Give each step its own governed assignment.** The default fresh harness
   starts with only the relevant brief and selected material. It does not
   inherit a long conversation merely because the previous step ran.
   The complete technical behavior, including continuation and alternative
   outputs, is in [ASTRA](../../ASTRA.md#complete-behavioral-explanation).
2. **Keep the library central and the step context small.** Search returns
   compact typed references. Select by task need, permissions, client and
   model compatibility, then load exact approved bytes. The full library
   does not enter one harness. A missing item should yield a useful no-answer
   result rather than a weak match presented as expertise.
3. **Reuse work when its contract fits.** Reviewed code, tools, skills,
   instructions, references and prior solutions can avoid rewriting. A
   package may hold several files; its name, labels or prose do not grant
   permission. The [harness intelligence rules](../../AGENTS.md#intelligence-rules)
   and [native placement study](NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
   define the distinction between a file's presence, discovery, load, use
   and verified benefit.
4. **Choose capability under explicit authority.** A model or harness choice
   depends on declared compatibility, available endpoint, task quality
   evidence and customer limits. A classification model or a multi-model
   disagreement strategy may help one decision, but neither may add model
   calls or spending outside the run contract. The
   [engine design](../architecture/ENGINES-BEHIND-FIXED-EDGES.md) keeps those
   mechanisms replaceable.
5. **Learn without self-approval.** Run History and customer feedback can
   suggest a better method, package, route or context policy. Generated or
   imported material stays a candidate until an independent process approves
   its exact bytes. A successful run does not promote its own tool.

## Outcomes to prove, not promises already earned

| Hypothesis | Comparison that would support it | Guard against a misleading win |
|---|---|---|
| Small or local models can finish more tasks with focused context and reusable intelligence. | Paired accepted-task rate on a frozen task population, same model and authority, with and without the selected material. | Include every failure and the cost of search, materialization, repair and verification. |
| A fresh harness avoids harmful accumulated context. | Compare fresh-per-step and continued-session arms with matched tasks, model, tools and budgets. | Measure quality as well as input size; sometimes earlier context is necessary. |
| Reusing code and procedures lowers total work. | Count accepted results, newly generated output, physical model usage, elapsed time and review effort. | A copied or stale procedure that fails acceptance is not a saving. |
| Work can continue overnight within the customer's limits. | Run real elapsed overnight tasks with crash, sleep, outage, cancellation and uncertain-effect cases. | Report useful unfinished work and all attempts, not only morning successes. |
| A growing library improves retrieval and task outcomes. | Measure held-out relevance, no-answer accuracy, native pickup, accepted results and withdrawal behavior as releases grow. | Count active approved packages separately from files, renderings, drafts and fetched-but-unused items. |

These tests follow the [benefit evidence guide](../guides/launch-benefits-and-evidence.md)
and [full-system benchmark rule](../../AGENTS.md#evidence-and-benchmarks).
The planned first milestone is 10,000 and the target is 100,000 distinct
approved harness-intelligence packages in an active release. The owner also
wants the file count visible as a separate measure. Package count alone does
not establish search quality, native use or customer value. The current
[SaaS and library synthesis](SAAS-AND-HUNDRED-THOUSAND-EXECUTION-GATES-2026-09-22.md)
records the gap between the live service and those targets.

## Status and handbook use

The September 22 [live audit](../verification/SAAS-LIVE-READINESS-AND-CUSTOMER-JOURNEY-2026-09-22.md)
found a reachable pilot with 43 packaged single Markdown bodies, but no
observed customer journey that fetched selected material, loaded it in a
native harness, used it, and finished an independently accepted step. It
also found public registration, sign-up email, checkout and the portal off
in the audited deployment. Candidate batches and local native probes are
research evidence, not served inventory or measured frontier performance.

Use this artifact as the handbook's product-intent page. Link the
[architecture companion](BALTOR-ARCHITECTURE-ARTIFACT-2026-09-23.md) for the
technical shape, the [roadmap](../roadmap/roadmap.yaml) for work status, and
the [benefit evidence guide](../guides/launch-benefits-and-evidence.md) for
publishable claims. Recheck the newest release evidence before copying any
present-tense sentence into a public page.
