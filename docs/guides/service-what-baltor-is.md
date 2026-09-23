# What Baltor is

Kind: customer guide to the hosted library, the local engine and their current boundaries.

Baltor gives your coding tools and agents material for the step they are working
on: instructions, skills, tools and reusable code. Your client searches the
hosted library, chooses an item and downloads its exact bytes. You keep your
own harness and model access.

## The goal and the current service

The goal is to make harnesses and multi-agent systems more efficient at solving
unfamiliar tasks within the user's budget and permissions. That includes giving
each step suitable context, reusing working code and choosing appropriate
models and methods. A reusable solution is one possible result of that work.

The local engine's default design gives each focused step a fresh harness with
the material that step needs. The hosted library is usable through your existing
client today. Connecting to the library does not by itself install the engine,
start separate harness processes or finish a task for you.

## Where the work happens

```text
Your task
├── Hosted Baltor library
│   ├── Searches the material your account may see
│   ├── Returns small references before bodies
│   └── Delivers selected bytes and records applicable download usage
└── Your environment
    ├── Runs your harness and any local engine
    ├── Holds your provider settings and model credentials
    └── Loads material, performs work and checks the result
```

The library receives what your client sends in a request, including search
text, selected item identities and the service credential. A search can contain
project information if you put it there. The library connection does not upload
your repository or forward your model credentials automatically.

## Files and packages

An item can be a text file or a package of files. The `catalogue_package/v1`
format supports
native instructions such as `AGENTS.md` and `CLAUDE.md`, skills with supporting
scripts and references, tools, contracts, plugin declarations and configuration.
Check the catalogue to see which items are currently available to your account.
Format support does not mean every possible package is already published.

A harness must load material through its own supported mechanism. A plugin can
need explicit activation; a tool can need dependencies and execution permission.
Downloading a file establishes neither of those facts.

## Give the harness its current assignment

A reusable package does not automatically carry the current task, inputs,
acceptance conditions or first action. Supply those when you start the focused
step. A file named `node_context.md` or `agents.state` is not a universal startup
standard. Use the client's supported instruction file, task input or explicit
file-loading mechanism, and verify that the step received it. Keep temporary
task state separate from reusable library material.

## Read the reference before downloading

| Field | Meaning |
| --- | --- |
| `family` | The material's family. Hosted harness material uses `harness`. |
| `source_layer` | The source holding its body. Harness material uses `harness_local`. |
| `kind` | The declared item kind, such as `skill`, `tool` or `instruction_file`. |
| `license` | The declared licence. |
| `declared_effects` | Operations the material says it needs. These are not execution permissions. |
| `qualification_basis` | The basis reported by the service. `host_attested` is the host's attestation, not a new review performed by the download. |

The manifest includes a digest and says `verify_before_use`. Compare downloaded
bytes with that digest, and check the result against your task. Retrieval,
loading, use and acceptance are separate events.

## Models and payment

The hosted library does not supply a model subscription or run your task's
model calls. Configure models in your harness or local engine. Those calls can
go to a local endpoint, a server you operate or a hosted provider, within the
permissions you set. Provider charges are separate from Baltor Pro.

## Next steps

- [Get started](https://app.baltor.ai/get-started) for account access.
- [Get set up](service-getting-set-up.md) to connect your client.
- [Searching and retrieving](service-searching-and-retrieving.md) for references and package downloads.
- [Usage and what you pay for](service-usage-and-what-you-pay-for.md) for metering and retries.
