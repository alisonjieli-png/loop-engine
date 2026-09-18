# Branding options: is there a name beyond Loop Engine?

Date: 2026-09-18. Owner question: should the product be branded as a
frontier harness fabric or something beyond Loop Engine? This record checks
candidate names against the Python package index, GitHub repository names,
and domain name registrations on that date, and gives a recommendation. It
changes no name. Product, repository, distribution, and import names stay
Loop Engine, `loop-engine`, and `loop_engine` until the owner decides.

## What the name has to say

The product is a runtime where every executable vertex is a Loop, a
solutioning space of harness instances that reason, build, and act, a
solutions space of published executable solutions, four intelligence layers,
independent verification, and export to packages and containers. A name that
says only "memory" or only "agents" undersells it. A name that says "fabric"
says that many small independent instances are woven into one working
whole, which is the right image. The risk is that "fabric" alone is one of
the most used words in software.

## Checks performed

| Candidate | Package index | GitHub repositories with the name | Domain answers on 2026-09-18 |
|---|---|---|---|
| harness-fabric | free | 3 repositories contain the words in other orders; none named harness-fabric | harnessfabric.com registered (answers); harnessfabric.ai no answer |
| harnessfabric | free | none | as above |
| loop-fabric | free | 13 repositories match the words; three named LoopFabric or close | loopfabric.com and loopfabric.ai registered (answer) |
| frontier-fabric | free | not searched separately | frontierfabric.ai no answer |
| agent-fabric | free | 418 repositories match the words, including Microsoft Fabric samples | agentfabric.ai registered (answers) |
| harnessloom | free | none | harnessloom.com no answer |
| loomwork | free | 27 repositories | loomwork.ai no answer |
| loom-engine | free | not searched separately | not checked |

Collisions for the bare word "fabric" verified the same day:

| Name | What it is | Signal |
|---|---|---|
| danielmiessler/fabric | An open source framework for augmenting humans with AI, prompt patterns | 43,990 stars |
| hyperledger/fabric | A permissioned blockchain platform | 16,719 stars |
| Microsoft Fabric | A data analytics platform | product line with many samples |

A method note: "free" on the package index means the JSON endpoint for that
name returned not found; "no answer" for a domain means the resolver
returned no address, which suggests but does not prove availability. A
registrar query is the authoritative check and was not run.

## Assessment

- "Fabric" as a modifier works; "Fabric" as the name does not. Three large
  projects own the bare word, one of them an AI framework with tens of
  thousands of stars. A search for the product would land on them.
- "Harness fabric" is descriptive and unclaimed as a name on the package
  index and on GitHub. The .com is registered; the .ai domain gave no
  answer. "Frontier harness fabric" reads as a category description rather
  than a name; it is a good tagline.
- "Loop fabric" keeps continuity with Loop Engine and the Loop runtime, and
  it is free on the package index, but the .com and .ai domains are taken
  and three repositories already use LoopFabric.
- "Harnessloom" is free everywhere checked and carries the weaving image
  without the collision, at the cost of being a coined word.

## Recommendation

Keep Loop Engine as the runtime and repository name. Introduce the fabric
idea as the product category and tagline first: "Loop Engine, a harness
fabric for verified solutions." Reserve harnessfabric.ai and harnessloom.com
now if the owner wants the option; both are cheap to hold and neither
commits the name. Decide on a rename only after the hosted proof of concept
exists, because a rename before then costs documentation and package work
that the proof of concept needs more. If a rename happens, "Harness Fabric"
is the descriptive choice and "Harnessloom" the distinctive one.

## What this record does not do

It does not check trademarks, it does not query a registrar, and it does
not rename anything. The AGENTS.md identity rules and the conformance scan
for retired terms still apply.
