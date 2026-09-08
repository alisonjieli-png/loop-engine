# How context reaches a loop node, 2026-09-07

Question from the owner: if every loop node is its own harness instance, how
does information reach it? Passing everything on the command line looks like
it would explode and end up in logs. The alternative sketched was a stored
context object, queried by an identifier, holding the original task, a long,
medium and short horizon, and a node-specific package of instructions,
contracts, tools and plugins, with one shared ledger that every node writes
to as itself.

This note answers what happens today, states the three constraints that
decide the design, lists the options with their hazards, and names the traps
in the identifier design specifically. It recommends a default and a way to
measure. It changes no code.

Facts marked observed were measured on this machine on 2026-09-07 and the
commands are given. Facts marked inferred are reasoning from those. Facts
marked not established are unknown and are labeled as such.

## 1. What happens today

Observed. Nothing task-specific travels on the command line. The OpenCode
instance is launched as `docker run` with flags, an image, and
`node opencode_stdio_bridge.mjs`. The goal text rides a JSON frame written to
the container's standard input, in `opencode_gateway_bridge.py` around line
304. Context files are compiled into an instance bundle whose bytes are
digest-checked before launch, then mounted read-only at `/workspace`. The
review probe `probe_e_bridge.py` confirmed the goal is absent from both the
argument vector and the approval effect.

Observed. The native path is different: it renders one work packet in
process and calls the provider directly. `LLMWorkPacket` carries ordered
context blocks, and `ContextPackManifest` records exactly what that call was
allowed to see, with per-item decisions and digests. No transport question
arises because no second process exists.

So the question is really about the harness path, and about any future path
where a node is a separate process.

## 2. Three constraints that decide most of it

### The command line cannot carry the package

Observed. One argument vector element is capped at 131,072 bytes on Linux
(32 pages). Measured directly:

```bash
python3 -c "import os; print(32*os.sysconf('SC_PAGE_SIZE'))"   # 131072
python3 -c "
import subprocess
for kb in (127, 128):
    try:
        subprocess.run(['/bin/true', 'x'*(kb*1024)], check=True)
        print(kb, 'KB OK')
    except OSError as e:
        print(kb, 'KB', e)"
# 127 KB OK
# 128 KB [Errno 7] Argument list too long
```

Observed. In the live campaign of 2026-09-06 the mean model call carried
34,774 input tokens and the largest carried 57,986. At roughly four bytes per
token that is about 139 KB on average and 232 KB at the top. The average
packet already exceeds the wall.

So the command line is not a design choice here. It cannot hold the package
today, and it would fail intermittently, on the larger tasks first, which is
the worst failure shape.

### The command line is world readable

Observed. `/proc/self/cmdline` is mode 444 on this machine and `/proc` is
mounted without `hidepid`. Any local account can read the full argument
vector of any process. A packet can quote proprietary source, customer rows,
or a credential that appeared in an error string. The sibling overnight
engine reached the same conclusion and wrote it into
`core/prompt_transport.py`, which puts the prompt in a file created at mode
0600 and leaves one constant sentence in the argument vector.

### The sandbox has no network

Observed. The instance runs with `--network none --read-only --cap-drop ALL`
and the workspace mounted read only. A node therefore cannot open a
connection to a database, local or remote. "Query a centralized store" has
exactly three physical realizations:

1. Mount the store file read only into the container and query it in the
   node process. Requires the query engine inside the image. The pinned image
   is a bare interpreter, so this means a new image with the dependency, and
   it exposes the whole file to the node unless the file is already scoped to
   that node.
2. The node asks the host over the existing standard input and output frames
   and the host performs the query. This is a capability call, not a database
   connection. It fits the frame protocol already in place and is auditable
   because every request is a frame the host records.
3. The host resolves everything before launch and writes the answers into the
   workspace bundle. This is what happens today, and it is push rather than
   pull.

Inferred. Option 2 is the natural home in this codebase, because the grant
model already lives on the host side and a frame is already the unit of
audit. Option 1 trades the grant boundary for convenience. Option 3 is the
current default and stays available.

## 3. What already exists, so it is not rebuilt

Observed, by reading the modules:

| Piece of the sketch | What already implements it |
|---|---|
| Content-addressed storage with references | `core/context_artifacts.py`: `ContextArtifactStore.put_text` returns a `ContextArtifactRef` carrying a content digest; `get_text` reads it back |
| A reference that proves its bytes | `loop/atomic_primitives.py`: `LoopValue` and `LoopValueRef` carry content digest, value contract reference, semantic role, and producer identity |
| Scoped resolution of a reference | `core/information_access.py`: `InformationResolver.materialize` takes an `InformationAccessRequest` with the requesting Loop and run, and enforces `InformationScope` (private to one Loop, allowed Loops, run shared), `authorized_loop_ids`, and `maximum_bytes` |
| A record of what one call could see | `core/context_pack_manifest.py`: per-item include, compact, exclude and duplicate decisions, kept token estimates, and a pack digest |
| Querying a file as a database | `core/duckdb_catalog.py`: `read_json_auto` over a JSONL catalog, behind a backend interface with a file backend beside it |
| The shared ledger | `loop/recursive_loop.py` `LoopLedger` in process, projected to `core/run_history.py` with a digest chain; `core/stage_store.py` writes `stages.jsonl` per runs directory |
| Long, medium and short horizons | Not present here as a rendering. Present in the sibling overnight engine as `core/horizons.py`, which labels the same closed state as constitutional, run knowledge, and this step's working set |
| A closed pull vocabulary | Not present here. Present in the sibling engine as `core/ledger_pull.py`: named keys only, engine-authored script, every query logged, SQLite now and DuckDB behind the same interface |
| Named transport arms | Not present here. Present in the sibling engine as `core/node_package.py`: argv, blob, env, stdin, ledger reference, and hybrid, selected per run, each with its hazards written down |

Inferred. The sketch is close to what the sibling engine already prototyped,
and most of its parts exist here under different names. The work is
connecting them, not inventing them.

## 4. The transport options

Every option below carries the same package. They differ only in how the
bytes physically reach the process.

| Arm | How | Cost | Hazards |
|---|---|---|---|
| Argument vector | Whole package as one element | None | Fails above 131,072 bytes, which the average packet already exceeds; world readable through `/proc`; appears in process listings and in anything that logs a command |
| Environment variable | Package in a private variable | None | No size wall in practice and not in `/proc/<pid>/cmdline`, but crash dumps and some wrappers export the environment |
| Standard input frame | Package piped in, constant argument vector | None | No filesystem surface and no wall. This is what the bridge does for the goal today |
| Content-addressed file | One file at mode 0600, the digest is the name, a constant sentence in the argument vector | One write per node | Identical state stored once, inputs provable by digest. Needs the file visible to the process, which for a container means a mount |
| Reference only | The node receives identifiers and pulls everything | One query per need | Smallest launch, but a node that cannot pull is blind, and every pull is a round trip |
| Hybrid | Core rendered and delivered by file or frame, everything else pulled by reference | One write plus pulls actually made | The pragmatic default. Needs both halves to work |

Observed for this repository: the frame arm already works and is in use. The
content-addressed store already exists. The pull half does not exist here.

## 5. Traps in the identifier design

These are the places the sketch would go wrong if built literally.

**An identifier is not authority.** If presenting a context identifier
returns the context, then guessing or copying an identifier is a read of
another node's material. This codebase already answers this: a reference is
resolved through `InformationAccessRequest`, which names the requesting Loop
and run, and the resolver checks the grant. A probe run during the 2026-09-07
review confirmed a sibling Loop in the same run cannot dereference another's
grant, and that a reference with a changed contract, digest or producer is
refused. Any pull path must go through that check rather than treating the
identifier as a bearer token.

**Carry the digest, not only the identifier.** A bare identifier points at
whatever the row holds now. A reference carrying a content digest is
replayable and provable, which is what makes an evidence record worth
keeping. `ContextArtifactRef` and `LoopValueRef` both already carry one.

**Many writers on one ledger is a known failure here.** The sketch has every
node writing the run's ledger as itself. Two processes writing one SQLite
table is the exact defect fixed in the reactive scheduler this week: both
read revision N, both insert N plus one, the loser receives an integrity
error and its connection is left inside an open transaction, after which
every later write on it fails. Two shapes avoid it. Either each node appends
to its own segment, keyed by node identity, and the engine merges into the
canonical history; or the engine stays the single writer and nodes emit
frames it records. The second is what the bridge does now, and it also keeps
the authorship rule added this week, that a bound ledger refuses Loop-owned
events for a Loop identity nobody registered.

**A query engine inside the sandbox is a new dependency and a new surface.**
The pinned image is a bare interpreter. Mounting a store file and querying it
in the node means building and pinning a new image, and it hands the node the
whole file. Brokering the query through the host keeps the existing image and
the existing grant boundary.

**Reference passing does not shrink context by itself.** This is the finding
that surprised me. The horizon objects are small: the frozen task for
`grid_path_cost` is 3,613 bytes and one host observation is 4,466 bytes,
while the mean call carried about 139 KB. The packet is not large because the
task and the observation are large. It is large because of everything else in
it. Deferring the small objects behind references would save almost nothing.
Savings come only from material the node decides not to fetch, which means
the pull log is the measurement that matters: what a node asked for that the
push did not give it, and what the push gave that no node used.

## 6. Recommendation

Inferred, and offered as a starting position rather than a conclusion.

1. Keep the frame arm as the default for the harness path. It has no size
   wall, no filesystem surface, and it is already in use and tested.
2. Add the content-addressed file arm for material too large or too repeated
   for a frame, using the existing `ContextArtifactStore`. The digest is the
   name, so identical state across nodes is stored once.
3. Add the pull half as a host-brokered capability, not a database
   connection: a closed vocabulary of named keys, resolved through the
   existing `InformationResolver` with the requesting Loop checked against
   the grant, and every request recorded as a frame. The sibling engine's key
   list is a good starting vocabulary: task, long horizon, medium horizon,
   short horizon, fingerprint, intelligence hits, memory, a named prior
   node's patch, sibling files, and the pull log itself.
4. Render the state in three horizons. This is a labeling of context blocks
   the packet already carries, not a schema change, so it can be measured
   against the current rendering with the same fields.
5. Keep the engine as the single ledger writer, with nodes emitting frames.
   Revisit only if a measurement shows the round trip costs more than the
   merge would.

What to measure, in this order: whether horizon labeling changes patch
acceptance and re-ask counts on the same fields; then what the pull log says
the push got wrong; then whether the file arm beats the frame arm on repeated
material. The campaign runner version 2 already shares one runs directory
across tasks and passes, so the store has data to compare against.

## 7. Not established

The comparison between arms has not been run here. No pull vocabulary exists
in this repository yet. The sibling engine's transport arms are read but not
executed in this session. Whether a node that can pull makes better use of
its budget than a node given a larger push is the open question this note
exists to frame, and nothing here answers it.
