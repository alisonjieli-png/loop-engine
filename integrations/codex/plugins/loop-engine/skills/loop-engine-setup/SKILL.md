---
name: loop-engine-setup
description: Check or configure a local Loop Engine installation, settings file, and provider readiness when the user asks to install, set up, diagnose, or verify Loop Engine.
---

# Loop Engine Setup

Use the installed `loop-engine` command as the authority.

1. Run `loop-engine doctor` and report exact failures.
2. Use `loop-engine settings check` when a settings file exists or the user asks about settings.
3. Do not print provider keys or place them in source files.
4. Check that Docker and the pinned Python image required by generated-project
   solves are available. Do not pull an image without user authority.
5. Do not download a model automatically.
6. A provider is not proved by offline self-tests. Run `models probe` only when
   the user authorizes the real call and supplies call and token ceilings.

Link the user to the repository quick-start guide when installation changes are required.
