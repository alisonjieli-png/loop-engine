"""An allowlisting HTTPS proxy for one comparison pilot trial.

Both arms of the pilot run with the same network setting: every HTTP and HTTPS
proxy variable inside the sandbox points at this proxy, and it opens a tunnel
only to the hosts on its allowlist, on port 443. Everything else is refused
with 403 and recorded. The allowlist is the same for both arms. The arm without
Baltor has no account, token or configuration that would make use of the
allowed hosts.

The proxy never sees request contents: a CONNECT tunnel carries TLS bytes it
cannot read. It records the host, port, method, decision, byte counts and
duration of each attempt in a JSON Lines ledger. A program that ignores the
proxy variables is not stopped here; the runner scans the harness's tool calls
for that afterwards. Only the Python standard library is used.
"""
from __future__ import annotations

import json
import os
import select
import socket
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

LEDGER_RECORD = "comparison_pilot_egress/v1"
TUNNEL_IDLE_SECONDS = 120
CONNECT_TIMEOUT_SECONDS = 20


def now_text():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class EgressProxy:
    """Tunnel to allowlisted hosts on port 443 and refuse everything else."""

    def __init__(self, ledger_path, trial_id, allowed_hosts):
        self.ledger_path = Path(ledger_path)
        self.trial_id = trial_id
        self.allowed_hosts = frozenset(host.lower() for host in allowed_hosts)
        self.lock = threading.Lock()
        self.server = None
        self.counts = {"allowed": 0, "refused": 0}

    def _write(self, row):
        row = dict(record_type=LEDGER_RECORD, trial_id=self.trial_id, at=now_text(), **row)
        with self.lock:
            self.counts["allowed" if row.get("allowed") else "refused"] += 1
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ledger_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    def start(self, port=0):
        proxy = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                return

            def _refuse(self, method, host, port, reason):
                proxy._write(dict(method=method, host=host, port=port, allowed=False, reason=reason))
                body = b"egress refused by the pilot proxy\n"
                try:
                    self.send_response(403)
                    self.send_header("Content-Type", "text/plain")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("Connection", "close")
                    self.end_headers()
                    self.wfile.write(body)
                except OSError:
                    pass
                self.close_connection = True

            def do_CONNECT(self):
                target = self.path
                host, _, port_text = target.rpartition(":")
                host = host.strip("[]").lower()
                try:
                    port = int(port_text)
                except ValueError:
                    self._refuse("CONNECT", host or target, None, "malformed_target")
                    return
                if host not in proxy.allowed_hosts or port != 443:
                    self._refuse("CONNECT", host, port, "host_not_allowed")
                    return
                started = time.monotonic()
                try:
                    upstream = socket.create_connection((host, port), timeout=CONNECT_TIMEOUT_SECONDS)
                except OSError as error:
                    proxy._write(dict(method="CONNECT", host=host, port=port, allowed=True,
                                      error=type(error).__name__, bytes_up=0, bytes_down=0))
                    try:
                        self.send_response(502)
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                    except OSError:
                        pass
                    self.close_connection = True
                    return
                self.send_response(200, "Connection Established")
                self.end_headers()
                up = down = 0
                client = self.connection
                sockets = [client, upstream]
                try:
                    while True:
                        readable, _, broken = select.select(sockets, [], sockets, TUNNEL_IDLE_SECONDS)
                        if broken or not readable:
                            break
                        done = False
                        for source in readable:
                            data = source.recv(65536)
                            if not data:
                                done = True
                                break
                            if source is client:
                                upstream.sendall(data)
                                up += len(data)
                            else:
                                client.sendall(data)
                                down += len(data)
                        if done:
                            break
                except OSError:
                    pass
                finally:
                    upstream.close()
                    proxy._write(dict(method="CONNECT", host=host, port=port, allowed=True, bytes_up=up,
                                      bytes_down=down, duration_ms=int((time.monotonic() - started) * 1000)))
                    self.close_connection = True

            def _plain(self):
                parsed = urlsplit(self.path)
                self._refuse(self.command, (parsed.hostname or "").lower(), parsed.port, "plain_http_refused")

            do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = do_PATCH = do_OPTIONS = _plain

        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self.server.server_address[1]

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
