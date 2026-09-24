# Ticket triage: checklist

## Before work

- [ ] No marker in double braces is left in `AGENTS.md`, this file or `.baltor/step/input.json`.
- [ ] The ticket file named in `input.json` exists and holds readable text.
- [ ] You know the allowed path prefixes, the file limit and the things unavailable tonight.

## Before handoff

- [ ] The answer is one JSON object with no text around it, and it holds every key of the schema.
- [ ] Every wanted result of the ticket is in `acceptance` word for word, or asked about in `open_questions`.
- [ ] For go and split, `open_questions` and `needs` are empty; for hold and split, `first_test` is null.
- [ ] Every path in `files_to_read` exists.
- [ ] Every item in `needs` appears in `unavailable_tonight`.
- [ ] Each reason names a ticket line or a file.
- [ ] No file was created, changed or deleted.
