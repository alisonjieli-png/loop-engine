# Keep partial work when a long job is interrupted

Save enough during a long job that an interruption costs minutes, not the whole run.

## When to use it

Use it for any job that runs longer than a few minutes: a build, a data job, an overnight run, a large import, or an agent working through many steps.

## Steps

1. Decide what "progress" means for this job: the last key processed, the files produced so far, the best result so far.
2. Write that progress to durable storage at points you choose, not only at the end.
3. Make each write complete or absent, never half written. Write to a temporary name and move it into place.
4. Record enough to continue: the position, the settings in use and the identity of the input, so a resume cannot continue against different data.
5. Catch the signals that ask a process to stop, write one last progress record, and then exit.
6. On start, look for an existing progress record, check that it matches the current input, and continue from it or say clearly why it cannot.
7. Keep the partial output usable and clearly labelled as partial, so a reader never mistakes it for the finished result.
8. Test the interruption: stop the job in the middle, restart it, and compare the final result with an uninterrupted run.

## Checks

- A record is written more often than the job is expected to be interrupted.
- Each record is complete or absent, never half written.
- A resume refuses to continue against different input.
- The interrupted and uninterrupted runs give the same final result in a test.

## Known-wrong example

An overnight job processes files for nine hours and writes its results at the end. At hour eight the machine restarts for an update. The morning report is empty, the logs show only that it started, and nobody can say which files were done. Writing progress every few minutes would have left eight hours of usable work and a clear place to continue.

## What to record

- The definition of progress and how often it is saved.
- The identity of the input the progress belongs to.
- The result of the interruption test.

## Source

- `src/loop_engine/core/run_checkpoint.py`: this repository writes a checkpoint of the best work so far when a run is signalled to stop, so an interrupted overnight run leaves something usable behind.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 0cf19eb.
