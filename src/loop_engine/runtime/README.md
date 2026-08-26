---
folder_id: runtime
parent: ""
ontology_version: 1.0.0
---

# Runtime

Per-run state at rest: saved runs, Runtime Memory scope rules, and offloaded artifacts. Nothing here is persistent intelligence.

Path reading:

```text
runtime
```

This folder inherits every rule from its ancestor READMEs:

```text
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
package root
|  -- runtime (this folder)
```
