# Taking payments: the exact steps only you can do

Kind: owner instructions. Everything else about payments is engineering work
and is being built and qualified in test mode. This document lists the small
number of actions that need you, because they need your identity, your bank
and your legal agreement.

The plan is one subscription, Baltor Pro, at 29 United States dollars each
month. Search stays free and the measured unit is one downloaded item.
Invited beta users are not charged.

## What is true today

Observed on October 5, 2026, reading the live account through its interface
with GET requests only. Steps 1 to 4 below were completed on September 21,
2026 and are kept as the record of how.

| Fact | State |
|---|---|
| Live account | `acct_1UHZ972IF9bCskLc`, charges and payouts enabled, nothing outstanding |
| What is sold | Baltor Pro, one active price, 29 United States dollars a month |
| Customer portal | cancels at the end of the paid month, updates the card, shows every invoice; your privacy and terms addresses are set |
| Payment notifications | one endpoint, enabled, for exactly the five events the service reads |
| Customers and subscriptions | none yet, so nobody has been charged |
| How the account sells | through Stripe's Managed Payments: Stripe, as Link, is the seller of record |

What Managed Payments means for your customers, from
<https://docs.stripe.com/payments/managed-payments/how-it-works>: checkout
says "Sold through Link" and adds sales tax for the customer's billing address
before they pay; Link emails the payment confirmation, the invoice and any
refund notice for every charge with the PDF attached, whatever your own email
settings in the Dashboard say; the card statement reads
`LINK.COM* BALTOR.AI`; customers can also cancel or change their subscription
on link.com, and Baltor follows that change through the same notifications.
Link support answers payment questions and may contact you about one. If you
do not answer within 48 hours, Stripe may refund the customer without asking
you.

## The two things only you can do now

1. **Keep your support email address current.** Open
   <https://dashboard.stripe.com/settings/business-details>. Link support sends
   every escalation about a Baltor payment to this address, and the 48 hours
   start when it is sent.
2. **Choose your renewal reminders.** Open
   <https://dashboard.stripe.com/settings/billing/subscriptions>. With
   Upcoming renewals switched on, Stripe emails each customer before every
   monthly renewal; switched off, it emails only before the yearly
   anniversary. Engineering's choice, if you leave it: switch it on, because a
   reminder before each charge prevents disputes from people who forgot they
   subscribed.

Everything else about taking payments is in place, and a customer paying
through the website is the product working.

## Step 1: know which account will take real money

Stripe keeps practice and real money apart. An account or workspace whose
name ends in sandbox is for practice only. It can never charge a real card,
and nothing created inside it moves to the real account. That is a feature,
not a problem: it is why engineering can build and test the whole payment
journey without touching money.

Open <https://dashboard.stripe.com/> and look at the account switcher at the
top left.

- If you see an entry marked Sandbox and a separate main account, the main
  account is the one that will take real money. Use it in step 2.
- If you only see the sandbox, create the real account from the same menu.
  Choose the country where your business banks.

Send back only the account name you chose. Engineering does not need its
identifier to continue.

## Step 2: activate that account

In the real account, open <https://dashboard.stripe.com/settings/account> and
complete activation. Stripe asks for, roughly in this order:

1. **Business type.** Individual or sole trader is a valid answer if you have
   no company yet. You can change it later.
2. **Your identity.** Legal name, date of birth, home address, and in the
   United States the last four digits of your social security number. Stripe
   may ask you to photograph an identity document.
3. **Business details.** A description of what you sell, your website and a
   support contact.
   - For the description, this is accurate: a subscription that gives
     developers access to reviewed material for coding tools.
   - For the website, use `https://baltor.ai`.
   - The support contact must be an address you read. Tell engineering which
     address you chose, and it will be published on the site and in the
     privacy notice.
4. **Statement descriptor.** The short text a customer sees on a card
     statement. `BALTOR` is a good choice. Keep it recognisable, or you will
     get disputes from people who do not recognise the charge.
5. **Bank account.** Where Stripe pays you. It must be in your name or your
   company's name.

Stripe usually answers within minutes, sometimes a day. Activation is not
instant in every country.

## Step 3: make a restricted key for the real account and store it

Do not create a full secret key, and do not paste any key into a chat window.

1. In the **real, activated** account, switch the dashboard out of test mode.
2. Open <https://dashboard.stripe.com/apikeys> and choose Create restricted
   key.
3. Name it `baltor-service-live`.
4. Give it **write** permission for exactly these resources, and leave every
   other permission at none:
   - Customers
   - Checkout Sessions
   - Billing Portal Sessions
   - Subscriptions
   - Prices
   - Products
   - Webhook Endpoints
5. Create the key and copy it. It begins with `rk_live_`.
6. On this workstation, in a terminal, run:

   ```bash
   cd /home/username/loop-engine
   python3 tools/operator_credentials.py store --ref stripe-live
   ```

   It asks for the key with the typing hidden, saves it in the system
   keyring, and prints only a confirmation. The value never reaches a
   command line, a file, a log or a chat window. An existing credential is
   never overwritten.

The slot refuses anything that is not a restricted live key. A full secret
live key, a test key and a restricted test key are all rejected, so a
mistake here cannot hand over the whole account.

## Step 4: tell engineering to switch payments on

Say that the live key is stored. Engineering then, in order:

1. Creates the product, the price, the customer portal configuration and the
   webhook endpoint in the real account, with the same command already used
   in test mode.
2. Puts the live key and the webhook signing secret into the deployment as
   references, never as values.
3. Runs one real subscription through the site with a real card, cancels it
   and confirms the refund.
4. Reports what happened before any customer is invited to pay.

## What you do not need to do

You do not need to create products, prices, a customer portal or a webhook
by hand. You do not need to find any identifier or secret for engineering.
You do not need to configure anything in the dashboard beyond activation.

## If you would rather not activate yet

Everything except real charging works without it. Invited people can sign
in, create client keys, connect their tools and use the catalogue. The paid
plan simply stays closed, and the site says so. Nothing in the rest of the
work waits on this.
