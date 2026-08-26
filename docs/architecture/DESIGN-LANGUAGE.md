# Loop Engine design language

Status: current design guidance.

Audience: anyone who writes or draws a public Loop Engine surface.

The goal is simple. A new reader should understand what Loop Engine builds,
what runs, and where reusable intelligence comes from without learning internal
project vocabulary first.

## 1. Explain the outcome first

Start with this path:

```text
Task -> Loop Practitioner -> Solution Canvas -> Result
```

Then explain the shared runtime and support system:

- One Loop object runs each executable graph vertex.
- Every Loop carries a versioned and digest-bound `LoopDefinition`.
- `LoopGraphDefinition` is the one authoritative static DAG.
- Each Loop has a selected mode and a step profile.
- Practitioner Loops build and test solutions.
- Intelligence Loops search, retrieve, frame, invoke, replay, and interpret.
- Solution Loops run the finished solution.
- A self-improvement Practitioner task reviews history and intelligence, then
  stages candidates.
- Core Architecture gives all three roles access to Intelligence Search and
  Retrieval, Web Research, and Custom Plugins when permitted.
- The Retrieval Engine searches classified records across all four layers.
- Custom Plugin discovery returns typed capability references without making
  the capability service a graph vertex.
- Four intelligence layers organize reusable knowledge.
- Runtime Memory carries temporary notes during one run.
- Run History, reports, and playback explain saved run history.

Do not open with the reference nine-step sequence. That sequence is one step
profile. It is not the product map.

## 2. Use the current component names

| Name | Meaning |
|---|---|
| Loop | The shared runtime object for one executable graph vertex. |
| Loop Practitioner | The role that understands, builds, and verifies work. |
| Practitioner Loop graph | The Loops and relationships used to build the work. |
| Solution Canvas | The declarative finished solution. |
| Solution Loop | One executable graph vertex in a Solution Canvas. |
| Self-improvement Practitioner task | A bounded task that reviews history, audits intelligence, and stages candidates. |
| Core Architecture | Intelligence Search and Retrieval, Web Research, and Custom Plugins. |
| Retrieval Engine | One search interface with lexical, vector, and hybrid modes. |
| Capability Directory | The search and handshake surface for executable services. |
| Intelligence Library | One searchable view across the four persistent intelligence layers. |
| Runtime Memory | The temporary note board for the current run. |
| Run History | Saved event history used by reports and playback. |

Use Starting, Spawned by, Queried by, Retrieved by, and Connected from for
Loop relationships. Use the exact relationship instead of a generic topology
term.

Do not use the bare word `Practitioner` as a public class name. Use Loop
Practitioner for the role. The package root does not expose a separate
role-specific runtime alias. Internal planning code is a service or algorithm
that runs inside a classified Loop, not another runtime.

## 3. Keep the three loop controls separate

| Public term | Current code | Meaning |
|---|---|---|
| Step profile | `framework`, `custom_steps`, Loop Template | The steps, their order, and repetition. |
| Effort setting | `power` | Bounded work limits such as iterations and model-call budget. |
| Operating settings | `OperatingProfile` | Permissions, provider access, and optimization preferences. |

Do not call all three a profile without a qualifier.

The four step profiles shown in introductions are:

1. Atomic code: one bounded action.
2. Compact: five steps.
3. Reference Practitioner: nine steps.
4. Custom: from 1 to 200 ordered steps, with repetition allowed.

The package currently contains 17 bundled Loop Templates. Fifteen are
registered and two are candidates. Candidate templates cannot run until they
are reviewed and registered. This is a fixed package library, not an external
template plugin registry.

## 4. Show the three modes in one order

Always use this order:

1. Deterministic
2. Hybrid
3. Non-deterministic

| Mode | Public explanation |
|---|---|
| Deterministic | Uses code, rules, calculation, and search. It does not call a language model. |
| Hybrid | Uses code first and may call a language model for a specific unresolved step. |
| Non-deterministic | A language model leads the step while the loop controls tools, limits, logging, and verification. |

Mode is a permission. Effort does not widen that permission.

When a detailed diagram shows several loops, show the mode on each loop. Do
not suggest that every loop inherits the same mode.

## 5. Show all four intelligence layers

Every system-level intelligence diagram must include:

1. Context Intelligence
2. Code Intelligence
3. Runtime History and Solution Intelligence
4. User Feedback Intelligence

Runtime Memory is separate because it is temporary and belongs to one run.

Code Intelligence currently includes conservative implemented-module
references. Do not imply that every item is an independently registered and
invokable capability.

Runtime History and Solution Intelligence can be empty on a fresh installation. The
current catalog loads saved Run History summaries but does not yet load saved
`SolutionLibrary` assets into this layer.

## 6. Describe extensions honestly

The package has built-in adapters and explicit registration points for areas
such as providers, resolvers, capabilities, and stores. Retrieval provides a
fixed selectable set of built-in backends behind one interface.

External plugins are potential future packages. The current release does not
auto-discover Python entry-point plugins and does not provide a plugin
marketplace. A diagram must not show potential plugins as installed features.

## 7. Visual tokens

Mode is the first color axis on diagrams, Canvas nodes, Studio labels, and run
rows.

| Token | Light | Dark | Meaning |
|---|---|---|---|
| `--mode-det` | `#155E54` | `#4EC0AE` | Deterministic |
| `--mode-hyb` | `#1B6E8F` | `#4FB0D6` | Hybrid |
| `--mode-mod` | `#B4690E` | `#E8A33D` | Non-deterministic |
| `--ink` | `#1A2129` | `#E8EDF2` | Text |
| `--paper` | `#FAFBF9` | `#12161B` | Background |
| `--line` | `#D5DAD6` | `#2A323B` | Rules and edges |
| `--candidate` | dashed border with low-opacity fill | same | Candidate or unreviewed work |
| `--verify` | `#C23B3B` | `#E06C6C` | Verification failures and refusals only |

Use Bricolage Grotesque for display text, IBM Plex Sans for body text, and IBM
Plex Mono for code and data. Use tabular numbers for aligned measurements.

Do not use color as the only signal. Repeat the mode or status in text.

## 8. Diagram order

Use the figure order in
[Architecture visual guidance](ARCHITECTURE-VISUAL-GUIDANCE.md):

1. Bird's-eye system map
2. One Loop object
3. Practitioner Loop graph
4. Solution Canvas
5. Self-improvement Practitioner task
6. Core Architecture and intelligence layers
7. Run history

Canvases use left-to-right graphs. Run History timelines are horizontal with the
newest event on the right. A reference nine-step figure can use a two-row rail,
but it appears only after the reader sees the full system.

## 9. Writing rules

- Use short sentences and ordinary verbs such as builds, starts, uses, tests,
  runs, saves, and searches.
- Define a technical term the first time it appears.
- Use report, log, contract, event history, or run record according to the
  actual meaning.
- Do not use unexplained abbreviations or internal route names.
- Do not call potential work shipped.
- Do not turn one successful run into a general success rate.
- Keep current behavior separate from planned behavior.
- Avoid ornamental punctuation. Use a period, comma, colon, or parentheses.

## 10. Review checklist

- The title describes what people can build.
- The first diagram starts with a task and ends with a result.
- Practitioner, Intelligence, and Solution are clearly shown as Loop roles.
- Self-improvement is clearly shown as a Practitioner task.
- The shared Loop object, modes, and step profiles are visible.
- The three Core Architecture capability groups and all four intelligence
  layers appear early.
- Providers, settings, workspaces, stores, history, and viewing are shown as
  internal runtime mechanics, not peer Core Architecture components.
- Runtime Memory is not drawn as a fifth persistent layer.
- Potential plugins are labeled as potential.
- The nine-step profile is presented as one option.
- Claims match current executable behavior.
- A new reader can understand every label without another document.
