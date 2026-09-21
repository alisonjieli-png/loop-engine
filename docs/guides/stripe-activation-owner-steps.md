# Taking payments: the exact steps only you can do

Kind: owner instructions. Everything else about payments is engineering work
and is being built and qualified in test mode. This document lists the small
number of actions that need you, because they need your identity, your bank
and your legal agreement.

The plan is one subscription, Baltor Pro, at 29 United States dollars each
month. Search stays free and the measured unit is one downloaded item.
Invited beta users are not charged.

## What is true today

Observed on September 21, 2026 by reading the account through its interface.

| Fact | State |
|---|---|
| Account reached by the stored test credential | `acct_1UHZ9KCCxLfArYED`, display name Baltor sandbox |
| Products in it | None |
| Prices in it | None |
| Webhook endpoints in it | None |
| Live charging | Not possible from this account until the step below is done |

The account is empty, so nothing you do now can disturb existing customers
or existing charges. There are none.

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
