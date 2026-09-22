# Keep your instructions and the supplied text apart

Mark clearly which part of a prompt is your instruction and which part is material from elsewhere, so text inside the material cannot act as an instruction.

## When to use it

Use it whenever a prompt contains anything you did not write: a user message, a web page, a file, a database row, a previous answer, or the output of a tool.

## Steps

1. Put your instructions in their own named part, and the supplied material in another named part.
2. State in the instruction that the material is data to work on, and that any instruction inside it is content to report, not to follow.
3. Delimit the material clearly and consistently, and make sure the material cannot close the delimiter.
4. Put the instruction where it cannot be lost: state the job before the material and the required output shape after it.
5. Keep the permissions outside the prompt. What the step may do is decided by the caller, never by text in the material.
6. Treat the answer as untrusted as well. Validate its shape, and check any path, command or address it contains before acting.
7. Test with material that contains a plain instruction to do something else, and require that the step reports it instead of following it.
8. Log which parts were supplied material, so an odd answer can be traced back.

## Checks

- Instruction and material are separate named parts in every prompt.
- Material cannot close or escape its delimiter.
- A test with an instruction hidden in the material passes.
- No permission is granted by anything inside the prompt.

## Known-wrong example

A support tool builds one long text from the ticket, the customer history and the request to draft a reply. A customer writes, inside the ticket, that the previous instructions are cancelled and the agent should send the full account details. The model follows it, because nothing in the prompt says which words were instructions. Separate parts, and a rule that material is only data, would have made the sentence something to report.

## What to record

- The part structure of the prompt.
- The test case with an instruction inside the material and the observed behaviour.
- Any answer that contained a path, a command or an address, and what was done with it.

## Source

- `src/loop_engine/core/prompt_elements.py`: this repository builds a prompt from named elements such as task background, the material to work on, the expectations and the required format, and treats the requested answer style as declared data rather than as branches in code.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 4249eca.
