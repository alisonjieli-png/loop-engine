# Normalize website addresses and keep the path as written

Bring website addresses to one form: a scheme, a lower case host and no trailing slash. Never change the case of the path.

## When to use it

Use it on website columns that mix `Example.COM`, `http://www.example.com/` and `https://example.com/Docs`. Use it before comparing, joining or counting by website.

## Steps

1. Leave null markers unchanged. Leave a value with a space inside unchanged at confidence 0.3 with the reason `whitespace_inside_url`.
2. When no scheme is present, add the declared default scheme. The default is `https`. This lowers the confidence to 0.9.
3. Split the address into scheme, host, port, path, query and fragment. Drop a user name and password written before the host.
4. Write the scheme and the host in lower case. Keep the path, the query and the fragment exactly as written.
5. Remove a leading `www.` only when that option is switched on. It is off by default.
6. Validate the host. It needs at least two labels. Each label holds letters, digits and inner hyphens. The last label holds only letters. An invalid host leaves the value unchanged at 0.3 with the reason `invalid_host`.
7. Remove a trailing slash from the path. A path of `/` alone becomes empty. This option is on by default.
8. A changed value has confidence 0.95, or 0.9 when the scheme was added.

## Checks

- `Example.COM/Path/Page?Q=1` becomes `https://example.com/Path/Page?Q=1` at 0.9.
- `HTTP://WWW.Example.com/` becomes `http://www.example.com` at 0.95, and `http://example.com` when `www.` removal is on.
- A port is kept.
- `example` alone is unchanged and escalated.

## Known-wrong example

A script writes the whole address in lower case. `https://example.com/Docs/Guide` becomes `https://example.com/docs/guide`. Many servers treat paths as case sensitive, so the new address can point to a different page or to none. Only the scheme and the host are safe to write in lower case.

## What to record

- The default scheme and the two options that were used.
- Each rewrite with its reasons, and each value left unchanged with `invalid_host` or `whitespace_inside_url`.

## Source

- `src/loop_engine/code_nodes/text_conformance_operations.py`: `website_normalize`.

Licence: MIT. Compiled from revision f29bddc. The operations module uses only the Python standard library.
