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
