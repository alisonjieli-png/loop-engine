# Your account

Kind: customer guide to sign-in, personal client tokens and access decisions.

Open [Get started](https://app.baltor.ai/get-started) to create your account.
Enter your email, open the link and choose a password on the confirmation page.
While the service cannot create accounts at once, the same form keeps your
address and we email you the link when your account can be created. Manage your
account at `/account`.

Your browser sign-in and your coding tool's client token are different
credentials. The browser manages your account. The client token authorizes the
specific service operations its scopes allow.

## Create a client token

On `/account`, open Your client tokens and create one for each client or
machine. Give it a label you will recognize. Copy the secret when it is shown;
later listings contain its identity and state, not the secret.

The service stores a digest of the token. An exact replay of its creation
request returns `token` as null, so repeating the request is not a way to
recover the original secret. Keep the token through your client's supported
secret mechanism, as [Get set up](service-getting-set-up.md) explains.

## What controls a download

| Check | What must hold |
| --- | --- |
| Account | The account is enabled and the credential is current. |
| Scope | The credential includes `provisioning:read`. |
| Grant | The account holds access to the selected item and its body. |
| Entitlement | The account has `bodies` access rather than metadata only. |
| Selection | The item still matches the requested digest and permitted filters. |

The service rechecks authorization when it releases the result. An unknown or
inaccessible identity returns `item_unavailable`; it is not listed as material
belonging to another account.

### Entitlements

| Value | Access |
| --- | --- |
| `metadata` | Search, discovery, listing and manifests. |
| `bodies` | Metadata and permitted body downloads. |

A subscription or operator grant supplies the account entitlement. Creating a
token does not upgrade it. An operator grant can make Baltor Pro free for an
account.

### Scopes

| Scope | Service operation |
| --- | --- |
| `provisioning:metadata` | Search, discover, list and manifest. |
| `provisioning:read` | Body reads and downloads. |
| `usage:read` | Your account's usage. |
| `billing:manage` | Authorized checkout and customer portal operations. |
| `access:manage` | Operator access administration. |

A personal client token is limited by the account, browser session and host
policy. It cannot create more client tokens through the customer management
endpoint; that operation requires a browser session.

## Token limits and state

The account page reads `service_client_access_options/v1` from
`/api/v1/account/access`. It shows the available scopes and token policy.

| Policy field | Meaning |
| --- | --- |
| `maximum_active_tokens` | Maximum active tokens. |
| `maximum_lifetime_seconds` | Longest allowed lifetime. |
| `default_lifetime_seconds` | Default requested lifetime. |
| `maximum_token_records` | Limit on retained token records. |

Each token has an expiry and an `active`, `expired` or `revoked` state. The
account page provides a Revoke action. A revoked or expired token is refused
on its next request; material already downloaded is not recalled.

## Confirm which account a client uses

With the environment variable from the setup guide available to your terminal:

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" https://app.baltor.ai/api/v1/session
```

The `service_session/v1` result contains `principal`, `authentication_mode`,
`token_expires_at` and `access_source`. The source is `subscription`,
`operator_grant`, `promotion_code` or `none`, and says what currently covers the
account. Check the principal's `tenant_id`, `entitlement` and scopes
before using a client on a shared machine. Keep credentials out of logs and
support messages.

## Subscription and help

Baltor Pro is $29 a month. Accounts with an operator grant use it free.
When available, the account page opens checkout or the customer portal. Account
creation and checkout are separate capabilities; available checkout does not
mean public registration is open.

Model access and provider charges remain yours. See
[Usage and what you pay for](service-usage-and-what-you-pay-for.md) for download
records, or [Troubleshooting](service-troubleshooting.md) for a refusal.
