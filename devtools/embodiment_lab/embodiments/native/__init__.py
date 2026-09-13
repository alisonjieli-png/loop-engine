"""In-process canonical Loop execution, with no agent harness."""

from ...runtime import execute


async def run(packets, context):
    for packet in packets:
        try:
            context.remaining()
            context.accept(packet, execute(packet))
        except Exception as exc:  # noqa: BLE001 - each failed trial must remain observable.
            context.failure(packet, exc)
