---
description: Check the structure of an explicitly supplied focused-step brief without running its task.
disable-model-invocation: true
---

# Check a focused-step brief

This is a candidate command. Use the brief explicitly supplied in the current
request. Do not search for a brief, inspect unrelated files, or infer authority
from a filename. If the brief is missing, ask for its contents.

The package's `contracts/brief-input.schema.json` defines the input. It names
an objective, logical input and output labels, constraints, excluded work,
acceptance checks, unresolved questions, requested effects and an authority
reference. An authority reference is a declaration to inspect, never a grant.

When the host permits this exact local process, run the package tool
`scripts/check_brief.py` with the trusted host interpreter `/usr/bin/python3`
in isolated mode (`-I -B`). This candidate targets Linux and requires Python
3.10 or newer; do not substitute an executable from the step PATH.
Resolve the tool under this plugin's supplied installation root and pass the
brief as JSON through standard input. Close the input stream after one JSON
object. Do not interpolate brief values into shell command text, infer a
working-directory path, install dependencies or run the declared task.
If the host cannot supply a safe standard-input invocation, return the input
contract and state that the deterministic check was not run.

Report the tool's structure result and outstanding questions. A passing
result means the declared outputs have named checks. It cannot prove that
the objective is sound, the check is sufficient, the permission is valid or
the task succeeded. Refer the supplied brief to the package's
`brief-reviewer` agent only when the caller has authorized a model review.
That agent produces advisory findings; it cannot approve this package.
