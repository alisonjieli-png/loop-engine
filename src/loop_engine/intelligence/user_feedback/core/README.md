---
folder_id: intelligence.user_feedback.core
parent: intelligence.user_feedback
ontology_version: 1.0.0
---

# Core

core-provenance records for user_feedback_intelligence.

Path reading:

```text
intelligence -> user_feedback -> core
```

This folder inherits every rule from its ancestor READMEs:

```text
  intelligence/README.md
  intelligence/user_feedback/README.md
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
intelligence.user_feedback
|  |  |  -- core (this folder)
```
