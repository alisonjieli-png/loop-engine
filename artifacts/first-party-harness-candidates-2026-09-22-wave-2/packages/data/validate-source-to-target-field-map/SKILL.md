---
name: validate-source-to-target-field-map
description: Review a proposed mapping from one source feed to a target schema. Use when field names match but units, row meaning, enumerations, nulls, or time semantics may differ.
---

# Validate a source-to-target field map

## When to use

Use this before treating an incoming feed as conforming to a target contract. A matching column name does not prove a matching meaning.

## Inputs

- Source and target schema versions, field definitions, row grains, keys, and representative values.
- The proposed field map and authorized transformation, enumeration, missing-value, and effective-time rules.
- The target's required fields and rejection behavior.

## Procedure

1. Compare source and target row grains and keys. Note any one-to-many or many-to-one mapping before checking fields.
2. For each mapped field, compare meaning, type, unit, allowed values, null meaning, time basis, and source of authority. Mark direct, transformed, ambiguous, or unsupported.
3. Check every required target field for an evidenced source or an explicitly supplied derivation. Record source fields with no target and target fields with no source.
4. Walk one ordinary record and one boundary or missing-value record through the proposed map. Show target values and every rejection or hold without inventing a default.
5. Report transformations that lose distinctions, such as collapsing two statuses into one, for a data owner to decide.

## Completion check

Return a versioned mapping table, sample record results, unsupported fields, semantic losses, and a proposed accept or hold decision for the mapping. Every required target field must have a supported outcome.

## Stop conditions

Stop an acceptance claim when row grain, field meaning, conversion, target requirement, or enum translation is unresolved. Do not write or load transformed records.
