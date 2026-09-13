"""Independent process candidates publish verified portfolio versions as they finish."""

import asyncio
from dataclasses import replace

from ...process_adapter import WorkerProcess


async def run(packets, context):
    semaphore = asyncio.Semaphore(context.policy.concurrency)

    async def candidate(packet):
        async with semaphore:
            worker = WorkerProcess(context.root / "workers" / packet.request_id)
            try:
                context.remaining()
                await worker.start()
                result = await worker.request(packet, context.remaining())
                context.accept(packet, result)
            except Exception as exc:  # noqa: BLE001 - losing candidates remain in the evidence.
                context.failure(packet, exc)
            finally:
                await worker.close()

    work = [
        replace(packet, request_id=packet.request_id + "." + method, method=method)
        for packet in packets
        for method in ("streaming", "batch")
    ]
    await asyncio.gather(*(candidate(packet) for packet in work))
