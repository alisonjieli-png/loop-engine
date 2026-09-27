# How a harness gets reusable components from Baltor

Source inspection: commit `e5d21e899c6d6c8b7791288aa9ef762917e483bc`,
September 27, 2026 UTC. Release 39 runs this source revision. Endpoint
behavior below comes from the server implementation and the recorded
customer download. Compact source presentation is a later change.

## Three different paths

The `src/loop_engine/...` names in the sample skill identify its original
source. A customer does not need to create those folders or load the Baltor
repository to follow that written procedure.

| Path | Meaning | Example |
|---|---|---|
| Original source | Where the component was derived from; used for attribution and review | A source file at a pinned repository revision |
| Package member | A file actually supplied with the selected component | `scripts/clip_captions.py` |
| Installed path | Where a particular harness reads or registers the component | A qualified skill folder, tool-wrapper folder, or an explicit read-file argument |

A reference to source code is not a bundled implementation. If the component
needs that code at execution time, its package or dependency contract must
supply it. A source citation alone does not satisfy that requirement.

## How material enters the catalogue

```mermaid
flowchart LR
    S[Projects, sessions, APIs, repositories and research] --> I[Inventory and select source material]
    I --> Q[Read and question the source with its provenance]
    Q --> P[Reuse code or produce a complete component candidate]
    P --> T[Check contracts, files, rights, effects and behavior]
    T --> R[Independent review]
    R --> V[Publish an approved catalogue revision]
    V --> C[Catalogue records and exact file bytes]
    F[Task failures and user feedback] --> Q
    F --> T
```

The installed discovery collector supplies source observations. Candidate
generation, independent admission and publication have their own records.
The broader internal research teams and fully automatic source-interrogation
workflow are still being assembled; this diagram does not claim they already
run unattended end to end. A new catalogue release can change available
components without changing the website image.

## The client and service path

This is a map of component ownership and network traffic. It is not an
executable Loop graph.

```mermaid
flowchart TD
    T[Your task] --> H[Your harness and chosen model]
    H --> Q[Ask for the component needed by this step]
    Q --> M[Model Context Protocol at /mcp]
    Q --> R[HTTP API or local client]
    M --> A[Baltor authenticates the account and checks scope]
    R --> A
    A --> S[Search the permitted catalogue metadata]
    S --> F[Return identities, purpose, source, effects and exact digests]
    F --> P[Harness selects a component]
    P --> V[Fetch its manifest and recheck access]
    V --> D[Request the exact body or package files]
    B[Server-side catalogue and body store] --> D
    D --> I[Verify bytes on the customer computer]
    I --> W[Place files or register a native tool binding]
    W --> E[Harness invokes existing code or loads instructions]
    E --> C[Check the task result]
```

The service searches and serves reviewed material. The customer runs their
harness and models. Retrieving a Python program does not execute it on the
Baltor server. The separate internal research programme produces research and
candidate improvements; it is not on this customer request path.

## What responds to each request

| Step | Model Context Protocol tool | Direct HTTP path | Response |
|---|---|---|---|
| Capabilities | Protocol initialization and tool listing; `provisioning_discover` for provisioning details | `GET /api/v1/capabilities` | Supported operations, versions and limits |
| Search | `intelligence_search` | `POST /api/v1/retrieval` | Small references and metadata; `bodies_loaded` is false |
| Browse | `provisioning_list` | `POST /api/v1/provisioning` with `operation: list` | Permitted catalogue entries, with pagination |
| Inspect | `provisioning_manifest` | The same provisioning path with `operation: manifest` | Exact identity, digest, licence, review and access information |
| Read text | `provisioning_read` | Provisioning with `operation: read` | Authorized text body, within inline limits |
| Download bytes | Use the HTTP download route from a client when exact package-file bytes are needed | `POST /api/v1/download` with `operation: read` and optional package `path` | Raw bytes and `X-Content-SHA256` |
| Report a problem | `provisioning_report` | Provisioning with `operation: report` | Recorded or withdrawn state and review handling |

The current HTTP request versions are `service_retrieval_request/v2` and
`service_provisioning_request/v2`. JSON success responses use
`service_http_result/v1`; downloads return bytes instead of that JSON wrapper.
The client supplies the selected item identity and expected item digest.
Package-file downloads also name the exact member path, then validate that
member's own returned digest. A single request identity is reused across the
same package transfer and an exact retry. A missing response does not mean
usage was never recorded.

On the server, `ServiceHttpApplication` dispatches the HTTP and protocol
operations. Authentication, effective scopes and catalogue permissions are
checked before disclosure, and access is revalidated. `authorized_hits`
searches one catalogue view. `ProvisioningServer` governs manifest/body
disclosure and metering. `CatalogueView.read_package_file` resolves declared
members; `VolumeBodyStore` retrieves and checks their content-addressed bytes.
Catalogue records and files use the service's persistent storage. Downloads
do not depend on a customer finding the original `src` paths on their machine.

## Placement and native execution

The Harness Working Directory Compiler is the intended shared boundary for
rendering and placement. Current installation support is narrower than that
complete design. A file downloaded successfully is not automatically an
installed or invoked tool.

Examples already examined in this research:

- OpenCode can load a TypeScript or JavaScript tool definition which invokes
  an existing Python program. The Python file alone is not the tool definition.
- Pi extensions can register tools and event handlers with its native runtime.
- Aider can receive a downloaded instruction through an explicit read-file
  setting. This differs from an automatically discovered skill directory.

The compiler profile needs both the file layout and the activation recipe:
registration, dependencies, permissions, tool identity, restart or reload
behavior, and a native check. Bindings for SDK calls, subprocesses, binaries,
HTTP, Model Context Protocol and other supported runtimes can reuse the same
underlying operation when they satisfy its contract.

## Shorter source displays and smaller context

Recommended presentation:

```text
Source: Baltor · Reuse existing work · revision db18890 · MIT
Source details: repository files, exact revisions, digests and review records
```

Keep the complete provenance available in component details and a structured
package reference. Put concise, actionable guidance in the normal instruction
file. Load supporting documents or source files only when the task needs them.

Changing the displayed label does not change downloaded bytes. Moving a source
appendix out of a downloaded instruction does change them; it must produce a
new, reviewed component revision or an explicitly bound compact variant.
Existing hashes and review records must continue to identify their original
bytes. A shortened file that silently drops an exception or condition is not
an equivalent compact edition.

The largest opportunity for reducing generated code is to invoke an existing
implementation and return its result or a short artifact reference. It does
not require inserting the full implementation into model context. Actual token
or cost savings still need a comparison on the target model and task.

## Evidence and current limits

One fresh customer completed signup, searched the library and downloaded
`find_duplicate_records_with_blocking_keys`. Aider subsequently loaded the
exact 2,722-byte body through its explicit read mechanism. A worked example
used the named existing implementation on synthetic rows and checked its
result. These observations are separate from a model-driven autonomous task.

OpenCode and Pi native executable binding checks are recorded in
`/home/username/baltor-private/native-code-bindings-20260927-v1`.
The prepared first-party customer skill is in
`/home/username/baltor-library/codex-lane/2026-09-27-customer-skill-1-v1`;
it has passed offline contract checks but remains a candidate awaiting
independent admission and native customer qualification.
