# Procedure: Appointment slot allocator for providers and rooms

Follow this procedure to do the activity with the helper `appointment_slot_allocator.py`. The helper does the mechanical part. The agent gathers inputs, makes the decisions below and checks the result.

## Ask the user first

1. Which providers or rooms take bookings, and for which services?
2. What are the opening blocks per date, and which bookings already exist?
3. How long is each appointment type, and is a buffer needed for cleaning, notes or travel?
4. How is priority decided (urgency, contract, first come), and may a request move to another provider than the one asked for?
5. Does any request carry personal or health details that must stay out of shared outputs?

## Steps

1. Collect availability as date, start and end per provider; merge adjacent blocks only when the provider confirms there is no break.
2. Add existing bookings so they block time.
3. Normalize each request: duration in minutes, service, priority 1 (most urgent) to 9, date window and preferred provider.
4. Run the helper and read bookings and unplaced.
5. For each unplaced request, decide: extend the window, open more availability, or contact the requester with the earliest alternative.
6. Check utilization: shares above 0.9 leave no room for urgent additions.
7. Send confirmations from the booking rows; keep request ids, not personal details, in shared logs.

## Decision points

### Strict preferred provider or any provider

- preferred only: choose when continuity of care or a named specialist matters more than speed; leave preferred_provider set and treat a different provider as a change the requester accepts
- any eligible provider: choose when speed matters more; drop preferred_provider

Default when nothing settles it: keep the preference; the helper falls back to another provider only when the preferred one has no slot in the window

Evidence that settles it: the requester's stated preference and the service's continuity rules

### Slot grid and buffer

- 15 minute grid, no buffer: choose when short consultations in one room
- 5 minute grid: choose when durations vary a lot and gaps matter
- buffer 10 to 15 minutes: choose when rooms need cleaning or providers write notes

Default when nothing settles it: 15 minute grid and the buffer the provider asks for

Evidence that settles it: how long changeovers take in practice

### What to do with unplaced urgent requests

- open overtime availability: choose when the provider agrees and cost is acceptable
- bump a lower priority booking: choose when policy allows it; do it by hand and record why
- refer elsewhere: choose when no capacity in the window

Default when nothing settles it: report the earliest possible date and ask a person

Evidence that settles it: the request's window and the service's urgency rules

## Quality checks

- No two bookings of one provider overlap once buffers are added.
- Every booking lies inside one availability block.
- Every request appears once: in bookings or in unplaced.
- Higher-priority requests are not left unplaced while lower ones in the same window got slots; if they are, check services and windows.

## Scenario variants

These are parameters of this one kit, not separate kits.

| Parameter | Values | Effect |
| --- | --- | --- |
| Speed | fast: one run with today's blocks; thorough: rerun after each change in availability | same method |
| Tools | free: this helper, a shared calendar file; paid: practice management or booking software | rows import into either |
| Harness | coding agent runs the helper; business user copies rows into a calendar | same result |
| Privacy | ids only, or names in a local copy | shared outputs carry ids only |

## Stop and ask, or hand to a person

- Clinical triage or deciding urgency: a qualified person sets priority.
- Sending messages to clients: needs its own approval and duplicate protection.
- Time zones and daylight saving changes: convert to one local time first.
