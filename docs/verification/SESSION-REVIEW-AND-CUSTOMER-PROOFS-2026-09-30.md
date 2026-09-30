# September 30 review and customer proofs

Kind: dated evidence, not a release or a general product-benefit claim.
The [delivery plan](../roadmap/DELIVERY-SEQUENCE.md) orders the unfinished work.
The [deployment record](../architecture/MVP-CLIENT-SERVER.md#current-deployment)
identifies the live image. These initial customer checks used release 54 and
catalogue `f817b2b3e82daee0acd73e6ce295d3ddceecf9a45d0f4ebab35501bfc2a79fd3`.

## Previous sessions: what was actually reviewed

A read-only inventory of the local Codex records found 216 threads and 156
prior project sessions: 18 top-level sessions and 138 delegated sessions.
The top-level population includes 13 owner-facing sessions and five probes or
reviewer sessions. The project population contains 662 turns, 569 top-level
user messages, 3,351 assistant messages and 26,169 projected command results.
Its raw records total 1,535,275,720 bytes. No source rollout was missing or
malformed, and no orphan rollout was found in the checked scope. The current
turn and unrelated projects were excluded.

All 569 top-level prompt entries were inspected. Of these, 478 shorter entries
were read in full; 91 longer entries were initially reviewed through openings,
outlines and endings, with selected entries subsequently opened in full. The
last available final response from each top-level session was read. This is
**not a complete semantic review of every assistant turn, delegated transcript
and command body**. A record census does not meet that stronger claim.

One raw/projected discrepancy was preserved: the previous session's final
read-only source-inspection command appears in its raw rollout but not its
command projection. The source snapshot has 136 command records where the
projection has 135. Private source histories and their credential-bearing text
were not copied into the repository or component library.

Inherited work was traced to the preceding closed sessions and saved as a
tracked patch plus an untracked archive before review. The unmerged support
worktree at `0769ca5e` was also inspected and its four modified files preserved
as a patch. It contains help-centre, chat and support-mail work absent from
main; this is a recovery finding, not evidence that chat is live.

## A genuinely new customer account

A new disposable mailbox completed the real email-first signup, confirmation,
password choice and fresh sign-in: two of two journey checks passed. The same
account then completed nine of nine first-use checks:

- Identity-provider binding, authentication and account session.
- Permission to issue a scoped key and receipt of that key.
- The shipped client handshake, search and a complete digest-checked download.
- Installation and byte verification in an OpenCode skill directory.

The selected one-file package was `normalize_and_recover_email_addresses`,
digest `b97b306b70d8c92a2bcd1b68d44b38a57a42e1b5c3a7716a599a355bab54ffb6`.
The observed handshake took 436 ms, search 448 ms, and download 1,489 ms.
No payment, operator entitlement grant or model call was used for these checks.
Native automatic skill activation and useful task completion are separate
claims; this installation check establishes neither by itself. Credentials and
mailbox state remain private, with the scoped client key in the system keyring.

## Live latency diagnostic

All 24 anonymous probes and all 42 authenticated probes completed successfully.
The authenticated probe used six serial requests per profile from one
workstation. Selected results:

| Profile | Median | Largest observed sample |
| --- | --- | --- |
| Lexical search | 113.344 ms | 249.701 ms |
| Hybrid search | 319.359 ms | 838.583 ms |
| Catalogue listing | 1,644.584 ms | 2,503.698 ms |

These include client/network overhead. They are not a concurrent-load test,
global latency estimate, reliable tail percentile or evidence of retrieval
quality. Server stage timings, cold-start behavior, catalogue refresh, memory
and held-out wrong-file cases remain required by S-6.32 and S-6.51.

## With and without material: a scorer defect, not a win

Four physical model calls ran through OpenCode 1.17.9 and Ollama Cloud
`gemma4:31b`, in without/with/with/without order. Each used the same eight-row
email-normalization task, temperature zero and an output allocation of 2,048
tokens. The with-material arm received the downloaded skill in the prompt;
automatic native skill discovery was not tested. Native tools were denied and
the relay permitted one physical call per trial, four total. This was not an
operating-system sandbox.

The original scorer recorded 7/8 for both baseline trials and 8/8 for both
with-material trials. Inspection found the scorer over-specified an action
label: it required holding a plausible valid domain, although the task did
not require that choice. Both arms normalized all eight values identically
and correctly. The action-score comparison is therefore invalid and must not
be advertised as improved accuracy. The failed scoring design and original
results are retained rather than silently rewritten.

| Arm | Input tokens per call | Output tokens per call | Native wall time, seconds |
| --- | --- | --- | --- |
| Without material | 1,264 | 224 | 7.045; 5.462 |
| With material | 2,084 | 224 | 4.532; 6.990 |

The provider reported 6,696 input and 896 output tokens across all four calls,
7,592 total, with zero cached tokens and HTTP 200 on every call. The material
added 820 input tokens per call. Two repetitions per arm do not establish a
speed advantage, and no total monetary cost was established. A request-log
heuristic for detecting exact material in serialized JSON was also faulty;
saved prompt files and a title-presence check establish the intended treatment,
not full wire equality from that heuristic.

The next comparison must freeze an unambiguous rubric and test its known-wrong
controls before model calls. Retain no-extra-material as an eligible baseline.

## Source intake

Two authorized requests used Reddit34's observed posts-by-subreddit endpoint.
DesignAndAI returned 25 posts in 2.366 seconds. The integrated aigamedev read
returned 25 posts in 1.488 seconds and produced 20 source-linked research work
orders through the existing managed store and scheduler; five posts had no
matching signal. These are unverified leads, not approved components.

The provider reported a 50-request allowance and 47 remaining after the second
read. No automatic retry, recurring Reddit timer, model expansion or component
publication was activated. The credential is in the system keyring. Raw post
bodies and author profiles were not retained. The additional supplied RapidAPI
services have no qualified adapter yet; their endpoint contracts and account
allowance remain unchecked.

## Editable browser and Blender example

Ashen Wilds is an original Three.js example, not a reference-video recreation
or an admitted library package. Five deterministic simulation tests passed.
The browser check through the real local service passed seven checks: served
page, movement, animation/lighting revision, rigged character export, complete
scene export, phone-width fit and no browser errors. The character GLB is
178,912 bytes with one rig and four clips; the revised scene GLB is 1,766,584
bytes with four rigs and sixteen clips.

Blender 4.5.3 LTS, through its official Python module in an isolated Python 3.11
environment, imported 892 meshes and sixteen animation actions, saved a native
project and rendered a CPU Cycles frame. A separate process reopened that
project and passed six checks, including four rigs, changing poses and no
missing image dependencies. Gameplay behavior stays in the JavaScript source;
GLB does not turn Blender into the game runtime.

The first standalone browser attempt failed on a favicon, and the second on
software shadow-rendering shaders. A reduced-effects profile passed, then the
real-service run above passed. The test browser had no WebMCP API; that optional
integration remains unqualified. A resized desktop viewport is not physical
phone coverage, and there is no measured hardware-renderer comparison yet.

## Private evidence location

Original reports, failed attempts, scripts, screenshots, exact source snapshots
and preserved patches are under
`/home/username/baltor-private/session-review-20260930-GYFErD`.
The folder is private. Do not publish it wholesale: account state and raw
histories have different sensitivity from the summaries above. A later release
record must identify the final checks and exact committed revision separately.
