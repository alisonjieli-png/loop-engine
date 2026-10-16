// systems.baltor.ai, retired: every request answers with one permanent redirect to the staff Systems view.
//
// Roadmap S-6.35.11. On October 14, 2026 another harness deployed an internal portal at systems.baltor.ai as its own
// Worker, outside the guarded release path and with no access control; on October 15 it was put behind HTTP sign-in as
// a stopgap. The staff Systems view now lives inside the service, at /admin/systems on the canonical site, where the
// service checks the staff role on every request. This Worker replaces the portal's code and serves nothing of its own.
//
// It reads no binding, no secret and no part of the request: not the path, the query, the method, a header or a body.
// The Location is one fixed address, so the redirect cannot be pointed anywhere else and copies nothing a caller sent.
// The answer carries noindex and is not stored by a cache, so the hostname can be reused later without a stale
// redirect. Uploading it is a provider step for the coordinating session; this file is the reviewed source.

export const TARGET = "https://baltor.ai/admin/systems";

export const HEADERS = Object.freeze({
  "location": TARGET,
  "cache-control": "no-store",
  "x-robots-tag": "noindex, nofollow",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
});

export function handle() {
  return new Response(null, { status: 301, headers: HEADERS });
}

export default {
  async fetch() {
    return handle();
  },
};
