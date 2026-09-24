# Step execution

Kind: component folder for the step executor slot (roadmap S-6.31).

This folder holds the step edge records, the step attempt envelope, the step
executor factory table, the session process and one module for each step
executor engine. The design is section 13 of
[Engines behind fixed edges](../../../../docs/architecture/ENGINES-BEHIND-FIXED-EDGES.md).

Naming rule: one module for each engine; the factory table module names
engine classes and defines none.

What is here: the step edge records (`records.py`), the envelope
(`envelope.py`), the factory table and descriptor projection (`engines.py`),
the harness declaration (`harness_manifest.py`, with the packaged manifests in
`data/step_harness_manifests.yaml`), the declared harness engine and its
sandbox launcher (`declared_harness.py`, `harness_launch.py`,
`harness_endpoint.py`), the custom Loop engine (`loop_runtime.py`,
`loop_harness_process.py`, `procedures.py`), qualification
(`qualification.py`) and the offline fixture harness the checks declare
(`fixture_harness.py`). The guide is
[Step execution](../../../../docs/components/core-architecture/STEP-EXECUTION.md).

Version rule: every record is `name/vN`. Readers refuse unknown keys and
unsupported versions before any effect.

A folder grants nothing: no path implies access, authority or routing.
