---
folder_id: kernel.loader
parent: kernel
ontology_version: 1.0.0
---

# Loader

Binds records and payloads from the three physical roots; owned today by core.knowledge_loader and ontology.catalog.

Path reading:

```text
kernel -> loader
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
|  |  -- loader (this folder)
```
