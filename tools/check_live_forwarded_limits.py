"""Bounded refusal observations for a second-network Cloudflare acceptance check.

No real credential, account mutation or request body is sent. Pair the UTC
observations with a separately recorded operator flood from another network.
This observer alone does not assert that the limiter is qualified.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import uuid

ORIGINS = ('https://baltor-pilot.fly.dev', 'https://baltor-web-edge.baltor-ai.workers.dev',
           'https://docs.baltor.ai', 'https://baltor.ai')


def observe(origin, *, samples=24, interval=5, opener=None, sleep=time.sleep):
    """Sample below the 30-attempt/60-second service ceiling from one network."""
    if origin not in ORIGINS or type(samples) is not int or not 1 <= samples <= 24 or interval < 5:
        raise ValueError('invalid_bounded_probe_scope')
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}))
    rows = []
    for index in range(samples):
        stamp = datetime.now(timezone.utc).isoformat()
        request = urllib.request.Request(origin + '/api/v1/usage',
            headers={'Authorization': 'Bearer ' + str(uuid.uuid4()), 'User-Agent': 'Baltor-limit-observer/1'})
        try:
            response = opener.open(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            response.read(100_000)
            rows.append({'at': stamp, 'status': response.status})
        if index + 1 < samples:
            sleep(interval)
    return {'record_type': 'live_forwarding_peer_observations/v1', 'origin': origin,
            'samples': rows, 'all_individually_unauthorized': all(row['status'] == 401 for row in rows),
            'qualification': 'requires_overlapping_other_network_limit_record'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origin', required=True, choices=ORIGINS)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--authorize-network-reads', action='store_true')
    args = parser.parse_args()
    if not args.authorize_network_reads or args.output.exists():
        parser.error('explicit bounded network reads and a new output path are required')
    result = observe(args.origin)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
    return 0 if result['all_individually_unauthorized'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
