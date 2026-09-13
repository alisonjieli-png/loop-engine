"""One fresh bounded process and canonical Loop per packet."""

from ...process_adapter import WorkerProcess


async def run(packets, context):
    for packet in packets:
        worker = WorkerProcess(context.root / "workers" / packet.request_id)
        try:
            context.remaining()
            await worker.start()
            context.accept(packet, await worker.request(packet, context.remaining()))
        except Exception as exc:  # noqa: BLE001 - each failed trial must remain observable.
            context.failure(packet, exc)
        finally:
            await worker.close()
