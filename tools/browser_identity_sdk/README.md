# Browser identity library build

Kind: build-time dependency source for the hosted account interface.
The package versions and lockfile pin the upstream Supabase browser client.
The generated bundle is shipped as a same-origin service asset. It is not a
Loop runtime, identity issuer or second account store.

Run `npm ci --ignore-scripts` in this directory, then `npm run build`.
The entry exports the upstream client constructor only. Host-approved account
configuration supplies the project origin and publishable key at runtime.
Never bundle a server secret or enable persistent browser credential storage.
