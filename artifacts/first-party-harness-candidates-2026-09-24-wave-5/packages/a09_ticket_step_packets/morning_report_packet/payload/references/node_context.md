# Overnight morning report: step background

## Objective

Give the person who starts work after night {{NIGHT_ID}} one report that says, with evidence, what finished, what waits for them and what is still open.

## Relevant context

- The night window, as the host recorded it: {{NIGHT_WINDOW}}.
- Each step of the night left a handoff, or should have. A step that appears in the activity logs without a handoff is unfinished, and so is a queued ticket that no handoff names. Nothing is dropped in silence.
- A ticket has several steps. It counts as complete only when the handoff of its final step, which the queue names in `final_step_id`, is complete. A ticket whose triage finished but whose later steps never ran stays unfinished, and so does a ticket whose final step the queue does not name.
- A handoff that says complete counts as complete only when every claim cites an existing file. A folder does not count, and neither does a handoff or the queue, notes or report file of this night. Otherwise the step is listed as unfinished and its claims appear under claims without evidence.
- The newest handoff of a step sets its section. Older ones are listed as superseded.
- The script only checks that a cited file exists and may be cited. A separate check of the finished report may open the files later. Write notes that such a check can confirm by opening the cited file.

## Current state

The steps of the night have ended or were stopped by the host. The folders named in `input.json` hold the night's handoffs and activity logs. Any earlier report draft is replaced by the next compile run.

## Contracts and input

- Input: `.baltor/step/input.json`, described by `.baltor/step/contracts/input.schema.json`. Read it; never edit it.
- Handoffs: `night_step_handoff/v1` objects, described by `.baltor/step/contracts/handoff.schema.json`.
- Output: the report JSON, one `night_morning_report/v1` object described by `.baltor/step/contracts/output.schema.json`, and its Markdown rendering. Both lie outside `.baltor/step/`.

## Acceptance

- Every claim, blocker and note in the report cites a path, and the script checked every cited path.
- Every queued ticket appears in the Tickets section, and none is complete before its final step is.
- Records that could not be read are listed in the report, not left out.
- No handoff, log, queue, evidence or packet file changed during the step.
