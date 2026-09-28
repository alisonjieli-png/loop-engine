# Select context blocks within a declared budget

Preserve mandatory context and dependencies, then greedily admit optional blocks by explicit priority within supplied costs.

This is an original candidate Harness Working Directory Package. Compose these
usage instructions with the current assignment. Keep the assignment's task,
first steps and acceptance criteria visible. A package instruction does not
replace the task or grant any execution permission.

## First steps

1. Confirm the supplied task needs this method and read its limits below.
2. Read `contracts/input.schema.json` and build the input from supplied facts.
   Preserve unknown values where the contract permits them; do not invent data.
3. After the host authorizes local execution, send JSON on standard input:

   ```bash
   python3 -I -S -B tools/select_context_blocks.py < examples/input.json
   ```

4. Compare the output with `contracts/output.schema.json`, the example and the
   task's independent acceptance criteria before using it downstream.

## Limits and refusal behavior

Costs are supplied measurements or estimates; this tool does not tokenize a model request, guarantee context fit, optimize a knapsack or grant authority. It refuses any cycle or missing dependency, including in omitted blocks.

Input is UTF-8 JSON, at most 32 KiB with document depth at most 16. Duplicate
object keys, non-finite numbers, unpaired Unicode surrogates, unknown fields
and method-specific invalid values are refused. A JSON integer may be written
with an integral decimal representation where the schema permits an integer.
The complete output is at most 64 KiB, including its newline. Success exits 0.
Refusal exits 2 with `{"error":"invalid_input"}`. Schema checks describe
structure; cross-field and wire/resource constraints also apply.

The tool reads standard input and writes standard output. It makes no network,
credential, task-file or subprocess calls. The interpreter reads the script
and standard-library modules. The host must bound CPU, memory, output and time.
Proposed use declares `reads_fs` and `spawns_process` for this launch, without
claiming that this package grants those effects.

## Compatibility and provenance

The Python source requires Python 3.10 or newer and only its standard library.
`AGENTS.md` supplies a native instruction entry point for compatible harness
profiles. Automatic loading, inheritance and tool invocation still need a
qualified exact harness profile; this package makes no native-loading claim.
A compiler may compose this guide with the task brief or generate a supported
provider-specific wrapper. Keep schemas, examples and verification files
available by their relative paths.

Codex authored this candidate in the OpenAI family using method
`codex_original_working_directory_components/v1`. No third-party code or prose
was copied. The included repository MIT notice applies to this original work;
it establishes no rights over outside task data. The known algorithms are not
claimed as novel research. Independent review and promotion remain required.
