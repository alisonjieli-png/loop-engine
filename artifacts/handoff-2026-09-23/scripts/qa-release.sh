#!/usr/bin/env bash
# Live checks after a release, run from the released tree. Usage: qa-release.sh <tag> <released worktree>
# The phone item digest is read from that tree's packaged manifest, because every catalogue anchor changes it.
set -u
TAG=${1:?tag}
REPO=${2:?released worktree}
OUT=$REPO/artifacts/architecture-audit-2026-09-19
LOG=/home/username/.le-ci-tmp/qa-$TAG; mkdir -p "$LOG"
PY=/home/username/.le-wave2/mcp-revision/.venv-mcp2/bin/python
cd "$REPO"
[ -e showcase/node_modules ] || ln -s /home/username/loop-engine/showcase/node_modules showcase/node_modules
[ -e .venv ] || ln -s /home/username/.le-wave2/mcp-revision/.venv-mcp2 .venv   # the service check runs the protocol client from <tree>/.venv
DIGEST=$(python3 -c "
import json
d = json.load(open('examples/29_intelligence_service/starter-catalogue/host-release/manifest.json'))
found = []
def walk(o):
    if isinstance(o, dict):
        if o.get('identity') == 'normalize_phone_numbers': found.append(o['digest'])
        for v in o.values(): walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(d); print(found[0])")
echo "released tree $(git rev-parse --short HEAD); phone item digest $DIGEST"
HOSTS="baltor.ai www.baltor.ai app.baltor.ai baltor-pilot.fly.dev demo.baltor.ai examples.baltor.ai docs.baltor.ai status.baltor.ai"

echo "== every hostname: home, privacy, capabilities digest"
for h in $HOSTS; do
  home=$(curl -s -o /dev/null -w '%{http_code}' "https://$h/")
  priv=$(curl -s -o /dev/null -w '%{http_code}' "https://$h/privacy")
  caps=$(curl -s "https://$h/api/v1/capabilities" | sha256sum | cut -c1-12)
  echo "$h home=$home privacy=$priv capabilities=$caps"
done

echo "== health and capabilities"
curl -s https://baltor.ai/api/v1/health > "$LOG/health.json"
curl -s https://baltor.ai/api/v1/capabilities > "$LOG/capabilities.json"
python3 - "$LOG" <<'EOF'
import json, sys
log = sys.argv[1]
h = json.load(open(f"{log}/health.json")); c = json.load(open(f"{log}/capabilities.json"))
r = h.get("result", h)
print("health:", r.get("record_type"), "alive", r.get("alive"), "ready", r.get("ready"))
for chk in r.get("checks", []):
    print("  ", chk.get("name"), "required" if chk.get("required") else "optional", "passed" if chk.get("passed") else "FAILED")
cr = c.get("result", c)
print("capabilities:", json.dumps({k: cr.get(k) for k in ("record_type",)}))
for path in (("website", "registration_available"), ("website", "waitlist_available"), ("billing", "checkout"), ("billing", "portal"), ("billing", "webhook")):
    node = cr
    for p in path: node = node.get(p, {}) if isinstance(node, dict) else None
    print("  ", ".".join(path), "=", node)
EOF

echo "== website checks on four hostnames"
for h in baltor.ai www.baltor.ai app.baltor.ai baltor-pilot.fly.dev; do
  node tools/check_hosted_website.mjs "https://$h" "$OUT/hosted-$TAG-website-$h.json" > "$LOG/web-$h.log" 2>&1 &
done
wait
for h in baltor.ai www.baltor.ai app.baltor.ai baltor-pilot.fly.dev; do
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[2], d['passed'], 'of', d['total'], 'failed:', [c.get('name') for c in d['checks'] if not c.get('passed')][:6])" "$OUT/hosted-$TAG-website-$h.json" "$h" 2>/dev/null || { echo "$h website check did not write a report"; tail -5 "$LOG/web-$h.log"; }
done

echo "== catalogue"
$PY tools/check_hosted_catalogue.py --origin https://baltor.ai --account pilot-owner --credential-host baltor-pilot.fly.dev \
  --query 'find duplicate customer records' --query 'clean a messy text column' --query 'check a result before handing it over' \
  --output "$OUT/hosted-$TAG-catalogue.json" > "$LOG/catalogue.log" 2>&1; echo "catalogue exit=$?"; tail -4 "$LOG/catalogue.log"

echo "== hosted service over HTTPS and the protocol"
$PY tools/check_hosted_service.py --origin https://baltor-pilot.fly.dev --account pilot-owner --isolated-account pilot-boundary \
  --identity normalize_phone_numbers --digest "$DIGEST" \
  --query 'normalize phone numbers' --authorize-metered-read --output "$OUT/hosted-$TAG-service.json" > "$LOG/service.log" 2>&1; echo "service exit=$?"; tail -4 "$LOG/service.log"
