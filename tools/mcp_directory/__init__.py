"""The public directory of Model Context Protocol servers and agent APIs, built from outside sources.

Kind: development tool package. It reads outside listings, merges them into one row per offering and
writes the compact data files and the generated parts of the page that the service serves at
`/directory`. It serves nothing itself, holds no credential and changes nothing outside its own state
folder and the packaged files it writes. The command is `tools/build_mcp_directory.py`.

Functional component and its engines:

```text
MCP directory build (functional component)
├── Edge: mcp_directory_listing/v1 records in, mcp_directory_manifest/v1 and mcp_directory_rows/v1 out
├── Source engine slot, in declared order of trust
│   ├── official_registry: the official MCP Registry list interface, paged by cursor, incremental
│   │   with updated_since, restartable from its saved cursor
│   ├── codex_research: the recorded research selection of September 23, 2026 (1,000 of 35,293
│   │   registry rows), read from its committed extract
│   ├── publisher_documentation: offerings a publisher documents on its own site, from a reviewed file
│   ├── github_directory: GitHub's MCP directory, read through its public list interface
│   └── docker_catalog: the Docker MCP Catalog repository at one pinned commit
├── Licence engine slot: github_graphql (the licence GitHub reports for a repository)
├── Category engine slot: keyword_rules/v1, a versioned rule file; the first match wins ties
└── Encoding: fixed part count, rows sorted in the page's default order
```

Directories whose terms forbid copying (Smithery, PulseMCP and Glama on September 24, 2026) are not
engines here. The page links to them. `mcp_directory/SOURCES.md` records each source's terms.
"""
