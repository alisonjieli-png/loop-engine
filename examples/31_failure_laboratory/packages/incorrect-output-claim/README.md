# Incorrect claim about the files

The package record says that `assets/columns.json` is JSON, and it pins a size
for `SKILL.md`. Neither is true: the table ends with a trailing comma, so no
JSON reader accepts it, and the skill file is longer than the pinned size. A
harness that trusts the record would hand the model a table it cannot read.

Expected refusal codes: `file_claim_false` for the size and
`media_type_claim_false` for the table.
