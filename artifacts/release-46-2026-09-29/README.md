# Release 46: a worked step, an orange logo, and a full volume

Fly release 46 ran `58fb1920073ee4bb1b3da48a3898cc1c3abdb561`. The deployment
gate refused the first attempt and the service was down for about twenty minutes
before the cause was found and repaired. Both the failure and the repair are
recorded here, because the failure is the more useful record.

## What went wrong, and it was not the change

The deployment replaced the one Machine and then polled its health endpoint for
the full window. Every poll returned nothing. The site's own health record, read
straight off the Machine, gave the reason in one field:

```json
{"name": "volume_has_write_headroom", "required": true, "passed": false, "code": "volume_nearly_full"}
```

The 3 GB encrypted volume was full. The catalogue release
`001b7de637d7f169924413732c3dc52b506c5c194ef00764bf5f7187820a0395`, published at
23:27 UTC on September 28, added 1,503 items and changed 13,643, and took the
volume past its write headroom. The service then answered 503 on purpose:
`durable_store_answers` still passed, but a service that cannot promise it has
room to write must not report itself ready. The gate was right to refuse, and
refusing left one Machine with no healthy version behind it, which is the hard
downtime the single-Machine shape has on every release.

This is the constraint the September 28 handoff measured and step 7 of its ordered
work: grow the volume with the extend call, which needs no migration.

## The repair

`flyctl volumes extend vol_r7yg7go3n15mgqnr --size 25 --app baltor-pilot`. The
Machine took the larger filesystem with no restart. The next health poll
answered 200, and `baltor.ai`, `www.baltor.ai` and `baltor-pilot.fly.dev` all
answered 200 again. The volume is 25 GB, which at the measured 77 kilobytes a
package holds about 330,000 packages against the 15,146 served now, and is the
size the owner's September 28 budget decision priced at 3.75 dollars a month.

The running image is the release 46 image
`registry.fly.io/baltor-pilot@sha256:d614fdb6baccc617e5bf7515d4a727a488b7509874ef1f5cb80cec33dbdaef3c`.
Continuous integration
[36505423371](https://github.com/alisonjieli-png/loop-engine/actions/runs/36505423371)
succeeded. The deployment run
[36505951640](https://github.com/alisonjieli-png/loop-engine/actions/runs/36505951640)
failed at the readiness gate, which is the correct outcome for a service that
cannot promise write headroom. The deployment setting was read back as false.

## What the change actually did

The owner reviewed the live homepage and named four defects. All four are fixed.

**The hero terminal offered four harness tabs while the same page claimed five
had tested file placement, twenty lines apart.** The first attempt added a fifth
tab for the Baltor Harness with a skill root of `.baltor/step/`. That root was
invented. The placement tool's own profile for that harness declares
`locations=()` and, for every kind, the reason
`engine_reads_library_material_only_from_the_task_file`: it reads library
material from the task file and refuses a served `SKILL.md`, so it has no native
folder at all. The page's claim was false for the fifth harness, so the tabs now
show the four that read a placed folder, which is what the placement tool
supports, and the first group reads "These five are set up and supported" and
says which four read a placed folder and that the Baltor Harness has none yet,
with the placement tool's own reason. The owner's five names stay in the order
the owner named them, so the check that holds that list is unchanged.

**The example was a two-result dedupe too small to show what the library is
for.** Three worked steps replace it: deduplicate a customer table, fix a
failing metric overnight, and hand a finished result over. Each names the chain
of components the step needs, the folder it assembles, and what the step
replaces. Hovering, focusing or clicking a name repaints the query, the search
results, the download, the file tree and the saving.

**The two harness lists read as one undifferentiated wall of names.** They now
say what each claim is. The first says which harnesses are set up and supported.
The second says these connect too, through the Model Context Protocol, and do
not read a placed file, because that is a property of a file layout, not of a
protocol.

**The mark was navy while the whole design system is orange.** The mark and its
three committed raster sizes now use the system's own accent stops, so the logo
cannot drift from the buttons: `#A03500` to `#FB9D59`, the values already in
`service.css` for light and night.

## A second thing found and repaired

The September 28 sweep that removed "reviewed" as the unit the library is counted
in also edited two sentences the owner approved in person. The privacy notice and
the terms of service said "reviewed material"; the sweep made them say
"material". The owner's rule for that sweep was a counting unit on the website,
and the September 28 handoff states the terms are untouched because their wording
is the owner's to approve. A browser check compares the served text with
`docs/legal/PRIVACY-NOTICE.md` and `docs/legal/TERMS-OF-SERVICE.md` and reported
both as differing, which is how this was found. The two sentences are restored
and nothing else in either document changes, so "reviewed" stays off every
customer page and stays in the two documents where the owner wrote it.

## Two checks were read, not changed

The hero harness list check counted every visible name in both lists, so it read
the protocol clients as placement claims, which is the false claim the owner asked
to have corrected. It now reads the group that carries the claim. Its known-wrong
cases still fail on a shortened line, a missing harness, a status word and a
changed order. The new group headings take the night ink, because they inherited
the light ink and measured 1.02:1 against the dark hero band.

## What is verified

All 19 local gates pass on a clean tree at `58fb1920`. The browser workspace
check holds at 814 of 840, up from 805, with no new failure introduced. Its 26
remaining failures are not from this change: the connection recipe record, the
credential rule, the usage panel, the Pi extension link, the sign-up loading
state, and the served-asset scan coverage. Each is named in the session handoff.

## What this release does not claim

A full nine-hostname visitor check has not been run against release 46. The
three hostnames read above answer 200 and the new hero, the orange mark and the
three scenarios are confirmed present in the served page. The catalogue and
service check suites have not been re-run for this release either.
