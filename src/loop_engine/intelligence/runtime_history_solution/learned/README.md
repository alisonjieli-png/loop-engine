---
folder_id: intelligence.runtime_history_solution.learned
parent: intelligence.runtime_history_solution
ontology_version: 1.0.0
---

# Learned

learned-provenance records for runtime_history_solution_intelligence.

Path reading:

```text
intelligence -> runtime_history_solution -> learned
```

This folder inherits every rule from its ancestor READMEs:

```text
  intelligence/README.md
  intelligence/runtime_history_solution/README.md
```

This file adds only the rules specific to this level.

## Allowed contents

- Records for intelligence_record
- New records enter as ``candidate`` until an independent review admits them; they are invisible to normal search unless a query explicitly includes candidates.
- One ``manifest.yaml`` when this folder carries machine-readable records.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.
- Records whose provenance contradicts this folder's source class (``learned``).

## Relationships

```text
intelligence.runtime_history_solution
|  |  |  -- learned (this folder)
```
