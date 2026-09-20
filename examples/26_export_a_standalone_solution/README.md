# Export a standalone solution

Export verification checks the manifest identity, declared file digests,
confined paths, and source restrictions before executing code. Local execution
requires `ExportVerificationPolicy` bound to the exact reviewed manifest.
The command line requires `--allow-local-execution` and
`--export-manifest-digest`. Interpreter isolation prevents access to the
installed Loop Engine package; it is not an operating-system sandbox. This
example authorizes its trusted built-in source template explicitly. Untrusted
generated exports require a separately qualified sandbox execution path.

This example conforms a messy company file and then exports the solution as
a package that runs without Loop Engine.

The solutioning side profiles every column, proposes typed conformance rules
from that evidence, runs the rules with a confidence and named reasons for
every correction, and stages low-confidence cells as typed escalation
requests. Nothing is escalated to a model here; the requests are the next
action a hybrid Loop would dispatch under its own authority.

The solutions side writes an installable package with the chosen rules, the
merged exception catalogs, the operations module, a console entry point,
tests, a manifest with a SHA-256 digest for every file, a Dockerfile, and a
Kubernetes Job manifest. It then verifies that package in an isolated
interpreter that cannot import `loop_engine`, runs the exported tests there,
and runs the entry point on the same input.

Install Loop Engine directly from GitHub:

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

Run the example from the repository directory:

```bash
python examples/26_export_a_standalone_solution/run.py
```

Add `--out DIR` to keep the exported package in a directory of your choice.

The output includes:

- the column profiles (case, whitespace, encoding, and shape shares);
- the rules proposed from the evidence, each with its reason;
- every correction with its outcome, confidence, and reasons;
- the report counts, the escalation questions, and the learned column
  evidence;
- the export record and the six verification checks.

The same export is available from the command line:

```bash
loop-engine export solution spec.json --out DIR
loop-engine export verify DIR --run-arguments '["--input","input.csv","--output-dir","out"]'
```

Where an exception can live, lowest precedence first: the packaged catalog
file, a catalog file in the task folder, evidence learned from the column
itself, inline rule parameters, and recorded escalation answers. Read the
[text conformance and export guide](../../docs/guides/text-conformance-and-standalone-export.md).

No network, no external service, no model calls.
