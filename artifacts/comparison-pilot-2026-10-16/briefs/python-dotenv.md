# AgentBriefs demonstration brief: python-dotenv 1.2.4

Kind: demonstration brief for the AgentBriefs proposal, written by engineering
on October 16, 2026 from dated public sources. It is not output of a qualified
AgentBriefs service. Every benefit below is a hypothesis to test. No experiment
has run, so this brief reports no realized benefit. The machine-readable form is
[python-dotenv.json](python-dotenv.json).

## Project as observed

[python-dotenv](https://github.com/theskumar/python-dotenv) reads key-value
pairs from a `.env` file. It is BSD-3-Clause-licensed, has 8,900 GitHub stars
and is listed under Configuration Files in
[awesome-python](https://github.com/vinta/awesome-python). Version 1.2.4 was
uploaded to [PyPI](https://pypi.org/project/python-dotenv/1.2.4/) on October 1,
2026.

- Its parser and writer have needed repeated repair. Version 1.2.3 (August 16)
  shipped pull request 680, which made `set_key` escape backslashes and made
  both quoted-value patterns treat a backslash as an escape. Version 1.2.4
  (October 1) fixed an empty unquoted value before an inline comment (663) and
  `dotenv get` on empty values (700) (`CHANGELOG.md`).
- Pilot task b withholds the parser half of pull request 680. None of the
  four pilot runs, two in each arm, changed the library within 20 requests.
  Two of them opened `parser.py` before the cap. Three spent 6 to 16 of their
  20 tool calls writing reproduction scripts and tests through unquoted shell
  heredocs, which change backslashes
  ([pilot report](../../../docs/verification/COMPARISON-PILOT-2026-10-16.md)).
- The test workflow at v1.2.4 covers Python 3.10 to 3.14, 3.14t and PyPy 3.11.
  The PyPI classifiers stop at 3.14.

## Opportunities worth one bounded experiment

### DV-1. Property-based round-trip tests for the writer and the parser

- **Evidence.** The three parser and writer fixes above came between August
  and October 2026. [Hypothesis](https://pypi.org/project/hypothesis/) 6.170.0
  (MPL-2.0, uploaded October 15, 2026) generates adversarial strings.
- **Estimated benefit, a hypothesis.** A property that every string written by
  `set_key` in each quote mode is read back unchanged by `get_key`, with the
  next key intact, would have caught the defect that pull request 680 fixed.
  It may catch the next one before release.
- **Experiment.** Generate values from text with backslashes, both quote
  characters, `#`, `$`, spaces, tabs and line breaks. Write each with
  `set_key` in the `always`, `auto` and `never` quote modes, write a sentinel
  key after it, and read both back. Run 2,000 examples against v1.2.2, the
  known positive, and against v1.2.4. Accept if it finds the backslash
  failure on v1.2.2, and if every failure on v1.2.4 is either a real defect or
  documented behaviour, such as `never` mode with a line break. Keep every
  counterexample.

### DV-2. A conformance table against two other `.env` readers

- **Evidence.** Node.js ships its own reader, `util.parseEnv`, added in
  v21.7.0 and v20.12.0 and no longer experimental since v24.10.0 and v22.21.0
  ([Node.js documentation](https://nodejs.org/api/util.html#utilparseenvcontent)).
  [Docker Compose](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/)
  uses single-quoted values literally, while python-dotenv 1.2.4's own tests
  expect `a='${b}'` to expand `b`. Baltor's
  [MCP directory](https://baltor.ai/directory) (October 14) lists agent
  servers that parse or compare `.env` files with their own code, such as
  EnvSync-LE (updated October 7, 2026).
- **Estimated benefit, a hypothesis.** A published table of where the three
  readers agree and differ would spare users who share one `.env` file across
  Python, Node and Compose some silent surprises.
- **Experiment.** Feed the same 60 fixtures (quotes, escapes, comments,
  `export`, interpolation and defaults, empty values, line endings) to
  `dotenv_values`, Node's `util.parseEnv` and `docker compose config`. Record
  each disagreement with the upstream documentation line that explains it.
  Accept as useful if it finds at least three disagreements and every one is
  traced to a source. Effects: local processes only; no file is published
  without the maintainers.

### DV-3. Add Python 3.15 to the test matrix

- **Evidence.** Python 3.15.0 was released on October 9, 2026
  ([endoflife.date](https://endoflife.date/python)). The v1.2.4 test workflow
  and the PyPI classifiers stop at 3.14 and 3.14t.
- **Estimated benefit, a hypothesis.** Users learn early whether 3.15 works.
  The cost is one more matrix job per run.
- **Experiment.** Run the existing suite on 3.15 and 3.15t in a fork. Accept
  if it passes or every failure is reported upstream.

## Considered and not recommended

- **Withheld: a model that repairs malformed `.env` files while loading.** No
  source read for this brief supports it, and it would send secrets to a
  model provider. It would make a deterministic parser nondeterministic and
  could rewrite a value silently. The brief raises no alert for it.
- **Advisories: none listed.** [OSV](https://osv.dev) returned no advisory
  for python-dotenv 1.2.4 or click 8.5.0 on October 16, 2026. An empty answer
  is not a security certificate, so the brief raises nothing.
- **Maintenance note, no experiment needed.** Python 3.10 reached end of life
  on October 1, 2026, and 1.2.4 still declares `requires-python >=3.10`. When
  to drop it is the maintainers' choice.

## Sources read on October 16, 2026

| Source | What it supplied |
| --- | --- |
| PyPI JSON for python-dotenv and hypothesis | Versions, upload dates, licences, classifiers |
| python-dotenv v1.2.4 tree (commit `a565c2cc`) | Changelog, test workflow, tests, README |
| Upstream commit `f7b18d9c` (pull request 680) | What the backslash fix changed |
| endoflife.date Python product | 3.15.0 release date, 3.10 end of life |
| OSV queries for python-dotenv 1.2.4 and click 8.5.0 | No advisory listed |
| Node.js util documentation (v26.12.0 page) | `util.parseEnv` history |
| Docker Compose interpolation documentation | Quoting and interpolation rules |
| Baltor MCP directory data | `.env` parsing and comparison servers |
| Baltor model directory and research watch | No entry bears on this library |
