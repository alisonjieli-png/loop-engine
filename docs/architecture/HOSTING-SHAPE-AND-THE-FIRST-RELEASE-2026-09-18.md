# Hosting shape for the first release, measured on 2026-09-18

Kind: architecture record. It states what was measured on this machine, what
follows from those measurements, and which questions remain open. It also
carries a dated snapshot of vendor prices read on 2026-09-18, marked as a
snapshot because prices change and because a price is not a measurement of
this system. Where a figure was computed from documented unit rates, it says
so.

Note added on September 20, 2026. This record is dated research and its text
below is unchanged. It names DigitalOcean App Platform as the first choice of
host. That recommendation was not adopted. The owner prefers Fly.io for
compute and delegated the infrastructure choices of the private pilot, and
the pilot was deployed on Fly.io under that authority. The
[deployment authority record](../../artifacts/architecture-audit-2026-09-19/pilot-deployment-authority.json)
is the place to check this. Fly.io is what runs. This record also says that
the first release does not need a managed database. That matches the pilot
and the private beta, which keep their records in SQLite on one Fly volume. A
PostgreSQL adapter is planned work for the paid public launch. The current
facts are stated in
[current deployment](MVP-CLIENT-SERVER.md#current-deployment).

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

## Configuring it programmatically, read on 2026-09-19

A second research pass read the configuration and operation documentation for
five platforms. The question was narrow: which one stands up and maintains a
single containerized service with a managed Postgres database using the fewest
manual steps in a web console, and what can be driven from a file, an
interface, or an agent facing server. Nothing was deployed, so every finding
below is documented behavior rather than observed behavior.

| Platform | One file defines it | Full interface | Terraform | Agent facing server | Prebuilt image from a registry | One step rollback |
|---|---|---|---|---|---|---|
| DigitalOcean App Platform | services and databases together | yes | in the vendor's own organization | yes, covering applications and databases | a first class registry type, public and private | one call, restoring code, configuration, and the specification |
| Render | services and databases together | yes | vendor calls it official, registry calls it partner | yes, but it cannot deploy a prebuilt registry image | yes, with credentials added in the console or through the interface | one call |
| Cloud Run | one service per file, no database | yes | the only official tier provider | yes | a public registry image directly, a private one through a remote repository | one command |
| Fly | one application per file, no database and no secrets | yes | none, withdrawn deliberately | yes, every command marked experimental | yes, private external registry authentication not documented | no rollback command by design |
| Hetzner Cloud | no application definition | yes | yes | none published | not applicable | disk level rebuild only |

Four findings decide it for this system.

The first is specific to us and settles more than the general comparison does.
We already publish a digest pinned image, so the release is a prebuilt image
pulled from a registry rather than a build from source. Render's agent facing
server documents that it cannot deploy prebuilt registry images, which is
precisely the operation we would want it for. Cloud Run deploys a public
registry image directly but requires a remote repository for a private one.
DigitalOcean treats that registry as a first class type for both.

The second is that a rollback is not one thing. DigitalOcean restores the
code, the configuration, and the specification together. Cloud Run shifts
traffic back to a whole earlier revision. Fly documents that it has no
rollback command deliberately, and that redeploying an older image runs it
against today's configuration, environment variables, and secrets. For a
service meant to be operated without thinking, that difference matters more
than a price.

The third is that one file covering the service and its database is rarer than
it sounds. Render and DigitalOcean do it. Cloud Run's service definition holds
one service and cannot express the database or a scheduled job at all, so the
equivalent needs either an infrastructure tool or several coordinated calls.
Fly's file can express neither the database nor its secrets.

The fourth is that an agent facing server is not a single standard of support.
One ships in a vendor's own organization under a permissive license, one lives
in an organization whose profile disclaims support, one ships inside a command
line tool with every command marked experimental, and one platform publishes
none. Treating those four as the same capability would be a mistake.

On the evidence read, DigitalOcean App Platform needs the fewest manual
console steps for this exact goal, with Render close behind and better on
preview environments and on published database limits. One ambiguity sits
directly under that conclusion and is recorded rather than resolved: whether
declaring a production database in the application specification creates a
managed cluster or only attaches to one that already exists was not settled by
the pages read. If it only attaches, the gap between the two narrows.

## Questions the first pass left open, resolved on 2026-09-19

A page that returns not found is not an answer, and neither is a page that
does not mention the thing. A second pass resolved the open questions through
the vendors' own machine readable sources: published interface schemas, the
source of their command line tools, their documentation repositories, their
release notes, and posts written by their own staff. Each finding below names
which kind of source produced it.

Two of these change what we would choose.

**Fly cannot pull a private image from an outside registry.**
Three independent vendor sources agree: the published machine interface schema
carries no credential field on an image, the command line tool passes no
credentials when resolving an image reference, and the vendor's own guide
scopes private images to its own registry and external registries to public
ones. Staff posts say the same. Our image is public today, so this does not
block us now, but it removes a platform from consideration the moment a
release needs to be private, and that vendor's own registry is documented as
collecting unused images rather than keeping them.

**Public images from the registry we already publish to deploy directly on
Cloud Run, and that reached general availability on 2026-07-14**
according to its release notes. A private one there needs a remote repository
rather than a credential. Images are cached for up to an hour, which is a trap
for a moving tag and irrelevant to us because we deploy by digest.

Four more resolutions worth keeping.

The sixty second idle timeout that Fly was once documented as enforcing was
retracted by the same staff member in a dated edit in April 2024. There is now
no documented maximum request duration there, and the one timeout setting is
documented with neither a default nor a unit, so the effective value is
undocumented rather than absent. On Cloud Run the maximum is stated plainly:
five minutes by default, extendable to sixty.

Managed Postgres on Fly left technical preview on 2025-04-29,
established by the commit that removed the preview banner from the
documentation source rather than by any announcement, and no statement that it
is generally available was ever published. Its second version is explicitly in
beta and available in one region. For a database a service depends on, that is
a status worth knowing before choosing.

Zero downtime deployment there is documented and conditional, and the
conditions are specific enough to get wrong: the health checks must be the
service level ones rather than the top level block, which the vendor states
plainly does not affect routing; at least two machines must run; and the
proxy stops sending new requests to a draining machine but does not wait for
the ones in flight, so the application itself must finish its work inside the
kill timeout.

Automated backup retention on Cloud SQL for Postgres defaults
to seven backups on the standard edition and fifteen on the higher one, with
transaction logs kept seven and fourteen days. That figure is not on the
backup page; it is in the command line reference, which is generated from the
tool's own argument definitions.

Two vendor documentation defects were found while resolving these, and both
matter if someone reads the page rather than the schema. Cloud Run's quota
page states a maximum of one hundred instances per project and region, which
contradicts its own footnote and its own worked example; the real per revision
default is one hundred and the regional ceiling is derived from the processor
and memory quota. Fly's page for its agent facing server lists nine command
groups, omits a tenth, and names a tool that does not exist; the source has
sixty tools at the version read.

## The database question, resolved on 2026-09-19, and what it changes

The ambiguity recorded above is resolved, and the answer corrects a claim this
document made. A DigitalOcean application specification that declares a
database creates one in exactly one case and attaches in every other. The
schema sentence is identical across five vendor artifacts, including the
published interface schema, the vendor's own generated client, and the
infrastructure tool's source: the cluster name is required for production
databases, and for development databases, if it is not set, a new cluster is
provisioned.

The structural proof is stronger than the sentence. The database object has
exactly seven fields and none of them is size, region, or node count. The
specification has no vocabulary for saying how large a cluster should be or
where it should live, so it cannot describe one into existence. The only thing
it can create is the fixed development database, and that one is PostgreSQL
only, one size, region locked to the application, without permission to create
further databases inside it, at seven dollars each month. The vendor's own
migration guide instructs the reader not to use it for anything that must
restore a real dump, and to create the managed cluster first.

So the earlier claim that one file covers the service and its database is true
for DigitalOcean only at the development tier. At the production tier the work
is three objects rather than one: create the cluster, attach it by name, and
add the application as a trusted source. Render needs two. On step count alone
for a production database, Render is now ahead, which reverses what this
document said yesterday.

**That comparison does not decide our first release, because our first release
does not need a managed database at all.** The storage measurement already
made that choice: the default is an embedded analytical database file over
packaged records, with a server database behind the same contract only when a
rollout needs one. The intelligence a client pulls is a catalogue and a set of
bodies, both of which ship inside the image we already publish by digest. A
release that serves them needs a container, a hostname, and a way to put a
newer image behind the same hostname. Every one of the five platforms does
that. Choosing between them on how they provision Postgres is answering a
question the first release does not ask.

What the first release does ask is narrower, and two findings answer it.

The first is that DigitalOcean's documentation names the Model Context
Protocol directly, which no other platform read here does. Its edge settings
page states that disabling the content delivery cache is required to use
server sent events or the Model Context Protocol over GET requests, and that
POST requests work with the cache enabled. That is a precise and useful fact
rather than a marketing mention. Because the protocol's GET channel is
optional, a first release that answers on POST alone runs on the default
hostname with nothing disabled. A later release that wants the server to push
notifications turns the cache off, which requires a custom domain and does not
work on the starter hostname. That is a known step with a known cost, recorded
now rather than discovered during an outage.

The second is that Render documents inbound WebSocket connections with no
maximum duration and no limit on their number, and documents server sent
events nowhere at all. DigitalOcean is the mirror image: server sent events
documented with a named prerequisite, WebSockets absent from every page, the
published schema, and the generated client, where the only occurrence of the
word describes the vendor's own console. Neither platform publishes a maximum
duration for an ordinary request, and both put the same content delivery
network in front of the application, so neither absence should be read as
permission to hold a request open for minutes.

The decision therefore stands where it was, for a corrected reason.
DigitalOcean App Platform remains the first choice for this release, not
because one file provisions a production database, which it does not, but
because the release is a prebuilt image behind a hostname, that platform
treats our registry as a first class source for both public and private
images, its rollback restores code, configuration, and specification together,
and it is the only one of the five whose documentation has considered the
protocol we intend to serve. Render remains the alternative, ahead on managed
Postgres step count and on documented streaming over WebSockets, behind on
deploying a prebuilt registry image through its agent facing server and on
publishing anything about encryption at rest for environment variables and
secret files, which it calls plaintext.

Three further facts are recorded because they bear on operation rather than
choice. DigitalOcean's automatic deployment keeps the previous container
serving until the new one passes its readiness check, then drains and
terminates the old one, and rolls back to the last healthy deployment when the
check fails; high availability still needs two containers. Its managed
PostgreSQL keeps one backup a day for seven days with point in time recovery
across the same seven days, and restores by creating a new cluster rather than
rewinding in place; backend connections run from twenty two on the smallest
plan to nine hundred and ninety seven on the largest. And a documentation
defect worth knowing: the published interface schema carries example values
for health check fields but no defaults, and the examples differ from the real
defaults, so reading an example as a default gives the wrong number in every
field.

Per pull request environments exist on DigitalOcean only as a recipe using the
vendor's own automation action, which creates a separate fully billed
application for each request and deletes it on close. That is worth having and
is not a platform feature.

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
