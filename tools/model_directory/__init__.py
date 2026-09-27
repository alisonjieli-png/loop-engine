"""The public model and endpoint directory, built from outside sources.

Kind: development tool package. It reads public, documented sources, merges them into one row per
model and one row per endpoint, refuses any row that does not keep its sources, and writes the
packaged files the service serves at `/models`, `/endpoints` and `/can-i-run`. It serves nothing
itself, holds no credential and changes nothing outside its state folder and the packaged files.
The command is `tools/build_model_directory.py`; `SOURCES.md` records each source's terms.

Functional component and its engines:

```text
Model directory build (functional component)
├── Edge: source records in; model_directory_models/v2, model_directory_endpoints/v2,
│   model_directory_hardware/v1, model_directory_moved/v1, the two browser indexes and
│   model_directory_manifest/v2 out
├── Source engine slot, each read through the bounded read-only HTTPS transport
│   ├── huggingface: the Hugging Face Hub API, model configurations and GGUF file lists
│   ├── modelsdev: the models.dev api.json, MIT licensed, for provider prices and the makers' own APIs
│   ├── litellm: LiteLLM's model price and context file, MIT licensed, for prices, limits and flags
│   ├── lmarena: the LMArena leaderboard dataset, CC BY 4.0, for the overall text arena score
│   ├── baltor_records: the source-backed output limits in src/loop_engine provider clients
│   ├── provider_documentation: provider and runtime facts a person read and dated
│   └── linked only, never read: the Ollama library, OpenRouter and Artificial Analysis, whose
│       terms refuse automated access or republication
├── Rules engine: loop_engine.core.service_runtime.model_directory, shared with the service; it
│   refuses a row that names a refused source
├── Fit engine: loop_engine.core.service_runtime.model_directory_fit, shared with the pages
└── Moved addresses: model_directory.moved compares the rows a build replaces with the rows it
    writes, so each address served once is redirected to where it moved or answers 410 Gone
```

Every row keeps its sources with the date each was read. A source that cannot be read keeps its
previous rows with their old dates, so a failed day never erases data and never pretends to be new.
"""
