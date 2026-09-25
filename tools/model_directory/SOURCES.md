# Sources of the model directory

Kind: source record, September 24, 2026. It names each source the builder
reads, the terms that allow it, what the directory takes from it, and the
sources it does not read. The pages show the same list with the day each
source was last read.

## Read by the builder

| Source | Address | Terms, read September 24, 2026 | Taken |
|---|---|---|---|
| OpenRouter Models API | `openrouter.ai/api/v1/models` | OpenRouter's models guide says its Models API "makes the most important information about all LLMs freely available". The builder reads only that documented interface and its per-model endpoints interface, once a day, never the website pages that the terms protect from scraping. | Context length, output limit, supported parameters, reasoning controls, knowledge cutoff, the Artificial Analysis indexes the API carries, and the price of each provider route on OpenRouter. |
| Hugging Face Hub API | `huggingface.co/api/models` | The Hub API is documented for programmatic use, the terms of service do not restrict it, and the robots file allows every path. The builder stays under the anonymous limit the API announces in its response headers. | Licence, safetensors parameter count, publication date, downloads, likes, task, chat template, configuration files and GGUF file lists with sizes. |
| models.dev | `models.dev/api.json` | The database is published under the MIT licence in `github.com/sst/models.dev`. | Direct provider prices with the record's own date, limits, capabilities, release dates, and each provider's documented address and key variable. |
| Baltor provider records | `src/loop_engine/core/*_client.py` | Baltor's own source. | Output limits that Baltor's provider clients declare or observed, with the day of each. |
| Reviewed provider and runtime documentation | `tools/model_directory/provider_documentation.json` | Each provider's public documentation, read by a person on the day each fact names. | API styles and addresses, authentication, structured output, tool calling, rate-limit, price and data-policy pages, runtime start commands, and what each harness reads. |
| Hardware vendor pages | `tools/model_directory/hardware.json` | Public specification pages of NVIDIA, AMD and Apple, read by a person on the day given. | Memory and memory bandwidth of each hardware preset. |

## Not read

| Source | Why |
|---|---|
| Ollama library, `ollama.com/library` | Ollama's terms of service, updated May 2026, refuse "automated means to access our services without permission". The pages link to it and to `ollama run hf.co/...`, which Hugging Face documents, and copy nothing from it. |
| OpenRouter website pages | Section 7 of OpenRouter's terms, updated August 31, 2026, refuses software that scrapes or copies information on the site. Only the documented Models API is read. |
| Benchmark leaderboards | A result another party published is linked with its publisher's name, never copied as Baltor's own claim. Only the indexes the OpenRouter Models API carries are shown, with their publisher. |

## Rules every row meets

The service's reader, `src/loop_engine/core/service_runtime/model_directory.py`,
and the builder apply the same rules, and `tools/test_model_directory.py`
holds each one with a known-wrong case:

- every row names each source address it uses and the day it was read;
- every fact names its source; a fact no source states is left out and the
  page shows Unknown;
- a price carries the date it applies to, and a price older than 30 days is
  marked beside its date;
- an estimate says it is one, and the memory formula is shown on the page;
- every row carries a `commercial_relationship` with kind none, and no order,
  filter, inclusion rule or hardware fit reads it.
