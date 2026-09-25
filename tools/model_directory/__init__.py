"""The public model and endpoint directory, built from outside sources.

Kind: development tool package. It reads public, documented sources, merges them into one row per
model and one row per endpoint, refuses any row that does not keep its sources, and writes the
packaged files the service serves at `/models`, `/endpoints` and `/can-i-run`. It serves nothing
itself, holds no credential and changes nothing outside its state folder and the packaged files.
The command is `tools/build_model_directory.py`; `SOURCES.md` records each source's terms.

Functional component and its engines:

```text
Model directory build (functional component)
├── Edge: source records in; model_directory_models/v1, model_directory_endpoints/v1,
│   model_directory_hardware/v1, the two browser indexes and model_directory_manifest/v1 out
├── Source engine slot, each read through the bounded read-only HTTPS transport
│   ├── openrouter: the OpenRouter Models API and its per-model endpoints API
│   ├── huggingface: the Hugging Face Hub API, model configurations and GGUF file lists
│   ├── modelsdev: the models.dev api.json, MIT licensed, for direct provider prices
│   ├── baltor_records: the source-backed output limits in src/loop_engine provider clients
│   ├── provider_documentation: provider and runtime facts a person read and dated
│   └── ollama_library: not an engine; Ollama's terms refuse automated access, so pages link
├── Rules engine: loop_engine.core.service_runtime.model_directory, shared with the service
└── Fit engine: loop_engine.core.service_runtime.model_directory_fit, shared with the pages
```

Every row keeps its sources with the date each was read. A source that cannot be read keeps its
previous rows with their old dates, so a failed day never erases data and never pretends to be new.
"""
