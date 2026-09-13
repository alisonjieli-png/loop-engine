# Crush diagnostic trial

Crush 0.92.0 is installed at
`/home/username/loop-engine/embodiments/crush/runtime/crush_0.92.0_Linux_x86_64/crush`.
The official source is [charmbracelet/crush](https://github.com/charmbracelet/crush).
This release uses FSL-1.1-MIT with a competing-use restriction. It is not counted
as an unrestricted open-source project.

The installed `crush run --quiet` command completed a private, isolated
OpenAI-compatible broker trial. Its configured native tools were absent from
the request. It made two requests: a title and a task answer. Native tool
enablement and injected-tool negative controls did not create the forbidden
file. Evidence is under
`/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y/remaining-recipes/crush/`.
Use `core-text-01/result.json`, `request-tools-01/result.json` and
`response-tools-01/result.json` for the final diagnostic controls.

This profile is not enabled as a canonical semantic embodiment. The engine
requires the original semantic packet in every model request, and the title
request does not meet that contract. No source-backed title-disable switch
was established. Renaming a session alone does not suppress it: this release
triggers title generation when prior real user text is absent. Do not weaken
the packet gate or invent a provider response to make this pass.

The diagnostic recipe is in
`/home/username/loop-engine/src/loop_engine/core/harness_remaining_recipes.py`.
It is not independent authority. Real inference would need the canonical
Ollama Cloud broker and a separately qualified auxiliary-free profile.
All saved calls here are local fixtures, not real model quality evidence.
