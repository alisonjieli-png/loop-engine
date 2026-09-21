# Review authorisation on every path

Check that each way into a piece of data asks who is calling and whether they may have it, not only the way the page uses.

## When to use it

Use it for every change that adds an endpoint, a background job, an export, an administrative screen or a new way to reach existing data.

## Steps

1. List every entry point to the data: each endpoint, each message consumer, each scheduled job, each report, each console command.
2. For each one, write who may use it and on which records.
3. Check that the identity comes from the session or the signed token, never from a value the caller supplied such as an account number in the request.
4. Check the record level rule, not only the route level rule. Being allowed to read orders is not being allowed to read this order.
5. Check that a missing permission is a refusal, not a default allow, and that an unknown role is refused.
6. Check the listing and search paths. They often return records the detail page would refuse.
7. Check that the same rule is applied when the caller is another service or an agent acting for a user.
8. Add one test per entry point that calls as a user who must be refused.

## Checks

- Every entry point has a written rule and a test that proves a refusal.
- Identity is taken from the session or token, not from request content.
- Record level rules are applied on list, search, export and detail paths alike.
- An unknown or missing role is refused.

## Known-wrong example

A team protects the order detail page correctly. The comma separated export of the same orders takes the account number from a query parameter because it was written as an internal tool and later exposed. Any signed in customer can export any account by changing one number. A list of entry points with a rule for each would have caught the export.

## What to record

- The entry point list with the rule for each.
- The refusal tests and their results.
- Any entry point deliberately left open and why.

## Source

- `src/loop_engine/core/workspace_operations.py`: this repository maps each write or command to an exact effect description, consumes one approval that is bound to that exact effect, and calls the backend at most once.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision eb757bc.
