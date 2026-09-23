---
name: map-repair-support-requirements-to-assets
description: Map a supported repair procedure to required parts, tools and test assets. Use when a repair plan may omit a prerequisite or count an unqualified substitute.
---

# Map repair support requirements to assets

## When to use

Use for one product revision and one approved repair scenario. The result is a readiness map, not a repair instruction or permission to operate equipment.

## Inputs

- Versioned approved repair procedure and product revision, including safety prerequisites and acceptance tests.
- Bill of materials, asset inventory, tool calibration or qualification evidence, item compatibility rules, locations and availability dates.
- Supplied substitution and reuse rules; named people or roles required for a step, without assuming they are available.

## Procedure

1. Split the procedure into dependencies: diagnosis, disassembly, replacement or adjustment, reassembly and acceptance. Extract exact asset requirements from the approved source.
2. Match each requirement to a version-compatible part, qualified tool or test asset. Distinguish on hand, reserved, unavailable and evidence missing.
3. Account for quantities consumed versus assets that can be reused. A shared test fixture available once cannot support overlapping work unless scheduling proves it.
4. Mark substitutions as proposed until the supplied approval rule and version evidence permit them. Keep safety and calibration gates separate from stock counts.
5. Build a readiness table and identify the first blocking dependency for each planned repair window.

## Completion check

Return the exact procedure and revision, requirement-to-asset map, quantity and timing assumptions, qualified substitutions, blockers and missing evidence. A ready claim requires every mandatory predecessor and acceptance asset.

## Known-wrong case and stop

Ten compatible spare parts do not make a repair ready if the required calibrated tester has expired. Hold readiness when the approved procedure, compatibility rule, safety prerequisite or test evidence is absent. Do not perform repairs, order parts or override equipment controls.
