# Loop Engine continuous component conformance prompt

Run this after each meaningful code batch or commit.

```text
Review the files changed since the last green checkpoint, then inspect their
transitive architecture interactions.

1. Did the change create or imply another runtime or active LoopNode?

2. Is every new semantic building block a typed, versioned, digestable passive
   component or an existing low-level implementation detail?

3. Does every independently governed operation execute through Loop?

4. Is any static component executing, calling a provider, reading hidden
   files, mutating itself, or granting authority?

5. Could a new class be a parameter, profile, policy, strategy, adapter,
   procedure, passive component, or composition instead?

6. Did settings, intelligence, prompts, handoffs, events, results, or reports
   bypass their canonical component and serialization contracts?

7. Did task-specific logic enter a generic path?

8. Did stable behavior move into a long string, f-string, arbitrary JSON or
   dictionary, synonym lookup, or print statement?

9. Does prompt preparation use LLMWorkPacket, selected Context Intelligence,
   the existing PromptAssemblySpec, a deterministic assembly Loop, a saved
   assembly snapshot, ModelGateway, and typed validation?

10. Are global, long-, medium-, short-, parent-, and local task relationships
    distinct? Can the receiver request more context without receiving private
    scratch or unrelated data?

11. Is availability-by-reference distinct from materialization and placement
    in the current model context?

12. Does deterministic work require canonical schemas?

13. Does hybrid work preserve and pass the deterministic attempt?

14. Does model-led work return typed proposals rather than authority?

15. Are the four intelligence layers, Core/Learned/Plugin namespaces, and nine
    functional domains still distinct?

16. Is LoopGraphDefinition still the sole reusable graph authority?

17. Are SolutionCanvas, procedures, packets, prompts, settings, questions,
    intelligence, events, and results still passive?

18. Did the change update the component glossary, data dictionary,
    interaction dictionary, folder map, and tests?

19. Does it generalize across wording, languages, domains, providers, models,
    outputs, risk, and context availability?

20. What adversarial mutation would expose the most likely shortcut?

21. Does every semantic value exposure and transformation have a logical Loop,
    with native operations confined to the intrinsic kernel or an exact final
    adapter boundary?

22. If pure atomic Loops are fused or cached, are all logical definitions,
    Loop IDs, digests, provenance, and failure locations preserved?

For every violation, add a failing test, repair the architecture, run focused
tests and conformance, and run a clean-install smoke when public behavior
changed.

Do not approve until all four statements are true:

NO NEW ARCHITECTURE REGRESSION
NO NEW EXAMPLE-SPECIFIC HARDCODING
NO NEW UNTYPED COMPONENT BOUNDARY
NO NEW CONTEXT-HANDOFF LEAK
```
