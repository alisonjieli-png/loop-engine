# Tool sources and a useful path to 1,000

Research date: September 23, 2026. Status: source review and proposed selection
rules. No external program or MCP server was installed or run for this report.
No item here is approved, served or qualified merely because it appears in an
upstream index. The current six systems candidates have their own
[exact-byte handoff](../codex-component-supply-2026-09-23/authored/authors/SYSTEMS-HANDOFF.md).

## Recommendation

Build a library of distinct, bounded operations with explicit inputs, outputs
and effects. Use mature upstream tools as implementation options behind those
contracts. Start with deterministic data work and local inspection, where a
small test corpus can establish useful behavior. Add service integrations as
their authentication, tenant boundaries and effect controls are qualified.

“Top 1,000” should mean a selected comparison population with stated criteria.
We have not measured a universal ranking of every tool. The existing metadata
collection supplies discovery leads; it does not supply 1,000 runnable, reviewed
customer packages. This report supplements that collection without downloading
the MCP Registry, SchemaStore or APIs.guru again.

## Count each thing separately

| Unit | Identity and counting rule |
| --- | --- |
| Provider or project | An organization or codebase. Count once as a source. |
| MCP server | A versioned server distribution or hosted endpoint. Its listing is not an individual tool. |
| Exposed MCP tool | An exact name and schema observed for a server revision, negotiated protocol, configuration and authorization scope. Aliases and versions stay linked. |
| Operation inside a multiplexer | A documented operation selected by a field such as `method`. Track separately from the exposed tool name; do not add both counts together. |
| CLI operation | A bounded command mode and contract. Every flag combination is not a new tool. |
| Library operation | A public API operation with an adapter contract. Overloads and wrappers do not automatically add useful capabilities. |
| HTTP API operation | A specified method/path/version is a discovery lead. Authentication and live behavior still need qualification. |
| Baltor method | A distinct task operation and acceptance contract. Multiple engine implementations or client renderings share its identity. |
| Baltor package | One independently admitted, retrievable package revision. Report logical method and approved package counts separately. |
| Physical file | A payload file inside a package. A schema, fixture and licence notice do not become three extra tools. |

The proposed target metric is 1,000 distinct useful methods represented by
approved packages. Also report candidate, qualified implementation, approved
package and physical-file counts. A package may contain several operations, and
one operation may have several engine packages; retain that many-to-many mapping
instead of assuming that all counts are equal. Client variants, model wording,
job-title labels and a new release of the same method do not increase method
coverage.

MCP provides paginated `tools/list`, schema-bearing tool definitions and optional
list-change notifications. Tool annotations are not inherently trusted. This
supports recording an exact discovery snapshot rather than inferring tools from
a server description. The referenced protocol page is a specific published
version, not a claim about Baltor's currently negotiated version.
[MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)

GitHub provides a concrete example: toolsets and individual tool selections are
additive, read-only mode filters write tools, environment configuration can
override CLI configuration, aliases can preserve renamed tool names, and local
and remote offerings differ. Some exposed tools multiplex several methods.
Consequently, a README list, one running server and one user's effective tool
list are different observations.
[GitHub MCP server](https://github.com/github/github-mcp-server)

## Primary sources worth using

All links below were consulted as primary documentation on the research date.
Floating documentation and repository landing pages are discovery evidence;
they are not immutable implementation pins. No third-party implementation was
copied. Before packaging an adapter, acquire the exact release/source revision,
build and licence evidence through the existing bounded acquisition pipeline.

| Source | Useful coverage documented upstream | Proposed Baltor treatment |
| --- | --- | --- |
| [Python standard library](https://docs.python.org/3/library/index.html) | Structured data, dates, exact numbers, collections, graphs, hashes and binary formats | Original narrow methods can reuse documented primitives with a pinned interpreter. Module availability and Unicode/time-zone data belong in qualification. |
| [GNU Coreutils](https://www.gnu.org/software/coreutils/manual/coreutils.html) | Text, ordering, comparison, checksums and file operations | Wrap selected operations with fixed arguments and bounded inputs. Keep file mutation separate from supplied-data transforms; pin locale and utility behavior. |
| [Git command reference](https://git-scm.com/docs/git) | Repository inspection, object plumbing, changes and references | Prefer documented structured/script interfaces. Git describes plumbing as more stable for scripts. Specify repository access, config, external helpers and output parsing in each adapter. |
| [jq manual](https://jqlang.org/manual/) | JSON selection, transformation, grouping and streaming | Package a fixed reviewed filter when useful; arbitrary supplied programs are a broader capability. Numeric behavior varies by version/build, so compare against the contract before replacing an exact arithmetic method. |
| [NetworkX algorithms](https://networkx.org/documentation/stable/reference/algorithms/index.html) | Paths, matching, flows, connectivity, graph comparison and many other algorithm families | A good engine/oracle source for explicitly bounded graph tasks. Distinguish exact from approximate algorithms, tie handling and graph models. |
| [SciPy API](https://docs.scipy.org/doc/scipy/reference/) | Optimization, statistics, interpolation, spatial computation and linear algebra | Use documented public APIs. State convergence, tolerances, random seeds and failure outcomes. A returned array is not evidence of an acceptable solution. |
| [SQLite JSON functions](https://www.sqlite.org/json1.html) and [security guidance](https://www.sqlite.org/security.html) | Structured-data querying and embedded database processing | Prefer fixed queries over supplied data. SQLite documents authorizers, limits, interruption and treatment of untrusted schema; make those explicit for any broader SQL capability. |
| [DuckDB security guidance](https://duckdb.org/docs/current/operations_manual/securing_duckdb/overview) and [extensions](https://duckdb.org/docs/current/operations_manual/securing_duckdb/securing_extensions) | An embedded query engine with file access and extension facilities | Useful for larger data tasks after a dedicated profile. External access, secrets and extension loading mean a SQL wrapper is not automatically pure computation. |
| [qpdf CLI](https://qpdf.readthedocs.io/en/stable/cli.html) | PDF inspection, page operations and transformations | Separate inspection and rewriting. Preserve warning/error distinctions; structural checks do not prove full document correctness. Input needs seekable storage, so this is not a drop-in replacement for a pure stdin method. |
| [ffprobe](https://ffmpeg.org/ffprobe.html) | Structured media/container/stream inspection and field selection | Start with bounded metadata inspection. Restrict input protocols and output fields, and qualify parser/resource behavior before exposing untrusted files. |
| [GitHub MCP server](https://github.com/github/github-mcp-server) | Repository, issue, pull-request and workflow operations | Select task-specific read scopes first. Retain actual tool/method schemas and server configuration rather than packaging an unrestricted server by default. |
| [Playwright MCP](https://github.com/microsoft/playwright-mcp) | Browser interaction, snapshots and diagnostics | Record browser/session state and exact tool schemas. A read-labelled diagnostic can accept a filename; declarations alone do not establish the adapter's actual effect policy. |

These are source families, not twelve ready-to-use packages or a count of their
functions. The treatment column is our engineering proposal, not a claim of
upstream endorsement. Licence and redistribution eligibility remain per exact
source artifact; a repository-level notice does not clear unrelated data,
documentation, dependencies or generated assets.

Two particularly useful design lessons follow from the sources:

- A jq implementation is not automatically equivalent to an exact-number Python
  method. The manual describes precision changes and build-dependent number
  handling. Keep the same edge only after equivalence tests pass.
- DuckDB explicitly recommends OS/container isolation for untrusted SQL and
  exposes extension autoinstall/autoload controls. A fixed query over in-memory
  supplied tables is a narrower qualification problem than an unrestricted SQL
  executor. That distinction should remain visible in search and permissions.

## Thirty-two next methods to investigate

These are original work-method proposals, not generated packages, approvals or
an additional task tracker. They were compared at the identity level with the
current 16 authored components and the prior populations recorded in the systems
duplication review. A deeper duplicate/contract comparison is still required
before authoring. Each group gives four distinct operations rather than four
job-title versions of one operation.

| Family | Proposed distinct methods | Example acceptance distinction |
| --- | --- | --- |
| Data constraints | Composite foreign-key orphan audit; ordered monotonic-series audit; supplied-domain membership audit; weighted confusion-matrix report | Missing and null keys differ; ties are specified; unknown labels refuse rather than disappear. |
| Exact numeric work | Largest-remainder allocation with explicit tie order; unit conversion over a supplied rational conversion graph; bounded piecewise-linear interpolation; integer check-digit verification | Conserved totals; contradictory conversion paths; no extrapolation by accident; reject malformed digit strings. |
| Time and calendars | UTC half-open window bucketing; date-range coverage audit; business-day offset over an explicit holiday set; timestamp-offset consistency check | Boundary timestamps, leap days, empty ranges and daylight-saving ambiguity are separately specified. |
| Graph decisions | Minimum cut with a checkable cut certificate; bipartite matching with an unmatched report; graph transitive reduction for a declared DAG; deterministic shortest path with explicit tie order | Disconnected inputs, capacity bounds, cycles, unreachable targets and ties distinguish methods and engines. |
| Structured text | Unified-diff structure parser; bounded delimiter-state scanner; explicit-token redaction with offset receipts; Markdown heading-tree extraction under a stated subset | Parse-only versus applying a patch; escaped delimiters; Unicode offsets; code-fence exclusions. |
| Build metadata | Lockfile artifact-digest consistency audit; supplied dependency licence-obligation inventory; target-platform tag compatibility check; declared command/environment diff | Reports over supplied records grant no install, redistribution or execution authority. Unknown formats refuse. |
| Binary/document metadata | PNG chunk order/CRC audit; WAV chunk inventory; bounded ZIP central-directory consistency report; PDF page-box consistency report over supplied extracted metadata | Size caps, malformed lengths and unsupported variants remain explicit. These do not claim full codec/document validation. |
| Evaluation evidence | Paired binary-outcome contingency report; exact rational budget reconciliation; stratified coverage-gap report; acceptance-evidence freshness report | Missing trials stay missing; duplicate receipts refuse; policy cutoff is explicit; evidence records do not approve themselves. |

Potential overlap to resolve before production: largest-remainder allocation may
overlap the prepared MiniMax apportionment method; ZIP inspection overlaps an
earlier mixed package; the paired-outcome report is adjacent to the new sign-test
package. Prefer reusing or extending their current contract where semantics
match. These leads are deliberately retained as reuse candidates rather than
counted as new supply. The prospective maximum is 32 leads, not 32 confirmed
coverage gains.

The first authoring choices should be the foreign-key audit, monotonic-series
audit, explicit holiday arithmetic, diff parser, transitive reduction and PNG
chunk audit. They offer separable contracts and adversarial fixtures. The graph
optimization and binary parser families need stronger resource and oracle checks
than simple record comparisons; their names alone do not make them low risk.

## A staged route to 1,000 useful methods

Use coverage targets as a planning hypothesis, revised by actual demand and
rejection rates. A possible allocation is 250 structured-data methods, 150
developer/repository methods, 120 numeric/statistical methods, 100 planning/graph
methods, 100 text/document methods, 80 media/binary-inspection methods, 80 bounded
service-read integrations, 60 workflow-verification methods and 60 carefully
controlled mutation integrations. These add to 1,000 targets, not 1,000 findings.
Do not fill a category with redundant wrappers to meet the allocation.

For selection, record a task example, a failed baseline or documented customer
need, expected reuse, existing alternative, verification oracle, dependency and
effect burden. Rank qualified candidates by observed accepted-task gain and
total overhead. Until there is usage evidence, label usefulness scores as
editorial estimates with reasons; download counts and stars are discovery
signals, not correctness evidence.

Recommended progression: a diverse pilot of 25–50 methods, then 100 after native
client loading and retrieval measurements, then 250 and 1,000 as review capacity
and distinct task coverage justify expansion. This is not a delivery forecast.
Track review minutes, rejected/duplicate fraction, sandbox availability,
retrieval success and accepted work per method before extrapolating throughput.

## Admission and retrieval considerations

Reuse the current `CataloguePackage`, factory, quarantine and independent-review
pipeline. This document proposes metadata fields, not a second runtime store or
registry. Bind method identity, exact payload digest, engine/version/build,
input/output schema digests, effective configuration, declared effects,
dependencies, provenance, rights evidence and qualification profile. A source
metadata row stays outside the approved item count until those stages complete.

For source discovery, parse static primary metadata first. A future live MCP
discovery job must treat starting a server and authenticating as real actions:
use a qualified sandbox, least necessary test scope, bounded pagination, empty
or synthetic workspace and an exact server pin. Do not execute arbitrary
registry launch commands merely to obtain their advertised tool names. Record
schema-list digests, discovery scope and list-change events; invalidate affected
qualification when schemas or configured behavior change.

Search should index the task verb/object, input/output formats, limits, effects,
required dependencies, compatible client profiles and known failure cases.
Aliases help retrieval while the canonical method ID prevents duplicate count
inflation. Retrieve a compact instruction/tool card first, then the exact package
and supporting material under the node's current budget and permissions. A
model-specific wording variant retains the same method identity and needs
separate evidence if it changes behavior. A package still needs explicit
composition with the current node task; its reusable instructions are not that
assignment.

## Qualification controls worth making reusable

1. Exact bytes: substitutions in script, schema, examples or executable metadata
   invalidate the prior review. Bind all package files and selected dependencies.
2. Contract agreement: mathematical integers such as `1.0`, booleans, near-integer
   decimals, duplicate JSON keys, nonfinite literals and Unicode byte limits.
3. Effects: an extra network attempt, task-file read, environment/credential read,
   subprocess or undeclared output path must be refused or recorded as a failure.
4. Algorithm oracles: independent small-case enumeration and invariants; shared
   code between implementation and oracle does not provide independent evidence.
5. Native loading: compare offered, fetched, written, loaded, invoked and accepted
   work. Include a missing entrypoint and wrong-path control for each client.
6. Retrieval: unseen tasks with hard negatives, method aliases and constrained
   effects. Measure relevance and refusal behavior, not only successful string
   matches against package titles.
7. Drift: a new executable/version/build, dependency, schema or effect policy
   triggers the affected requalification. Historical evidence stays immutable.

## Scope and remaining evidence

This report establishes primary-source leads and concrete selection rules. It
does not establish immutable pins for the external implementations, package
redistribution rights, native-client compatibility, performance improvements or
1,000 distinct approved tools. Those gaps are qualification work, not reasons to
pause original candidate authoring. The existing six systems packages remain
frozen; none of their payload bytes changed during this research.
