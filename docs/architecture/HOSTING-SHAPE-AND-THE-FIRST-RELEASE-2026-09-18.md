# Hosting shape for the first release, measured on 2026-09-18

Kind: architecture record. It states what was measured on this machine, what
follows from those measurements, and which questions remain open. It also
carries a dated snapshot of vendor prices read on 2026-09-18, marked as a
snapshot because prices change and because a price is not a measurement of
this system. Where a figure was computed from documented unit rates, it says
so.

## The assumption worth challenging first

Two hosting proposals were written for this system. Both began by asking which
platform should run harness instances. That question front loads the most
expensive, highest liability, least differentiated part of the system:
isolating and scheduling somebody else's agent workload.

The prior question is whether the first release hosts execution at all.

Three deployment shapes are available, and they are not variations of one
design. They differ in who runs the model, who runs untrusted code, and what
can honestly be metered.

| Shape | Loop Engine runs | The customer runs | Needs a model allowance | Runs untrusted code |
|---|---|---|---|---|
| Serve and provision | the intelligence layers, the capability catalogue, provisioning, authentication, telemetry intake | harness instances, their own models | no | no |
| Hosted deterministic work | the above, plus the detection and correction families on supplied data | a client that uploads and collects | no, for the confident band | no, the code is ours |
| Hosted execution | the above, plus customer harness instances | a client interface | yes | yes |

The third shape is the one that requires sandboxing, a scheduler, warm pools,
snapshots, and a cluster. The first two require a container, a database, and
an object store.

## What was measured

All figures are from this machine on 2026-09-18, with the commands recorded in
the session that produced this record.

The serving side is small.

| Measurement | Result |
|---|---|
| Catalogue of 20,000 capabilities, resident memory | 65 megabytes |
| Catalogue of 2,000 capabilities, resident memory | 26 megabytes |
| One manifest answered, either catalogue size | 6 microseconds |
| One body read with its digest checked | 9 microseconds |
| One manifest as bytes on the wire | 405 bytes |
| One capability body as bytes on the wire | 2.8 kilobytes |
| Every body of a 500 capability catalogue | 1.2 megabytes |
| A listing of 500 references with no filter | 240 kilobytes |

Two facts follow directly.

The serving workload is not processor bound. A service answering in
microseconds and resident in tens of megabytes sits below the smallest paid
tier every platform sells, so the compute tier is not the distinguishing cost
and the platform choice is not an architectural decision at this size.

Transfer is the distinguishing cost. An unfiltered listing is four hundred
times the size of the manifest a caller actually wanted. That is an interface
decision rather than a hosting one: a caller asks with a tag request and
receives the handful that match, and large bodies are delivered from object
storage rather than proxied through the application.

Two further measurements bear on the execution question.

A container from the published image starts and exits in a median of 230.4
milliseconds over ten runs, against 10.4 milliseconds for a process. A short
node pays about twenty two times more for its own container than for a process
in a pool, which is an argument about node duration, not about platforms.

The four intelligence layers currently hold 544 records: 441 context, 75 code,
28 runtime history, and none yet from user feedback. An analytical database
for historical queries is premature against 28 run records; the transactional
store is the whole requirement until the history is orders of magnitude
larger.

## The shape that is demonstrable today

The detection and correction families resolve without a model. Calling
`text_conformance` with three rows returns column profiles with pattern counts
and shares, typed rule proposals, and generated database statements, and makes
no model call at any point. The escalation band needs a model; the confident
band does not.

This matters because the single authorized model route has been answering with
a usage limit since 2026-09-18, and nothing in this repository has been live
qualified since 2026-09-14. A release whose first surface needs a model
allowance cannot be demonstrated today. A release whose first surfaces are
provisioning and deterministic correction can be.

## The decision

The first release hosts serving and deterministic work. It does not host
customer harness instances.

That choice rests on four things rather than on a preference.

1. The customer's model allowance pays for the customer's model calls, which
   removes the constraint that currently blocks every live demonstration here.
2. Nothing untrusted runs on our side, so the isolation machinery, and with it
   the reason to run a cluster, does not enter the first release.
3. The measured serving footprint fits the smallest tier anywhere, so the
   platform can be chosen on operational familiarity and data location rather
   than on architecture.
4. The differentiated part of this system is the intelligence, the contracts,
   the qualification evidence, and the reuse. Running a container is not.

Hosted execution stays a later configuration rather than a rewrite. Execution
already sits behind an explicit adapter registry where importing an adapter
registers nothing, and the provisioning modules depend only on record modules,
with no process, socket, or cloud dependency. The first customer who needs
hosted execution chooses the backend, and that choice is made against their
workload rather than guessed now.

## What this changes about metering

This is a consequence that neither hosting proposal drew, and it has to be
recorded because the published units would otherwise become dishonest.

The metering units named in the packaging guide are verified completions,
avoided model calls, optimize hours, and judgment depth. If the customer runs
execution, none of the first three is observable here. A completion we did not
run and did not verify cannot be sold as a verified completion.

The units that remain honest for the first release are the bodies a tenant
reads from the provisioning surface, which the service observes directly and
already meters, and completions of the deterministic families we run
ourselves, which we also observe directly. Verified completions return as a
unit when we run execution and verify it.

The never metered list is unchanged: outcome and verification records, reading
one's own history, exports, and refusals.

## What this changes about telemetry

Telemetry from a client run is reported by the client. It is evidence about
what a client says happened, and it is not evidence that the work was
independently verified. Client reported telemetry is typed as client reported,
kept in the same store, and never counted toward an independent verification
claim. A record that cannot say which of the two it is would quietly convert
one into the other.

## Prices read on 2026-09-18

A research pass read the vendor pages directly on 2026-09-18 and recorded the
figures below with their sources. Prices change, so these are a dated snapshot
for one decision rather than a fact about the world. Anything computed from
documented unit prices is marked as computed and shows its arithmetic.

The usual comparison is one processor and two gigabytes of memory running
continuously for a month. That comparison is the wrong size for this service,
which is the first thing the measurements above settle, but it is the
comparison every vendor publishes, so it is the one that makes the shapes
comparable.

| Shape | One processor, two gigabytes, one month | How it is known |
|---|---:|---|
| Fly Machines, shared processor, Ashburn | $10.70 | documented |
| DigitalOcean basic instance | $12.00 | documented |
| Hetzner Cloud shared processor, Ashburn or Hillsboro, two shared processors | $20.49 | documented through the vendor's own price interface |
| Render standard service | $25.00 plus the workspace plan | documented |
| Cloud Run worker pool | $36.04 | computed from documented per second rates |
| Kubernetes Engine Autopilot, the pod alone | $39.77 | computed |
| Kubernetes Engine Autopilot, pod plus the cluster fee | $112.77, or $38.37 after the monthly credit | computed |
| Cloud Run service, instance billing | $57.82 | computed |
| Cloud Run service, request billing, busy all month | $76.21 | computed |
| Cloud Run service, request billing, one idle minimum instance | $19.71 | computed |
| Render Workflows on the flexible tier, running continuously | $219.00 | computed |

Three readings follow.

Request billed compute is cheaper only when the service is genuinely idle. The
same shape costs $57.82 on Cloud Run with instance billing, $25.00 on Render,
and $20.49 on Hetzner Cloud in Virginia. Its advantage lives entirely in the
idle case, where one minimum instance costs $19.71 and a bursty request billed
service costs less again.

A cluster costs seventy three dollars a month before a single pod runs, since
the management fee is a flat rate per cluster per hour. The free credit covers
exactly one cluster per billing account. That fee is irrelevant once many pods
share a cluster and decisive when two or three do.

The measured footprint says none of this row is the right size. Twenty
thousand capabilities sit in sixty five megabytes and answer in microseconds,
so the smallest instances on these lists are the relevant ones: the smallest
Fly shape with 256 megabytes is documented at $1.94 a month, and the request
billed free allowance of 180,000 processor seconds and two million requests a
month would cover a great deal of early traffic before anything is owed.

## The cost that actually varies

Delivery is where the platforms differ by two orders of magnitude, and
delivery is this service's main job.

| Where a body is delivered from | Price out to the internet | How it is known |
|---|---|---|
| Hetzner Cloud, United States | at least one terabyte included, then $1.20 per terabyte | documented |
| DigitalOcean | two thousand gibibytes included on a twelve dollar instance, then $0.01 per gibibyte | documented |
| Fly Machines, Ashburn | $0.02 per gigabyte | documented |
| Render | five hundred gigabytes on the paid workspace, then $0.15 per gigabyte | documented |
| Cloud Storage | $0.12 per gibibyte for the first ten tebibytes | documented |

Computed on one terabyte delivered in a month, that is roughly $1.20 on
Hetzner, about $20 on Fly, about $79 on Render beyond its allowance, and about
$123 from Cloud Storage. The compute for this service is a rounding error
beside that spread, which is why the interface decision above matters more
than the platform decision: a caller that asks with a tag request and receives
a handful of manifests transfers kilobytes, and a caller that lists everything
transfers a quarter of a megabyte before it has fetched anything at all.

The database is the other large line. A small managed Postgres on the major
platform was computed at about $100 a month for two processors and seven and a
half gigabytes, and doubles with high availability. Managed Postgres from the
smaller platforms was quoted by the owner's own study at $52 to $55. For a
service whose working set is measured in tens of megabytes, that line is
chosen on durability and support rather than on capacity.

## What the spend controls actually do

This matters for a single operator more than the unit prices do.

Budget alerts on the major platform do not cap spending; the documentation
says so directly. A spend cap that does stop usage exists but is in preview
and covers named services including Cloud Run, while the cluster service, the
managed database, object storage, and the analytical database are not in that
list. One smaller platform documents no billing alerts at all and tells
customers to watch the dashboard. Another documents no cap on the pages that
were read.

A release with no hard ceiling on the most expensive services is a release
that needs its own admission and reservation limits, which this system already
has, rather than a reliance on the platform to stop.

## How to choose the host when the time comes

The choice is between request billed compute, an always running instance, a
managed server, and dedicated hardware. The deciding variable is duty cycle,
and duty cycle is measurable rather than arguable.

Request billed compute wins while the service is idle most of the time. An
always running instance wins when connections stay open, an index stays
resident, or background intake runs continuously. A managed server wins when a
provider's written support scope genuinely covers this stack and predictable
capacity suits the load. Dedicated hardware wins at sustained high
utilization, and brings a recovery design with it rather than a single
machine.

Two measurements decide it, and neither exists yet: the occupancy a real
protocol client produces, including whether it holds a stream open, and the
egress a representative month of package delivery produces. Both are cheap to
obtain from one instrumented deployment, and both change the answer more than
the published tier prices do.

A cluster enters when there is untrusted execution to isolate or a fleet large
enough that scheduling it by hand is the constraint. Neither is true of a
release that serves records and runs its own deterministic code.
