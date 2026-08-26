---
folder_id: intelligence
parent: ""
ontology_version: 1.0.0
---

# Intelligence

The four persistent intelligence layers at rest, each split into core, learned, and plugin provenance.

Path reading:

```text
intelligence
```

This folder inherits every rule from its ancestor READMEs:

```text
```

This file adds only the rules specific to this level.

## Allowed contents

- Records for intelligence_record
- One ``README.md`` stating this local contract.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.

## Relationships

```text
package root
|  -- intelligence (this folder)
```
