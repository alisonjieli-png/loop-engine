---
folder_id: governance
parent: ""
ontology_version: 1.0.0
---

# Governance

Candidate staging through independent review, approval, and explicit promotion. Promotion is never inferred from retrieval or a good score.

Path reading:

```text
governance
```

This folder inherits every rule from its ancestor READMEs:

```text
```

This file adds only the rules specific to this level.

## Allowed contents

- Lifecycle records for intelligence_record, policy
- One ``README.md`` stating this local contract.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.

## Relationships

```text
package root
|  -- governance (this folder)
```
