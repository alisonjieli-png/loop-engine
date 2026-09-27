# Components, packages and files

Kind: customer guide to selecting and checking library material.

A component is reusable material you select for a task: a skill, instructions,
configuration or a tool. Your harness decides how to use the selected material
within the permissions you gave it.

## Three useful terms

| Term | Meaning |
| --- | --- |
| Component | The material you search for and select. Service responses often call it an item. |
| Package | A delivery bundle containing one or more files. Its document lists the files and their digests. |
| File | One payload, with a relative path, byte size, media type, role and digest. |

A tool might need instructions, a Python script and a schema. Those files can
travel together as one package. Keep their relative paths when preparing the
working directory.

## Identity and exact bytes

The item identity names what you selected. The digest pins the bytes for that
selection. Keep both, along with the `catalogue_release` that the search
response names.

A search returns small references and each hit's package summary before any
body is loaded. The manifest then reports the source, licence, declared effects
and whether your credential may download the body. A package document has its
own digest, and each file inside it has its own digest too.

Follow [Searching and retrieving](https://app.baltor.ai/docs/searching-and-retrieving)
to download and compare the exact bytes.

## Evidence for your task

| Question | Evidence to look for |
| --- | --- |
| Did I receive the selected version? | The downloaded bytes match the selected digest. |
| Can this harness discover it? | The required native path, configuration and dependencies are present. |
| Did the harness load it? | An observation from that harness, beyond file presence. |
| Was it used? | The task's execution record or other direct observation. |
| Did it help finish the task? | A result checked against your acceptance condition. |

Read the review information and the scope it covers. A review of one version
does not establish the outcome of your next task. Your harness keeps
responsibility for its model, local execution and task checks.

See [What Baltor is](https://app.baltor.ai/docs/what-baltor-is) for the hosted
library and local engine, or [Get set up](https://app.baltor.ai/setup) to connect
your existing client.
