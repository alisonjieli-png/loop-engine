# State the permissions and limits of an assignment

Say exactly what the worker may touch, run, reach and spend, so that nothing has to be guessed from the wording of the task.

## When to use it

Use it for every assignment given to an automated agent or an unattended process, and for any work that runs with credentials you would not hand out casually.

## Steps

1. Name one folder the work may write in, and say that everything else is read only.
2. List the commands or kinds of command that may be run, and say that anything else needs a new decision.
3. State the network rule: no access, a named list of destinations, or open access with a reason.
4. State which credentials are available, in which scope, and which are not available at all.
5. Give a limit on the resources: time, memory, disk, number of calls and money, each as a number.
6. Bind every approval to the exact action it was given for. A changed action needs a new approval.
7. Say clearly which actions have effects outside the machine, such as sending a message or making a payment, and require a separate approval for each one.
8. Give the process an environment that contains only what was declared, rather than the whole environment of the machine it runs on.

## Checks

- An attempt to write outside the named folder is refused and visible.
- A command that was not listed does not run.
- Each outside effect has its own approval bound to the exact action.
- The resource limits are numbers, and reaching one stops the work.

## Known-wrong example

An agent is asked to clean up old files and inherits the full environment of the build machine, including a deployment credential. A confused path sends it to the wrong folder and it deletes part of a published artifact store. Nothing refused it, because nothing had been declared. One named folder and a cleared environment would have turned it into a refusal.

## What to record

- The declared folder, commands, network rule and credentials.
- The resource limits and which ones were reached.
- Each approval, the exact action it covered and who gave it.

## Source

- `src/loop_engine/core/harness_confinement.py`: a confined process here sees a cleared environment holding exactly the variables that were declared, each naming a place inside the sandbox rather than a setting of the host.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 40fce69.
