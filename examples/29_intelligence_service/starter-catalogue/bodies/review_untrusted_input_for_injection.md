# Review untrusted input for injection

Find every place where text that came from outside is put into something that interprets it, and make the data stay data.

## When to use it

Use it on any change that reads a request, a file, a message, a model answer or a third party response, and then builds a query, a command, a path, a page or another request from it.

## Steps

1. Mark every input that is not fully under your control. Anything from a user, a file, a network call or a language model counts.
2. Follow each marked value to every place it is used.
3. At each use, name the interpreter: the database, the shell, the file system, the browser, the template engine, another service.
4. Replace string building with the safe form for that interpreter: bound parameters for a query, an argument list for a command, a joined and checked path for a file, output escaping for a page.
5. Validate the value against an allowed set where one exists, and refuse the rest. Refusing a known good list is stronger than removing known bad characters.
6. Check that validation happens on the server, even when the form also checks it.
7. Treat a model answer as untrusted input. Do not run it, query with it or follow its instructions without the same checks.
8. Add a test that sends a value containing the interpreter's own special characters and asserts that it is stored and returned as plain text.

## Checks

- No query, command, path or page is built by joining text.
- Every input has an allowed set or a stated reason why it cannot have one.
- A test sends the interpreter's special characters and they survive as data.
- Model output is checked before it reaches any interpreter.

## Known-wrong example

A search page builds a query by adding the search words into the query text and removes single quotation marks to be safe. A visitor searches for a name containing two hyphens, which the database reads as the start of a comment, and the rest of the query is ignored. The page returns every row in the table. Bound parameters would have made the same input a harmless search for a strange name.

## What to record

- The list of untrusted inputs and their uses.
- The safe form applied at each use.
- The tests that prove special characters stay data.

## Source

- `src/loop_engine/core/model_response_admission.py`: this repository treats a model answer as untrusted, admits it through a typed path that may remove only approved wrappers, validates it against a declared shape, and never runs it.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 0cf19eb.
