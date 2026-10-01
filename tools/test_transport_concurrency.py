"""Pinned real Uvicorn transport limits, distinct from expensive operation slots.

Only loopback, synthetic service state and small public responses. These checks
do not qualify 128 simultaneous maximum-size responses or a total memory cap.
"""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import resource
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import uvicorn

from loop_engine.core.service_runtime import http_entrypoint
from loop_engine.core.service_runtime.http import ServiceHttpConfiguration
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http

EVENTS = []
MAXIMUM_SMALL_RESPONSE_BYTES = 512 * 1024
PAGE_PATHS = ('/login', '/public-good', '/assets/public-good.css', '/assets/public-good.js')


@contextmanager
def transport_server(*, ceiling=128):
    servers = []
    server_type = uvicorn.Server
    def capture(configuration):
        server = server_type(configuration)
        servers.append(server)
        return server
    with tempfile.TemporaryDirectory(prefix='transport-cap-') as folder:
        fixture = HttpDomainFixture(Path(folder))
        with patch.object(uvicorn, 'Server', side_effect=capture):
            with running_http(fixture, maximum_transport_concurrency=ceiling) as (base, application):
                yield base, application, servers[0]


async def connection(base):
    from urllib.parse import urlsplit
    target = urlsplit(base)
    reader, writer = await asyncio.wait_for(asyncio.open_connection(target.hostname, target.port), 5)
    return reader, writer, target.netloc


def send(channel, path):
    _reader, writer, host = channel
    writer.write(('GET ' + path + ' HTTP/1.1\r\nHost: ' + host + '\r\nConnection: keep-alive\r\n\r\n').encode('ascii'))


async def response(channel):
    reader, writer, _host = channel
    await writer.drain()
    header = await asyncio.wait_for(reader.readuntil(b'\r\n\r\n'), 15)
    lines = header.decode('latin1').split('\r\n')
    status = int(lines[0].split()[1])
    fields = {key.lower(): value.strip() for line in lines[1:] if ':' in line for key, value in (line.split(':', 1),)}
    size = int(fields['content-length'])
    if not 0 <= size <= MAXIMUM_SMALL_RESPONSE_BYTES:
        raise AssertionError('test response exceeded its declared small-response allowance')
    body = await asyncio.wait_for(reader.readexactly(size), 15)
    return status, fields, body


async def request(channel, path):
    send(channel, path)
    return await response(channel)


async def close(channels):
    for _reader, writer, _host in channels:
        writer.close()
    await asyncio.gather(*(writer.wait_closed() for _reader, writer, _host in channels), return_exceptions=True)


async def accepted(server, count):
    deadline = time.monotonic() + 5
    while len(server.server_state.connections) < count:
        if time.monotonic() >= deadline:
            raise AssertionError('server did not accept the bounded connection set')
        await asyncio.sleep(0.005)


async def idle_page_burst(base, application, server):
    """24 completed keep-alives plus 72 new page/asset requests, dispatched together."""
    idle, burst = [], []
    try:
        for _ in range(24):
            channel = await connection(base)
            idle.append(channel)
            status, _headers, _body = await request(channel, '/api/v1/public-good/files')
            if status != 200:
                raise AssertionError('keep-alive warmup did not complete')
        await accepted(server, 24)
        free_workers = application._slots._value
        burst = list(await asyncio.gather(*(connection(base) for _ in range(72))))
        await accepted(server, 96)
        observed_connections = len(server.server_state.connections)
        # No request serialization: every write is queued before waiting on any
        # response, reproducing a browser page/asset burst with held keep-alives.
        for number, channel in enumerate(burst):
            send(channel, PAGE_PATHS[number % len(PAGE_PATHS)])
        started = time.monotonic()
        replies = await asyncio.gather(*(response(channel) for channel in burst))
        seen = {'limit': server.config.limit_concurrency, 'idle_keep_alives': len(idle), 'burst_requests': len(burst),
            'connections_before_dispatch': observed_connections, 'free_workers_before_dispatch': free_workers,
            'worker_limit': application.configuration.maximum_concurrent_operations,
            'account_limit': application.configuration.maximum_concurrent_operations_for_each_tenant,
            'statuses': {str(value): sum(reply[0] == value for reply in replies) for value in sorted({reply[0] for reply in replies})},
            'transport_503s': sum(status == 503 and body == b'Service Unavailable' for status, _headers, body in replies),
            'largest_response_bytes': max(len(body) for _status, _headers, body in replies),
            'seconds': time.monotonic() - started, 'uvicorn_version': uvicorn.__version__,
            'http_protocol': server.config.http_protocol_class.__name__}
        await close(burst)
        burst = []
        resumed = await connection(base)
        try:
            status, _headers, _body = await request(resumed, '/api/v1/public-good/files')
            seen['after_burst_status'] = status
        finally:
            await close((resumed,))
        seen['process_peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        EVENTS.append(seen)
        return seen
    finally:
        await close((*idle, *burst))


class TransportConfigurationTests(unittest.TestCase):
    def configuration(self, **changes):
        return ServiceHttpConfiguration('https://service.example.invalid', ('service.example.invalid',), **changes)

    def test_default_is_independent_and_worker_account_and_byte_caps_do_not_expand(self):
        default = self.configuration()
        self.assertEqual(default.maximum_transport_concurrency, 128)
        self.assertEqual(default.maximum_concurrent_operations, 8)
        self.assertEqual(default.maximum_concurrent_operations_for_each_tenant, 4)
        self.assertEqual(default.maximum_response_bytes, 262144)
        self.assertEqual(default.maximum_request_bytes, 65536)
        self.assertEqual(default.request_timeout_seconds, 30)
        for workers in (1, 2, 8, 16):
            configured = self.configuration(maximum_concurrent_operations=workers)
            self.assertEqual(configured.maximum_transport_concurrency, 128)
        self.assertEqual(ServiceHttpConfiguration(**asdict(default)), default)

    def test_strict_bounded_transport_threshold_refuses_unlimited_and_unusable_values(self):
        for value in (2, 32, 64, 128):
            self.assertEqual(self.configuration(maximum_transport_concurrency=value).maximum_transport_concurrency, value)
        for value in (None, False, True, -1, 0, 1, 129, 1024, '128', 128.0, float('inf'), float('nan')):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                self.configuration(maximum_transport_concurrency=value)

    def test_new_setting_is_keyword_only_preserving_existing_positional_profile(self):
        config = ServiceHttpConfiguration('https://service.example.invalid', ('service.example.invalid',), (),
            'Synthetic', 65536, 262144, 16384, 67108864, 50, 8, 7.0)
        self.assertEqual(config.request_timeout_seconds, 7.0)
        self.assertEqual(config.maximum_transport_concurrency, 128)

    def test_actual_entrypoint_passes_transport_limit_not_worker_multiple(self):
        config = self.configuration(maximum_transport_concurrency=64, maximum_concurrent_operations=2)
        application = SimpleNamespace(configuration=config, create_app=Mock(return_value=object()))
        with patch.object(http_entrypoint, 'load_host_application', return_value=(application, {})), patch.object(uvicorn, 'run') as run:
            self.assertEqual(http_entrypoint.main(['serve', '--config', '/synthetic-host.json']), 0)
        self.assertEqual(run.call_args.kwargs['limit_concurrency'], 64)
        self.assertFalse(run.call_args.kwargs['proxy_headers'])
        self.assertFalse(run.call_args.kwargs['access_log'])
        self.assertNotEqual(run.call_args.kwargs['limit_concurrency'], config.maximum_concurrent_operations * 4)


class TransportLoopbackTests(unittest.TestCase):
    def test_real_idle_keep_alive_and_page_burst_succeeds_with_workers_still_free(self):
        with transport_server() as (base, application, server):
            seen = asyncio.run(idle_page_burst(base, application, server))
            self.assertEqual(server.config.limit_concurrency, 128, 'loopback fixture bypassed production limit')
            self.assertEqual(application.capabilities()['limits']['transport_concurrency'], 128)
        self.assertEqual(seen['statuses'], {'200': 72})
        self.assertEqual(seen['transport_503s'], 0)
        self.assertEqual(seen['free_workers_before_dispatch'], 8)
        self.assertEqual(seen['account_limit'], 4)
        self.assertEqual(seen['after_burst_status'], 200)

    def test_known_wrong_32_threshold_refuses_same_burst_before_the_application(self):
        with transport_server(ceiling=32) as (base, application, server):
            seen = asyncio.run(idle_page_burst(base, application, server))
        self.assertGreater(seen['transport_503s'], 0)
        self.assertNotEqual(seen['statuses'], {'200': 72}, 'known-wrong old coupling escaped the control')
        self.assertEqual(seen['free_workers_before_dispatch'], 8)
        self.assertEqual(seen['account_limit'], 4)
        self.assertEqual(seen['after_burst_status'], 200)

    def test_128_threshold_still_refuses_at_boundary_and_recovers_without_restart(self):
        async def scenario(base, server):
            channels = []
            try:
                # Raw accepted idle connections count too; this is not a claim
                # that Uvicorn stops accepting TCP sockets at the threshold.
                channels = list(await asyncio.gather(*(connection(base) for _ in range(126))))
                await accepted(server, 126)
                good = await connection(base)
                channels.append(good)
                below = await request(good, '/api/v1/public-good/files')
                refused = await connection(base)
                channels.append(refused)
                at_limit = await request(refused, '/api/v1/public-good/files')
                self.assertEqual(below[0], 200)
                self.assertEqual(at_limit[0], 503)
                self.assertEqual(at_limit[2], b'Service Unavailable')
                self.assertEqual(at_limit[1].get('connection'), 'close')
                EVENTS.append({'limit': 128, 'at_127_connections': below[0], 'at_128_connections': at_limit[0],
                               'scope': 'small metadata response; transport threshold only'})
            finally:
                await close(channels)
            deadline = time.monotonic() + 5
            while server.server_state.connections:
                if time.monotonic() >= deadline:
                    raise AssertionError('boundary connections did not close')
                await asyncio.sleep(0.005)
            resumed = await connection(base)
            try:
                self.assertEqual((await request(resumed, '/api/v1/public-good/files'))[0], 200)
                self.assertTrue(server.started)
                self.assertFalse(server.should_exit)
            finally:
                await close((resumed,))
        with transport_server() as (base, _application, server):
            asyncio.run(scenario(base, server))


if __name__ == '__main__':
    unittest.main()
