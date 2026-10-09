"""Appointment slot allocator: place requests into providers' free time with durations, buffers and priorities.

Requests are taken in priority order (1 first), then by earliest allowed date, then input order. Each request goes
to the earliest free start time, on a step grid, that fits its duration inside one availability block of an
eligible provider and keeps the buffer clear of that provider's other bookings. A preferred provider is tried first
and used whenever it has any fitting slot in the window. A pure function of its JSON input; the command line reads
standard input and writes standard output.
"""
from __future__ import annotations

from kit_schema import KitRefusal, check, parse_date, parse_time, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_id": "two providers or two requests share an id",
    "invalid_date_or_time": "a date is not a real calendar date or a time is not HH:MM",
    "empty_availability_block": "an availability block ends at or before its start",
    "overlapping_availability": "one provider has two availability blocks that overlap on the same date",
    "unknown_provider": "a request or an existing booking names a provider that is not listed",
    "reversed_window": "a request's latest_date is before its earliest_date",
}
_BLOCK = {"type": "object", "required": ["date", "start", "end"], "additionalProperties": False,
          "properties": {"date": {"type": "string"}, "start": {"type": "string"}, "end": {"type": "string"}}}
INPUT_SCHEMA = {
    "type": "object", "required": ["providers", "requests"], "additionalProperties": False,
    "properties": {
        "providers": {"type": "array", "minItems": 1, "maxItems": 500, "description":
                      "people or rooms with availability blocks (date, start, end) and the services they offer",
                      "items": {"type": "object", "required": ["id", "availability"], "additionalProperties": False,
                                "properties": {"id": {"type": "string", "minLength": 1}, "name": {"type": "string"},
                                               "services": {"type": "array", "items": {"type": "string"}},
                                               "availability": {"type": "array", "items": _BLOCK,
                                                                "maxItems": 2000}}}},
        "requests": {"type": "array", "minItems": 1, "maxItems": 5000, "description":
                     "appointments to place: duration, optional service, priority, date window, preferred provider",
                     "items": {"type": "object", "required": ["id", "duration_minutes"], "additionalProperties": False,
                               "properties": {"id": {"type": "string", "minLength": 1},
                                              "service": {"type": "string"},
                                              "duration_minutes": {"type": "integer", "minimum": 5, "maximum": 720},
                                              "priority": {"type": "integer", "minimum": 1, "maximum": 9},
                                              "earliest_date": {"type": "string"}, "latest_date": {"type": "string"},
                                              "preferred_provider": {"type": "string"}}}},
        "existing_bookings": {"type": "array", "items": {"type": "object", "required": ["provider", "date", "start",
                                                                                       "end"],
                                                         "additionalProperties": False,
                                                         "properties": {"provider": {"type": "string"},
                                                                        "date": {"type": "string"},
                                                                        "start": {"type": "string"},
                                                                        "end": {"type": "string"}}},
                              "description": "bookings already made; they block time like new ones"},
        "slot_step_minutes": {"type": "integer", "minimum": 5, "maximum": 120,
                              "description": "grid for candidate start times (default 15)"},
        "buffer_minutes": {"type": "integer", "minimum": 0, "maximum": 240,
                           "description": "gap kept free before and after each booking (default 0)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["bookings", "unplaced", "utilization"],
    "properties": {
        "bookings": {"type": "array", "description": "one row per placed request, in placement order",
                     "items": {"type": "object", "required": ["request", "provider", "date", "start", "end"],
                               "properties": {"request": {"type": "string"}, "provider": {"type": "string"},
                                              "date": {"type": "string", "format": "date"},
                                              "start": {"type": "string", "format": "time"},
                                              "end": {"type": "string", "format": "time"},
                                              "preferred_provider_used": {"type": "boolean"}}}},
        "unplaced": {"type": "array", "description": "requests that could not be placed, with the reason",
                     "items": {"type": "object", "required": ["request", "reason"],
                               "properties": {"request": {"type": "string"},
                                              "reason": {"enum": ["no_provider_offers_service",
                                                                  "no_free_slot_in_window"]}}}},
        "utilization": {"type": "array", "description": "available and booked minutes per provider, existing bookings included",
                        "items": {"type": "object", "required": ["provider", "available_minutes", "booked_minutes",
                                                                 "share"],
                                  "properties": {"provider": {"type": "string"},
                                                 "available_minutes": {"type": "integer"},
                                                 "booked_minutes": {"type": "integer"},
                                                 "share": {"type": "number"}}}},
    },
}


def clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _times(row: dict) -> tuple:
    date, start, end = parse_date(row["date"]), parse_time(row["start"]), parse_time(row["end"])
    if date is None or start is None or end is None:
        raise KitRefusal("invalid_date_or_time", f"{row['date']} {row['start']} to {row['end']}")
    if end <= start:
        raise KitRefusal("empty_availability_block", f"{row['date']} {row['start']} to {row['end']}")
    return date, start, end


def free_start(blocks: list, taken: list, duration: int, step: int, buffer: int, first, last):
    """The earliest (date, start) in ``blocks`` within [first, last] that fits ``duration`` clear of ``taken``."""
    for date, start, end in blocks:
        if (first is not None and date < first) or (last is not None and date > last):
            continue
        busy = [(begin - buffer, finish + buffer) for day, begin, finish in taken if day == date]
        candidate = start
        while candidate + duration <= end:
            if all(candidate + duration <= begin or candidate >= finish for begin, finish in busy):
                return date, candidate
            candidate += step
    return None


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    providers, requests = payload["providers"], payload["requests"]
    for label, rows in (("provider", providers), ("request", requests)):
        ids = [row["id"] for row in rows]
        if len(set(ids)) != len(ids):
            raise KitRefusal("duplicate_id", f"repeated {label} id")
    step, buffer = payload.get("slot_step_minutes", 15), payload.get("buffer_minutes", 0)
    blocks, taken, available, booked = {}, {}, {}, {}
    for provider in providers:
        rows = sorted(_times(block) for block in provider["availability"])
        for (day_a, start_a, end_a), (day_b, start_b, _end_b) in zip(rows, rows[1:]):
            if day_a == day_b and start_b < end_a:
                raise KitRefusal("overlapping_availability", f"{provider['id']} on {day_a.isoformat()}")
        blocks[provider["id"]] = rows
        taken[provider["id"]] = []
        available[provider["id"]] = sum(end - start for _day, start, end in rows)
        booked[provider["id"]] = 0
    for booking in payload.get("existing_bookings", []):
        if booking["provider"] not in blocks:
            raise KitRefusal("unknown_provider", booking["provider"])
        day, start, end = _times(booking)
        taken[booking["provider"]].append((day, start, end))
        booked[booking["provider"]] += end - start
    order = []
    for index, request in enumerate(requests):
        first = parse_date(request["earliest_date"]) if "earliest_date" in request else None
        last = parse_date(request["latest_date"]) if "latest_date" in request else None
        if ("earliest_date" in request and first is None) or ("latest_date" in request and last is None):
            raise KitRefusal("invalid_date_or_time", request["id"])
        if first and last and last < first:
            raise KitRefusal("reversed_window", request["id"])
        if request.get("preferred_provider") and request["preferred_provider"] not in blocks:
            raise KitRefusal("unknown_provider", request["preferred_provider"])
        order.append((request.get("priority", 5), first.toordinal() if first else 0, index, request, first, last))
    order.sort(key=lambda row: row[:3])
    bookings, unplaced = [], []
    for _priority, _first_key, _index, request, first, last in order:
        eligible = [provider["id"] for provider in providers
                    if "service" not in request or request["service"] in provider.get("services", [])]
        if not eligible:
            unplaced.append({"request": request["id"], "reason": "no_provider_offers_service"})
            continue
        preferred = request.get("preferred_provider")
        choice = None
        if preferred in eligible:
            slot = free_start(blocks[preferred], taken[preferred], request["duration_minutes"], step, buffer,
                              first, last)
            if slot:
                choice = (preferred, slot)
        if choice is None:
            options = []
            for provider_id in sorted(eligible):
                slot = free_start(blocks[provider_id], taken[provider_id], request["duration_minutes"], step,
                                  buffer, first, last)
                if slot:
                    options.append((slot[0], slot[1], provider_id))
            if options:
                date, start, provider_id = min(options)
                choice = (provider_id, (date, start))
        if choice is None:
            unplaced.append({"request": request["id"], "reason": "no_free_slot_in_window"})
            continue
        provider_id, (date, start) = choice
        end = start + request["duration_minutes"]
        taken[provider_id].append((date, start, end))
        booked[provider_id] += request["duration_minutes"]
        row = {"request": request["id"], "provider": provider_id, "date": date.isoformat(), "start": clock(start),
               "end": clock(end)}
        if preferred:
            row["preferred_provider_used"] = provider_id == preferred
        bookings.append(row)
    utilization = [{"provider": provider["id"], "available_minutes": available[provider["id"]],
                    "booked_minutes": booked[provider["id"]],
                    "share": round(booked[provider["id"]] / available[provider["id"]], 4)
                    if available[provider["id"]] else 0}
                   for provider in providers]
    return {"bookings": bookings, "unplaced": unplaced, "utilization": utilization}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
