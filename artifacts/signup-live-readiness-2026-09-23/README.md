# Read-only live signup readiness

September 23, 2026. Observations use public GET endpoints, named credential
helpers, Fly secret-name listing, and one allowlisted read of `/data/host.json`.
No account/setting mutation, signup, login, message, payment, OAuth refresh or
TLS weakening occurred. No secret value is stored in these artifacts.

- `public-state-1.json`: Baltor public capability/identity and Supabase public
  settings, with the publishable key omitted.
- `host-state-1.json`: selected host flags/origins, email-block absence and
  Boolean environment-name presence; no raw host contents.
- `fly-secret-names.json`: Fly's name/digest/deployment-state list, not values.
- `credential-presence-1.json`: selected named local references and OAuth expiry
  status; no OAuth resolution/refresh performed.
- `sender-domain-readiness-1.json`: one Resend domain-list GET returned 401;
  domain status and sending permission remain unestablished.
- `source-bindings.json`: exact instruction/helper/guide sources inspected.
- `read_public_state.py`, `read_host_state.py`, `read_sender_domains.py`: narrow
  observation scripts. Each refuses to overwrite its original evidence file.

The first web browsing tool could not retrieve the Baltor API URLs. The direct
bounded HTTP client then succeeded with ordinary TLS verification and
`trust_env=False`; that was not a TLS bypass. All Fly access went through
`tools/fly_operator.py`; API credential resolution used
`tools/operator_credentials.py` references. The latter's OAuth refresh path was
deliberately not called.

The [verification report](../../docs/verification/SIGNUP-LIVE-READINESS-READONLY-2026-09-23.md)
separates observed facts from unavailable management/sender/password gates.
Create new dated observation paths for a successor; do not edit historical
readiness bytes into a claim that a later state was already observed.
