---
folder_id: governance.candidates
parent: governance
ontology_version: 1.0.0
---

# Candidates

Unreviewed staged output; candidate-only by definition and excluded from search unless a query explicitly includes candidates.

Path reading:

```text
governance -> candidates
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
|  |  -- candidates (this folder)
```
