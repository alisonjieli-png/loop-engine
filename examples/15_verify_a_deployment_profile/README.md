# Verify a deployment with a typed Loop profile

This example checks whether one deployment should continue or roll back. It
uses a versioned Verifier Practitioner profile and checks the typed connection
from a metrics loop before either loop runs.

## Why use a loop

A direct threshold function can make the final decision. The loop is useful
here because it gives the verification role, step profile, contract, mode,
decision path, and stop condition one inspectable identity.

## Run settings

| Setting | Value |
|---|---|
| Loop role | Verifier Practitioner |
| Run mode | Deterministic |
| Step profile | Adversarial review |
| Intelligence layers | None |
| Runtime Memory | Not used |
| Chronicle | Not saved |

## Install

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

## Run it

```bash
python3 examples/15_verify_a_deployment_profile/run.py
```

No key, network connection, input file, or external account is required.

## Expected result

The typed connection is compatible. The Verifier Practitioner runs four
deterministic steps and returns `rollback` because the observed error rate is
above the declared maximum.

The run makes zero model calls and writes no files.

## Watch it live

This example prints the final structured result. It does not start the live
viewer.

## Play it back

This example does not save a Chronicle. Use the campaign or playback examples
when saved playback is required.

## What this example does not prove

One fixed threshold check does not prove that the thresholds are correct for a
production system. It shows profile binding, typed port compatibility, and
deterministic execution.

Read [Loop profile ontology](../../docs/components/loop-object/LOOP-PROFILE-ONTOLOGY.md)
and [Typed loop connections](../../docs/guides/typed-loop-connections.md).
