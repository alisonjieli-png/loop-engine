# Sources of the model directory

Kind: source record, September 27, 2026. It names each source the builder
reads, the licence or terms that allow it and the day they were checked, what
the directory takes from it, the publishers it links to without copying, and
the corrections made to reviewed facts. The pages show the same list with the
day each source was last read.

The rule since September 27, 2026: the directory republishes values only from
sources that are openly licensed or documented for programmatic use. A
publisher whose terms forbid copying is linked and never copied.

## Read by the builder

| Source | Address | Licence or terms, and the day checked | Taken |
|---|---|---|---|
| Hugging Face Hub API | `huggingface.co/api/models` | The Hub API is documented for programmatic use, the terms of service do not restrict it, and the robots file allows every path (read September 24, 2026). The builder stays under the anonymous limit the API announces in its response headers. Each model card declares the model's own licence. | Licence, safetensors parameter count, publication date, downloads, likes, task, chat template, configuration files and GGUF file lists with sizes. |
| models.dev | `models.dev/api.json` | MIT. The repository moved from `sst/models.dev` to `github.com/anomalyco/models.dev`; its LICENSE was read on September 27, 2026. | Provider prices with each record's own date, the limits and capabilities of the makers' own APIs, release dates, and each provider's documented address and key variable. |
| LiteLLM model price and context file | `raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` | MIT. The repository's LICENSE puts everything outside `enterprise/` under the MIT licence, and the file sits at the root; read September 27, 2026. | Provider prices as listed on the day the file was read, and, from the maker's own entry only, input and output limits and the function calling, response schema and reasoning flags. |
| LMArena leaderboard dataset | `datasets-server.huggingface.co/rows`, dataset `lmarena-ai/leaderboard-dataset`, subset `text_style_control`, split `latest` | CC BY 4.0, declared in the dataset card; read September 27, 2026. The licence asks for credit, a link to the licence and a note of changes. The pages name LMArena, link the licence, and say the score is the overall category, rounded to a whole number. | The overall text arena score with style control, for a hosted row whose maker the arena names with exactly the same model identifier. |
| Baltor provider records | `src/loop_engine/core/*_client.py` | Baltor's own source. | Output limits that Baltor's provider clients declare or observed, with the day of each. |
| Reviewed provider and runtime documentation | `tools/model_directory/provider_documentation.json` | Each provider's public documentation, read by a person on the day each fact names. | API styles and addresses, authentication, structured output, tool calling, rate-limit, price and data-policy pages, runtime start commands, and what each harness reads. |
| Hardware vendor pages | `tools/model_directory/hardware.json` | Public specification pages of NVIDIA, AMD and Apple, read by a person on the day given. | Memory and memory bandwidth of each hardware preset. |

Joins are exact. A models.dev offer or a LiteLLM entry joins an open model
only when its model identifier equals the Hugging Face repository, ignoring
case, and brings that provider's price only. The maker's own LiteLLM entry
joins a hosted model only when it names exactly the model identifier in the
maker's models.dev list. An arena score joins a hosted model only when the
arena's organization maps to that maker in the reviewed record and the arena's
model name equals the maker's model identifier. When models.dev and LiteLLM
both price one provider for one model, the models.dev price is kept.

models.dev and LiteLLM each keep a list of OpenRouter's own prices among their
providers. Those values are part of the two openly licensed records and are
shown as those records state them, with the record named as the source. The
builder reads nothing from OpenRouter itself.

## Linked, never copied

| Publisher | Why |
|---|---|
| Ollama library, `ollama.com/library` | Ollama's terms of service, updated May 2026, refuse "automated means to access our services without permission". The pages link to it and to `ollama run hf.co/...`, which Hugging Face documents, and copy nothing from it. |
| OpenRouter, every interface | Section 7 of OpenRouter's terms, updated August 31, 2026, refuses software that will "scrape or copy any information on the Site or the Services" and access "for purposes of reselling API access to Models or otherwise developing a competing service" (as read on September 27, 2026 for the shared research service landscape record). Until September 27, 2026 the builder read OpenRouter's Models API and its per-model endpoints interface. It reads neither now, and the reader refuses any row that names them. The pages link to openrouter.ai, and to a model's page there when an open record names the model's OpenRouter identifier. |
| Artificial Analysis | Its website terms, dated April 28, 2024, grant only "personal, noncommercial use" and forbid building "a similar or competitive website, product, or service" (as read on September 27, 2026 for the same record). Its indexes reached the directory inside OpenRouter's answer until September 27, 2026. The reader now refuses any value it published, and the pages link to it. |

## Checked and not read yet

| Source | Licence, checked September 27, 2026 | Why it is not read yet |
|---|---|---|
| Portkey models, `github.com/Portkey-AI/models` | MIT | Its prices, in cents per token, cover the providers that models.dev and LiteLLM already cover, so a third list would add duplicate prices without filling a gap. It becomes an engine when a provider it lists has no price in the other two. |
| Epoch AI Benchmarking Hub, `epoch.ai/benchmarks` | CC BY 4.0 for Epoch AI's own runs. Results from external projects keep their original licences. | Adopting it needs a licence gate for each benchmark, so that only Epoch AI's own runs are republished, and a reader for its archive of CSV files. Its model names still need an exact join. |

## Corrections

- Ollama Cloud structured output, corrected September 27, 2026. The reviewed
  record said supported, citing `docs.ollama.com/capabilities/structured-outputs`
  as read on September 24. The source of that page in Ollama's repository,
  `github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx`,
  opens with "Ollama's Cloud currently does not support structured outputs."
  The commit of April 22, 2026 (`3b43b9bc`) added that note, and issue 12362,
  "JSON reply schema is ignored by Cloud model", has been open since September
  21, 2025. The record now says no, cites the repository source and links the
  issue. models.dev lists structured output as true for 8 of its 24 Ollama
  Cloud models; the directory takes no capability fact from a per-model record
  of a service other than the maker's own API, so that value does not reach the
  pages.

## Rules every row meets

The service's reader, `src/loop_engine/core/service_runtime/model_directory.py`,
and the builder apply the same rules, and `tools/test_model_directory.py`
holds each one with a known-wrong case:

- every row names each source address it uses and the day it was read;
- a row that names a refused source (OpenRouter, its endpoints interface or
  Artificial Analysis) is refused whole, and the builder exits 1;
- a source read by script names an address on that source's own hosts;
- a price comes only from models.dev or LiteLLM, and a published result
  carries a value only from LMArena, never a value that a linked-only
  publisher published;
- every fact names its source; a fact no source states is left out and the
  page shows Unknown;
- a price carries the date it applies to, and a price older than 30 days is
  marked beside its date;
- an estimate says it is one, and the memory formula is shown on the page;
- every row carries a `commercial_relationship` with kind none, and no order,
  filter, inclusion rule or hardware fit reads it.
