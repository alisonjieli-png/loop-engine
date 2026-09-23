# Search effect selection: independent QA

September 23, 2026. Read-only review of the `search-effects` worktree; no provider
calls or source edits. Source inspected: `http.py` SHA-256
`e113363d2271270c8fafc17e80fbd2a187171f49637692c3a8fde265026ee759`.

**No material blocker found in the scoped effect-selection repair.** The ten
focused HTTP/protocol tests independently pass with the worktree's qualified
Python environment. They use temporary state and loopback requests; searched
material executes no process/tool/model, reads no body and records no usage.

The source passes the validated `authority_effects` selection into the existing
principal-bound provisioning list, preserving item grants, metadata/read scopes,
entitlement and the final disclosure-grant snapshot check. Choosing an effect
does not create execution or download authority. A metadata-only item retains
`body_allowed: false`.

The closed schema uses the canonical effect vocabulary and unique array values.
Malformed, duplicate, unknown or wrongly typed values refuse before ranking,
including an irrelevant query that otherwise returns no candidates. Missing or
empty selection retains the previous empty-authority behavior. HTTP and both
supported MCP flows use the same validator and selection path.

The HTTP request advances to `service_retrieval_request/v2`; old/missing/future
record versions refuse. Capabilities advertise the request version. MCP tool
schemas expose the new selector without treating it as a new permission. A
client reaching an old server cannot silently inject the field because that
reader rejects unknown request fields.

The test population also confirms denied tenant/grant/scope behavior, unrelated
queries, unchanged ranking when an irrelevant effect is added, and refusal after
an in-flight grant change. These checks support this bounded repair; they are
not a production load test or the final integrated CI run.

The first rerun used the system interpreter and could not construct the service
because its MCP package lacks `mcp.server.caching`. The qualified worktree
interpreter succeeded: ten tests in 3.375 seconds. That initial environment
mismatch is not attributed to this source change.

Integration condition: apply the author's separate documentation delta to the
restored guides and rebuild the six generated documentation bodies. Otherwise
their v1 examples and description of unavailable effect selection would be
stale. The author has prepared that delta; final source/full CI and deployment
verification remain the integrating session's responsibility.
