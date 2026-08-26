---
folder_id: intelligence.runtime_history_solution.plugin
parent: intelligence.runtime_history_solution
ontology_version: 1.0.0
---

# Plugin

plugin-provenance records for runtime_history_solution_intelligence.

Path reading:

```text
intelligence -> runtime_history_solution -> plugin
```

This folder inherits every rule from its ancestor READMEs:

```text
  intelligence/README.md
  intelligence/runtime_history_solution/README.md
```

This file adds only the rules specific to this level.

## Allowed contents

- Records for intelligence_record
- Plugin records arrive through declared plugin roots and never overwrite core or learned records.
- One ``manifest.yaml`` when this folder carries machine-readable records.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.
- Records whose provenance contradicts this folder's source class (``plugin``).

## Relationships

```text
intelligence.runtime_history_solution
|  |  |  -- plugin (this folder)
```
