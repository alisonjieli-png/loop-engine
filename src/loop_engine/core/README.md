# Core Architecture

Core Architecture supplies capability ports and internal runtime mechanics.
It is distinct from Code Intelligence, which contains governed executable
assets. Released runtime code is not a separate persistent intelligence layer.

## Purpose

Core supplies the shipped capability groups: Intelligence Search and
Retrieval, Web Research, and Custom Plugins. Providers, model routing,
settings, workspaces, approvals, stores, Runtime Memory, Run History,
reports, playback, and provider adapters are internal runtime mechanics.

## Allowed contents

- Core capability implementations and their typed contracts.
- Internal runtime mechanics used by Loops.

## Prohibited contents

- Runtime Loop instances; work runs only through LoopStartRequest.
- Provider credentials, authorization headers, or raw secrets.
- Mutable Learned data; Learned state lives outside the installed
  package.
