#!/usr/bin/env bash
# Read-only HTTP probe of the live public website. GET and HEAD only, no credentials,
# one request at a time with a pause between requests. Usage: bash live-http-probe.sh > output.txt
set -u
origin="${1:-https://baltor.ai}"
pause() { sleep 0.4; }
echo "observed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ) origin=$origin"
echo "== status, media type and size of named addresses (GET, browser-like Accept header)"
for path in / /how-it-works /pricing /connect /waitlist /get-started /docs /examples /security /privacy /login /signup /app /account /admin \
            /robots.txt /sitemap.xml /favicon.ico /manifest.webmanifest /site.webmanifest /.well-known/security.txt /no-such-page \
            /api/v1/capabilities /api/v1/health; do
  printf '%-28s ' "$path"
  curl -s -o /dev/null -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8' \
    -w '%{http_code} %{content_type} %{size_download}B\n' "$origin$path"; pause
done
echo "== the same unknown addresses without a browser Accept header"
for path in /robots.txt /no-such-page; do printf '%-28s ' "$path"; curl -s -o /dev/null -w '%{http_code} %{content_type}\n' "$origin$path"; pause; done
echo "== HEAD requests to pages"
for path in / /pricing /docs; do printf 'HEAD %-23s ' "$path"; curl -s -o /dev/null -I -w '%{http_code} %{content_type}\n' "$origin$path"; pause; done
echo "== response headers of the home page (GET)"
curl -s -D - -o /dev/null "$origin/"; pause
echo "== caching and compression of static files (GET with Accept-Encoding)"
for path in / /assets/service.css /assets/service.js /assets/supabase-client.js /assets/geist.woff2 /assets/geist-mono.woff2 /assets/baltor-mark.svg; do
  printf '%-30s ' "$path"
  curl -s -o /dev/null -H 'Accept-Encoding: gzip, deflate, br, zstd' -w 'status=%{http_code} encoding=%header{content-encoding} cache=%header{cache-control} bytes_on_wire=%{size_download}\n' "$origin$path"; pause
done
echo "== plain HTTP and the other hostnames (GET /, redirects not followed)"
for host in baltor.ai www.baltor.ai app.baltor.ai docs.baltor.ai status.baltor.ai examples.baltor.ai demo.baltor.ai baltor-pilot.fly.dev; do
  printf 'https://%-24s ' "$host"; curl -s -o /dev/null -w '%{http_code} redirect=%{redirect_url}\n' "https://$host/"; pause
done
printf 'http://baltor.ai/            '; curl -s -o /dev/null -w '%{http_code} redirect=%{redirect_url}\n' "http://baltor.ai/"; pause
echo "== head tags a link preview or search engine reads without running the page script"
curl -s "$origin/pricing" | grep -o -i -E '<title>[^<]*</title>|<meta name="description"[^>]*>|<link rel="canonical"[^>]*>|<meta property="og:[^>]*>|<meta name="twitter:[^>]*>|<link rel="manifest"[^>]*>|<meta name="theme-color"[^>]*>|<link rel="(icon|apple-touch-icon)"[^>]*>'
