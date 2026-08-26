---
folder_id: intelligence.context.learned
parent: intelligence.context
ontology_version: 1.0.0
---

# Learned

learned-provenance records for context_intelligence.

Path reading:

```text
intelligence -> context -> learned
```

This folder inherits every rule from its ancestor READMEs:

```text
  intelligence/README.md
  intelligence/context/README.md
```

This file adds only the rules specific to this level.

## Allowed contents

- Records for intelligence_record
- New records enter as ``candidate`` until an independent review admits them; they are invisible to normal search unless a query explicitly includes candidates.
- One ``manifest.yaml`` when this folder carries machine-readable records.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.
- Records whose provenance contradicts this folder's source class (``learned``).

## Relationships

```text
intelligence.context
|  |  |  -- learned (this folder)
```
