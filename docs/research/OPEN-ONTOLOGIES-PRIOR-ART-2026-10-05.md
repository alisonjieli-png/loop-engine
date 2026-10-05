# Open Ontologies: prior-art record for Baltor

Kind: dated research record, October 5, 2026. It answers the owner's question
about a LinkedIn post by André Lindenberg of October 5, 2026 on Open
Ontologies, under rule 6 of the
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority):
a project taken from GitHub enters as an engine adapter pinned to its source
revision and licence, with a Baltor-native engine beside it or a recorded
reason why none is needed, and the record says what was found and why it was
adopted, adapted or rejected. The [roadmap](../roadmap/roadmap.yaml) remains
the task authority. Nothing here publishes, approves or qualifies material,
and no binary or container of the project was downloaded or run.

Every fact names its source and was observed on October 5, 2026 unless another
time is given. "Read in code" means read in the source at the pinned commit,
not run. Inferred and unchecked facts are marked where they occur. Paths
marked `OO:` are relative to
`https://github.com/fabio-rovai/open-ontologies/blob/9b2dfc24ebebe32e1127ba44e5047503729de40f/`.

## Decisions

| Question | Decision | Reason |
|---|---|---|
| Library supply through the programs line | Rejected for now; no row added | The line's own dry run refused it as `not_a_command_line_program` ("formula answered 404"): Homebrew has no `open-ontologies` formula. Licence and release digests pass. |
| Library supply through the protocol server line | Rejected; nothing to produce | The official registry does not list it, and its declared package is a container image, which the line refuses as `no_npm_or_pypi_package`. |
| Engine slot | No slot added | None of the 51 slots fits and no Baltor caller reasons over RDF or OWL. The slot it would need is sketched in step 3. |
| Ideas for Baltor's catalogue change path | Adapt a consequence report and an additions-only verdict; an independent proof checker is optional; reject its apply and rollback semantics | Baltor already binds the base and refuses undeclared change; what it lacks is a list of the downstream consequences of a change before publish. |
| Its ontologies as library material | Rejected for now | The IES ontologies are `licence_unknown` to the lines' own licence code and no line reads Turtle; the case-study ontologies are CC-BY-4.0 files inside an MIT repository; the pizza reference carries no licence. |

## The repository

Found by searching GitHub repositories for "open-ontologies" and confirmed by
the README, not by the name. Its opening lines are "Plan a change to a
production ontology. See every consequence before you apply it." and "Open
Ontologies is written in Rust. It ships as one binary." Its worked example is
the one-triple change with "new consequences 901", and its first figure is
described as "A hand-drawn animation of ies-core.ttl" (`OO:README.md`, lines 10
to 90). `kapoorsunny/open-ontologies` and `nicolas-geysse/open-ontologies` are
forks of it (GitHub `fork: true`, parent `fabio-rovai/open-ontologies`).

| Fact | Value | Source |
|---|---|---|
| Repository | `fabio-rovai/open-ontologies`, not a fork, owner type User, created 2026-03-09, homepage tesseractsemantics.com | `https://api.github.com/repos/fabio-rovai/open-ontologies` |
| Default branch and head | `main` at `9b2dfc24ebebe32e1127ba44e5047503729de40f`, committed 2026-10-01T22:45:38Z | `https://api.github.com/repos/fabio-rovai/open-ontologies/commits/main` |
| Version at head | `Cargo.toml` says 2.1.0, which no release carries yet | `OO:Cargo.toml` |
| Licence, GitHub's interface | MIT, file `LICENSE`, blob `591685ae60273c0d99dccb3fe127fbac35789d3e` | `https://api.github.com/repos/fabio-rovai/open-ontologies/license` |
| Licence text at head | The MIT License, "Copyright (c) 2026 Fabio Rovai"; it agrees with the interface | `OO:LICENSE` |
| Stars and forks | 612 stars (the post said 548), 77 forks, 0 open issues | repository interface |
| Latest release | `v2.0.1`, published 2026-09-28T08:52:39Z. The annotated tag object `735180ba5e9b6ce851320468a2b25d963b087c43` points at commit `d118719043905132d314611dcee9f0cac5f87868`; GitHub reports the tag as unsigned | `https://api.github.com/repos/fabio-rovai/open-ontologies/releases/latest` and `.../git/tags/735180ba5e9b6ce851320468a2b25d963b087c43` |
| Release asset digests | GitHub publishes a SHA-256 `digest` for all 10 assets. The release's own `SHASUMS.txt` lists the 9 binaries and agrees with GitHub's digest for each; its own bytes match GitHub's digest for it | `https://api.github.com/repos/fabio-rovai/open-ontologies/releases/tags/v2.0.1`; `gh release download v2.0.1 -R fabio-rovai/open-ontologies -p SHASUMS.txt` |
| Build provenance | GitHub's attestation interface lists one SLSA v1 provenance statement for the Linux binary's digest. Its subjects are all 9 binaries, built by `.github/workflows/release.yml` at `refs/tags/v2.0.1`, commit `d1187190`. The signature was not verified here | `https://api.github.com/repos/fabio-rovai/open-ontologies/attestations/sha256:7a54594aad74c572c993fb09f1d0ea3c661f2348592dde542bb8f2fdfeba3572` |
| Platforms | Engine binary for macOS arm64 and x86_64, Windows x86_64 and Linux x86_64 (glibc). The five Lean checker binaries are Linux x86_64 only. Container image `ghcr.io/fabio-rovai/open-ontologies`. Source build with Rust 1.85 or later. No Linux arm64 binary | release assets; `OO:README.md` "Install" |
| Package managers | No Homebrew formula (404 in the dry run below). Not on crates.io: `https://crates.io/api/v1/crates/open-ontologies` answered 404 while the control `.../crates/oxigraph` answered 200. The pure-Python second engine `open-ontologies-lite` 0.5.0 is on PyPI, licence expression MIT, requires `pyoxigraph>=0.5,<0.6`, uploaded 2026-08-21 | dry run; `https://pypi.org/pypi/open-ontologies-lite/json` |

Release `v2.0.1` assets, with GitHub's published digests:

| Asset | Bytes | SHA-256 |
|---|---|---|
| `open-ontologies-x86_64-unknown-linux-gnu` | 82,186,376 | `7a54594aad74c572c993fb09f1d0ea3c661f2348592dde542bb8f2fdfeba3572` |
| `open-ontologies-aarch64-apple-darwin` | 66,806,368 | `268ca690b893c8f33f1d4491084fc1e8fc7e0adbbddda59595a419f943c4552b` |
| `open-ontologies-x86_64-apple-darwin` | 73,910,168 | `6e424ac7102577e609015b35f056288618aa3739955794b2a415bf939a6a298e` |
| `open-ontologies-x86_64-pc-windows-msvc.exe` | 62,507,008 | `765803297dbaaeef6fce9bcb2b1794d0bd6683a21afa7981d504722ff611e1bf` |
| `oo-cert-x86_64-unknown-linux-gnu` | 5,371,208 | `68223b4db193783a52bd2810a66ce2ad3a3780f963a5ef84753564c051e3e532` |
| `oo-horn-x86_64-unknown-linux-gnu` | 5,344,296 | `967224162167ddfa55dd3196e86ea719157f121b62981f283c0315381da0477b` |
| `oo-lrat-x86_64-unknown-linux-gnu` | 4,443,928 | `752f2fafaa6df9ad23fd3150524066a5066d3a32fbb20ce4489c79e54d05ab96` |
| `oo-resolution-x86_64-unknown-linux-gnu` | 4,466,008 | `94b5832ec10d6a9f535a7e392eec4ee9994bbafed81672744c8e7b79e67f4140` |
| `oo-shacl-x86_64-unknown-linux-gnu` | 4,728,872 | `f965878d06c1a0ea9c80bb36b668dd02f0aec5ab4ccccb1474975af18de799da` |
| `SHASUMS.txt` | 923 | `dff0ff546d043d7a0c4e47e35da0ef40238b551f7f3bfa554248644062339f82` |

### What the post claims and what the source shows

| Claim in the post | What the source shows |
|---|---|
| Written in Rust, ships as one binary | The engine is one Rust binary (edition 2024; Oxigraph 0.5 patched to the author's fork at revision `abf36ef2`; `rmcp` for the protocol). The proof checkers are five more binaries built from core Lean 4 v4.33.1 without Mathlib, released for Linux x86_64 only (`OO:Cargo.toml`; `OO:README.md` "Stack"). |
| One line gave 901 new consequences | The README's worked example: `ex:hasParent rdfs:domain ex:Person` gives added classes 0, removed classes 0, blast radius 0, risk `low`, conservativity `not_conservative_under_rule_table` and 901 new consequences under the `owl-rl` rule table (`OO:README.md`, lines 78 to 90). Not reproduced here. `onto_plan` computes the consequences only with `check_conservativity: true`, and the project calls the verdict conservativity under a Horn rule table, not in a description logic (`OO:docs/lifecycle.md`). |
| Plans like Terraform with a blast-radius report, apply and rollback over the protocol | Tools `onto_plan`, `onto_apply`, `onto_lock`, `onto_monitor`, `onto_monitor_clear`, `onto_drift`, `onto_version`, `onto_history`, `onto_rollback` and `onto_lineage` exist. Blast radius counts triples that reference removed terms. Risk is `high` when anything is removed and triples are affected, `medium` for any other removal and `low` otherwise (`OO:src/plan.rs`, lines 190 to 222). |
| A separate Lean checker re-verifies the proofs offline | A certificate is two tab-separated files, `asserted.tsv` and `derivations.tsv`, with `asserted.sha256`. `oo-cert` and `oo-horn` re-derive each line under the rule it names and exit 1 on a line that does not hold, under the theorem `OOCert.certificate_sound` (`OO:README.md`, "What the proof contains"). The project states its limits: an unsatisfiability answer carries no guarantee, its Rust and Python engines share one algorithm and are not independent, and the locality-module guarantee is cited, not machine-checked. |
| The README image: ies-core.ttl reasoned over and proved, with Vampire, E, Z3 and a Lean 4 certificate | The project's inventory calls E and Vampire differential oracles that are never an authority, Z3 and cvc5 solvers whose returned models are checked and whose unsat answers are testimony, and Lean 4 the only kernel behind its certificates (`OO:docs/reasoning-systems-inventory.md`, "Status at a glance"). |

### Protocol tools and how a change is authorized

- 122 tools at head, listed in `OO:docs/tool-reference.md`, which is generated
  from the `#[tool]` attributes of `src/server.rs` and held by a test. Eight
  need an optional Cargo feature (four `embeddings`, two `plugins`, two
  `postgres` or `duckdb`; `OO:src/toolfilter.rs`, line 450), so a default build
  serves 114. The registry declaration `.mcp/server.json` still says 116 tools
  and version 0.1.9.
- Disputed at the same commit: `OO:README.md` line 445 says the published
  binaries and the container image use the default feature set, while
  `OO:Dockerfile` line 13 builds the image with
  `--features embeddings,plugins,sql`.
- Tool groups that an operator can allow or deny (`expand_group`,
  `OO:src/toolfilter.rs`, line 499):
  - `read_only`, 15 tools described as "safe to expose to untrusted callers":
    `onto_status`, `onto_validate`, `onto_query`, `onto_stats`, `onto_diff`,
    `onto_lint`, `onto_history`, `onto_lineage`, `onto_cache_status`,
    `onto_cache_list`, `onto_repo_list`, `onto_dl_check`, `onto_dl_explain`,
    `onto_search` and `onto_similarity`. `onto_query` parses a SPARQL query,
    never an update (`OO:src/graph.rs`, `select_with_dataset` calls
    `parse_query`).
  - `mutating`, 21 tools that change the store, among them `onto_load`,
    `onto_clear`, `onto_save` (writes a file), `onto_reason`, `onto_ingest` and
    `onto_rollback`.
  - `governance`, 11 tools: `onto_plan`, `onto_apply`, `onto_lock`,
    `onto_drift`, `onto_enforce`, `onto_monitor`, `onto_monitor_clear`,
    `onto_align` and three feedback tools.
  - `remote`, 4 tools: `onto_pull`, `onto_push`, `onto_marketplace` and
    `onto_import`.
  - The other tools are in no group. Ten named tool profiles (`full`,
    `authoring`, `validation`, `reasoning`, `alignment`, `governance`, `data`,
    `planning`, `retrieval`, `evaluation`) narrow the surface by job, and
    `--tools-allow` and `--tools-deny` narrow it further.
- Authorization of apply (read in code, `OO:src/server.rs` line 2530 and
  `OO:src/plan.rs` line 267). No credential, approval or second person is
  asked for: any client that can call `onto_apply` applies. Without a
  `plan_id` it applies the newest plan of the calling session; a named
  `plan_id` reaches the plans of other sessions on purpose. A monitor watcher
  can set a block flag that `safe` and `migrate` respect and `force` ignores,
  and `onto_monitor_clear` clears it. Locked IRIs appear in the plan's
  `locked_violations` and are not checked again at apply.
- A plan does not bind the store it was computed against. The stored plan
  keeps the proposed Turtle and the added and removed class and property lists
  (`load_plan`, `OO:src/plan.rs` line 397). Apply recomputes the triple delta
  against the live store and brings it to the proposed state, so a store that
  changed between plan and apply is overwritten without refusal (inferred from
  the code, not run).
- Rollback (`onto_rollback`, `OO:src/server.rs` line 1015; `rollback_version`,
  `OO:src/ontology.rs` line 276) clears the store and loads the newest snapshot
  saved under a label, with no check of the state it replaces.
- Transport: `serve` speaks the protocol over standard input and output with
  no authentication. `serve-http` takes one optional bearer token from
  `--token` or `OPEN_ONTOLOGIES_TOKEN`, empty meaning disabled
  (`OO:src/config.rs`, line 693).
- Effects (read in code): network through the four `remote` tools and the HTTP
  listener; files through the state database under `~/.open-ontologies` unless
  `--data-dir` is given, `onto_save` and certificate folders; processes, since
  provers, Lean checkers and Fast Downward are started by name from `PATH`;
  credentials, the HTTP token and, in builds with `embeddings`, an embeddings
  API key. The command line has no `--version` flag (the clap `#[command]` at
  `OO:src/main.rs` line 181 declares no version). `version LABEL` saves a
  snapshot, and `status`, which prints the version, creates the data folder and
  its SQLite database (`setup`, `OO:src/main.rs` line 1457).

### External provers and their licences

None is linked into the engine. Each is a separate process found on `PATH`
(`OO:src/tstp.rs`, `OO:src/fol_solve.rs`, `OO:src/sat.rs`,
`OO:src/plan_classical.rs`), and none is needed for plan, apply, rollback or the
RDFS and OWL RL certificates. Versions are the project's own
(`OO:docs/reasoning-systems-inventory.md`, line 21 onward). Licences were read
from each upstream licence file.

| System | Role in the project | Licence, from the upstream file | GitHub's licence interface |
|---|---|---|---|
| Lean 4 v4.33.1 | The kernel of every checker; core only, no Mathlib | Apache-2.0 (`leanprover/lean4`, `LICENSE`) | Apache-2.0 |
| Vampire 5.1.0 | First-order prover, an oracle | "a (modified) BSD 3-Clause licence" (`vprover/vampire`, `LICENCE`) | NOASSERTION |
| E 3.2.5 | First-order prover, an oracle | Both GPL-2.0-or-later and LGPL-2.1-or-later (`eprover/eprover`, `COPYING`) | NOASSERTION |
| Z3 4.16.0 | SMT solver; models checked, unsat answers testimony | MIT (`Z3Prover/z3`, `LICENSE.txt`) | NOASSERTION |
| cvc5 1.3.4 | Second SMT oracle | Modified BSD; optional GPL libraries are off by default (`cvc5/cvc5`, `COPYING`) | NOASSERTION |
| Isabelle/HOL | A second formalisation, not a runtime dependency | BSD-style (`isabelle-prover/mirror-isabelle`, `COPYRIGHT`) | NOASSERTION |
| Rocq 9.2 | A third formalisation of the Horn layer only | LGPL-2.1 (`rocq-prover/rocq`, `LICENSE`) | LGPL-2.1 |
| Fast Downward | Classical planner behind `onto_plan_classical` | GPL-3.0 (`aibasel/downward`, `LICENSE.md`) | GPL-3.0 |
| Mace4 and Prover9 | Model finder kept, prover declined | Not checked here | Not checked |
| Oxigraph | The linked RDF store and SPARQL engine, patched to a fork | Apache-2.0 for `LICENSE-APACHE` | Apache-2.0 |

The GPL and LGPL programs stay separate processes and are optional, so they
put no condition on the MIT engine as Baltor would start it (inferred). Baltor
re-hosts no binary in any case. The Rust dependency tree was not audited crate
by crate.

## Step 2: library supply

### The programs line

`tools/supply_lines/program_installs.py` is keyed by Homebrew formula. It reads
`formulae.brew.sh/api/formula/<name>.json`, and GitHub release digests only add
to a formula's recipe when the release tag carries the formula's version. Open
Ontologies passes the licence gate (MIT, interface and text agree) and the
checksum gate (a published digest for every asset, agreeing with
`SHASUMS.txt`). It has no formula.

The dry run used the line's own reader in this worktree, with a candidate row
added to `program_sources.json` for the run:

```text
["open-ontologies", "open-ontologies", ["status"], "fabio-rovai/open-ontologies",
 ["network", "reads_secret", "writes_fs"], "data"]
```

```bash
PYTHONPATH=.:tools:src python tools/build_library_supply.py programs \
  --run-folder /home/username/.le-ci-tmp/tmp/ontologies/programs-dry-run-1 \
  --authorize-network-reads --formula open-ontologies --materialize
```

| Run | Candidates | Refused | Reason | Store |
|---|---|---|---|---|
| `--formula open-ontologies`, 2026-10-05T15:16Z | 0 | 1 | `not_a_command_line_program`: "formula answered 404" for `https://formulae.brew.sh/api/formula/open-ontologies.json` (request 2 at 15:16:03Z; request 1 read the Homebrew analytics) | not written: no `--authorize-store-writes` |
| Control, `--formula jq`, same command | 1 | 0 | none | not written |

The row was removed after the run because the task admits a row only when its
dry run passes; `program_sources.json` is unchanged. Any later recipe needs two
facts from above: the version arguments cannot be `--version`, and `status`
writes the data folder, so its smoke test has to pass `--data-dir` with a
disposable folder.

Decision: rejected for now. A line change would admit it, and this task does
not make one: a GitHub release mode of the programs line, keyed by repository
and tag, that takes GitHub's published digests, and the provenance attestation
when present, as the recipe's checksums. Open Ontologies would pass such a mode
today. Estimated effort is about one day with tests in
`tools/supply_lines/program_installs.py` and `tools/test_supply_lines.py`. The
same mode would open the line to other single-binary programs without a
Homebrew formula; how many was not counted.

### The protocol server line

- The official registry does not list it. The supply line's complete pass of
  October 5 (started 00:56:35Z, finished 02:14:48Z, 39,437 entries read,
  `registry_complete: true`, run folder
  `/home/username/baltor-library/supply/mcp-registry/2026-10-04`) holds no
  entry and no refusal that names `fabio-rovai` or `open-ontologies`, in its
  quarantined entries or in `refusals.jsonl`. Later the same day
  `https://registry.modelcontextprotocol.io/v0.1/servers?search=open-ontologies`
  returned `{"servers":[],"metadata":{"count":0}}`, and
  `.../v0.1/servers/io.github.fabio-rovai%2Fopen-ontologies/versions` answered
  404 while the same path for `io.github.wlsdks/ontology-atlas` answered 200.
- The repository prepares a listing. `OO:README.md` line 1 carries
  `<!-- mcp-name: io.github.fabio-rovai/open-ontologies -->`, and
  `OO:.mcp/server.json` declares that name, version 0.1.9 and one package:
  `registryType: oci`, `ghcr.io/fabio-rovai/open-ontologies:0.1.9`, transport
  stdio.
- A listing of that declaration would still give no package. The line packages
  only entries with an npm or PyPI package run over standard input and output
  (`_has_package`, `tools/supply_lines/mcp_registry.py` line 82) and refuses
  the rest as `no_npm_or_pypi_package` (line 256). The PyPI package
  `open-ontologies-lite` has a `server` extra, but no registry entry names it.
- The line has no single-server selection, so this step ran no new dry run: a
  second full pass would read about 39,000 entries for one answer. The
  decision rests on the complete pass above and on the line's code.

Decision: no connection package now, and none would result from listing the
current declaration.

## Step 3: engine fit

None of the 51 slots in `src/loop_engine/data/engine_slots.yaml` reasons over
RDF or OWL, plans a schema change or computes the impact of a change. The
nearest by name are `library_format_validation`, which checks a package
against its published format, and `catalogue_qualification_resolver`, which
decides whether an item binding is approved; neither takes a graph and a rule
profile. No Baltor caller reads an ontology, a knowledge graph or SPARQL. Step 1
of section 11 of the
[functional component standard](../architecture/FUNCTIONAL-COMPONENT-STANDARD.md)
("Add a slot only when none fits", LE-SLOT-001) and this task's rule (no slot
without a caller) give the same answer.

Decision: no slot now. A step that needs one would get this slot:

```text
knowledge_graph_reasoning (sketch only, not catalogued)
├── edge
│   ├── request: graph bytes and digest, rule profile, goal triples
│   └── result: derived triples, certificate files, the independent checker's verdict
├── selection: one_of; a result stays a candidate until a checker verdict accepts it
├── engines
│   ├── open_ontologies_cli: engine adapter, v2.0.1 at d1187190, MIT, Linux binary 7a54594a...
│   │   ├── a container from the GHCR image with no network, because it has network tools
│   │   └── or a supervised subprocess with --data-dir in a disposable folder
│   └── Baltor-native track: optional. A standard-library RDFS closure that writes the same
│       certificate files is small, and the Lean checkers check either engine's certificate
└── conformance kit: W3C RDFS and OWL 2 RL entailment cases, and a forged derivation line that
    every engine's checker must refuse (the project's own known-wrong case)
```

## Step 4: ideas for Baltor's catalogue change path

### Compared with what Baltor has

| Concern | Open Ontologies | Baltor today | Assessment |
|---|---|---|---|
| Declaring a change | The proposed Turtle is the whole desired state; anything absent is removed | `catalogue_reconciliation_request/v1` declares additions, replacements with expected versions, and withdrawals with expected versions and a note; anything undeclared is refused (`validate_result` and `compose`, `tools/reconcile_catalogue_bundle.py` lines 196 and 220) | Baltor is stricter |
| Binding to the base | None: apply recomputes against the live store | The request names `base_release` and `base_bundle_digest`. `require_live_base` (line 156) compares release, content digest, schema digest and population with the live view before composing, before upload and before the pointer moves, and the service refuses a moved pointer as `catalogue_pointer_moved` (`src/loop_engine/core/service_runtime/catalogue_releases.py` line 291) | Baltor is ahead |
| What apply names | A `plan_id` | The reconciliation proof's SHA-256 and the bundle digest (`publication_inputs`, `tools/publish_catalogue_delta.py` line 274); `check_proof` recomputes the proof from both bundles (line 292) | Baltor binds content, not only an identifier |
| Shape counts | Added and removed classes, properties and individuals, triple delta, blast radius, a risk word | Proof counts of unchanged items, additions and replacements; new blob count and bytes from `write_reconciled`; added, changed and withdrawn items in the release record (`_changes`, `catalogue_releases.py` line 261); blobs present and to upload in the delta plan | Equivalent for items and files |
| Consequences beyond the shape | Opt-in conservativity: the consequences over names the store already uses that a change adds, each with its rule and premises | None computed. The runbook says a replacement "needs separate review of any exact-version access grant" (`docs/guides/launch-setup-runbook.md` line 563), and nothing lists those grants | The gap worth closing |
| Guards | Locks only warn; `force` passes the monitor block | Every guard refuses; no bypass mode | Baltor is ahead |
| Rollback | Restores a labelled snapshot with no expected state | `rollback-catalogue` needs `--expected-release`, verifies every body of the target release before moving the pointer and keeps durable withdrawals withheld (`catalogue_releases.py` line 404) | Baltor is ahead |
| Checking the proof | A Lean program that shares no code with the engine | `check_proof` recomputes the proof with `proof_for`, the same code that wrote it | A shared misreading would pass both |

### Advances to adopt

1. A consequence report of a catalogue change, before publish (adapted). A
   read-only `catalogue_change_plan/v1` record written beside the private
   `reconciliation.json` and never uploaded as material. For the declared
   change it lists:
   - items: added, replaced and withdrawn identities with old and new versions
     (already in the proof);
   - files: new blobs and bytes (already computed), and blobs that no served
     item references after the change;
   - search entries: cards added, changed and removed, and the judged queries
     of `examples/30_search_quality/relevance-judgements.json` (354 requests)
     whose top 10 changes when the same search policy runs over the base and
     over the candidate;
   - grants, read on the host: Public Good grants naming a replaced or
     withdrawn version (`service_public_good_access_grant/v1` pins one
     `item_version`, `src/loop_engine/core/service_runtime/public_good.py`
     line 82); snapshot grants (`service_grants/v1`, whose item bindings carry
     body and descriptor digests) naming a replaced or withdrawn item; accounts
     that follow the release (`service_grants/v2`) and will receive the
     additions; additions that declare effects and stay withheld until a client
     declares them.

   Where: the local part as a `--plan` mode of
   `tools/reconcile_catalogue_bundle.py`, or a sibling
   `tools/plan_catalogue_change.py`; the host part as a read-only service
   command `catalogue-plan` beside `catalogue-status` in
   `src/loop_engine/core/service_runtime/catalogue_commands.py`, built the way
   `follow_all_tenants_preview` (line 91) already previews a grant move
   without writing. Effort: about one day for the local part and one to two
   days for the host part. Each needs a known-wrong case: a replacement of a
   version that a fixture Public Good grant names must appear in the report,
   and a report that omits it must fail the test.
2. A verdict for additions-only releases (adapted, part of item 1). The daily
   sequence adds items only, so its expected property is that nothing already
   served loses a consequence: no judged query loses an expected item from its
   top 10, and no grant names a changed version. The report states
   `conservative_over_judged_queries` or `not_conservative_over_judged_queries`
   with the lost rows. The word names what was measured, the stored judged
   queries, and is never a guarantee over all queries, just as Open Ontologies
   names its verdict for its rule table. Effort: half a day on top of item 1.
3. An independent proof checker (optional). A standard-library script, for
   example `tools/check_reconciliation_proof.py`, that imports nothing from
   `loop_engine`, reads the two bundles and `reconciliation.json`, and checks
   byte by byte that unchanged rows are identical, that additions,
   replacements with new versions and withdrawals are exactly the declared
   ones, and that counts and content digests recompute. The delta publisher
   would run it beside `check_proof`. Known-wrong cases: an undeclared changed
   row, a missing row, a retag that changes only the batch, a forged count.
   Effort: half a day to one day. It catches a misreading shared by
   `proof_for` and `check_proof` and grants no authority.
4. Protected identities (adapted, after item 1). Open Ontologies' locks only
   warn. Baltor could keep a host-side list of identities that a
   reconciliation may replace or withdraw only with a named review for each,
   for example the items that exact-version Public Good grants bind, which
   item 1 lists, and refuse at compose time. Where: an input file read by
   `_declared` in `tools/reconcile_catalogue_bundle.py`, so the request record
   keeps its version. Effort: half a day.

### Rejected

- Recomputing a change at apply time without binding the base, a `force` mode
  that passes a guard, and locks that only warn. Baltor's compare-and-swap and
  refusals already do better.
- Monitors that roll back on their own (`auto_rollback`). An automatic pointer
  move after a failed check would be a second writer beside the operator;
  Baltor's rollback stays an explicit command with an expected release.
- Feedback that suppresses a warning after three dismissals
  (`OO:docs/lifecycle.md`, "Feedback"). Dismissals would silence a check
  without a recorded decision.

## Its ontologies as library material

| Material | Licence evidence | Decision |
|---|---|---|
| `ies-core.ttl`, the ontology of the README figure | Upstream `IES-Org/ies-core` at `206b83bb13cbc32ef154c1c426087335162075bb`: `spec/ies-core.ttl` (89,207 bytes, SHA-256 `f28bf6979a252c79f4843346380a578ddcd869e96827ded56cfc432887ff84f3`, version "0.1.2 (RC1)") opens with the MIT licence text under "Crown Copyright (c) 2026" and declares `dcterms:license <https://spdx.org/licenses/MIT.html>`. The repository's `LICENSE.md` licenses code under MIT and documentation under OGL-UK-3.0. GitHub's interface answers NOASSERTION for it, for every repository of `IES-Org` and for the archived `dstl/IES4` | Rejected for now. The lines' licence code (`decide`, `tools/supply_lines/licences.py`) answers `licence_unknown` when GitHub names no licence, and no line reads Turtle. The in-file MIT statement is bound to the exact file, so a per-file licence path could later admit it together with its SHACL validation files; that is a change to the lines' licence code, not made here. The copy in Open Ontologies (`OO:benchmark/reference/ies-core.ttl`, 86,907 bytes, version "0.1.0 (RC1)") is older than upstream |
| Case-study ontologies, for example `OO:case-studies/insurance-register-ontology/iro-core.ttl`, `OO:case-studies/investment-fund-ontology/ifo-core.ttl`, `heritage-aerial`, `robot-safety-security-crosswalk` and `modip-plastics-kg` | Each declares CC-BY-4.0 in the file (`dcterms:license`) or in its folder's `LICENSE`, "Copyright (c) 2026 Kampakis and Co Ltd, trading as The Tesseract Academy". `modip-plastics-kg` also holds source data © the Museum of Design in Plastics under CC-BY-4.0 and scripts under MIT | Rejected for now. CC-BY-4.0 is on the allowlist, but each file is a worked example for one case study rather than a reusable job, and a repository-level decision (MIT) would mislabel these files: an import must bind the licence per file and keep the attribution |
| `OO:benchmark/reference/pizza-reference.owl` | No licence or rights statement in the file | Rejected: no licence is bound to the bytes |
| The 33 standard ontologies of `onto_marketplace` (`OO:src/marketplace.rs`) | Fetched at run time from each publisher; the marketplace records no licence for a standard | Not material from this repository: each needs its own publisher's evidence |

## Limits

- No binary or container of Open Ontologies was downloaded or run. The
  901-consequence example and every behaviour described from code are as read,
  not reproduced.
- The provenance attestation was read from GitHub's interface and not verified
  cryptographically.
- The Rust dependency tree was not audited crate by crate.
- The registry finding rests on one complete pass and two direct lookups on
  October 5, 2026; the project can publish its listing at any time.
