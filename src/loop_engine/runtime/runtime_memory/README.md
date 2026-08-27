---
folder_id: runtime.runtime_memory
parent: runtime
ontology_version: 2.0.0
---

# Runtime memory

Temporary single-run state; never promoted into a persistent layer automatically.

Path reading:

```text
runtime -> runtime_memory
```

This folder inherits every rule from its ancestor READMEs:

```text
  runtime/README.md
```

This file adds only the rules specific to this level.

## Allowed contents

- Run output written by the runtime
- One ``README.md`` stating this local contract.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.

## Relationships

```text
runtime
|  |  -- runtime_memory (this folder)
```
