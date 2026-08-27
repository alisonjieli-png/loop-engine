---
folder_id: intelligence.context.plugin
parent: intelligence.context
ontology_version: 2.0.0
---

# Plugin

plugin-provenance records for context_intelligence.

Path reading:

```text
intelligence -> context -> plugin
```

This folder inherits every rule from its ancestor READMEs:

```text
  intelligence/README.md
  intelligence/context/README.md
```

This file adds only the rules specific to this level.

## Allowed contents

- Records for intelligence_record
- Plugin records arrive through declared plugin roots and never overwrite core or learned records.
- One ``manifest.yaml`` when this folder carries machine-readable records.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.
- Records whose provenance contradicts this folder's source class (``plugin``).

## Relationships

```text
intelligence.context
|  |  |  -- plugin (this folder)
```
