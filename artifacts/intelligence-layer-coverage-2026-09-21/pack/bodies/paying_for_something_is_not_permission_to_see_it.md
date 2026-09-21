# Paying for something is not permission to see it

Kind: recorded repair from Runtime History and Solution Intelligence.

## When to use this record

Use it when you are building the part of a service that decides whether a
caller may see an item, and more than one fact about the caller is available
at that point.

## What was recorded

The serving path was changed to require two separate things before it
discloses any item metadata or any body: an exact host-installed grant for
that tenant, and a matching qualification decision.

The record then names three things that cannot stand in for that authority:

1. Payment entitlement. A caller who has paid has an entitlement, not a grant.
2. The effect names carried on the request. What a caller says it intends to
   do is not permission to do it.
3. Classification tags on the item. How an item is filed says nothing about
   who may read it.

Items that are unknown or not approved are absent everywhere, not hidden
selectively: absent from discovery counts, from listing results, from the list
of withheld identities, from manifests, and from bodies.

## Why absence has to be complete

A count is a disclosure. If an unapproved item is excluded from the list but
still counted, the caller learns that something exists which they may not see.
If it appears in a list of withheld identities, the caller learns its name.
The two facts together are often enough to identify the item.

## The known-wrong case

The wrong design is to check payment at the edge and treat every later step as
authorised. Entitlement answers whether a caller may be billed. It does not
answer which tenant's material this caller may read.

## What to record

Record the grant, the qualification decision, and the refusal reason. Keep the
entitlement check and the authority check as separate named steps so neither
can quietly become the other.

## Source

`artifacts/architecture-audit-2026-09-19/provisioning-access-repairs.md`,
section "Outcome".
