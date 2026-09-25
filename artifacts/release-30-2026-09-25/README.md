# Release 30 evidence, September 25, 2026

Fly release 30 of `baltor-pilot` went live at 15:29 UTC from main
`2502556760981e536f838fa3456d0aebf5e883d0` after continuous integration run
36151852734 passed, through deployment run 36154237825. The image is
`sha256:c075f297d8c1717cd462d84151c0496bad89b751586e4726dc5a4606c9352de6`;
the rollback target is release 29. The record is
[`pilot-release-30.json`](../architecture-audit-2026-09-19/pilot-release-30.json).

## What changed

- A harness can ask with version 2 of the provisioning request. It names each
  item's library tier, follows the account's library setting and reads the
  `Baltor-Step-Effects` header; without the header, a step may read files.
  The protocol tools ask this way.
- The homepage shows the live number of served library items.
- Two demonstration steps show the search results a harness now receives.

## How it was checked

| Check | Result |
|---|---|
| What a person sees: 44 pages at desktop and phone width, light and dark, and 8 hostnames | no problem; 338 links checked |
| The customer's search and download with the homepage digest guard | 6 of 8 |
| The service transport and isolation | 19 of 19 |

Advice: 135 of 135 addresses answer, the Pi extension matches on all nine
hostnames, and 216 of 216 detailed browser rules pass on baltor.ai.

## The two failed catalogue checks

Both demonstration pages print the digest of an item that reads files:
`layer_exception_catalogs_with_precedence` (`0a8cc8cd`) and
`check_for_existing_work_before_building` (`b710af36`). The check asked for
each with a version 1 manifest request, which holds no step effect, so the
service answered 400 `item_withheld`. Asked the same question with version 2,
the service answered 200 with exactly the printed digests.

The pages were right, and the check was asking the wrong question. But it
pointed at a real gap: the website's download button and the Pi extension still
sent version 1 after a version 2 search. An item that reads files was offered
by search and then refused on download. Three starter items, the ones that
declare only reading files, were affected, and every Community item would have
been. The six starter items that also write files, run a process or use the
network are withheld by both versions unless the header allows them.

Release 30 stays live, because rolling back would also take version 2 away from
every protocol client. The next release moves the website's download, the Pi
extension, the documentation examples and this check to version 2. The
Community catalogue is published after that release is live, not before.

The screenshots are kept outside the repository.
