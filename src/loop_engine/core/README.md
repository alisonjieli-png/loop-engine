# Core Architecture

The built-in, immutable, released portion of Core Code Intelligence.

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
