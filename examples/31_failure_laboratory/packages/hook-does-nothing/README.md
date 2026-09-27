# A hook that does nothing

The hook configuration registers an event after each write, but its only
handler has an empty command. Claude Code accepts the file and runs nothing,
so the package looks installed and never acts.

Expected refusal codes: `hook_does_nothing`.
