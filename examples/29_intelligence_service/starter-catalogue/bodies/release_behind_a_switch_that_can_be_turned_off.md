# Release behind a switch that can be turned off

Separate putting code into production from turning behaviour on, so the risky moment is a setting change rather than a deployment.

## When to use it

Use it for a change that is large, risky, slow to deploy, or that several teams must release together.

## Steps

1. Put the new path behind a named switch that defaults to off, and deploy it turned off.
2. Keep the old path working while the switch exists. Two paths is the cost you are paying for the ability to go back in seconds.
3. Make the switch a stored setting, read at use time, not something compiled in or read only at start.
4. Turn it on for yourself, then for a small group, then for a percentage, watching at each step.
5. Choose in advance what you watch and the value that means turn it off.
6. Make turning it off need no deployment, no build and no approval chain, and test that path before you need it.
7. Record who changed the switch, when and to what. A switch nobody can explain is worse than a branch in code.
8. Remove the switch and the old path once the new one is proved, and give that removal its own change.

## Checks

- The switch defaults to off and the deployment with it off is safe.
- Turning it off takes effect without a deployment, and was tested.
- Every change of the switch is recorded with a person and a time.
- Each switch has an owner and a date for its removal.

## Known-wrong example

A team adds fifteen switches over a year and removes none. The combinations are never tested together, and a customer hits a pair that nobody has run. The behaviour cannot be reproduced, because nobody records which values were in force. Recording the values with each request, and removing a switch when its change is proved, would have kept both problems away.

## What to record

- The switch name, owner, default and removal date.
- Every change with the person, time and value.
- The values in force when an unusual result is reported.

## Source

- `src/loop_engine/core/guardrail_intelligence.py`: this repository keeps the rules that narrow what a run may do as records rather than as branches in code, with a declared level of enforcement and a path for challenging a rule that blocks work wrongly.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 1700841.
