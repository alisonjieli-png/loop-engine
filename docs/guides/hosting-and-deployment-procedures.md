# Hosting and deployment procedures

Kind: operating guide. The owner requested preparation for all major hosting
families and an extensible path for additional providers. These procedures are
documented preparation, not claims that every provider profile has been
deployed and qualified.

## Current host

The private pilot runs on Fly.io. The owner selected Fly.io for the pilot. The
[current deployment](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
section records the Machine, the hostnames, the storage and the release. Read
that section for the facts. This guide does not repeat them.

Only the [Fly.io Machines](#flyio-machines) profile has been deployed. Every
other profile in this guide is documented preparation. The owner requested
preparation for all major hosting families, so the procedures for other
providers remain. No provider is excluded for a later release.

An earlier version of this guide said that no preferred vendor was selected.
The [hosting shape research](../architecture/HOSTING-SHAPE-AND-THE-FIRST-RELEASE-2026-09-18.md)
of September 18 and 19, 2026 recommended DigitalOcean App Platform first. That
recommendation was not adopted. Both statements were corrected or annotated on
September 20, 2026. The research remains a dated record of what was read.

## First hosted workload

The first hosted workload is the website, subscriber dashboard, payment event
handling, and intelligence service. Customers run their harnesses. Optional
hosted execution has separate placement, sandbox, resource, and spending
requirements. Choosing Google Cloud Run as a web-service host would not mean
hosting customer harness execution there.

## Common deployment contract

For the proposed managed-service combination, read the
[Supabase and Vercel profile](supabase-and-vercel-launch-profile.md). It
evaluates a shared authentication and database service, a separately hosted
website, and two portable Python serving placements. It is not an account
selection or permission to create resources.

Every target consumes the same reviewed release inputs: exact source revision,
image digest and processor architecture, application command and port,
configuration version, schema version, secret references, hostname, identity
settings, payment mode, durable-store location, artifact-store location,
resource limits, scale bounds, allowed network paths, and spending authority.
These are proposed deployment requirements at existing service, workspace,
and storage boundaries, not a second runtime configuration authority.

Separate development, staging, and production accounts or namespaces as the
chosen provider permits. Keep their credentials, payment events, record
namespaces, and test data separate. Deploy the same built image between
environments; do not rebuild it silently during promotion.

The repository contains two images. The worker image from `Dockerfile` keeps
its default `doctor` command. The service image from `Dockerfile.service`
starts the product service with `loop-engine service serve`. The repository
also contains the Fly profile `fly.toml` and offline Kubernetes examples.
Definitions for the other providers, and durable deployment wiring beyond the
single SQLite volume, still need implementation under step S-6.13. Do not
deploy the worker image's `doctor` default and call it the product. The
[two service commands](../architecture/MVP-CLIENT-SERVER.md#two-service-commands)
table says which command is the product service.

## Shared routine

1. Preflight the exact account, region, authority, quota, image, architecture,
   command, protocol version, store, secret references, and DNS plan. An
   unsupported platform capability is an explicit refusal.
2. Render a provider definition from the approved inputs and inspect the
   resulting change plan. Validate it locally before an authorized apply.
3. Back up or snapshot mutable state and record the current release. Apply
   only compatible migrations with a tested restore or forward-repair path.
4. Deploy the image and complete readiness checks against the configured
   dependencies. Liveness should not disclose tenant information or require
   a customer credential. Application data endpoints remain authenticated.
5. Exercise sign-in, subscription state, protocol connection, scoped search,
   template access, digest-bound body fetch, usage persistence, and revocation
   at the real hostname. Record failures with the same visibility as successes.
6. Upgrade using the next exact image and configuration. Rehearse restoration
   of the previous image, configuration, secret references, and compatible data
   state. An old image alone is not a complete rollback.
7. Retire only explicitly identified resources after traffic and writes are
   reconciled. Preserve required records and backups. Unknown work does not
   become cancelled merely because its endpoint disappeared.

Every provider procedure below uses this routine. A frontend can be hosted
separately while the service follows any qualified container profile.

## Local containers and single server

Use a versioned Compose application with a release image, secret references,
explicit volumes or an external database, backup destination, and a reverse
proxy when the service needs a public hostname. Local development binds to
localhost. Validate with `docker compose config`, then use an authorized
`docker compose up -d` against the reviewed files. Upgrade the image reference
and recreate the service; restore the previous configuration and image for
rollback. Test restart and restore separately from container recreation.
[Docker production guidance](https://docs.docker.com/compose/how-tos/production/).

## Vercel

Prepare the website and the optional Python serving application as independent
deployment units with environment-bound service URLs. Keep durable records,
artifacts, identity, and entitlements outside process memory. Run local builds
and inspect the complete Python dependency bundle, request limits, streaming,
and database pooling before selecting the function profile. Use the common
acceptance routine on an authorized preview and production deployment. Roll
back code and configuration independently of database migrations. The Hobby
plan is non-commercial; do not assume it covers a paid launch.
[Python applications](https://vercel.com/docs/functions/runtimes/python),
[plans](https://vercel.com/pricing).

## Supabase

Treat Supabase as a candidate authentication, Postgres, and private object
storage provider. Prepare current schema migrations, tenant policies,
authorization configuration, private buckets, secret references, and separate
database and object backup procedures. Qualify existing store and identity
adapters against an explicitly authorized project. Test revoked access and
restoration of both metadata and bodies; a database backup does not restore
the stored objects. Follow the
[Supabase and Vercel profile](supabase-and-vercel-launch-profile.md) for sources,
cost limits, and required checks. This is not a deployment of the full Python
engine into an Edge Function.

## Fly.io Machines

This is the deployed profile of the private pilot. The
[launch setup runbook](launch-setup-runbook.md#prepared-fly-access-on-the-development-workstation)
holds the prepared access and the exact settings.

Prepare `fly.toml` with the exact image, application command, port, health
checks, resources, scale bounds, and storage references. Deploy an approved
configuration using `fly deploy --image` with the release digest. Observe the
Machines and test the real service. Roll back by deploying the saved image
with the saved configuration and reconciling secrets and data explicitly.
Choose volumes or an external store according to the required writer and
availability model. Qualify the selected deployment strategy and connection
draining behavior. [Fly deployment procedure](https://fly.io/docs/launch/deploy/).

## Render

Prepare a Blueprint or API-managed service definition for the prebuilt image,
port, health check, environment, secrets, scaling, and database or disk
bindings. Validate the definition, create or update the approved service,
and observe the deployment through the documented interface. Roll back the
service release and separately verify database migration compatibility.
Test the actual streaming and client connection behavior rather than assuming
every connection survives a deployment.
[Image deployment](https://render.com/docs/deploying-an-image),
[Blueprints](https://render.com/docs/infrastructure-as-code).

## DigitalOcean App Platform

Prepare an application specification naming the image digest, component
command, port, health checks, environment, secrets, resources, and required
database attachment. Use the documented application API or `doctl` to apply
the reviewed specification. Test readiness, client requests, and rollback
against the saved application configuration. A production database declaration
requires an existing managed cluster; it does not create one merely by naming
it. Create that resource only under separate recorded authority.
[Application specification](https://docs.digitalocean.com/products/app-platform/reference/app-spec/),
[database API fields](https://docs.digitalocean.com/products/app-platform/reference/api/),
[image deployment](https://docs.digitalocean.com/products/app-platform/how-to/deploy-from-container-images/).

## Google Cloud Run

Prepare a service definition or deployment command with the exact image,
region, service identity, ingress policy, secret references, resources,
concurrency, request timeout, and instance bounds. Use `gcloud run deploy`
or the service API after preflight. Keep durable state in the selected
external store. Verify the image registry route supported by the target
account, then test the client protocol and reconnect behavior. Roll back to
the previous revision with compatible configuration and data. Record scale
and egress observations before comparing costs.
[Cloud Run image deployment](https://docs.cloud.google.com/run/docs/deploying).

## Amazon Elastic Container Service and Fargate

Prepare a task definition with the immutable image, command, resources,
execution and task roles, logs, secrets, and network settings. Bind it to an
approved service, load balancer, durable store, and health policy. Register
the new task revision and update the service to that exact revision; wait
for stability and run the common acceptance routine. Roll back to the prior
task revision and reconcile the service configuration and schema separately.
Managed Kubernetes and virtual-machine alternatives use the corresponding
procedures below.
[Service updates](https://docs.aws.amazon.com/cli/latest/reference/ecs/update-service.html).

## AWS App Runner

Prepare the service's source image configuration, access role, command,
port, resource allocation, network access, secrets, and health checks. Use the
service API to create or update the approved service and start the deployment
through its documented workflow. Observe the operation and perform the
common checks. Restore the previous source/configuration on rollback and
verify external state separately. Confirm that the selected image source
and application requirements fit this service before accepting the profile.
[App Runner deployment](https://docs.aws.amazon.com/apprunner/latest/dg/manage-deploy.html).

## Azure Container Apps

Prepare the container-app environment, application definition, image,
registry access, ingress, port, secrets, resources, scale bounds, and external
state bindings. Use the Azure command line or deployment API to create a
revision from the approved definition. Test its hostname and route traffic
only after acceptance. Restore a previously qualified revision and its
compatible state bindings for rollback. Azure Kubernetes Service and virtual
machines use the relevant procedures below.
[Container Apps setup](https://learn.microsoft.com/en-us/azure/container-apps/get-started).

## Kubernetes on any qualified distribution

Extend the existing `examples/28_containerized_worker/k8s` definitions with
environment overlays, an exact image, service and ingress, workload identity,
secret references, storage, resource limits, health checks, and network
policy. Use `kubectl kustomize` or the corresponding render command first;
use server-side validation against the authorized cluster before applying.
Observe rollout and run the common acceptance suite. Reapply the saved
release overlay for rollback and independently handle schema compatibility.

The same application contract can target Google Kubernetes Engine, Amazon
Elastic Kubernetes Service, Azure Kubernetes Service, DigitalOcean Kubernetes,
or a qualified self-managed distribution. Cluster identity, ingress,
identity bindings, storage classes, backup, and network enforcement need a
separate overlay and qualification for each target. A valid YAML file does
not establish cluster behavior.
[Kustomize workflow](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/).

## Virtual servers

For Hetzner Cloud, DigitalOcean Droplets, Amazon EC2, Google Compute Engine,
Azure virtual machines, or another provider, first provision or select the
explicitly authorized machine through that provider's interface. Record
operating-system support, architecture, private/public networking, firewall,
storage, workload identity, backup, and resource limits. Install the trusted
container runtime through its documented package channel. Apply the reviewed
single-server Compose definition and use the common routine.

Keep machine provisioning separate from application deployment. A provider's
virtual server is not a managed application service unless its support
agreement explicitly says so. Rebuilding a machine from a saved definition
and restoring state must be part of qualification.
[Hetzner server model](https://docs.hetzner.com/cloud/servers/overview/),
[Docker deployment model](https://docs.docker.com/compose/how-tos/production/).

## Dedicated servers and on-premises hosting

Use the same image and state contracts through Compose or Kubernetes.
The operator supplies hardware, operating-system maintenance, networking,
certificates, storage, backups, power and failure recovery, and physical
access controls. A managed-server contract must name which of those duties
the vendor actually performs. Test restoration on another machine before
claiming durable operation. A dedicated server is a capacity choice, not a
different Loop runtime or permission model.

## Cloudflare Containers

Prepare a Worker wrapper and container configuration for the service image,
binding, port, lifecycle, secrets, limits, and external state. Use the
documented Wrangler deployment workflow and independently version the
wrapper and image. Validate streaming, authorization metadata, cancellation,
and persistence across container sleep or replacement. Roll back both the
wrapper and the image binding. This profile needs its own qualification; a
plain Worker is not assumed to run the Python service unchanged.
[Cloudflare Containers](https://developers.cloudflare.com/containers/).

## Static frontends

Build the website and dashboard assets once with an environment-specific
service URL and public identity configuration. Publish those assets to a
selected static hosting service or content-delivery network. Keep private
credentials and authorization decisions in the backend. Verify sign-in
redirects, browser origin policy, subscription flows, documentation links,
and the exact frontend/backend version pair. Roll back the assets separately
from the backend while preserving compatibility. Static hosting supplies
the interface, not durable entitlement or protocol processing.

## Additional providers

An additional provider enters through a new deployment profile at the existing
boundary. Record capabilities and unsupported states, render the target's
definition, inspect the change plan, and run the same acceptance and recovery
suite. Preserve image/configuration identity and state portability. The
inventory is open-ended; listing a provider never implies live support.

## Qualification record

Every profile records preparation, local validation, hosted smoke checks,
durability, restore, rollback, protocol compatibility, operating limits, and
the exact evidence source separately. The
[status artifact](../roadmap/CONTINUATION-STATUS.md) links every procedure.
One successful deployment qualifies that observed profile and workload,
not every region, scale level, or provider in this guide.
