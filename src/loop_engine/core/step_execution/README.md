# Step execution

Kind: component folder for the step executor slot (roadmap S-6.31).

This folder holds the step edge records, the step attempt envelope, the step
executor factory table, the session process and one module for each step
executor engine. The design is section 13 of
[Engines behind fixed edges](../../../../docs/architecture/ENGINES-BEHIND-FIXED-EDGES.md).

Naming rule: one module for each engine; the factory table module names
engine classes and defines none.

Version rule: every record is `name/vN`. Readers refuse unknown keys and
unsupported versions before any effect.

A folder grants nothing: no path implies access, authority or routing.
