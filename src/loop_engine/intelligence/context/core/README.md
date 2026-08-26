---
folder_id: intelligence.context.core
parent: intelligence.context
ontology_version: 1.0.0
---

# Core

core-provenance records for context_intelligence.

Path reading:

```text
intelligence -> context -> core
```

This folder inherits every rule from its ancestor READMEs:

```text
  intelligence/README.md
  intelligence/context/README.md
```

This file adds only the rules specific to this level.

## Allowed contents

- Records for intelligence_record
- Records must declare lifecycle ``registered`` or later; shipped core records are immutable within a release.
- One ``manifest.yaml`` when this folder carries machine-readable records.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.
- Records whose provenance contradicts this folder's source class (``core``).

## Relationships

```text
intelligence.context
|  |  |  -- core (this folder)
```
