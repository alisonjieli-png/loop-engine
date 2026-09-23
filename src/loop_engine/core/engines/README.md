# Engine framework

Kind: component folder for the shared engine framework (roadmap S-6.30).

This folder holds what every engine slot shares: the engine slot catalogue
and its joins, the engine records, selection, evidence and measurement.
Engines themselves stay in the registries and folders of their own
components. The design is
[Engines behind fixed edges](../../../../docs/architecture/ENGINES-BEHIND-FIXED-EDGES.md).

Naming rule: one module for each part of the framework, named without an
`engine_` prefix (`slots.py`, `slot_index.py`, `selection.py`). A factory
table module names engine classes and defines none; an engine module holds
exactly one engine and lives in the folder its slot names.

Version rule: every record is `name/vN`. Readers refuse unknown keys and
unsupported versions before any effect, and a record that an older release
must not honour gets a new version.

A folder grants nothing: no path implies access, authority or routing.
