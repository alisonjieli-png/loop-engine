# JSON Review Algorithm

## Logic Flow
1. **Ingestion**: Read up to 1MiB from `stdin`.
2. **Parsing**: Use `json.loads` with a custom `object_pairs_hook`. This hook is critical for detecting duplicate keys in a single pass without extra complexity.
3. **Traversal**: Perform a single recursive depth-first traversal of the resulting Python object.
4. **Counting**: During traversal, increment counters for each primitive type.
5. **Validation**:
   - If `depth > 32`, immediately raise `ERR_DEPTH`.
   - If a number is encountered, check `math.isfinite()`. If not, raise `ERR_NONFINITE_NUMBER`.
6. **Output**: Return a JSON object containing the summary or the error code.

## Complexity
- **Time**: $O(N)$ where $N$ is the number of characters in the input.
- **Space**: $O(D)$ where $D$ is the maximum depth of the JSON (stack space).

## Known Limitations
- The tool does not validate JSON Schema, only structural integrity and type distribution.
- It does not perform any filesystem or network operations, making it safe for sandboxed execution.
- It treats `true`/`false` as booleans, distinct from `1`/`0`.
