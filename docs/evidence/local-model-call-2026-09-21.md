# One real local model call, September 21, 2026

Kind: dated evidence record. It reports what happened on one machine with
one model on that date. It is not a benchmark, and nothing here is a rate
that another machine will reproduce.

Why it exists: the
[overnight local model guide](../guides/overnight-solving-on-local-models.md)
and its example answer the engine's own local endpoint adapter from a
fixture rather than a socket. That proves the wire format and the token
accounting and nothing about a physical server. This record closes that gap
with one call that opened a real socket to a real local server holding real
weights.

## What was run

The engine's own adapter, `make_adapter` over a `CustomEndpoint` with wire
`ollama`, locality `local` and authentication `none`, against a local
server on `http://127.0.0.1:11434`. No fixture, no injected opener, no
provider account and no credential anywhere in the path.

The output capacity was read from the server's own model information
through `/api/show`, from the field `qwen2.context_length`, and passed as a
typed `ModelOutputCapability` naming that source. It was not guessed and
not taken from a general default. The probe refuses to run when the server
reports no context length.

## The machine

| Part | Value |
|---|---|
| Video memory | NVIDIA GeForce RTX 3060, 12288 MiB |
| System memory | 61 GiB |
| Model | `qwen2.5-coder:7b` |
| Parameters | 7.6 billion |
| Quantization | Q4_K_M |
| Context length the server reports | 32768 |
| Video memory in use with the model resident | 6659 MiB of 12288 MiB |

## What was observed

Three calls, the same prompt each time, 64 prompt tokens in and 18 tokens
out, every one reported by the server rather than counted here.

| Call | Elapsed | Answer state |
|---|---|---|
| First, with the model not yet loaded | 87.28 s | ok, finished for the reason `stop` |
| Second | 0.71 s | ok, finished for the reason `stop` |
| Third | 0.78 s | ok, finished for the reason `stop` |

The endpoint record reported `has_key` false and carried no `api_key`
field, checked before the call rather than after.

## The one thing worth carrying into a design

The first call cost 87 seconds and the next cost 0.7 seconds. Almost all of
that first number is the server loading 4.7 GB of weights into video
memory, not the model thinking.

For an unattended overnight run this is the difference between a night that
finishes and a night that does not. A run that lets the server unload
between steps pays that load again at every step. A run that keeps one
model resident pays it once. Any schedule that alternates between two
models on a 12 GiB card will also pay it repeatedly, because both cannot
stay resident at this size.

That is a structural fact about loading weights, not a measurement of this
model's quality or speed.

## What this does not show

It does not show how fast this model is: 18 output tokens is far too few to
carry a rate, and no rate is claimed. It does not show how good the answer
was; the model returned one plausible sentence about one small Python
question and nothing graded it. It does not show that a whole overnight run
completes, because no overnight run was performed. It says nothing about
any other model, quantization, card or machine.

## How to repeat it

The probe is not committed. It builds a `CustomEndpoint` for the local
server, reads the context length from `/api/show`, refuses to continue if
the endpoint record carries a key, calls `make_adapter(endpoint).chat` with
`max_tokens=0` so the adapter requests the full declared capacity, and
prints the provider-reported token counts. Rebuild it from that
description rather than trusting a copy.
