# Containerized worker

This example carries the recipes for running Loop Engine as containers and
validates them offline. Nothing is built or deployed; the checks prove the
recipes have the properties a deployment needs.

The repository `Dockerfile` builds the engine image: a slim Python base,
the package installed from source, a non-root user, and the `loop-engine`
command as the entry point. The `k8s` folder holds a worker Deployment that
serves the hosted service surface (`loop-engine serve api` with a tenants
file mounted from a Secret and a readiness probe on the health endpoint)
and a Job that runs example 26 inside the image with no retries.

Install Loop Engine directly from GitHub:

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

Run the example from the repository directory:

```bash
python examples/28_containerized_worker/run.py
```

The output lists, for the Dockerfile, whether there is one base image,
whether it is digest-pinned (required by the check), whether the image
runs as a non-root user, whether the entry point is `loop-engine`, and
whether any secret-shaped text is present. For each manifest it lists the
kind and version, the non-root security context, resource requests and
limits on every container, the image reference placeholder, the absence of
secret-shaped text, and the kind-specific rules: a Job never retries
silently and the worker serves the service surface with a readiness probe.

To build and deploy, replace `IMAGE_REFERENCE` with a digest-pinned image
and create the `loop-engine-tenants` Secret from a tenants file that holds
key digests only:

```bash
docker build -t loop-engine:0.1.0 .
loop-engine --new-tenant acme --tenants tenants.json
kubectl create secret generic loop-engine-tenants --from-file=tenants.json
kubectl apply -f examples/28_containerized_worker/k8s/
```

Read the [packaging tiers and hosted service guide](../../docs/guides/packaging-tiers-and-hosted-service.md).

No network, no external service, no model calls, no cluster.
