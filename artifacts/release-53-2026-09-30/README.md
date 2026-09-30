# Release 53: audience paths and the distinct-file counter

The image from `fa1696b3` is live. The homepage shows 88,373 distinct files
and 27,811 packages separately. Engineers, Designers and AI Agents have their
own entry paths; direct requests to the designer page succeed.

The [release record](../architecture-audit-2026-09-19/pilot-release-53.json)
names the image, exact source, checks and rollback to release 52.
CI run 36669688050 passed. Deployment run 36675414386 deployed the image,
then failed on the Machines API timeout during grant confirmation. After
checking that the original command was no longer running, bounded detached
initialization completed both grant and policy commands. Nothing registered
an account, reset paid access or called a model provider. The deployment gate
was read back as off. GitHub's failed workflow conclusion remains unchanged.

Live checks passed 226 of 226 browser cases and 40 of 40 HTTP cases across
ten origins. Visitor checks found no problem across 58 pages, 241 views,
354 links and nine website hostnames. The frozen local browser pass was
956 of 957; its deck-size failure remains recorded.

Private reports are in
`/home/username/baltor-private/release-20260930-4IMwyK`.
No candidate was admitted by this deployment. Catalogue publication and the
million-file target remain separate work.
