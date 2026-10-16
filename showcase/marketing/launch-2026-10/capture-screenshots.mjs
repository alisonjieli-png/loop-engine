/* Capture the launch press-kit screenshots from the live public websites.

   Read-only by construction: a fresh signed-out browser context for each viewport, GET and HEAD requests to the
   declared origins only, and no sign-in, form entry, download, payment or model call. Each image is encoded as WebP
   inside the browser and refused above the size ceiling. The record names every page's address, answer, heading,
   capture time and digest, so a reader can tell which live state an image shows.

   Usage: node showcase/marketing/launch-2026-10/capture-screenshots.mjs /absolute/new/output-directory */
import {mkdir, writeFile} from 'node:fs/promises';
import {resolve, dirname, isAbsolute} from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

export const MAX_IMAGE_BYTES = 400 * 1024;
export const MAX_IMAGES = 12;
export const QUALITIES = Object.freeze([0.86, 0.8, 0.74, 0.68, 0.6]);
export const VIEWPORTS = Object.freeze([
  {name: 'desktop', width: 1440, height: 900, mobile: false},
  {name: 'phone', width: 390, height: 844, mobile: true},
]);
export const ORIGINS = Object.freeze(['https://baltor.ai', 'https://agentfeeds.si']);
export const PAGES = Object.freeze([
  {id: 'home', url: 'https://baltor.ai/', subject: 'Baltor homepage'},
  {id: 'library', url: 'https://baltor.ai/library', subject: 'The library page with the live file count'},
  {id: 'component', url: 'https://baltor.ai/gallery/post-halftone-dots', subject: 'One component page'},
  {id: 'connect', url: 'https://baltor.ai/setup', subject: 'Get set up, the connect guide'},
  {id: 'pricing', url: 'https://baltor.ai/pricing', subject: 'Pricing'},
  {id: 'agentfeeds', url: 'https://agentfeeds.si/', subject: 'The AgentFeeds brand site'},
]);

/** True only for a GET or HEAD request to one of the declared HTTPS origins. */
export function allowRequest(method, url, origins = ORIGINS) {
  if (!['GET', 'HEAD'].includes(method)) return false;
  let parsed;
  try { parsed = new URL(url); } catch { return false; }
  return parsed.protocol === 'https:' && origins.includes(parsed.origin);
}

/** Problems with a declared capture set: too many images, a repeated page or an undeclared origin. */
export function checkTargets(pages = PAGES, viewports = VIEWPORTS, origins = ORIGINS) {
  const problems = [], seen = new Set();
  if (pages.length * viewports.length > MAX_IMAGES) problems.push(`more than ${MAX_IMAGES} images`);
  for (const page of pages) {
    if (seen.has(page.id)) problems.push('repeated page ' + page.id);
    seen.add(page.id);
    if (!allowRequest('GET', page.url, origins)) problems.push('undeclared origin ' + page.url);
  }
  return problems;
}

/** WebP bytes at the first tried quality that fits the ceiling. The encoding page makes no network request. */
export async function encodeWebp(page, png, maxBytes = MAX_IMAGE_BYTES, qualities = QUALITIES) {
  for (const quality of qualities) {
    const encoded = await page.evaluate(async ({source, quality}) => {
      const image = new Image();
      image.src = source;
      await image.decode();
      const canvas = document.createElement('canvas');
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      canvas.getContext('2d').drawImage(image, 0, 0);
      const address = canvas.toDataURL('image/webp', quality), prefix = 'data:image/webp;base64,';
      return address.startsWith(prefix) ? address.slice(prefix.length) : '';
    }, {source: 'data:image/png;base64,' + png.toString('base64'), quality});
    if (!encoded) throw new Error('This browser did not encode WebP.');
    const bytes = Buffer.from(encoded, 'base64');
    if (bytes.length <= maxBytes) return {bytes, quality};
  }
  throw new Error('No tried quality fits the image size ceiling.');
}

async function main(output) {
  if (!output || !isAbsolute(output)) throw new Error('Give a new absolute output directory.');
  const problems = checkTargets();
  if (problems.length) throw new Error(problems.join('; '));
  const here = dirname(fileURLToPath(import.meta.url)), repository = resolve(here, '../../..');
  const modules = resolve(process.env.BALTOR_SHOWCASE_MODULES || resolve(repository, 'showcase/node_modules'));
  const {chromium} = await import(pathToFileURL(resolve(modules, 'playwright-core/index.mjs')).href);
  const {findBrowser} = await import(pathToFileURL(resolve(repository, 'showcase/tools/media-common.mjs')).href);
  await mkdir(output); // An existing folder is refused, so an earlier capture is never replaced.
  const record = {
    record_type: 'baltor_launch_screenshots/v1', started_at: new Date().toISOString(), origins: ORIGINS,
    scope: 'Signed-out public pages, GET and HEAD to the declared origins only. No account, form, download, payment or model call.',
    images: [], blocked: [], errors: [],
  };
  const browser = await chromium.launch({executablePath: await findBrowser(), headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage']});
  try {
    const encoder = await browser.newPage();
    for (const viewport of VIEWPORTS) {
      const context = await browser.newContext({
        viewport: {width: viewport.width, height: viewport.height}, deviceScaleFactor: 1, isMobile: viewport.mobile,
        hasTouch: viewport.mobile, colorScheme: 'light', reducedMotion: 'reduce', serviceWorkers: 'block',
        acceptDownloads: false,
      });
      await context.route('**/*', route => {
        const request = route.request();
        if (allowRequest(request.method(), request.url())) return route.continue();
        record.blocked.push({method: request.method(), url: request.url()});
        return route.abort();
      });
      const page = await context.newPage();
      page.on('pageerror', error => record.errors.push({page: page.url(), error: error.message}));
      for (const target of PAGES) {
        const response = await page.goto(target.url, {waitUntil: 'networkidle', timeout: 45000});
        await page.evaluate(() => document.fonts.ready);
        await page.waitForTimeout(1200);
        const state = await page.evaluate(() => {
          const visible = node => node && node.getClientRects().length > 0 && getComputedStyle(node).visibility !== 'hidden';
          const heading = [...document.querySelectorAll('h1')].find(visible);
          return {title: document.title, heading: heading ? heading.textContent.replace(/\s+/g, ' ').trim() : '',
            sideways: document.scrollingElement.scrollWidth - innerWidth};
        });
        const {bytes, quality} = await encodeWebp(encoder, await page.screenshot({type: 'png'}));
        const file = `${target.id}-${viewport.name}.webp`;
        await writeFile(resolve(output, file), bytes, {flag: 'wx'});
        record.images.push({
          file, subject: target.subject, url: target.url, final_url: page.url(), status: response ? response.status() : null,
          viewport: `${viewport.width}x${viewport.height}`, title: state.title, heading: state.heading,
          sideways_pixels: state.sideways, captured_at: new Date().toISOString(), webp_quality: quality,
          bytes: bytes.length, sha256: createHash('sha256').update(bytes).digest('hex'),
        });
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
  record.finished_at = new Date().toISOString();
  record.passed = record.images.length === PAGES.length * VIEWPORTS.length && record.errors.length === 0
    && record.images.every(image => image.status === 200 && image.heading && image.bytes <= MAX_IMAGE_BYTES
      && image.sideways_pixels <= 1);
  await writeFile(resolve(output, 'capture-record.json'), JSON.stringify(record, null, 2) + '\n', {flag: 'wx'});
  console.log(JSON.stringify({output, passed: record.passed, images: record.images.length,
    blocked: record.blocked.length, errors: record.errors.length}));
  if (!record.passed) process.exitCode = 1;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) await main(process.argv[2]);
