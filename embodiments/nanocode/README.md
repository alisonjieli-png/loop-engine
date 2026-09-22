# nanocode adapter experiment

The upstream nanocode agent completed a private text roundtrip through an
isolated scripted provider. No real model was called. Three negative probes
also passed: native tool declarations were refused before the callback, an
injected tool response did not create a file, and command text was not executed.

The [official repository](https://github.com/1rgs/nanocode) is pinned at
`b009d3dbedf14795a5c10804a5455386563f4b5b`. Its README declares MIT, but this
revision contains no standalone license file and the GitHub API reports no
recognized license. The license evidence remains incomplete.

The stock program uses a terminal, fixed Anthropic Messages endpoints, and six
native tools. The local adapter imports the unchanged source, supplies a
private loopback endpoint and exact model, empties the tool registry, and
replaces terminal input and Markdown display functions for a single complete
task. It then calls the upstream `main()` and model loop. This is an explicit
headless adapter, not a claim that the stock CLI supports these settings.

The new Messages codec accepts text only. The parent broker must enforce the
authorized output allocation because the upstream request still asks for its
fixed 8,192-token allowance. The codec does not call a provider. Any later real
model qualification must use the separately authorized Ollama Cloud broker.

The fixture records, written on the machine that ran this work to
`artifacts/harness-expansion-20260909-DNMQ3Y/lightweight-recipes/` and not
distributed with the repository,
contain exact requests, output, callback counts, and negative results. The
startup record named `nanocode-version-01` is a terminal startup and quit
check; nanocode has no version flag. Its identity is the source revision.

This experiment does not establish task quality, a full-system benchmark,
automatic adapter registration, or permission to execute native tools.
