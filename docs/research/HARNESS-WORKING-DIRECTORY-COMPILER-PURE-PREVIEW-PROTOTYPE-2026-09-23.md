# Harness Working Directory Compiler: pure preview and implementation decision

September 23, 2026. This report records an isolated artifact prototype and a
concrete proposed patch sequence for the existing owner. It adds no task tracker
and makes no production qualification claim.

## Decision after inspecting the active owner

Implement the full active compiler as an evolution of the existing
`material_install_layout` slot and `ClientLayoutProfile` owner. Do not register
a second compiler service or introduce another runtime type.

The slot is presently a candidate release-time seam, with empty runtime protocol
and boundary bindings. The installer implements one OpenCode layout and a
single UTF-8 skill-body renderer. Promoting the complete package compiler needs
contract, registry, ontology and caller changes together. That is wider than
this bounded prototype, so no active edge was invented to make the experiment
look shipped.

The [pure prototype](../../artifacts/harness-working-directory-compiler-prototype-2026-09-23/README.md)
demonstrates complete package byte transport, immutable previews and the named
refusal cases. Its files are only under `artifacts/`; no `src/`, `tools/` or
architecture registry source changed. It reuses real package/profile types but
is not imported by their runtime owners.

## Runtime ownership remains unchanged

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

```text
Existing material-install-layout component, proposed active evolution
├── ClientLayoutProfile v2: passive compatible-layout data
├── Typed compilation request and preview/result
├── Selected implementation
│   ├── Baltor deterministic package renderer
│   └── External adapter only after independent qualification
├── Existing confined writer: separately authorized effects
└── Existing fresh-instance executor: native discovery, use and acceptance
```

Compilation is a low-level primitive inside its owning classified work. The
prototype creates no separately scheduled Loop and does not choose another
Loop's role, mode or authority. The active boundary must be added to the
existing registry when the actual component contract is introduced, with its
owning role/profile explicitly resolved.

## Results from the bounded implementation

Sixteen checks pass. Seven removed-guard controls are detected. The tests use
in-memory synthetic packages and workspace observations, without native clients,
model/network calls or workspace installation.

| Property | Observed behavior |
| --- | --- |
| Full package tree | Every declared file appears once in the plan; missing/extra payloads refuse |
| Opaque bytes | `00 ff 80 0d 0a` remains identical; digest and media type preserved |
| Existing skill frontmatter | Copied exactly, without another generated header |
| Required role | Refuses a file role outside the host profile's declared mechanical support |
| Name collision | Normalized identities producing the same destination refuse |
| Parent/file collision | A desired file that is another desired file's parent refuses |
| Expected current state | Changed observed bytes refuse both compilation and the pure post-preview comparison |
| Unsafe parents | Missing parent observations or a reported symlink/special-file parent refuse |
| Worker effects | Cannot gain networking or processes from an installation grant or a profile label |
| Installation authority | Preview remains inspectable without a write grant; it reports the requirement without applying it |
| External engine | Explicit `engine_unavailable`, with no fallback or shell execution |

The [saved evidence](../../artifacts/harness-working-directory-compiler-prototype-2026-09-23/removed-guards-2.json)
is narrower than native qualification. The copied skill-root location was
already data in `ClientLayoutProfile`; no installed harness read this new
complete package in the experiment. Other native placements remain unsupported
by this prototype. A role whitelist is not proof that a hook or plugin will
activate correctly.

## Concrete implementation patch sequence

These are changes to existing roadmap work, not independent tasks to track.

| Patch slice | Exact owner and required change | Gate before use |
| --- | --- | --- |
| Contract ownership | Introduce `core.harness_working_directory_compiler` under the existing core component and move/generalize `ClientLayoutProfile` and `NativeLocation` from the installer into it; update all in-repository imports/callers together | No duplicate definitions or legacy shim; import-boundary and package-install checks |
| Record evolution | Adopt reviewed `native_client_layout_profile/v2` and `native_material_install_preview/v2`, using the prior draft schemas as review input | Unknown versions/fields refuse; active v1 caller migration is explicit; historical evidence remains unchanged |
| Canonical payload input | Take existing `CataloguePackage`, `CataloguePackageFile` and exact immutable bodies with source/approval/dependency references | Complete inventory, per-file bytes, package digest and dependency closure verified before compilation |
| Direct implementation | One Baltor deterministic engine implementing the fixed pure compiler protocol; preserve bytes by default, with explicit qualified transformations only | The same collision, stale-state, opaque-byte, role and authority population used here, plus full contract cases |
| Engine registration | Fill the existing `material_install_layout` slot's protocol, native registry, declaration, scope and tests; join existing engine/boundary registries, interaction and architecture records | Registry/ontology conformance; independent engine qualification and actual initialization negotiation |
| External adapter | Register an installed Agent Harness adapter only after its output passes the same fixed contract; otherwise report unavailable | Unsupported mandatory semantics refuse; no fallback that weakens authority or drops files |
| Installer application | Make `tools/install_selected_material.py` obtain and display the checked v2 plan, then pass its exact bytes and expected state to the existing confined writer | Real no-symlink observations, stale-state comparison at use, foreign-file refusal, explicit replacement policy and truthful partial-effect record |
| Native qualification | Bind profile to executable/build/interface/configuration and run authorized controlled native discovery/activation probes | No profile promotion from constructor/path tests; package retrieval, placement, discovery, use and acceptance stay distinct |

The exact internal filenames above are a concrete proposal for the integrating
session, not already registered symbols. A separate engine module/factory table
should follow the repository's engine-folder conventions when that owner is
introduced. It must extend the existing slot, never become a second source of
truth for profiles, approvals or packages.

The version-two preview differs materially from the current metadata-only
preview: exact rendered bytes require already retrieved bodies, and retrieving
them may be metered. Keep metadata selection, body retrieval, pure compilation
and authorized application as separate stages. A dry preview can require future
write authority without possessing or granting it.

## Limits to retain during implementation

`ExistingState` is an input record, not a secure filesystem capability. Production
must obtain it through existing confined readers and check it again at the
effect boundary; a truthful snapshot can still become stale. The prototype's
comparison cannot make a check-then-write sequence atomic. Managed-file update,
multi-file partial failure and rollback require their own writer checks.

The experiment's profile wrapper and result shape are private artifacts. They
are deliberately not presented as active implementations of the draft v2 wire
schemas. The production migration should remove that temporary wrapper, fold
the accepted fields into the existing profile owner and provide the full schema
contract. The synthetic example grants no admission, native compatibility or
execution permission.

No source was merged, pushed or deployed by this prototype. The root integrating
session owns whether to preserve the research patch and when to take the wider
registered implementation slice.
