# Testing the whole client journey in containers

Kind: operating guide. It describes what one drill does today, what a passing
run proves and what it does not prove. Planned work has its own section at the
end.

The service can answer a request, and the install tool can write a file. Those
are two separate facts, and neither of them is a customer who received usable
material. The
[container journey drill](../../tools/check_client_journey_in_containers.py)
joins them into one run: it builds the service image from the working tree,
registers real starter catalogue items behind a host manifest, starts a server
container and a separate client container on a private Docker network that has
no route off the machine, and then runs the journey the way a customer runs it.

The drill starts no model turn, contacts no provider and writes no credential
into its report. Every container, network, volume and image it creates carries
a name of that run and is removed before the drill returns.

## How to run it

```bash
PYTHONPATH=src .venv/bin/python tools/check_client_journey_in_containers.py \
  --report /some/new/path/container-journey.json
```

The report path must not exist. The drill takes the name first, with an
exclusive create, and writes a short unfinished record into it. Only when the
run ends does it write the finished report into that same reserved file, so a
name taken by someone else while the containers are running cannot lose the
result. Docker must be available. Building the image downloads the packaged
dependencies, so the machine needs to reach the package index for the build
step; the containers themselves then run with no external network at all.

Add `--client-binary /path/to/opencode` to mount a client executable that is
already installed on the machine, read only, into the client container. With
it, the drill also observes the client's own listing of the installed material.
Without it, the drill records the listing state and names the two checks that
need the listing as skipped. A skipped check is never counted as passed. The
drill never runs a client subcommand that would start a model turn.

Every address the drill uses belongs to the typed settings record: the port the
server listens on, the loopback port the client container forwards, and the
public base URL the host configuration declares. That last one is a name under
the reserved `.invalid` top level name, so it can never resolve anywhere.

The server container runs the image's own command, which binds every address
and declares a trusted proxy in front of the service. The service refuses to
start that way until its host configuration states where each caller's address
comes from, because behind a proxy every caller would otherwise share one count
of refused sign-in attempts. The host configuration therefore carries
`request_limits` with the `header` source and a header name that the settings
record owns and that belongs to no provider. The service's own settings record,
`ServiceRequestLimits`, checks the name before any container starts. The drill
has no proxy, so no request carries that header, and the service counts each
refused attempt under the address of the client container that sent it. A test
removes the statement from the host configuration and requires the drill to
fail where the server stops.

The drill states no address vocabulary of its own. It asks the service's own
address owner, `validate_public_url` in
[the authentication adapter](../../src/loop_engine/core/service_runtime/http_auth.py),
which scheme that owner accepts for a public name and which it accepts for a
loopback address, and it refuses to start if it cannot read that answer as one
of each. In the same way it reads the expected client listing command, and the
subcommands that would start a model turn, from the client layout profile in
[the install tool](../../tools/install_selected_material.py), which owns them.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role: Practitioner, Intelligence, or Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A container, an image, a Docker network and this drill are not runtime types
and are not graph vertices. A client such as OpenCode is a harness: an adapter
that a Loop uses. A separately initialized harness process can perform the
assignment of a discrete cognitive or act step Loop node. Read the
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation)
before describing one. On the service side, the search, the manifest and the
download are each already owned by a classified Loop in the
[HTTP adapter](../../src/loop_engine/core/service_runtime/http.py). Placing a
file grants no permission and promotes no item.

## What the drill sets up

```text
Two containers on one private Docker network
├── Server container
│   ├── The service image built from the working tree
│   ├── A generated host configuration and host manifest on its own volume
│   ├── Real starter catalogue bodies under an artifact root
│   ├── Two tenants created by the configure command
│   └── Three keys issued by the issue-key command
├── Client container
│   ├── The same image, so the package and its dependencies are already there
│   ├── The repository tools folder mounted read only
│   ├── An empty project folder on its own volume
│   └── The first tenant's key, under one variable name
└── Second client container
    ├── The other tenant's key
    └── The key that the revocation drill cancels
```

The two tenants are given different grants. Three items are granted to the
first tenant only, two to both tenants, and two to the second tenant only. One
item is held back from the manifest on purpose, because the catalogue declares
its licence as unknown and the host accepts only the exact licence identifiers
it lists.

A key reaches a container through a named environment variable. No key value
is ever written into a command line, a call log, a report or the console. The
drill reads only the identity of an issued key.

## What one passing run proves

The report keeps three kinds of statement apart. `observations` holds what the
drill read back from the containers. `checks` holds each named comparison and
whether it passed, and `skipped_checks` names a check that could not run and
why. `declared` holds the small number of values that no check measures: this
drill asks for no model turn and no provider call anywhere, and writes no
credential into its report, so it declares zero for each. A declared value is a
statement about how the drill is written, not an observation of the service,
and it is never counted as a passing check.

The report separates the facts rather than adding them up.

| Fact | Meaning |
|---|---|
| `registered_in_the_host_manifest` | Items the host attested and the server loaded. |
| `offered_to_the_first_tenant` | Items that tenant's search returned. |
| `offered_to_the_second_tenant` | Items the other tenant's grants cover. |
| `selected_for_install` | Identities the install run was asked for. |
| `fetched_by_the_install_run` | Bodies the install run downloaded. |
| `installed_in_the_native_client_layout` | Files written under the client's own folder. |
| `verified_against_the_served_digest` | Installed files whose served part matches the digest the service named. |
| `reported_by_the_client` | Items the client itself listed, or empty when no client executable was supplied. |

The drill runs these checks in one pass:

- The image builds from the working tree, and the report keeps its identity.
- The private network reports no external connectivity, the client container
  has no default route, and a public name does not resolve inside it.
- An item whose declared licence is unknown is refused before registration.
- The configure command creates both tenants and both grant sets, and creates
  no remote account.
- Health answers without a key.
- Usage is refused without a key, and so are the two routes where a caller
  without a key would obtain reviewed material: the manifest and the download.
  Each answers 401 with the code `unauthorized`.
- A request whose Host header is outside the list the host configuration
  declares is refused with status 421 and the code `invalid_host`, even when it
  carries a valid key.
- Search offers exactly the items that tenant's grants cover, never an item of
  the other tenant, and it offers every identity the install run then selects.
- The manifest names the digest and the size of a selected item.
- The downloaded body matches both the digest the manifest named and the digest
  in the response header, and its length matches the size the manifest named.
- The retrieval result, the manifest and the download response header carry the
  exact record versions this drill reads. A service that changed one of them
  turns that check red instead of passing unnoticed.
- The install tool refuses plain HTTP to a host that is not a loopback address.
- Every selected item is offered, fetched and installed, with no refusal.
- Every installed file sits under the client's own folder, holds the served
  body byte for byte, and matches the digest the manifest named.
- Usage counts every downloaded item.
- The client command the install run recorded holds no subcommand that would
  start a model turn. With a client executable, that recorded command is the
  client's own listing subcommand, and the client lists every installed item
  under its own name.
- An item granted to the other tenant is refused, while a shared item is still
  served to that tenant.
- A revoked key is accepted before the revocation and refused at the next
  request.
- A body whose bytes no longer match its reviewed digest is refused, and the
  same body is served again once its bytes are restored.
- The server restarted on the same volume still reports the same usage.
- Every container, network, volume and image of the run was removed.

## The observed runs

On 21 September 2026 the drill ran on the development workstation, first in an
earlier shape and then in the shape this guide describes.

The earlier shape ran thirty three checks with a client binary and thirty one
without it, and an independent review found that it named one skipped check
where two were needed. Those runs are kept here as the earlier record. In the
run recorded at 12:26 the drill file had the hash
`12ec30003b71704f9bf1b27acbe21808143d3bd8e3308304760035ebcebb529c` and the
image identity was
`sha256:5c1b147e3947889f7a7afadcccfae46fdc09fb2b60cb12dc148b19b637545519`.

After that review was answered the drill ran three more times. At 13:02, with
the OpenCode binary version 1.18.31 mounted read only, all thirty six checks
passed and none was skipped. At 13:03, without a client binary, all thirty four
checks that could run passed, and the two checks that need the client's own
listing were named as skipped rather than counted as passed. In that second
report `reported_by_the_client` is empty, not zero. At 13:08, after this work
was brought up to date with the main branch, the run with the client binary
passed all thirty six again.

The drill file had the hash
`2710b2477247808982cb68c785c2631357df2944efe719608407ad183385ac36` in all three
runs. The three image identities were
`sha256:11f8f2bd825a997181c1baa4ab2c51b449edb3e5cbbf1dfca9663583c5834ac0`,
`sha256:21651463e1a0b6181329ddf0b85d36af13e2718d52605a2a8c45e15c75f4e8e7` and
`sha256:8501542341499af7f284c9329d6fa1321e79769b712e894b241a08fe116a5643`. The
first two runs read one starter catalogue file and the third read another,
because the main branch corrected one reviewed body in between. The
`source_files` map in each report records which one it read.

The image identity names one build, not the source. Building the same tree
again gives a different identity, because the packaging step writes a new
timestamp. Runs minutes apart, over the same source, produced different image
identities and the same source hashes. The stable record of what was tested is
therefore the `source_files` map in the report, which holds the SHA-256 hash of
every file whose content decides what the drill observes.

Each of the three later runs registered seven items. The first tenant was
offered five and the second four. Three were selected, three were fetched,
three were installed under `.opencode/skills`, and three matched the served
digest byte for byte. In the two runs with a client binary the client listed
three, and the command the install run recorded for it was `debug skill
--pure`. In the run without one, no client command was recorded at all. Usage
rose from one to four metered item reads across the install run and stood at
five, unchanged, across a restart of the server on the same volume.

The refusals answered as follows. A request with no key was refused on the
usage route, on the manifest route and on the download route, each with status
401 and the code `unauthorized`. A request carrying a valid key and a Host
header outside the declared list was refused with status 421 and the code
`invalid_host`. The other tenant's item was refused with `item_unavailable`,
while the shared item was still served to that tenant. The revoked key answered
with status 200 before the revocation and `unauthorized` after it. The tampered
body was refused with `body_integrity_failed` and served again with its
reviewed digest once restored. The served record versions read back as
`service_retrieval_result/v1` for the search, `provisioning_manifest/v2` for
the manifest and `service_download/v1` in the download response header.

The client process created one file of its own, `.opencode/.gitignore`. The
install tool records what the client process adds rather than hiding it.

## What the drill does not prove

- There is no identity provider. A key is issued by the host command inside the
  server container, not by a customer signing in. Browser sign-in, account
  activation and the sign-up email are all absent.
- There is no browser. Nothing here exercises the website, the dashboard or any
  page the service serves.
- There is no payment provider. The two tenants hold an operator entitlement
  written into the host configuration, not a subscription.
- No model turn runs. A file the client lists is material the client
  discovered. It is not material a model read, used or benefited from.
- There is no public name, no certificate and no proxy. Two containers talk to
  each other over plain HTTP on a private network.
- The limit on refused sign-in attempts is stated but not reached. No request
  carries the client address header, and the drill sends far fewer refused
  attempts than the limit allows.
- The host attests the catalogue items. Host attestation is not independent
  qualification, and no item in the starter catalogue has been approved.
- The catalogue subset is seven items of the forty nine in the starter
  catalogue, chosen in a fixed order. A passing run says nothing about the
  other items.
- The drill runs on one machine with one Docker version. It is not a test of
  the deployed pilot, its volume or its network.
- The declared values in the report are not measurements. That the drill starts
  no model turn and makes no provider call is a statement about how the drill
  is written, kept in its own `declared` block. No check observes it.
- One request is sent with a Host header outside the declared list, on the
  manifest route. The other routes are not probed that way, and the list of
  allowed browser origins is empty in this host configuration, so nothing here
  exercises it.

## Two findings about the install tool

The drill was written around two properties of
[the install tool](../../tools/install_selected_material.py) that a customer
will meet.

The first is that the tool accepts an HTTPS address or a loopback address and
refuses plain HTTP to anything else. That refusal is correct, and the drill
checks it as a negative control. It also means the tool cannot be pointed
straight at another container on a private network. The client container
therefore runs a small forwarder that listens on its own loopback address and
passes the bytes to the server container. The bytes still cross the private
network between the two containers; only the address the tool is given is
local. A customer with the same problem terminates TLS in front of the service.

The second is that the tool removes only the key variable it was named from the
environment of the client process it starts. Any other secret in that
environment reaches that process. The drill therefore keeps the other two keys
in a separate container, so that no key but the one the tool was named can
reach the client process.

## Removed-guard controls

The drill takes several minutes and needs Docker, so its logic is also driven
by a recorded command runner in
[the fast checks](../../tools/test_check_client_journey_in_containers.py).
That file answers every Docker command from a prepared world, so the whole set
runs in about one and a half seconds. The count a reader can re-derive is
printed by the command that runs them:

```bash
PYTHONPATH=src:tools .venv/bin/python -m unittest \
  tools.test_check_client_journey_in_containers
```

On 21 September 2026 that command reported seventy seven checks, and each of
its runs took between 1.4 and 1.5 seconds on the development workstation.

Sixteen of them are removed-guard controls. Each removes one piece of service
behaviour from the recorded answers and names the drill check that must turn
red: a service that answers without a key, which must fail both the free route
check and the metered route check; one that answers a Host header outside the
declared list; one that changes a record version it serves; one that serves a
body that does not match its digest; one that serves the other tenant's item;
one that still honours a revoked key; one that serves a tampered body; a server
that forgets the usage when it restarts; an install run whose recorded client
command names a subcommand that starts a model turn, which must fail both model
turn checks; an install that writes something other than the served body; an
install tool that accepts plain HTTP to a host that is not a loopback address;
a host that registers an item whose licence is unknown; a private network that
has external connectivity; a container that keeps a route off the machine; a
container that resolves a public name; and a client that does not list the
installed material.

Four more checks cover what happens when a step cannot be completed: a failed
build, a step that fails inside a container, a service that never becomes
healthy, and a refusal to remove a resource the run did not create.

Three groups cover what the drill refuses before it creates anything. A
catalogue row whose body path climbs out of the catalogue, points at a link
that leaves it, is absolute, names no file, or is not text at all is refused
with a typed code. A report path already taken is refused, a report path in a
folder that does not exist is refused, and a shorter report never leaves the
tail of a longer one behind. An address owner that accepts every scheme
everywhere, or none at all, is refused rather than guessed.

One check is written for the accounting itself. It drives a world whose client
listing state is `client_executable_not_found`, then asserts that both checks
that need the listing are named in `skipped_checks`, that neither appears among
the checks, that neither is added to the count, and that the run still passes.

A removed-guard control that cannot fail proves nothing, so each guard added on
21 September 2026 was patched away in the drill's own source, one at a time,
and the named fast check was run again. Eleven guards were treated this way:
the second skipped name, the listing check reading the recorded client command,
the install check reading the recorded client commands, the metered routes
probed without a key, the unexpected Host header comparison, the served record
version comparison, the catalogue body path confinement, the exclusive create
of the report name, the truncation of the reserved report, the refusal of an
address vocabulary the drill cannot read, and the derivation of external
connectivity from the two network checks. Each patch made its named check fail,
and the source was restored after every one.

The tampered body is also a live removed-guard control. During the real run the
drill changes the bytes of one reviewed body on the server volume, keeps its
length the same, observes the refusal, and then puts the original bytes back
and observes the item served again.

## Not implemented yet

- A run against the deployed pilot. That needs the owner's authority and makes
  one metered body read for each new item.
- Browser sign-in, account activation and a subscription in the journey. They
  need an identity provider and a payment provider that the drill cannot start
  without network access.
- A model turn that shows a client used an installed item. This needs
  model-call authority and a comparison with a withheld or changed resource, as
  the [harness instance layout guide](harness-instance-context-layout.md)
  describes.
- Layout profiles for clients other than OpenCode. The install tool has one
  layout profile today.
- More than one client container at a time, and a check that two customers
  installing at once each get their own material.

The [native client guide](native-client-material-loading.md) describes the
install tool itself. The
[onboarding guide](harness-service-onboarding.md) describes the wider customer
journey that this drill runs one pass of.
