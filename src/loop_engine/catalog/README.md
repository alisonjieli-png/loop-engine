# Catalog

Backend-neutral intelligence access: one catalog, many store adapters.

## Purpose

The catalog resolves the same logical records whether they are
materialized as package JSONL, DuckDB tables, SQLite rows, a server
database, a portable bundle, or a remote service.

## Allowed contents

- Store protocol, handshake, capability, and query modules.
- One adapter implementation per backend kind under `stores/`.

## Prohibited contents

- Runtime Loop instances; work runs only through LoopStartRequest.
- Provider credentials, authorization headers, or raw secrets.
- A second catalog authority; the composite catalog is the one logical
  view.

## Authority

Adapters declare their authority role in their capability handshake.
Derived indexes are disposable and rebuildable. No adapter is the
ontology.
