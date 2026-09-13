"""A bounded pool of persistent processes, each serializing its own packets."""

import asyncio

from ...process_adapter import WorkerProcess


async def run(packets, context):
    workers = [
        WorkerProcess(context.root / "workers" / f"pool-{i}")
        for i in range(context.policy.concurrency)
    ]
    try:
        for worker in workers:
            await worker.start()

        async def lane(index):
            worker = workers[index]
            for packet in packets[index :: len(workers)]:
                try:
                    context.accept(
                        packet, await worker.request(packet, context.remaining())
                    )
                except Exception as exc:  # noqa: BLE001 - isolate a failure without dropping sibling results.
                    context.failure(packet, exc)

        await asyncio.gather(*(lane(i) for i in range(len(workers))))
    finally:
        await asyncio.gather(*(worker.close() for worker in workers))
