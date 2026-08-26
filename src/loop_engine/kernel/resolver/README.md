---
folder_id: kernel.resolver
parent: kernel
ontology_version: 1.0.0
---

# Resolver

Turns references into registered profiles and definitions; owned today by loop.loop_profile_ontology and loop.builtin_resolvers.

Path reading:

```text
kernel -> resolver
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
|  |  -- resolver (this folder)
```
