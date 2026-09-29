# Release 52

The [release record](../architecture-audit-2026-09-19/pilot-release-52.json)
names the deployed source, image, rollback image and test evidence.
Source `6940d515` passed CI run `36645686094`. The image and packaged-grant
steps in deployment run `36646310068` succeeded. The final billing-policy
confirmation returned a Machines API timeout, so the workflow remains failed.

Read-only inspection found the billing policy current and no earlier command
still running. The same idempotent command was then started once, detached,
under the service user. It exited zero: both policies current, nothing changed,
no paid access ended, no accounts created and no provider calls. Live checkout
and portal availability match its report. The output and exit status are kept
under `/data/incoming/release52-billing-policy*.json` on the existing Machine.
The deployment setting is off. This recovery does not erase the workflow failure.

The live browser check passed 218/218. Ten service origins passed 40/40 HTTP
checks covering availability, active catalogue, file count and the corrected
review explanation. The same checker rejected the old wording before deploy.
The local browser suite passed 948/948, including all 197 broken-page controls;
the offline self-test passed 3,688/3,688 with no provider calls.

Private result files and their digests are named in the release record. The
active catalogue remains at 27,811 packages and 88,373 distinct payload files;
its [publication evidence](../catalogue-publication-2026-09-29/programs-3910.json)
is separate from this image release. The 35 original creative seed packages
remain candidates, and the million-file target is not complete.

The operator command currently constructs the complete application and its
catalogue before checking billing. Decouple that initialization and give long
deployment operations durable, bounded result polling before the next scale
increase. The live result is verified; the deployment transport still needs
that repair.
