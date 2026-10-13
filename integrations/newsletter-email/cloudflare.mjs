import {DurableObject} from 'cloudflare:workers';
import worker from './worker.mjs';
import {quotaFetch} from './quota.mjs';

// Keep this SQLite-backed namespace and stable object name across upgrades.
// No public fetch route, RPC method, reset, alarm or deletion is exposed.
export class NewsletterAdmission extends DurableObject {
  async fetch(request) { return quotaFetch(this.ctx.storage, request); }
}
export default worker;
