# Write a pinned container image and a batch job that does not retry

Generate a container definition and a Kubernetes Job with safe defaults: a pinned base image, a user without privileges, declared resources and no automatic retry.

## When to use it

Use it when a packaged solution must run as a scheduled or one time batch job, and the person who deploys it did not write it.

## Steps

1. Declare the container settings as typed data: one base image reference without spaces, an optional image digest in the form `sha256:` and 64 hexadecimal characters, a processor quantity, a memory quantity and the arguments.
2. Start the container definition from the base image. Add the digest when one is given. When none is given, put a comment above that line. The comment says that the base image is not pinned and must be pinned before production use.
3. Copy the package into `/app`, install it without a download cache, and switch to user 65534, which has no privileges.
4. Write the entry point as a list, either the console command or the module started by the interpreter.
5. Write the job with a backoff limit of 0 and a restart setting of never, so a failed run is not repeated by the platform.
6. Remove the finished job after 86400 seconds.
7. Set the resource requests equal to the resource limits. The defaults are `500m` processor and `512Mi` memory.
8. Mount an empty working volume at `/work` and pass the arguments, for example the input path and the output directory below `/work`.
9. Leave the image reference in the job as a placeholder that the deploying person replaces after the build.

## Checks

- An image digest that is not `sha256:` with 64 hexadecimal characters is refused.
- An unpinned base image produces the warning comment.
- The container does not run as the administrator user.
- The job has no retry, and its requests equal its limits.

## Known-wrong example

A generated job uses the latest tag of the base image, runs as the administrator user and restarts on failure with six retries. The job sends an invoice file to a partner. After a timeout the platform runs it six more times, and the partner receives seven files. A job with an external effect must not be retried by the platform.

## What to record

- The base image reference, its digest and whether it was pinned.
- The resource quantities and the arguments.
- The image reference that replaced the placeholder at deployment.

## Source

- `src/loop_engine/code_nodes/solution_export.py`: `ContainerSpec`, `render_dockerfile` and `render_kubernetes_job`.

Licence: MIT. Compiled from revision 565e133. The render functions use only the Python standard library.
