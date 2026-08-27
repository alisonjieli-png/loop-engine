---
folder_id: intelligence.runtime_history_solution
parent: intelligence
ontology_version: 2.0.0
---

# Runtime history solution

Persistent runtime_history_solution_intelligence collection grouped by provenance.

Path reading:

```text
intelligence -> runtime_history_solution
```

This folder inherits every rule from its ancestor READMEs:

```text
  intelligence/README.md
```

This file adds only the rules specific to this level.

## Allowed contents

- Records for intelligence_record
- One ``README.md`` stating this local contract.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.

## Relationships

```text
intelligence
|  |  -- runtime_history_solution (this folder)
```
