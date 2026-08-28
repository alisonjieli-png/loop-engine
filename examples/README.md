# Examples

Install the complete package directly from GitHub:

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Each numbered folder has a runnable `run.py` and its own `README.md` with
network, model, file, cost, and external-effect notes.

## Useful work

| Example | What it does |
|---|---|
| [01 prioritize a support queue](01_prioritize_support_queue/) | Ranks support tickets by operational impact. |
| [02 predict customer renewal](02_predict_customer_renewal/) | Builds and grades a prediction artifact. |
| [05 Kaggle competition](05_kaggle_competition/) | Runs a narrow external competition workflow. |
| [06 reconcile invoices](06_reconcile_invoices/) | Reconciles invoices with nested loops and visible retries. |
| [10 validate a customer import](10_validate_customer_import/) | Compiles and runs a deterministic Solution Canvas with validation and fallback. |
| [20 inspect five text requests](20_compile_text_tasks/) | Checks five task-intake records without claiming that their solutions ran. |

## Models and intelligence

| Example | What it does |
|---|---|
| [03 connect a model](03_connect_a_model/) | Checks providers and makes one loop-governed model call. |
| [09 search the intelligence layers](09_search_the_intelligence_layers/) | Searches all four layers as a loop, returns `LoopRef` objects, and materializes one selected item. |
| [11 seed space Context Intelligence](11_seed_space_context/) | Gives a self-improvement task to a Practitioner Loop and prepares balanced categorized domain candidates. |
| [12 wrap a large codebase](12_wrap_a_large_codebase/) | Represents a million-line worker and a 9 GB dataset with small cards and selected component loops. |
| [13 Brave Search plugin](13_brave_search_plugin/) | Registers, discovers, and invokes a Core Architecture capability. The default run is offline. |
| [14 five-problem campaign](14_five_problem_campaign/) | Runs five frozen utility problems with deterministic loops and saves replayable histories. |
| [15 verify a deployment profile](15_verify_a_deployment_profile/) | Binds a versioned Verifier profile and checks typed loop ports before a deterministic release decision. |
| [16 audit published harness evidence](16_compare_complex_harnesses/) | Validates source-backed published results without running a harness or model. |
| [17 classify harness files](17_classify_harness_files/) | Classifies real repository sources into the four intelligence layers without activating them. |
| [18 three-model ensemble](18_three_model_ensemble/) | Trains linear, neural, and tree models as Spawned Loops, ensembles them, and verifies the result honestly. |
| [19 four-memory demonstration](19_four_memory_demonstration/) | Two-run migration scenario exercising working, episodic, semantic, and procedural memory through the canonical runtime. |

## Understand a run

| Example | What it does |
|---|---|
| [04 read run reports](04_read_run_reports/) | Writes text, Markdown, HTML, and JSON reports. |
| [07 watch a run live](07_watch_a_run_live/) | Shows console, polling, and server-sent events in real time. |
| [08 play back a saved run](08_play_back_a_saved_run/) | Loads the same saved Run History without rerunning the work. |

Run a local example from the repository checkout:

```bash
python3 examples/01_prioritize_support_queue/run.py
```

Installed examples do not assume a checkout location:

```bash
loop-engine --example support-queue
loop-engine --example intelligence-layers
loop-engine --example context-seed
loop-engine --live-demo --port 8770
loop-engine --studio --runs-dir "$HOME/.loop-engine/runs" --port 8765
```

New examples should follow the
[example README template](../docs/templates/example-readme.md). Keep the
problem realistic, name every external effect, and add each safe offline run
to CI.
