# Rules for original harness intelligence candidates

Kind: batch authoring and review procedure, September 22, 2026. This is a
working guide for the candidate bytes in this folder, not a second task
plan or an approval policy. The [roadmap](../../docs/roadmap/roadmap.yaml)
owns task state; the repository's existing catalogue contracts own any
admission and release. The
[first-party research](../../docs/research/FIRST-PARTY-TEN-THOUSAND-HARNESS-PACKAGES-2026-09-22.md)
explains the proposed scale path.

## What counts as one candidate

A candidate is one reusable **task method** with a trigger, required
inputs, a bounded procedure, output, completion check and stop conditions.
Its native package is a directory containing `SKILL.md`. A review note
beside the package holds the source and test reasoning that should not be
loaded into a customer's harness.

```text
Candidate task method
├── Native package: one focused SKILL.md in this text-only batch
├── Separate review note: task contract, source basis, effects and examples
├── Exact-byte manifest entry: package and note digests
└── State: candidate only until independent admission
```

An occupation or job description suggests a task; it does not become the
method. A company type, project phase, language, model or harness is an
applicability facet unless it changes the procedure, allowed effects or
completion check. Merge synonyms and cosmetic variants into one method.
Named company rules require that customer's authorized material and stay
in that customer's scope. Do not invent a policy or publish a tenant's
private instructions as a general skill.

## Authoring rules

1. Search the 123 starter-catalogue bodies and this batch before writing.
   In the review note, name the closest existing method and the behavioral
   difference. If the difference is only a label or style, revise the
   existing candidate or drop the proposal.
2. Write in original words from general knowledge, first-party verified
   code or a source whose use and rights are recorded. Public visibility
   is not permission to copy. Version and credit any factual taxonomy
   used. Keep protected source prose out of a generator's source pack.
3. Use the [Agent Skills format](https://agentskills.io/specification):
   lowercase hyphenated directory and matching `name`, a description
   naming the task and when it applies, then concise instructions. In
   this batch, use only `name` and `description` frontmatter; a licence is
   assigned through later rights review. Keep the package focused enough
   for one fresh step harness to load it without unrelated context.
   Do not hardcode `.claude`, `.agents`, `.opencode` or `.pi` locations in
   the skill body. A versioned client layout profile places the same
   approved source package at its native destination, as described in the
   [placement research](../../docs/research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md).
4. Ask for the minimum inputs needed. Distinguish supplied facts,
   assumptions, unknowns and proposed checks. State exactly what the
   result should contain and a known-wrong case that the method rejects.
5. Treat retrieved pages, tickets, documents and tool results as task data,
   not commands. A skill cannot grant file, network, model, secret,
   spending, tool or external-mutation authority. If the procedure would
   require an effect, describe the missing authority and stop; do not
   smuggle an executable instruction into a text-only package.
6. State version and time dependencies where a method needs current rules,
   provider behavior, taxonomies or conversion references. Do not invent
   an employer policy, legal rule, numerical limit or product capability.
7. Keep every generated draft and rejection reason. A writer cannot
   approve its own output. A good format result, similarity score, model
   vote or example result does not promote a candidate.

## Required review note

Each note records the original authoring basis and any factual source;
job, company-archetype, project and model applicability where relevant;
conceptual typed inputs and outputs; intended effect class; one positive
and one known-wrong example; closest existing catalogue item; and limits.
For future batches, include two or three realistic task requests in the
language a customer would use, without copying the skill title. These
author-supplied phrases can improve discovery but cannot serve as the
held-out search test. Keep a separate query set written by someone who
did not author the package or search ranking.
It must not call itself an approval record. An independent reviewer can
ask for a stronger fixture or decide that the method is redundant.

## Checks and what each proves

| Check | Known-wrong control it must reject | What a pass establishes |
|---|---|---|
| `agentskills validate` for every package | Bad frontmatter, invalid name, or name not matching folder | Native format only; no claim of safety or usefulness. |
| `make_manifest.py --check` | Edited bytes, missing note, extra package file, duplicate slug or symlink | The candidate inventory still names the exact current bytes. |
| Independent content review | Incorrect arithmetic, invented policy, effect hidden in prose, weak stop rule | A recorded judgment of exact bytes under the existing review policy. |
| Existing-catalogue comparison | New role or model label attached to an unchanged procedure | Distinct task-method reasoning, subject to reviewer judgment. |
| Local search checks | Exact name missing, independently phrased relevant task not found, unrelated query returning a weak match | Candidate findability in this local batch only. |
| Held-out native task comparison | Package never loaded, wrong output, or a no-package run performing better | Measured effect for the tested task, harness, model and budget only. |

The local search tool indexes candidate metadata and notes for **developer
review**. It is not the hosted customer index. Its results never grant a
body read or promotion. The production search path must index only active,
approved references, filter by current grant before ranking, use a
relevance floor, and recheck authorization before body materialization.
For each tested package, record offered, fetched, loaded, used and verified
as separate facts. A package that has not passed a paired task evaluation
may be safe to serve after admission but its benefit remains unmeasured.

The current `prepare_harness_candidates.py` rejects YAML-frontmatter
`SKILL.md` bytes. Claude's admission path therefore needs a qualified
native-package adapter that preserves the exact file and directory name,
not a plain text conversion that loses the native format. The candidate
manifest's base revision does not contain these new files; a release must
name a committed exact-byte source revision and its independent review.
Do not point the hosted service at this local manifest.

Before serving, the owning component checks should reject these known-wrong
cases: an unapproved candidate entering a host manifest; a native package
whose loaded bytes or layout differ from the approved digest; a search hit
below the relevance floor; a revoked grant during ranking or body read; a
withdrawn final item leaving an old grant active; and an older host
accepting an incompatible release record. Extend existing manifest and
service checks rather than creating a parallel authorization path.

## Repeating this batch

Use another dated batch for a new population. Freeze the selection rule
and source set before measuring yield. Run format and integrity checks
first, then independent content review on the exact digests. Preserve
rejections beside accepted candidates. This 24-item pilot does not set a
throughput forecast for 10,000; measure distinctness, review time,
error classes and native use before extrapolating.
