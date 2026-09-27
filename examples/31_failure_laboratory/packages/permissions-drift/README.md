# Permissions drift

The skill pre-approves shell commands and a web fetch, while the item record
declares only that it reads files. A customer who allows only file reading
would install a skill that runs `git push` without a prompt. The declared
effects of an item must cover everything its files ask a harness to allow.

Expected refusal codes: `authority_exceeds_declared_effects`.
