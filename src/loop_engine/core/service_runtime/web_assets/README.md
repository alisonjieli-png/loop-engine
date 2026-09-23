# Service web assets

Packaged public pages and a same-origin authenticated workspace. The HTTP
adapter serves only the named HTML, stylesheet and script. It never serves
the repository, source inventory, configuration files or internal reports.

Service tokens stay in page memory and are cleared on disconnect. Model
provider keys are not collected. Search, downloads, usage and configured
billing sessions use the real versioned service routes. Downloads check the
selected content digest before saving. No file is executed or automatically
installed into a harness.

The workspace is not an identity provider. Tenant creation and subject binding
remain explicit operator operations. A billing session is not an entitlement.
The service's capability record distinguishes configured behavior from live
provider qualification.

## One call to action

Every public link or button that starts the access journey says "Get
started" and opens the Get started page at `/connect`. The addresses
`/get-started` and `/waitlist` open the same page. That page leads with one
panel, chosen from the service's capabilities record: account creation when
`website.registration_available` is true, otherwise the invitation request
form when `website.waitlist_available` is true, and otherwise the way to reach
the operator. The operator's panel is also the careful state, so the served
page shows it until the service answers, and keeps it when the record is
missing or carries a version the page was not written for. The browser checks
in `tools/check_service_workspace.mjs` read every public page on three real
services and report a second label for the same journey, an invitation
request outside that panel, and account creation while registration is closed.
