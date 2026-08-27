# Live Ollama text-scenario verification

## Result

`VERIFIED WORKING` locally for one bounded Ollama Cloud route and five public
text tasks. GitHub Actions now runs the same check after trusted pushes to
`main` and saves a secret-safe artifact.

This is a provider and typed-orientation proof. It is not proof that the five
requested solutions were executed.

## Execution path

```text
trusted push to main
└── GitHub-hosted Ubuntu runner
    └── five reviewed text files
        ├── model-free task compilation
        ├── model-assisted Orientation decision through ModelGateway
        │   └── one Ollama Cloud model-attempt Loop
        ├── ordinary typed contract validation
        └── secret-safe evidence result
```

The GitHub workflow is scheduling infrastructure. It does not have a Loop run
mode. The compilation work is model-free. Each semantic provider attempt is a
model Loop. Ordinary code independently checks the returned JSON contract.

## Local live result

The accepted run used:

- provider: `ollama_cloud`;
- route: `cloud.default`;
- model: `deepseek-v4-flash:0731`;
- scenarios: `5`;
- physical model attempts: `5`;
- provider-reported tokens: `4,043`;
- elapsed wall time: `12.876548` seconds;
- failover: disabled;
- result: five accepted `ready` decisions.

## GitHub Actions result

GitHub Actions run
[`33123560731`](https://github.com/alisonjieli-png/loop-engine/actions/runs/33123560731)
passed all six jobs at feature commit
`c203aa2a8a6857a700014fc8fa12bb870e2ca340`.

The `five live Ollama text scenarios` job:

- completed in `55` seconds;
- made `5` physical model attempts;
- accepted all `5` typed decisions;
- recorded `3,733` provider-reported tokens;
- uploaded `live-ollama-scenarios.json`;
- produced artifact content SHA-256
  `2919306eba0faba9c53d0b884dce919711ac8487e96b8473587ad49468895894`;
- passed a downloaded-artifact secret-shaped value scan.

The five live tasks reuse the text files in
`examples/20_compile_text_tasks/tasks/`. Their live policy is autonomous. A
`ready` result means the next governed preparation step may begin. It does not
mean required files already exist, network or file effects are authorized, or
the task has finished.

## Security and failure behavior

Only the live scenario step receives `OLLAMA_API_KEY`. Checkout, Python setup,
package installation, and artifact upload do not receive it. Pull-request jobs
do not run the live lane.

Saved evidence excludes:

- credentials and authorization headers;
- raw prompts and model responses;
- private reasoning;
- raw provider error text.

The job fails when the secret is missing, the route is unavailable, provider
usage is unreported, a task makes anything other than one physical attempt, or
an output violates its exact typed contract. An Ollama outage therefore remains
a visible provider failure. It is not replaced by a fixture or another model.

## Limits

This proof covers one provider, one exact model route, and five small public
orientation tasks. It does not establish general model suitability, full
flagship modeling execution, dataset authorization, report generation,
production availability, or provider cost bounds.
