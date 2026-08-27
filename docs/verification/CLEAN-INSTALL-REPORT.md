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
