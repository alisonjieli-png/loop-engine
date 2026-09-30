# Worker distribution

Kind: build and launch support, not an executable graph runtime.

The root Dockerfile builds the downloadable worker. This directory holds its
pinned native dependency lock, explicit harness profiles, task launcher and
Compose configuration. These files belong to the existing command-line and
harness execution boundaries. A folder is needed because Docker and Compose
consume physical files; this is not a second registry or a new Loop type.

The product never imports this directory. The launcher calls the public
`loop-engine solve` command. Native adapters use the existing versioned
semantic response edge, configured model broker and cumulative allocation.
The worker adds no credential or model access by itself.

The profiles declare `trusted_process`: the outer container is the physical
boundary, not a separate OS sandbox for every assignment. The existing
Bubblewrap profile remains independently selectable and never falls back
implicitly. See the [operating guide](../docs/guides/container-worker.md).

`tools/test_worker_launcher.py` checks launch allocation, paths, explicit
command authority and the import boundary. `tools/check_worker_bundle.py`
checks installed native process mechanics in the actual image. The publication
workflow requires both successful source CI and installed-image checks.
