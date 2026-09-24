# Baltor privacy notice

Kind: published notice. The owner approved it on September 22, 2026, with
Baltor.AI as the operator and the postal contact address below. It states
what the hosted Baltor service stores today, taken from the source and the
deployment. Planned behaviour is marked as planned.

Operator: Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States.

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
| A waiting list entry, if you ask to join the list: your email address, an optional note of at most 280 characters, the state of the entry and its dates | To invite people in small groups | The service database |
| A record of each refused request: a random reference, the address path, the reason code, the account when one is known, the time and the service version | To find and fix problems. The last 500 are kept and older ones are removed. A record never holds a password, a key, a promotion code, a request body or your network address. | The service database |
| Your payment details | Planned, when billing opens. Stripe collects and keeps them. Baltor receives only a customer identifier and the state of your subscription. | Stripe |

The service keeps a count of refused sign-in attempts for each network
address in memory for a short time, to slow down guessing. It is not written
to disk. To stop one machine from flooding the waiting list, the service also
keeps the times of recent waiting list requests under a keyed one-way digest
of the sending network address, never the address itself, and removes them
once the one-hour counting window has passed.

## What the service does not do

- It sets no cookies. When you sign in with your email address, the page
  keeps your sign-in in your browser tab's session storage until you close
  the tab or sign out, so reloading the page keeps you signed in. A key you
  enter on the sign-in page is kept only in the memory of the page.
- It runs no analytics, advertising or tracking scripts. Every script on the
  site is served from the site itself.
- It keeps no log of requests that succeed. Refused requests are recorded
  as described above.
- Email sent to you has open and click tracking switched off.
- It does not sell or share your data. The providers named above process it
  only to run the service.

## Backups and deletion

The hosting provider keeps daily snapshots of the service database for five
days. To delete your account and its records, write to the contact address
below. Deletion removes the account record, the key digests and the usage
records; snapshots expire within five days. To leave the waiting list, ask
in the same way: the entry keeps only a one-way digest of the address and
the history of decisions, so the address itself is gone. Self-service
deletion is planned.

## Contact

Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States.

Questions that contain no personal data can also go to the public issue
tracker of the repository. Do not post personal data in a public issue.

## Changes

This notice changes when the service changes what it stores. The history of
this file is the record of those changes.
