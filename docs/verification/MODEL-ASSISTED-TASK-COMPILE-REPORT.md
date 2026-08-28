# Model-assisted task-compilation verification

## Result

`VERIFIED WORKING` locally for one Ollama Cloud review added to the existing
deterministic task compiler.

The same typed path supports configured OpenRouter and OpenCode Go credentials.
Those two providers were contract-tested without a live call because their keys
were not available in the test environment.

## Execution boundary

```text
task text
├── deterministic task-compilation Loop
│   └── authoritative compiled task and requirement dispositions
└── optional authorized provider review
    └── ModelGateway
        └── one model-attempt Loop
            └── exact JSON validation
                └── advisory Orientation review
```

The model review does not replace the compiled task. It cannot change a hard
requirement policy, grant an effect, or claim that the task ran.

## Credential input

The command accepts a provider-specific value, a credential by reference, or a
hidden prompt:

- `--ollama-api-key VALUE` or `OLLAMA_API_KEY`;
- `--openrouter-api-key VALUE` or `OPENROUTER_API_KEY`;
- `--opencode-go-api-key VALUE` or `OPENCODE_GO_API_KEY`;
- `--provider-key-env ENV_NAME` for another environment-variable name;
- `--prompt-for-provider-key` for an interactive no-echo prompt.

A direct value is intended for disposable local testing. It may be visible in
shell history or the process list. In every form, the key is installed in the
process environment only for the provider call and the prior value is restored.
The compiled output, model review, provider description, and failure result do
not contain the key.

The total token ceiling is derived from the selected route's declared maximum
output and the exact assembled prompt. A user may supply a stricter
`--max-total-tokens` override, but an override below the derived minimum is
refused before the call.

OpenCode CLI remains a separate coding harness. It continues to use the
credential configured through OpenCode `/connect`. The `opencode_go` compile
provider is a direct OpenAI-compatible API route and does not read OpenCode's
credential file.

## Local live evidence

The accepted Ollama Cloud run used the flagship public modeling request:

- deterministic compiler model calls: `0`;
- advisory Orientation model calls: `1`;
- total physical model calls: `1`;
- provider: `ollama_cloud`;
- model: `deepseek-v4-flash:0731`;
- provider token accounting: complete;
- provider-reported tokens: `967`;
- review status: `ready`;
- delegated choices: `dataset_source`, `target_column`;
- user questions in autonomous mode: `0`;
- raw provider key in command output: absent;
- derived total token ceiling: `68,834`;
- ceiling source: declared model output maximum plus exact prompt bytes.

The same command also passed from a clean wheel installation. That run used
one Ollama call, reported `2,601` tokens, and derived the same `68,834` ceiling.

## Offline verification

- model-assisted compilation checks: `8/8`;
- changed-file parameter-boundary findings: `0`;
- missing key: typed refusal before a provider call;
- hidden prompt without an interactive terminal: typed refusal;
- unsupported OpenCode Go model: typed refusal before a provider call;
- insufficient token ceiling: typed refusal before a provider call;
- direct-value OpenRouter and OpenCode Go parsing: accepted; invalid model
  selection refused without printing the supplied value.

## Limits

The accepted live result proves one Ollama-assisted semantic review. It does
not prove OpenRouter or OpenCode Go availability, full task execution, dataset
selection, model training, or report generation.
