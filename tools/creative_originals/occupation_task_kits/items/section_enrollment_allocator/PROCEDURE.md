# Procedure: Section enrollment allocator with prerequisites and waitlists

Follow this procedure to do the activity with the helper `section_enrollment_allocator.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Which sections are open, with capacity, time block and course prerequisites?
2. How are priority groups defined (year, program, accommodation), and is registration time a tie-breaker?
3. Which completed courses count for prerequisites, and are in-progress courses accepted?
4. May a student hold two sections of one course (labs, repeats)?
5. Who may see the waitlists and enrollment results?

## Steps

1. Export sections, students and requests from the registration system into the input shape.
2. Validate the tables with record_entry_validator before running.
3. Run the helper; read enrollments, not_enrolled and section_fill.
4. For sections with long waitlists, decide whether to add a section or raise capacity.
5. For missing prerequisites, check the student record before telling the student.
6. Publish results to students individually; share only counts more widely.

## Decision points

### Order of processing

- priority group then registration time: choose when the institution publishes priority groups
- registration time only: choose when first come first served is the rule; put everyone in group 1

Default when nothing settles it: priority group then registration time

Evidence that settles it: the published registration policy

### Full sections

- waitlist: choose when seats may open later
- add a section: choose when the waitlist exceeds about half a section and staff exist

Default when nothing settles it: waitlist and report counts to the scheduler

Evidence that settles it: section_fill waitlisted counts

## Quality checks

- No section has more enrolled students than capacity.
- No student holds two sections of one course or two sections in one time block.
- Every enrolled student meets the course prerequisites.
- Each request appears once, in enrollments or in not_enrolled.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: one run on final requests; thorough: rerun after each add or drop window | same method |
| Tools | free: this helper with CSV exports; paid: student information systems | same rows |
| Privacy | student ids only in outputs | names stay in the source system |

## Stop and ask, or hand to a person

- Exceptions and overrides by advisers: a person records them and reruns.
- Fee holds and other registration blocks held in other systems.
