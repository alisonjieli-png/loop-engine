# Guard shell commands with an allowlist

## What is active

A hook checks each shell command before it runs, including Monitor commands. A command runs only when it starts with an entry in `.baltor/step/guard-shell-command-allowlist.json`. Read that file before your first shell command.

Commands joined with `&&`, `||`, `;` or `|` are checked part by part. The hook refuses file redirection, `$( )`, backticks, `$NAME`, `${...}`, unquoted braces, background `&`, subshells and commands over several lines. PowerShell is refused. Programs that run other programs, such as `env`, `xargs`, `sudo` and `bash -c`, are always refused, and so are `export`, `alias` and other builtins that change later commands. For a command with refused options, write `*`, `?` and `[` patterns inside single quotes.

## If something is refused

1. Read the reason. It names the refused part and lists the allowed command starts.
2. Rewrite the command in an allowed form, or split it into separate commands.
3. Do not retry the same command with other spelling or quoting.
4. If the step needs a command that is not allowed, stop and report the command and why you need it.
