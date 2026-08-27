# Nomenclature and architecture regression report

## Verdict

Checkpoint -1 is verified locally. Remote GitHub Actions verification is
pending the main-branch push that contains this report.

The sole concrete and public runtime is `Loop`.

```text
Node                         abstract structural category only
└── Loop                     sole concrete operational runtime

LoopDefinition               immutable executable description
LoopDefinitionRef            exact identity reference
LoopDefinitionRecord         passive searchable projection
LoopStartRequest             passive invocation request
LoopGraphDefinition          executable graph authority
SolutionCanvas               candidate and builder
RunHistory                   append-only execution evidence
```

There is no active first-party `LoopNode` class or package-root alias.
Historical serialized `kind: loop_node` input is accepted only by
`read_legacy_loop_node_record()` and migrates to `LoopDefinitionRecord`. New
records emit `kind: loop_definition_record`.

## Recovery preservation

| Artifact | SHA-256 |
|---|---|
| `artifacts/recovery/pre-semantic-repair.patch` | `cd63205a1832dfb8f58dca9abe7a2cfe0816e8c464b1ca1eeab211fb04ee0b8b` |
| `artifacts/recovery/pre-semantic-repair-files.txt` | `55fbf25e71af42fd2d10bb5df3ebc751fcf5faaf6592c119ccfee2422b1c0640` |
| `artifacts/recovery/pre-semantic-repair-head.txt` | `2ed9566084b3bc5e8dd47dfcb18db5743d9ee6e6d2257f2e2d38f41541cdc779` |
| `artifacts/verification/semantic_migration_manifest.jsonl` | recorded at final commit review |

The migration manifest records symbol, annotation, import, diagnostic,
serialized-contract recovery, ontology-front-matter, and semantic-authority
changes. The repair did not reset or discard the shared worktree.

## Change classification

`artifacts/recovery/change-classification.jsonl` separates:

- useful independent solve, routing, retrieval, learning, and parameter-boundary work;
- valid definition, record, reference, and semantic-dictionary cleanup;
- the rejected runtime rename and guard changes that were repaired;
- exact legacy record compatibility work.

## Deterministic proof

| Gate | Result |
|---|---:|
| Source self-test | 1,338 / 1,338 passed |
| Source zero-tolerance conformance | 28 / 28 gates passed |
| Clean-wheel self-test | 1,337 / 1,337 passed |
| Clean-wheel conformance | 28 / 28 gates passed |
| Runtime import | `Loop.__name__ == "Loop"` |
| Runtime subclasses | 0 |
| Public `LoopNode` export | absent |
| Active `LoopNode` classes | 0 |
| Legacy record migration | 4 / 4 passed |
| Saved canonical Run Histories | 11 / 11 loaded with intact chains |
| Semantic mutation checks | duplicate term, second runtime, active alias/class, and legacy emission detected |

Commands:

```bash
.venv/bin/python -m loop_engine --self-test
.venv/bin/python -m loop_engine --conformance
python -m build
python -m twine check <dist artifacts>
<clean-venv>/bin/loop-engine --self-test
<clean-venv>/bin/loop-engine --conformance
```

## Distribution proof

| Artifact | SHA-256 |
|---|---|
| `loop_engine-0.1.0-py3-none-any.whl` | `41a0b4caf2479c9f9671e634235ad675542fac8191e42c7c14e3ed174c812ed6` |
| `loop_engine-0.1.0.tar.gz` | `2ffe17e94a7000d49ffd1cada727c92f747470ae78722cfc41f3bec10b296502` |

The first wheel exposed missing intelligence package data. The corrected wheel
includes runtime-read Markdown, HTML, JSON, JSONL, and YAML assets. A later
install attempt hit temporary disk quota while copying NCCL; removing only the
temporary proof environments and retrying produced a complete installation.

## Remaining work

Checkpoint -0.5 remains not yet proven. The current static denominator is 251
first-party Python files, 1,923 analyzed public or cross-module callables, and
175 unapproved parameter-boundary findings. Complete file, symbol, folder,
string/blob, and generalization inventories plus the data-driven procedure
model belong to the next audit session.
