# Drop-in extensions

This example shows the added-file layout. Discovery does not call a provider,
execute capability code, admit a skill, or promote intelligence.

```text
example_extension/
├── providers/
│   └── free_gateway.yaml
├── capabilities/
│   └── summarize.yaml
├── skills/
│   └── summary-skill/
│       └── SKILL.md
├── plugins/
│   └── summary-plugin/
│       └── loop-engine-plugin.json
└── intelligence/
    └── context/
        └── plugin/
            ├── manifest.yaml
            └── records.jsonl
```

Run the inspection without a provider call:

```bash
python3 examples/23_drop_in_extensions/run.py

loop-engine extensions discover \
  --extension-root examples/23_drop_in_extensions/example_extension
```

The provider route stays inactive until both environment values exist:

```bash
export EXAMPLE_GATEWAY_BASE_URL="https://gateway.example/v1"
export EXAMPLE_GATEWAY_API_KEY="replace-with-a-real-key"

loop-engine models inventory \
  --extension-root examples/23_drop_in_extensions/example_extension
```

The URL is illustrative. Do not probe it. Replace it with a provider's real
documented endpoint and source-backed maximum-output record.

Capability, skill, and intelligence files remain candidates. Their normal
admission and review paths still apply.
