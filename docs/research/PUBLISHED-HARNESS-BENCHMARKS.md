# Published harness benchmark evidence

The reviewed sources do not support a claim that Loop Engine beats another
harness. Loop Engine has no independent published benchmark result.
The repository now matches its two saved full-system smoke results against
this catalog by exact comparison key. It finds zero fair matches. This is a
measured exclusion, not a claim that either system wins.

Deep Agents has the clearest published same-harness configuration studies in
this review.
Artificial Analysis provides an independent same-model comparison across
Opencode, Cursor CLI, and Claude Code.
Microsoft publishes a tau2-bench result for its Agent Framework Lab and base
Agent path, but that result does not measure the newer Harness bundle. A safety
paper compares OpenAI Agents SDK, Google ADK, and OpenClaw graphically on a small
matched subset. No qualifying numeric result was found for Pydantic AI Harness,
OpenAI Agents SDK general task performance, or the Microsoft Harness bundle.

## Search scope and freshness

This review was refreshed on 2026-08-25. It checked these primary or official
sources:

- Artificial Analysis Coding Agent Index v1.4 and its methodology text;
- two LangChain reports about Deep Agents harness changes;
- the HarnessAudit arXiv v2 paper, including Figure 8 and its framework adapter
  appendix;
- the Pydantic AI Harness issue and pull request named in the catalog;
- the official OpenAI Agents SDK repository and documentation;
- the official Microsoft Agent Framework repository, documentation, and pinned
  tau2 lab report;
- the official OpenAI GPT-5.3-Codex release page;
- the current public Loop Engine repository and its benchmark files.

This was a focused source review, not a claim that every page on the internet
was searched. A later published result may change a `no_qualifying_result_found`
finding.

## Numeric results found

| System | Benchmark and population | Model | Published score | Evidence limit |
|---|---|---|---:|---|
| Deep Agents CLI, baseline configuration | Terminal-Bench 2.0, all 89 tasks described by the source | gpt-5.2-codex | 52.8% | Harness-author report; exact code commit not stated |
| Deep Agents CLI, improved configuration | Terminal-Bench 2.0, same 89 tasks | gpt-5.2-codex | 66.5% | Several harness dimensions changed together |
| Deep Agents, base | Curated difficult tau2-bench subset, count not stated | GPT-5.3 Codex | 33% | Author-selected subset, not the full benchmark |
| Deep Agents, custom profile | Same stated subset | GPT-5.3 Codex | 53% | Profile changes include tool changes |
| Deep Agents, base | Curated difficult tau2-bench subset, count not stated | Claude Opus 4.7 | 43% | Author-selected subset, not the full benchmark |
| Deep Agents, custom profile | Same stated subset | Claude Opus 4.7 | 53% | Prompt profile changed |
| Microsoft Agent Framework Lab TaskRunner | tau2-bench airline domain, 50 tasks | gpt-5 agent and gpt-4.1 user simulator | 62.0% | Base Agent path, not `create_harness_agent` |
| Codex | Terminal-Bench 2.0, population count not stated | GPT-5.3-Codex xhigh | 77.3% | Different model and non-SDK harness |
| Opencode | Coding Agent Index v1.4, 326 tasks across three components | Claude Opus 4.7 medium | 51.28% | Exact harness release and tool inventory not exposed in page text |
| Cursor CLI | Same index, population, model, and effort | Claude Opus 4.7 medium | 46.66% | Exact harness release and tool inventory not exposed in page text |
| Claude Code | Same index, population, model, and effort | Claude Opus 4.7 medium | 42.39% | Exact harness release and tool inventory not exposed in page text |

## Independent same-model harness comparison

Artificial Analysis Coding Agent Index v1.4 holds Claude Opus 4.7 at medium
effort and compares three coding harnesses. The index covers DeepSWE with 113
tasks, Terminal-Bench 2.1 with 89 tasks, and SWE-Atlas-QnA with 124 tasks. Each
task has three attempts. Scores are averaged within each benchmark, then the
three benchmark scores receive equal weight.

| Harness | Index | DeepSWE | Terminal-Bench 2.1 | SWE-Atlas-QnA |
|---|---:|---:|---:|---:|
| Opencode | 51.28% | 39.53% | 78.28% | 36.02% |
| Cursor CLI | 46.66% | 31.56% | 74.53% | 33.87% |
| Claude Code | 42.39% | 27.43% | 77.15% | 22.58% |

This is the strongest cross-harness comparison in the reviewed evidence because
the model, effort, benchmark release, task population, evaluator, aggregation,
and managed external environments are fixed. Harness-native tools are allowed
to differ because they are part of the harness intervention.
[Artificial Analysis Coding Agent Index](https://artificialanalysis.ai/agents/coding-agents)

LangChain reports that its Deep Agents CLI score moved from 52.8% to 66.5%
on 89 Terminal-Bench 2.0 tasks while holding gpt-5.2-codex fixed. That is a
13.7 point change reported by the harness author. The article says prompts,
tools, middleware, context handling, and verification behavior changed, so it
does not isolate one causal feature. The machine-readable comparison therefore
records `tools_held_fixed: false`. [Primary LangChain report](https://www.langchain.com/blog/improving-deep-agents-with-harness-engineering)

The second LangChain report uses a curated difficult subset of tau2-bench. It
reports GPT-5.3 Codex moving from 33% to 53% and Claude Opus 4.7 moving from 43%
to 53%. The source does not publish the selected task ids or population count.
These values should not be presented as full tau2-bench scores.
[Primary LangChain profile report](https://www.langchain.com/blog/tuning-deep-agents-different-models)

Microsoft reports 62.0% on 50 airline tasks with a gpt-5 service agent and a
gpt-4.1 user simulator. The pinned source describes Agent Framework Lab's
TaskRunner and base Agent path. It is not evidence for the newer Harness bundle.
[Pinned Microsoft tau2 report](https://raw.githubusercontent.com/microsoft/agent-framework/6acab3d1d6e310c319859c585844871f56a0a8c7/python/packages/lab/tau2/README.md)

OpenAI reports 77.3% for GPT-5.3-Codex at xhigh reasoning on Terminal-Bench
2.0. This is useful context, but it is not an OpenAI Agents SDK score. It also
uses a different model from the Deep Agents Terminal-Bench study, and the page
does not state the task count. [Official OpenAI result](https://openai.com/index/introducing-gpt-5-3-codex/)

## Graphical safety result

HarnessAudit arXiv v2 compares OpenAI Agents SDK, Google ADK, and OpenClaw on
five matched tasks in Figure 8. The paper states that OpenAI Agents SDK and
Google ADK have higher safety adherence than OpenClaw across tool use, resource
access, and information flow. Exact Figure 8 values are graphical and not
tabulated in the paper text, so the catalog stores only the qualitative
ordering. The paper does not test Microsoft Agent Framework.
[HarnessAudit arXiv v2](https://arxiv.org/html/2605.14271v2)

## No qualifying result found

| Subject | Status on 2026-08-25 | Scope limit |
|---|---|---|
| Pydantic AI Harness | `no_qualifying_result_found` | Issue 120 and pull request 338 show evaluation work, but the reviewed live workflows were skipped |
| OpenAI Agents SDK general performance | `no_qualifying_result_found` | Testing and evaluation plumbing is not a published task score; Codex is a different harness |
| Microsoft `create_harness_agent` | `no_qualifying_result_found` | The tau2 lab score belongs to the base Agent path; HarnessAudit does not test Microsoft |
| Loop Engine | `no_qualifying_result_found` | Local tests and provider checks are not independent published benchmarks |

The reviewed Pydantic sources are
[issue 120](https://github.com/pydantic/pydantic-ai-harness/issues/120) and
[pull request 338](https://github.com/pydantic/pydantic-ai-harness/pull/338).
The OpenAI and Microsoft searches used their official
[OpenAI Agents SDK repository](https://github.com/openai/openai-agents-python)
and [Microsoft Agent Framework repository](https://github.com/microsoft/agent-framework).

No qualifying result found means the focused review did not find a result that
met this catalog's admission rules. It does not mean a score of zero.

## Comparison verdict

The catalog supports one independent same-model cross-harness group from
Artificial Analysis and three same-harness configuration studies for Deep
Agents. It does not place the other records into that group because their
benchmark release, population, model, effort, evaluator, or external environment
differs.

The current evidence therefore supports these narrow statements:

- LangChain reports meaningful score changes after modifying Deep Agents while
  holding the model fixed within each study.
- Artificial Analysis reports Opencode above Cursor CLI and Claude Code on its
  v1.4 composite while holding Claude Opus 4.7 medium fixed.
- HarnessAudit reports a qualitative safety ordering across three frameworks on
  a five-task matched subset.
- Microsoft publishes one Agent Framework Lab tau2 result that must not be
  attributed to its Harness bundle.
- No reviewed source establishes that Loop Engine is better than these systems.

## Unmeasured intelligence and reuse dimensions

None of the reviewed comparisons measures a governed four-layer intelligence
bank, cold-to-warm reuse, candidate promotion, or user-guidance retrieval. This
statement is limited to the sources reviewed on 2026-08-25. It identifies an
evaluation gap that Loop Engine would need to test independently. It is not
evidence that Loop Engine is better.

The machine-readable source is
[`published-harness-evidence.json`](../benchmarks/published-harness-evidence.json).
