# A client reader that assumes one response encoding

Kind: recorded failure and its repair, from Runtime History and Solution
Intelligence.

## When to use this record

Use it when you are writing or debugging a client for a service whose
transport is allowed to answer in more than one encoding, and the client
hangs, times out, or reports that the response could not be parsed.

## What was recorded

A browser check of the guided connection did not complete. Its success
condition was never reached, so the run was recorded as a failure rather than
as a pass with a warning.

Inspection found the cause. The service protocol transport is allowed to
answer with server-sent events. The first version of the browser reader
assumed every answer was one complete document of JavaScript Object Notation.
When the service answered with an event stream, the reader waited for a
document that was never going to arrive.

## The repair

The reader was changed to handle bounded event frames and to match the
request identity carried in each frame, so an answer is paired with the
request that asked for it. The original failing report was kept beside the
later passing report instead of being overwritten.

## The known-wrong case

The wrong repair is to force the service to answer with one complete document
so the old reader keeps working. That removes a supported transport behaviour
to protect a client defect. Another wrong repair is to read the frames but
ignore the request identity, which appears to work until two requests are in
flight and the answers are paired with the wrong questions.

## What to record

Record the exact success condition that was not reached, the encoding the
service actually sent, the repair, and both reports. Keep the failing report.
It is the evidence that the later pass means something.

## Limits

This is local browser evidence against a loopback service with no external
provider calls. It does not qualify any named coding harness.

## Source

`artifacts/architecture-audit-2026-09-19/guided-connection-browser-1.json`
(the failure), `guided-connection-browser-3.json` (the later pass), and
`src/loop_engine/core/service_runtime/web_assets/service.js`.
