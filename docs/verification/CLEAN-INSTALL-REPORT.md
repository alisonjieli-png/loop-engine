# Clean install report

## Result

`VERIFIED WORKING` for the source-controlled wheel built from the pre-push
Checkpoint -1 tree.

Environment:

- Python 3.10.20
- isolated virtual environment outside the repository
- wheel installed with all 78 resolved dependencies
- commands executed outside the source tree

Proof:

| Check | Result |
|---|---|
| Import | installed `site-packages/loop_engine` |
| Public runtime | `Loop` |
| Runtime class name | `Loop` |
| Runtime subclasses | none |
| `LoopNode` export or attribute | absent |
| CLI help | passed |
| Self-test | 1,337 / 1,337 passed |
| Conformance | 28 / 28 gates passed |
| Wheel metadata | Twine passed |
| Source distribution metadata | Twine passed |

Artifact hashes:

```text
41a0b4caf2479c9f9671e634235ad675542fac8191e42c7c14e3ed174c812ed6  loop_engine-0.1.0-py3-none-any.whl
2ffe17e94a7000d49ffd1cada727c92f747470ae78722cfc41f3bec10b296502  loop_engine-0.1.0.tar.gz
```

The artifacts remain local build evidence. They are not a PyPI release.

## Current GitHub main proof

Commit `9ca80fdaec8c393561cacb623c8c3f0e523c3461` was installed from GitHub with:

```bash
python -m pip install \
  "git+https://github.com/alisonjieli-png/loop-engine.git@main"
```

Pip reported the same resolved commit. The proof used a fresh Python 3.14.4
virtual environment. Its dependencies had already been installed by the
preceding exact-wheel smoke; `loop-engine` itself was removed before the GitHub
installation.

| Check | Result |
|---|---|
| GitHub branch readback | `main` at `9ca80fda...` |
| VCS package build and install | passed |
| Installed public runtime | `Loop` |
| `loop-engine doctor` | passed |
| Five-step demo | solved and independently verified |
| Demo provider calls | 0 |
| Saved Run History | hash chain intact |
| Studio HTML and run query | passed on port 18765 |
| GitHub Actions | run `33109648651`, all five jobs passed |

The standard Studio command uses port 8765. That port was already occupied by
a separate Taedri Studio process in the proof environment. The installed Loop
Engine Studio was therefore verified with the same run directory and
`--port 18765`. The unrelated process was not changed.

The current source-controlled build artifacts have these hashes:

```text
25a36b25a32e89752d5a32412f90c6dff642bda40daff29015f51b5f65d89478  loop_engine-0.1.0-py3-none-any.whl
7ba828404c812fcee93399ca650aed0d8beca0c601363258a0b56f79e8cdbcc7  loop_engine-0.1.0.tar.gz
```

These artifacts also remain build evidence, not a PyPI release.
