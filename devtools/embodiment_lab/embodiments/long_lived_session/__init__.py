"""One persistent process; fresh explicit state and Loop identity per packet."""

from ...process_adapter import WorkerProcess


async def run(packets, context):
    worker = WorkerProcess(context.root / "workers" / "session")
    try:
        await worker.start()
        for packet in packets:
            try:
                result = await worker.request(packet, context.remaining())
                context.accept(packet, result)
            except Exception as exc:  # noqa: BLE001 - retain failures before explicit process recovery.
                context.failure(packet, exc)
                # A failed process is never mistaken for a reusable live session.
                await worker.close()
                if context.policy.seconds > 0:
                    context.remaining()
                    await worker.start()
    finally:
        await worker.close()
