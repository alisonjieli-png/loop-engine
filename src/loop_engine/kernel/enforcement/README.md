---
folder_id: kernel.enforcement
parent: kernel
ontology_version: 1.0.0
---

# Enforcement

Approvals, boundaries, and workspaces; owned today by loop.effect_approval and core boundary services.

Path reading:

```text
kernel -> enforcement
```

This folder inherits every rule from its ancestor READMEs:

```text
  kernel/README.md
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
kernel
|  |  -- enforcement (this folder)
```
