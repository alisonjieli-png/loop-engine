---
folder_id: governance.promotion
parent: governance
ontology_version: 2.0.0
---

# Promotion

Explicit promotion records only; retrieval, a good score, or model confidence never promotes anything.

Path reading:

```text
governance -> promotion
```

This folder inherits every rule from its ancestor READMEs:

```text
  governance/README.md
```

This file adds only the rules specific to this level.

## Allowed contents

- Lifecycle records for intelligence_record
- One ``README.md`` stating this local contract.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.

## Relationships

```text
governance
|  |  -- promotion (this folder)
```
