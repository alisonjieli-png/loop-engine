---
name: read-step-assignment
description: "Read the assignment of the current focused step from its packet in .baltor/step/: task fields, packet files, required result fields and earlier results. Use it first in a fresh session that holds a step packet, through the step packet tools or the local script."
license: MIT
compatibility: "Python 3.10 or later, standard library only, for the script. Reads .baltor/step/ under the workspace root and writes nothing."
metadata:
  version: "0.1.0"
---

# Read the step assignment

## When to use it

Use it at the start of a fresh session when the workspace has a
`.baltor/step/` folder. The packet in that folder is your whole assignment.
This skill only reads it; it changes no file.

## First action

Call the tool `read_step_assignment` with no arguments. If your client has no
such tool, run the script in this skill's `scripts/` folder from the
workspace root. In the plugin placement the command is:

```bash
python3 -I -B .baltor/plugins/portable-step-packet-plugin/skills/read-step-assignment/scripts/read_assignment.py
```

## Steps

1. Read `task.objective`. It is the only goal of this session.
2. Read `task.effects` and `task.model_calls_authorized`. Plan nothing that
   needs another effect or another model session.
3. Read `node_context.md`, then `checklist.md`: call `read_step_file` with
   the file name, or run the script again with `--file node_context.md`.
4. Note `output.required_fields`. The result must hold each of them, and
   only named fields when `output.extra_fields_allowed` is false.
5. Look at `results.count`. When it is above 0, an earlier session already
   wrote a result; read `node_context.md` for whether to improve it.
6. Write down, one line each: the objective, the first action from
   `node_context.md` and the required fields. Then start the work.

## Checks

- `task.record_type` is `node_assignment/v3`.
- Every file that `node_context.md` names is in `files`, or it is a
  workspace file outside the packet.

## Done when

You can state the objective, the allowed effects and every required result
field, and you have read `node_context.md` and `checklist.md`.

## Stop and report when

- The answer is an error such as `step_folder_missing`, `task_missing` or
  `task_record_type_unsupported`. Report `error` and `detail` as given.
- The objective needs an effect that `task.effects` does not list.
- Two packet files disagree. Quote both lines and stop.

## Known-wrong example

A model skips this skill, reads only the root instruction file and answers
with `{"release": "2.4.1"}`. The assignment card listed `version`,
`release_date` and `change_count` as required fields, and the result writer
refuses the answer with `missing_required_field` and `unknown_field`.
