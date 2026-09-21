# Recorded direction: build general mechanisms

Kind: recorded guidance from a person, held in User Feedback Intelligence.

| Field | Value |
|---|---|
| Guidance type | `constraint` |
| Scope | `organization` |
| Strength | `instruction` |
| Timing | `next_safe_boundary` |
| Timing in the recorded words | before writing new control flow, prompts, or checks |
| Recorded | 2026-09-14, by the repository owner |

## The guidance as recorded

Build general mechanisms. Do not add control flow, prompts, or checks written
for one task, one dataset, or one benchmark.

## What it asks a step to do

Before adding a branch, ask what the branch is keyed on. If it is keyed on the
identity of a particular input, a particular file name, a particular customer,
or a particular benchmark, the branch is a shortcut that will pass today and
mislead tomorrow.

The general version is usually available and is usually shorter. A branch on
one dataset's column names becomes a branch on a declared schema. A prompt
written for one task becomes a prompt with a typed slot for the task. A check
that asserts one expected output becomes a check that asserts the property the
output must have.

## Response expected from a step

A step that receives this guidance should name what its new mechanism is keyed
on, and confirm that the key is a declared property rather than an identity.
When it cannot find the general version, it should say so plainly and record
the specific version as provisional rather than presenting it as the design.

## Limits

This is guidance, not permission and not proof. Generality is not an excuse to
build something nobody needs. A mechanism with one caller is still allowed to
exist; a mechanism with one caller and a branch on that caller's name is not.

## Source

`AGENTS.md`, section "Persistent general solving", first bullet.
