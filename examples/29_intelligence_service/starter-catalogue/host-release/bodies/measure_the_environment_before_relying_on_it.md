# Measure the environment before relying on it

Find out what this machine and this session actually offer by measuring. A capacity that was written down in advance describes some other machine.

## When to use it

Use it before planning work that depends on memory, disk, processors, data size, installed tools or network access.

## Steps

1. List the folders, files, data and tools that are present. Mark each one as inspected or assumed, and name what it is for.
2. Decide where the work happens. Name the working directory, what must be staged into it, and what must be true of it before acting.
3. Measure what the machine offers: processors, memory, free disk, tool versions and network access. Treat every capacity that was declared and not measured as unknown.
4. When one fact about the environment is unknown and matters, spend one cheap observation on it. Do not assume a default.
5. Measure the size of the input before choosing a method. When the size is unknown, prefer a form that processes the input in parts to one that must hold it whole.
6. Ask what changes when the input grows by three orders of magnitude.
7. Say where the time and the memory go from measurement, not from the shape of the code.
8. Name every source of variation that is not pinned, so that a second run on a second machine gives the same result.

## Checks

- Every capacity in the plan is marked as measured, with the command or call that measured it, or as unknown.
- No listed file or tool is marked as inspected without an observation.
- The plan states how it behaves when the input is larger than memory.

## Known-wrong example

A plan says that the machine has 64 gigabytes of memory. The number comes from a project document. The work runs in a container that is limited to 4 gigabytes. The job loads the whole file, runs for forty minutes and is killed. One measurement at the start would have shown the limit and selected a method that reads the file in parts.

## What to record

- The inventory with the inspected or assumed mark for each item.
- Each measurement with its value, its unit and its time.
- The capacities that remain unknown.

## Source

- `src/loop_engine/intelligence/context/core/practitioner_context_intelligence.yaml`: the guidance records about measuring and not declaring, probing the environment and streaming when the size is unknown, and the perspectives of the environment prober, the scale reasoner, the performance engineer and the reproducibility engineer.
- `src/loop_engine/strings/question_engine.py`: the question forms named `inventory_setting` and `workplace_setup`.

Licence: MIT. Compiled from revision 7ed4e85.
