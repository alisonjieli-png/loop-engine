# Experimental embodiments as independent launch surfaces

Status: accepted for the experimental project requested on 2026-09-07.

Scope clarified on 2026-09-08: this decision covers Loop Engine's internal experiments only. The user requested separately owned codebases and evaluators. Those live in the sibling `solver-lab` workspace, outside this repository. They do not depend on this lab, and Loop Engine is one project among peers. Existing experiments and their results remain here.

Scope updated on 2026-09-09: the current request explicitly places harness
implementations, dependencies and logs inside `/home/username/loop-engine`.
Older sibling workspaces remain reference inputs. A semantic-step embodiment
is now selected through the public solve configuration and the existing
external-harness registry. This does not enable the quarantined raw-host adapter
or introduce another operational runtime type.

## Decision

Add `embodiments/` as a development and distribution boundary. Every design gets a visible folder with its own status, launcher, manifest, tradeoffs and qualification plan. Shared comparison mechanics live in `devtools/embodiment_lab`. Product execution remains the canonical Loop runtime.

This structure preserves alternatives without duplicating engines. The distinction is implementation lifecycle: a persistent worker, a fresh process and a durable activation have different launch and failure semantics. A category alone cannot contain their runnable packages and qualification cases.

## Constraints

No embodiment may create a first-party operational `*Node` class, subclass Loop, bypass exact authority, or silently replace an unavailable provider with a fixture. The experimental catalog is passive discovery metadata. Existing runtime registries, canonical Run History and reactive output stores remain authoritative.

Only implemented and qualified configurations may be offered as working. Planned folders must refuse execution explicitly. No fixed winner is selected for users. Every comparative claim names the population, evaluator, model/fixture status, resources, failures and limitations.

## Initial scope

Six deterministic mechanism implementations establish the shared comparison path. Additional folders preserve adaptive decomposition, qualified code reuse, OpenCode, brokered containers, local host agents and transactional semantics as distinct plans. They do not claim live qualification from documentation or file presence.
