# Common questions

Kind: customer answers about connecting, retrieving and using library material.

## Using an existing harness

You can connect an existing client to the hosted library without installing the
local engine. Use the published recipe for your client, then confirm its account
and available tools. See [Get set up](https://app.baltor.ai/setup).

## Choosing a model

Configure models in your harness. Your Baltor service token authorizes library
operations; model-provider credentials and charges remain separate. Connecting
the library does not select a model or start a task for you.

## Getting an empty search result

An empty result can reflect the query, account access, withdrawn material or
selection filters. Check the effects the step is already allowed to use and the
current request format. Read the service's capabilities before using a filter.

Selecting material with declared effects does not grant permission to execute it.
See [Searching and retrieving](https://app.baltor.ai/docs/searching-and-retrieving).

## Checking a downloaded package

Compare the received bytes with the selected digest. For a package, inspect its
file list and verify each retrieved file against its own digest. Preserve the
relative paths and inspect required dependencies before loading the material.

File presence, successful loading and a checked task result are separate facts.

## Understanding usage

The service records applicable item reads. That count does not measure model
tokens or successful tasks. Keep the same request identity when retrying the same
uncertain read, as [Usage and what you pay for](https://app.baltor.ai/docs/usage-and-what-you-pay-for)
explains.

## Reporting a problem

Keep the endpoint, time, error code, request reference, item identity and digest.
Describe whether the failure occurred during connection, search, download or
native loading. Leave credentials and private task content out of the report.
See [Troubleshooting](https://app.baltor.ai/docs/troubleshooting).
