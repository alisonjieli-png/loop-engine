# Delimited-block draft format

September 24, 2026, United States Eastern. The generator gains a second
draft format, `original_native_file_blocks/v1`, for every producer. Each
planned file travels in its own block with its path and no JSON escaping,
after a two-line header. The JSON format stays the default. The run chooses
the format with `--draft-format`, and `run.json` names it.

- The prompt resource is
  `tools/resources/original-native-generation-blocks-prompt-v1.json`, bundle
  `original_native_generation_blocks` 1.0.0.
- The strict reader refuses, each with its own code: an unterminated block,
  a duplicate path, a path escaping the package, an unplanned path, content
  outside blocks or after the END line, a missing header or END line, an
  empty file and a missing planned file. One exact enclosing Markdown fence
  may be removed, and the completion records it.
- `check_removed_guards.py` removes each of 12 guards in memory. Every
  control is detected (`removed-guards-*.json`). No provider is called.
