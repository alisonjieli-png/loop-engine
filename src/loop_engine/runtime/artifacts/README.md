---
folder_id: runtime.artifacts
parent: runtime
ontology_version: 2.0.0
---

# Artifacts

Digest-addressed offloaded context payloads; runtime output, not catalog artifacts.

Path reading:

```text
runtime -> artifacts
```

This folder inherits every rule from its ancestor READMEs:

```text
  runtime/README.md
```

This file adds only the rules specific to this level.

## Allowed contents

- Run output written by the runtime
- One ``README.md`` stating this local contract.

## Prohibited contents

- Runtime Loop instances; work runs only through ``LoopStartRequest`` into the one ``Loop`` runtime.
- Provider credentials, authorization headers, or raw secrets.
- Python modules of any kind.

## Relationships

```text
runtime
|  |  -- artifacts (this folder)
```
