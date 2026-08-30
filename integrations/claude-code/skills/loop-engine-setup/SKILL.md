---
name: loop-engine-setup
description: Check or configure Loop Engine when the user asks to install, set up, diagnose, or verify it.
disable-model-invocation: true
allowed-tools: Bash, Read
---
# Loop Engine setup

Run `loop-engine doctor` and, when requested, `loop-engine settings check`.
Check Docker readiness for generated-project solves. Never print keys or
download models automatically. A live provider call requires explicit user
authorization and bounded call and token limits.
