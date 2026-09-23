---
name: audit-resource-capacity-by-interval
description: Check whether planned work fits qualified resource capacity in each time interval. Use when a schedule fits the week's total hours but overbooks a shift, machine, or required skill.
---

# Audit resource capacity by interval

## When to use

Use this for a proposed schedule and a declared resource pool. Enough capacity over a whole week does not prove that each required interval is feasible. Passing interval totals alone does not prove that indivisible jobs can be assigned without conflicts.

## Inputs

- Planned jobs with demand units, duration or time windows, required qualifications, and any precedence or indivisibility rule.
- Resource identities, qualifications, working intervals, maintenance or break intervals, and capacity units.
- The scheduling horizon, time zone, and supplied rule for shared or interchangeable resources.
- A proposed complete assignment or a separately authorized feasibility result when a feasible-schedule verdict is requested.

## Procedure

1. Put demand and capacity on the same time basis and unit. Preserve indivisible work and qualification requirements instead of reducing everything to aggregate hours.
2. Partition the horizon at every job, shift, break, or maintenance boundary. For each interval, list eligible resources and overlapping committed demand.
3. Check capacity per eligible resource or declared interchangeable pool. Flag a job that can fit only by using an unqualified or unavailable resource.
4. Show the first overloaded interval and the jobs that contribute to it. Distinguish a firm assignment from a proposed one. An overload proves the proposal infeasible under the supplied rules; no overload is only a necessary check.
5. If a feasible verdict is requested, inspect a supplied complete assignment or a separately authorized feasibility result. Check each indivisible job's continuous placement, resource identity, qualifications, time window, breaks, shared-resource use, and precedence. Do not treat a solver's success label as proof without checking its assignment against these constraints.
6. State the smallest missing fact or constraint that prevents a feasibility decision. Without a valid assignment or separately verified result, report only that no interval overload was found.

## Completion check

Return interval-level demand and eligible capacity, assignment conflicts, overloads, and unresolved constraints. Report an overload as an infeasibility finding. Report a feasible schedule only when a complete assignment passes every supplied interval, identity, qualification, indivisibility, and precedence constraint; otherwise report that feasibility remains unverified.

## Stop conditions

Stop a feasibility claim if job timing, duration, qualification, time zone, resource availability, or a valid assignment is unresolved. Do not run a scheduler, move jobs, or modify a live schedule without separate authority.
