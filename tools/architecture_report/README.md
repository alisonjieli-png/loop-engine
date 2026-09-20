# Architecture report presentation

Kind: generator-owned report assets. These files render the repository's main
architecture artifact. They are not an application server or runtime policy.

`diagrams.json` declares software relationships at three levels. The renderer
combines them with measured source inventory, the original dated comparison,
and the authoritative roadmap. The HTML does not edit task completion or
grant deployment, model, or payment authority.

`development.js` renders the development log and owner preparation checklist.
Checklist instructions come from `continuation.owner_actions` in the existing
roadmap. Browser checkmarks contain only action identities and their content
digests. They are personal preparation notes, never verified task completion,
provider configuration, secret storage, or permission to deploy or spend.
Importing marks for changed instructions does not mark the changed task ready.

Install the pinned layout dependency with `npm ci --ignore-scripts` in this
folder, then run `tools/architecture_audit.py` with the repository environment.
The canonical generated file is `loop-engine-system-map.html`. The earlier
`architecture.html` and `mvp-client-server.html` names point to it. These are
small forwarding pages, not competing full reports. Do not edit projections by hand.

The generated file embeds styles, application scripts, report data, selected
source notes, the pinned ELK library, and its license. Full inventory and graph
downloads are embedded compressed archives. It needs no companion file or
network request. If layout fails, a readable component and connection list
remains available. Editing the report never changes runtime authority or task
completion.

Tables retain their source dates and unknown values. Structural import
relationships are not observed calls or executable Loop graphs. Test evidence
is displayed only under its exact source identity.
