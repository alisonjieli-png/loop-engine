"""Private bounded worker processes. Process separation is not an OS sandbox."""

from __future__ import annotations

import asyncio
import json
import os
import signal
import sys
from pathlib import Path

from .contracts import MAX_PACKET_BYTES, WorkPacket, canonical


class WorkerProcess:
    """An adapter, not an operational runtime or graph vertex."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.process = None
        self.lock = asyncio.Lock()

    async def start(self):
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        root = Path(__file__).resolve().parents[1]
        env = {
            key: os.environ[key]
            for key in ("PATH", "LANG", "LC_ALL")
            if key in os.environ
        }
        env.update(
            {
                "PYTHONPATH": os.pathsep.join((str(root), str(root.parent / "src"))),
                "PYTHONDONTWRITEBYTECODE": "1",
                "HOME": str(self.directory),
            }
        )
        self.process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "embodiment_lab.worker",
            cwd=str(self.directory),
            env=env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            start_new_session=True,
            limit=MAX_PACKET_BYTES,
        )
        return self

    async def request(self, packet: WorkPacket, timeout: float) -> dict:
        async with self.lock:
            raw = canonical(packet.to_dict()).encode() + b"\n"
            if len(raw) > MAX_PACKET_BYTES:
                raise ValueError("packet too large")
            if self.process is None or self.process.returncode is not None:
                raise RuntimeError("worker unavailable")
            try:

                async def exchange():
                    self.process.stdin.write(raw)
                    await self.process.stdin.drain()
                    line = await self.process.stdout.readline()
                    if not line or len(line) > MAX_PACKET_BYTES:
                        raise ValueError("missing or oversized worker response")
                    return json.loads(line)

                return await asyncio.wait_for(exchange(), timeout=timeout)
            except BaseException:
                await self.close()
                raise

    async def close(self):
        process = self.process
        if process is None:
            return
        self.process = None
        if process.stdin:
            process.stdin.close()
        if process.returncode is None:
            try:
                await asyncio.wait_for(process.wait(), timeout=0.5)
            except asyncio.TimeoutError:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                await process.wait()
