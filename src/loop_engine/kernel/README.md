---
folder_id: kernel
parent: ""
ontology_version: 1.0.0
---

# Kernel

Kernel concerns documented at rest: loading, resolution, execution, and enforcement. Each member names the existing owning modules; it does not add another executor.

Path reading:

```text
kernel
```

This folder inherits every rule from its ancestor READMEs:

```text
```

This file adds only the rules specific to this level.

## Allowed contents

- Contract documents
- One ``README.md`` stating this local contract.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.

## Relationships

```text
package root
|  -- kernel (this folder)
```
