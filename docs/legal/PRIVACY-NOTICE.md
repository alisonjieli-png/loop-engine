# Baltor privacy notice (draft)

Kind: draft for the owner to read before live charging. It states what the
hosted Baltor service stores today, taken from the source and the deployment.
Planned behaviour is marked as planned.

## What Baltor is

Baltor serves reviewed material, such as guidance, skills and reusable code,
to the tools that you run on your own computer. Your tasks, your files, your
prompts and your model keys stay on your computer. The service never
receives them and has no way to ask for them.

## What the service stores

| Data | Why | Where |
|---|---|---|
| Your email address and password | To sign you in. The password is kept only by the identity provider, in hashed form. Baltor never stores or sees it after sign-up. | Supabase, United States |
| An account record that links your sign-in to your account | To know which material you may read | The service database on Fly, United States (`iad`) |
| A digest of each access key | To check a key without being able to show it again. The key itself is shown once and never stored. | The service database |
| One usage record for each downloaded item: the item name, its digest and the time | To show you your usage and, when billing opens, to reconcile it | The service database |
| A digest of a browser session that you signed out of, until it would have expired | To refuse that session afterwards | The service database |
| Your payment details | Planned, when billing opens. Stripe collects and keeps them. Baltor receives only a customer identifier and the state of your subscription. | Stripe |

The service keeps a count of refused sign-in attempts for each network
address in memory for a short time, to slow down guessing. It is not written
to disk.

## What the service does not do

- It sets no cookies and uses no browser storage for your sign-in. Your
  session lives in the memory of the page, so closing or reloading the page
  signs you out.
- It runs no analytics, advertising or tracking scripts. Every script on the
  site is served from the site itself.
- It writes no request log. Email sent to you has open and click tracking
  switched off.
- It does not sell or share your data. The providers named above process it
  only to run the service.

## Backups and deletion

The hosting provider keeps daily snapshots of the service database for five
days. To delete your account and its records, write to the support contact.
Deletion removes the account record, the key digests and the usage records;
snapshots expire within five days. Self-service deletion is planned.

## Contact

During the beta, questions that contain no personal data can go to the public
issue tracker of the repository. A private contact address is planned before
live charging; until it exists, do not post personal data in a public issue.

## Changes

This notice changes when the service changes what it stores. The history of
this file is the record of those changes.
