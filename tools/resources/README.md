# Operator-tool resources

This folder holds versioned passive resources used by repository operator tools.
It is not a catalogue, engine registry or runtime component.

`original-native-generation-prompt-v1.json` owns the original native generator's
system instructions. Its `original_native_generation_prompt/v1` record declares
the bundle identity and version. The generator reads it as bounded regular UTF-8
JSON, refuses unsupported shapes/versions and renders it through the existing
`PromptResourceBundle` owner without input slots. One immutable in-memory render
is used for the campaign.

The resource SHA-256 and rendered text digest are separate facts. Both are bound
into `original_native_generation_run/v4`, alongside direct implementation
digests. A changed resource cannot resume an existing run. The first extracted
resource renders exactly the prior inline system text, without a trailing
newline. Its 1,076 UTF-8 bytes hash to
`02436f583453916c23f9ab7c19bd1cd5a27afeb0ec475116920b27e2ceb2fe87`.

Ship the resource beside its operator module in a source checkout. Change prompt
semantics through a new reviewed version, not by editing an active campaign's
resource and bypassing its binding. No key, candidate body or model output
belongs in this resource.
