# Tactical Hermes read-only discovery

September 23, 2026. Zero model calls, zero credentials sent.

- `configuration-inspection.json`: source hashes and safe configuration presence.
- `unauthenticated-model-listing.json`: default TLS certificate failure.
- `ca-verified-unauthenticated-model-listing.json`: published CA used with hostname
  validation; hostname mismatch still refuses the metadata request.
- `server-certificate-observation.txt`: public leaf identity, dates, SANs and hash.
- `cloudflare-origin-ca-rsa.pem`: public CA certificate, not a secret or private key.
- `ca-source-attempts.json`: successful official source download and digest.

An earlier download of the same CA URL without a browser user agent returned HTTP
403. No insecure retry occurred. The certificate's other domain was not contacted.
No model identity, model capacity or family is qualified by these failed reads.
The original source inspection precedes the final custom-adapter repair, so its
custom_endpoint source hash identifies that intermediate working tree exactly.

See the [binding proposal](../../docs/verification/TACTICAL-HERMES-PROVIDER-BINDING-2026-09-23.md).
