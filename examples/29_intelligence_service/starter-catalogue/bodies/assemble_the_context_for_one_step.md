# Assemble the context for one model step

Give a single model step exactly what that step needs to do its job, as named parts you can change one at a time.

## When to use it

Use it whenever you build a prompt for one step of a larger task, rather than handing a model the whole conversation and hoping.

## Steps

1. Write the job of this step in one sentence, with the output it must produce.
2. List the parts the step needs: the task as originally stated, the current state, the exact input to work on, the rules it must respect, the shape of the answer, and any examples.
3. Include the whole of anything the step must act on word for word. Summarising the input is how meaning is lost.
4. Refer to large material by a reference the step can fetch if it needs it, instead of pasting it.
5. Keep the parts separate and labelled, so you can add or remove one part and see what it was worth.
6. Put the instruction about what to do near the end, after the material, and say what the answer must look like.
7. Record which parts were included for this call, so a later comparison can attribute a difference to a part.
8. Check the assembled text yourself before sending. Read it as if you knew nothing else.

## Checks

- The step has one stated job and one stated output shape.
- Anything the step must act on is present in full.
- Each part is labelled and can be removed on its own.
- The parts included are recorded with the call.

## Known-wrong example

A summarising step is given the last forty messages of a conversation because that was easy. The model summarises the conversation instead of the document, because the document arrived twenty messages ago and is now half truncated. Naming the parts, and including the document in full as its own part, would have made the job clear and the result repeatable.

## What to record

- The job sentence and the output shape.
- The parts included and their sizes.
- The references used instead of pasted material.

## Source

- `src/loop_engine/core/llm_work_packet.py`: this repository builds a passive packet for one model step from labelled context blocks and one work directive, and the packet itself never performs the call.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision f29bddc.
