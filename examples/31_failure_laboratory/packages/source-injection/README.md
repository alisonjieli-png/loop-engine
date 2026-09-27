# Source injection through imports

A CLAUDE.md imports two files from outside the project: an environment file
two folders up and the GitHub command line's host file in the home folder.
Claude Code expands such imports into the model's context, so the served file
would pull the customer's own settings and tokens into every session. A served
file may import only what the package or the customer's project holds. The
laboratory stores the body as `claude-file.md` so that it never acts on a
session working in this repository.

Expected refusal codes: `referenced_path_escapes`.
