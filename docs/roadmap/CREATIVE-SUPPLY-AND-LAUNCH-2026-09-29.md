# Creative supply, reusable assets and a two-channel launch

Kind: dated implementation plan and research record, September 29, 2026.
The [roadmap](roadmap.yaml) remains the task authority. This record extends
S-6.214 and S-6.215; it does not claim new components are approved or served.

## Measured starting point

The active catalogue holds 27,811 packages and 88,373 distinct payload files.
The 119,820 file placements include repeated bytes and are not the million-file
metric. The gap to one million is 911,627 distinct approved, served files.
The publication evidence is
[the September 29 record](../../artifacts/catalogue-publication-2026-09-29/programs-3910.json).
The website change now being checked makes distinct files the main count and
packages the secondary count. It does not create additional supply.

Scale six lines together: software and data tools; creative computation;
native production projects; assets and references; rights-cleared owner
projects; and source-linked research. Count neither rejected candidates nor
copies, arbitrary preset permutations, padding or metadata churn as growth.
Keep one implementation when parameters suffice. Report generator families,
distinct asset variants, package placements and distinct file bytes separately.

The serving path still needs measured memory and p95 search latency at the
target population. Large textures, videos and meshes need a qualified delivery
path before they exceed the current per-file limit. More files alone do not
prove retrieval usefulness or customer value.

## Asset families and their controls

These are common production families, not a measured popularity ranking.
Kenney's [catalogue](https://kenney.nl/assets) spans 2D, 3D, UI, audio, pixel
and texture collections. [Infinigen](https://github.com/princeton-vl/infinigen)
provides procedural nature, interiors and articulated objects. These are
existing systems to inspect and adapt behind qualified engine edges, not a
reason to create a separate runtime.

| Family | Useful reusable material | Important controls and checks |
| --- | --- | --- |
| Characters and bodies | Original proportion references, proxy bodies, skeletons, skinning tests | Units, joint order, rest pose, proportions, weight sums, deformation, permitted use |
| Clothing and equipment | Garment patterns, attachment sockets, fit envelopes, material presets | Body compatibility, clearance, thickness, clipping, cloth assumptions |
| Animals and creatures | Quadruped, wing, fin, tail and segmented-body generators | Topology, joint axes, limits, symmetry, contact, gait phase; synthetic rather than measured anatomy |
| Vehicles | Modular chassis, wheels, suspension, cockpit and camera setups | Wheelbase, track width, clearance, steering, collision proxy, mass assumptions |
| Trees and foliage | Branch generators, leaves, grass clusters, scatter rules | Crown shape, density, season, wind weights, instancing, level-of-detail limits |
| Terrain and rocks | Height fields, cliffs, boulders, soil layers | Coordinate scale, slope, erosion assumptions, seams, collision and navigation |
| Water | Surface generators, shoreline masks, wave and foam fields | Depth, amplitude, wavelength, time, normals, transparency and renderer support |
| Sun, sky and weather | Lighting rigs, sky parameters, cloud fields and precipitation | Exposure, color space, angles, time, physically based versus artistic mode |
| Buildings and streets | Walls, openings, roofs, doors, stairs, roads and signs | Grid, dimensions, sockets, roof pitch, clearance, accessibility assumptions |
| Props and interiors | Furniture, containers, appliances, cables and fixtures | Pivots, articulation, contact, material scale, collision, opening clearance |
| Effects and styles | ASCII, Braille, dithering, pixelation, outlines, particles and transitions | Palette, pixel grid, temporal stability, seed, alpha, audio synchronization |
| Game and design interfaces | Icons, HUDs, controls, charts, typography and sound cues | Readability, localization, safe areas, contrast, input state and licensing |

Each asset needs a small discovery card, versioned parameter schema, original
or licensed source, reference previews, provenance, dependency lock and checks.
Geometry records should state units, handedness, up/forward axes, origin,
bounds, material slots, sockets, collision representation, UV assumptions and
detail budgets. A skeleton additionally needs stable joint names, parent
indices, rest transforms and explicit motion conventions. A pretty preview
does not establish animation, simulation or engine compatibility.

Keep generator, recipe, baked asset and run-specific evidence distinct. A new
seed is a variant of the same generator, not a new independent capability.
Retain the editable source when baking to a portable representation. Infinigen's
[export documentation](https://github.com/princeton-vl/infinigen/blob/main/docs/source/ExportingToExternalFileFormats.md)
describes lossy baking, incomplete material transfer and unqualified animation
export. Those limitations must survive an adapter, not disappear from its label.

Poly Haven's [licensing page](https://polyhaven.com/license) distinguishes CC0
asset files from protected website renders and copy; its API has separate
terms. Asset reuse permission is not permission to scrape every page or copy
its preview. Record rights per file and generate our own previews where needed.

OpenPose's [output documentation](https://github.com/CMU-Perceptual-Computing-Lab/openpose/blob/master/doc/02_output.md)
describes keypoint output, not a complete anatomical or rigging standard.
Original non-human references should declare their own topology and synthetic
status. Do not relabel illustrative joint limits as biological measurements or
assume the OpenPose software and weights have unrestricted commercial rights.

## Compose before generating source

The model selects a compact contract, resolves compatible dependencies,
supplies parameters, executes a qualified engine and checks the result.
Source is loaded for inspection or repair when necessary. Existing code-asset,
solution-graph and engine-slot contracts own this path. Every executable graph
vertex remains a Loop; individual vertices, pixels and render frames do not
become model calls.

The same discipline applies to ordinary SaaS and data work: schema migrations,
authorization checks, pagination, idempotent writes, data normalization,
file conversion and fixture generation can be reusable executable components.
Measure accepted results, revision success, integration failures, latency and
total cost against the no-extra-material baseline. Do not infer token savings
from having a smaller contract card alone.

## Discovery and private project review

The [community watch](../../tools/knowledge_radar/README.md#bounded-community-watch)
now has bounded feed intake, managed records, a durable queue and an optional
native web-research worker. Leads stay unverified. Posting, rights clearance,
reproduction, component admission and catalogue publication remain separate.
No API key or paid scraping service is required for the currently tested path.
Blocked access stops that source; the worker does not switch to evasion.

The owner authorized review of the Expansion drive and MAIN_PROJECTS. The
current inventory reads metadata and bounded project headers, not every line
of every project or chat. Raw histories remain private. Repository remotes
have credentials removed; malformed remotes make provenance unresolved. No
imported code executes automatically. Mine distinct useful functions, assets
and known failures only after ownership and file-level rights are established.

## Address-to-scene lane

The requested address-to-video experience is a composition of geocoding,
source selection, street/building retrieval, elevation, coordinate conversion,
geometry construction, scene assembly, camera planning, rendering and checks.
No particular private address is stored in this public record or rendered by
this research.

Candidate sources include [OSMnx](https://osmnx.readthedocs.io/en/stable/getting-started.html),
[Overture buildings](https://docs.overturemaps.org/guides/buildings/) and
[USGS elevation data](https://www.usgs.gov/the-national-map-data-delivery/gis-data-download).
Pin revisions, access limits, attribution, coordinate reference systems,
local origin and vertical datum. Footprints do not establish facade appearance,
roof form, private interiors or accurate height. Missing geometry may be
inferred for visualization only when clearly labeled. A recreation is not a
survey, a live view or a claim of exact physical accuracy.

## Showcases that earn the product claim

Published screenshots and creator reports are inspiration, not reproduced
benchmarks. OpenAI's [Time to Fly](https://developers.openai.com/showcase/time-to-fly),
[Brick Platformer](https://developers.openai.com/showcase/brick-platformer) and
[Clockwork Observatory](https://developers.openai.com/showcase/impossible-kinetic-architecture)
suggest reusable mechanics, asset consistency, spatial composition and testing.
Two published images were inspected in this session; no external game was
played because the computer-use browser was unavailable.

Build three own examples first: a data/software task, an editable launch
animation and a procedural scene. Show the brief, actual output, exact package
versions, editable source, requested revision, failure record and supported
environment. Never use someone else's selected image as proof of Baltor's
output. A simple original visual proof can ship before an ambitious game.

## Standalone service and OpenAI plugin

Use one catalogue, account, entitlement and version identity. The website
handles independent acquisition and subscriptions. A plugin is another way
to use that service, initially for scoped search, previews, contract inspection
and supported exports. It cannot silently install software on a user's machine.

The current [OpenAI plugin guidelines](https://developers.openai.com/plugins/plugin-guidelines)
permit existing paid-account access but prohibit digital subscription sales,
upgrade promotions and ChatGPT-specific surcharges inside plugins. Therefore
do not promise a paid plugin purchase or put checkout buttons in it. The old
app-guidelines URL returned 404; the current plugin-guidelines page was read.
Check the rules again before submission. Listing approval is not established.

Expose reviewed operations individually. Do not hide arbitrary execution behind
a generic dispatcher or dynamic schema tool. Minimize task context; a plugin
does not inherit full chat history. Keep identity, Baltor entitlement, model
allowance and execution permissions separate. Address-based work requires its
own supported, consented resource path; do not casually add precise-address
fields to the plugin schema, which the current guidelines restrict.

## Launch and advertising sequence

The owner reports a newsletter of more than 20,000 design-interested readers.
This is an existing distribution channel, not verified Baltor revenue,
activation, consent scope or conversion. The paid-ChatGPT share is unknown.

1. Finish three reproducible showcases, the file/package count, onboarding,
   retrieval, complete download and revision checks. Publish known limits.
2. Prepare a designer landing page with one clear task, an editable example and
   the existing Baltor plans. Keep the technical catalogue available separately.
3. Invite a small newsletter cohort using the owner's authorized mailing tools
   and valid subscriber permissions. Measure first accepted project and repeat
   use before expanding to the whole audience. No email has been sent here.
4. Offer the same useful workflows through the plugin after native integration
   tests and directory approval. Do not market an unapproved listing as live.
5. Prepare advertising around observed outputs: source-to-animation,
   parameter-to-scene and reliable revision. Test distinct audiences and messages
   with a holdout where practical. Engineering spends nothing on ads; the owner
   controls spend. Do not launch retargeting or new tracking under the existing
   privacy notice without the required decision.

Judge channels by activated, retained customers and contribution after compute,
storage, delivery, support and payment costs. Newsletter opens and raw installs
are diagnostic signals, not the main success criterion. Keep acquisition cost
and payback as measured cohort values, not invented market averages.

## Founder and investor narrative

Prepare a deck around: the repeated-work problem; a live creative revision;
contract-first reuse; the current product and exact serving baseline; the
design audience; subscription economics; competition; measured task evidence;
distribution; milestones; team; and a funding use tied to those milestones.
Label the million-file goal as a target. Label the newsletter as owner-reported.
Do not invent revenue, partnerships, customer logos, benchmark wins or a funding
ask. Existing public deck claims retain their source-evidence requirements.

## Order of implementation

Finish and deploy the count and billing-bootstrap repairs; activate the reviewed
bounded discovery schedule; complete private inventory and selective extraction;
qualify original style and procedural-asset generators; publish a small tested
creative batch and its showcase; then expand the supply lines against measured
search, delivery, quality and demand. Newsletter and plugin distribution should
follow a useful working experience, not a file-count announcement alone.
