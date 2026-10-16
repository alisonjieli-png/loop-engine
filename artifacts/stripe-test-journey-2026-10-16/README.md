# Paid path in Stripe test mode and live configuration, October 16, 2026

Kind: dated verification record. It repeats the
[October 5 run](../stripe-test-journey-2026-10-05/) on the source of public
`main` at `7a13618e` before launch, after the October 11 price change. The
service code is the code of the running release 93.

## Results

| Part | Steps passed | What it covers |
| --- | ---: | --- |
| Checkout | 18 of 18 | Email sign-up, refusal of a download before payment over HTTP and MCP, the plans record, the one Stripe customer, payment on the Stripe-hosted page with a test card, signed webhook events granting downloads, downloads over HTTP and MCP recorded as usage, the portal listing the paid invoice and cancelling at the period end, access until then, and refund and deletion ending access |
| Renewal | 6 of 6 | A test clock passes the end of the paid month; access continues while the renewal invoice is a draft, and the paid renewal extends it |
| Failed renewal | 6 of 6 | A declined card at renewal makes the subscription past due and access ends |

Each part ran the real service on a loopback socket, composed by the host
loader the deployment uses, against the Stripe test environment through
`tools/check_stripe_test_journey.py`. No live charge was made.

## Live configuration, read only

`live-stripe-read-only.json` was read with GET requests only. The live
account can charge and pay out and has no requirement due. The webhook
endpoint `https://app.baltor.ai/api/v1/billing/webhook` is enabled for the
five subscription and invoice events the service reads. The default portal
configuration cancels at the period end and shows invoice history, privacy
and terms links.

Two recurring prices are active: the $49 Pro price that new checkout uses
(`baltor_pro_monthly_usd_49_20261011`) and the earlier $29 Pro price that
existing subscriptions would keep. No subscription of any status exists yet.
No live $9 or $99 price exists. That matches the pricing page: Basic is free
through December 31, 2026 with no automatic charge, and Max is a public
preview whose checkout the service refuses before any customer effect.
Before January 1, 2027, Basic needs its live price or a longer free period.
