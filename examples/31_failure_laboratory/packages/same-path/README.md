# Two packages that write the same path

Two command packages both install `review.md` into the commands folder, with
different bytes. Each package is correct alone. Installed together, the second
replaces the first, or an installer that refuses to overwrite stops halfway.
The check reports this as a collision of the set, never as a refusal of
either package.

Expected refusal codes: `target_path_collision`.
