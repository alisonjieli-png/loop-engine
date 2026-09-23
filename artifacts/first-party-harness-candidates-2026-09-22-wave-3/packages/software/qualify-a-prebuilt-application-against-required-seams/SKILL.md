---
name: qualify-a-prebuilt-application-against-required-seams
description: Check a prebuilt application against mandatory interfaces, capabilities, deployment limits, and failure behavior. Use before recommending adaptation instead of a new build.
---

# Qualify a prebuilt application against required seams

## When to use

Use when a team is considering an existing package for a specified application need. This produces a fit and gap assessment from supplied contracts; it does not install, purchase, or execute the package.

## Inputs

- The required task outcomes, typed input and output contracts, identity and access rules, operating environment, and non-negotiable limits.
- The candidate package's exact version, interface specifications, documented capabilities, dependency and licence evidence, and independently observed interaction records when available.
- The intended integration points and the rule for accepting an adapter or manual step.

## Procedure

1. Turn every mandatory need into an observable obligation. Separate a capability label from its required data shape, volume, failure state, and authority semantics.
2. Map each obligation to an exact candidate interface and separate its documented claim from any independently observed interaction. Mark `observed supported`, `documented only`, `requires adaptation`, `unsupported`, or `unknown`. A precise specification is still a claim about behavior until a qualified interaction checks it.
3. For an adaptation, name the required mapping, the meaning it could lose, its dependency, and a check that would reject a wrong mapping. Keep an unsupported hard requirement as a blocker.
4. Check deployment constraints, maintenance status, licence compatibility, data location, and exit or migration cost using supplied evidence. An unknown condition stays unknown.
5. Compare the candidate's remaining adaptation work with the original requirement. Return the obligations, gaps, and tests a later build-versus-adapt decision must consider. Keep documented-only seams provisional.

## Completion check

Return a versioned obligation matrix with source references, claim-versus-observation status, adaptation work, blocking gaps, and the next discriminating test. A qualified fit claim needs independently checked evidence for every mandatory seam, especially failure and permission behavior; a documented-only match remains provisional.

## Stop

Hold a qualified fit recommendation when an interface version, required capability, rights state, or independent check of mandatory integration behavior is missing. Do not infer compatibility from a feature name, precise but untested specification, or successful demo on another workload.
