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

The command accepts a credential by reference or through a hidden prompt:

- `OLLAMA_API_KEY` for `ollama_cloud`;
- `OPENROUTER_API_KEY` for `openrouter`;
- `OPENCODE_GO_API_KEY` for the direct `opencode_go` API route;
- `--provider-key-env ENV_NAME` for another environment-variable name;
- `--prompt-for-provider-key` for an interactive no-echo prompt.

There is no raw `--api-key VALUE` option. The key is installed in the process
environment only for the provider call and the prior value is restored. The
compiled output, model review, provider description, and failure result do not
contain the key.

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
- provider-reported tokens: `1,092`;
- review status: `ready`;
- delegated choices: `dataset_source`, `target_column`;
- user questions in autonomous mode: `0`;
- raw provider key in command output: absent.

The same command also passed from a clean wheel installation. That run used
one Ollama call and reported `1,740` tokens.

## Offline verification

- model-assisted compilation checks: `6/6`;
- changed-file parameter-boundary findings: `0`;
- missing key: typed refusal before a provider call;
- hidden prompt without an interactive terminal: typed refusal;
- unsupported OpenCode Go model: typed refusal before a provider call;
- insufficient token ceiling: typed refusal before a provider call.

## Limits

The accepted live result proves one Ollama-assisted semantic review. It does
not prove OpenRouter or OpenCode Go availability, full task execution, dataset
selection, model training, or report generation.
