# Loop Engine prompts

Every prompt defers to the current repository, `AGENTS.md`, the Architecture
Constitution, machine-readable contracts, and enforcing tests. Load one prompt
for the active task. Do not concatenate several prompts into a larger mandate.

## Broad continuation

Use only the [universal solver continuation
brief](LOOP-ENGINE-UNIVERSAL-SOLVER-HANDOFF.md) for broad continued
development. It is model-neutral and is the sole broad continuation prompt.
Current checkout and test facts belong in a generated `session_handoff/v1`
packet, not in the prompt.

## Focused entry points

Choose one of these only when its scope exactly matches the task:

- [Universal component prompt suite](UNIVERSAL-COMPONENT-PROMPT-SUITE.md)
  routes a component change through implementation, independent review,
  ideation, and conformance prompts in separate sessions.
- [Ollama component qualification lab](OLLAMA-COMPONENT-QUALIFICATION-LAB.md)
  creates a separate black-box qualification repository.
- [Architecture showcase and video
  prompt](LOOP-ENGINE-ARCHITECTURE-VIDEO-BUILD-PROMPT.md) changes the
  presentation artifacts.

The focused entry points do not supplement the broad continuation brief in the
same session.

## Supporting guidance

These pages explain a concern. They are not additional session prompts:

- [Generalized self-tuning Loop
  guidance](GENERALIZED-LOOP-NODE-SELF-TUNING-GUIDANCE.md)
- [Adversarial component architecture
  review](ADVERSARIAL-COMPONENT-ARCHITECTURE-REVIEW.md)
- [Component ideation and
  conformity](COMPONENT-IDEATION-AND-CONFORMITY.md)
- [Continuous component
  conformance](CONTINUOUS-COMPONENT-CONFORMANCE.md)
- [Universal component implementation
  mandate](UNIVERSAL-COMPONENT-IMPLEMENTATION-MANDATE.md)

Load one of these only when the selected focused workflow calls for it.

## Design history

The following files preserve earlier mandates and research directions. They
are not current entry points. Some contain retired runtime, relationship,
intelligence, or Run History terms. Do not paste them into a new session:

- [AGI LoopNode network food for
  thought](AGI-LOOPNODE-NETWORK-SELF-ORIENTING-FOOD-FOR-THOUGHT.md)
- [Everything-is-a-Loop adversarial
  audit](LOOP-ENGINE-EVERYTHING-IS-A-LOOP-ADVERSARIAL-AUDIT.md)
- [Strict everything-is-a-Loop
  primitives](STRICT-EVERYTHING-IS-A-LOOP-PRIMITIVES.md)
- [Governing development
  prompt](LOOP-ENGINE-GOVERNING-DEVELOPMENT-PROMPT.md)
- [Self-orienting Code Intelligence master
  prompt](LOOP-ENGINE-SELF-ORIENTING-CODE-INTELLIGENCE-MASTER-PROMPT.md)
- [Cleanup and intelligence access
  prompt](LOOP-ENGINE-CLEANUP-AND-INTELLIGENCE-ACCESS-PROMPT.md)
- [Adversarial intelligence-seeking
  mandate](LOOP-ENGINE-ADVERSARIAL-INTELLIGENCE-SEEKING-MANDATE.md)
- [Plane-interaction mandate](LOOP-ENGINE-PLANE-INTERACTION-MANDATE.md)
- [LoopNode specification mandate](LOOP-ENGINE-LOOPNODE-SPEC-MANDATE.md)
- [Development Assurance Plane
  mandate](LOOP-ENGINE-DEVELOPMENT-ASSURANCE-PLANE-MANDATE.md)
- [Development Assurance Intelligence
  mandate](LOOP-ENGINE-DEVELOPMENT-ASSURANCE-INTELLIGENCE-MANDATE.md)
- [Development Engineering Assurance Planes
  mandate](LOOP-ENGINE-DEVELOPMENT-ENGINEERING-ASSURANCE-PLANES-MANDATE.md)
- [Parallel execution and microservice
  mandate](LOOP-ENGINE-PARALLEL-EXECUTION-MANDATE.md)
- [Intelligence Foundry and Capability Campaign
  mandate](LOOP-ENGINE-FOUNDRY-AND-CAMPAIGN-MANDATE.md)
- [Universal evolution prompt](LOOP-ENGINE-UNIVERSAL-EVOLUTION-PROMPT.md)

Always use `/home/username/loop-engine` as the workspace directory. Read the
current repository before acting because implementation and evidence may have
changed since a prompt was written.
