/* Exercise the packaged example through the real service, including its CSP.
   No model, customer account or external asset is used. Output must be new. */
import {chromium} from '../showcase/node_modules/playwright-core/index.mjs';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';

const [base, suppliedOutput] = process.argv.slice(2);
if (!base || !suppliedOutput) throw new Error('Usage: node tools/check_creative_arena.mjs BASE_URL NEW_OUTPUT_DIRECTORY');
const output = resolve(suppliedOutput);
await mkdir(output);
const browser = await chromium.launch({
  executablePath: process.env.CHROME_BIN || '/opt/google/chrome/chrome',
  headless: true, args: ['--no-sandbox', '--enable-unsafe-swiftshader'],
});
const page = await browser.newPage({viewport: {width: 1440, height: 960}, acceptDownloads: true});
const errors = [];
page.on('pageerror', error => errors.push(error.message));
page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
function readGlb(bytes) {
  if (bytes.readUInt32LE(0) !== 0x46546c67 || bytes.readUInt32LE(4) !== 2 || bytes.readUInt32LE(8) !== bytes.length) {
    throw new Error('Export is not a complete glTF 2 binary.');
  }
  return JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
}
try {
  const response = await page.goto(new URL('/demo/ashen-wilds', base).href);
  await page.locator('[data-view="creative-arena"]:visible iframe').waitFor();
  const frame = await page.locator('.creative-arena-frame').contentFrame();
  await frame.locator('#begin').waitFor();
  const actualFrame = page.frames().find(value => new URL(value.url()).pathname === '/assets/creative-arena/index.html');
  await actualFrame.waitForFunction(() => window.baltorArena?.inspect().renderedFrames > 5, null, {timeout: 45000});
  const initial = await actualFrame.evaluate(() => window.baltorArena.inspect());
  await page.screenshot({path: output + '/desktop.png', fullPage: true});
  await frame.locator('#begin').click();
  await frame.locator('#world').focus();
  await page.keyboard.down('KeyW');
  await page.waitForTimeout(750);
  await page.keyboard.up('KeyW');
  const moved = await actualFrame.evaluate(() => window.baltorArena.inspect());
  await frame.locator('#pause').click();
  await frame.locator('#scene-tools summary').click();
  await frame.locator('#motion').selectOption('Run');
  await frame.locator('#atmosphere').selectOption('dawn');
  await page.waitForTimeout(500);
  const revised = await actualFrame.evaluate(() => window.baltorArena.inspect());
  const exports = {};
  for (const [button, name] of [['#export-character', 'warden.glb'], ['#export-scene', 'arena.glb']]) {
    const downloadEvent = page.waitForEvent('download');
    await frame.locator(button).click();
    const download = await downloadEvent;
    await download.saveAs(output + '/' + name);
    const bytes = await readFile(output + '/' + name);
    const gltf = readGlb(bytes);
    exports[name] = {bytes: bytes.length, skins: gltf.skins?.length || 0,
      animations: gltf.animations?.map(value => value.name) || [], nodes: gltf.nodes?.length || 0};
  }
  await page.screenshot({path: output + '/revised.png', fullPage: true});
  await page.setViewportSize({width: 390, height: 844});
  await page.waitForTimeout(400);
  await page.screenshot({path: output + '/phone.png', fullPage: true});
  const phoneFits = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  const frameFits = await actualFrame.evaluate(() => document.documentElement.scrollWidth <= innerWidth);
  const checks = {
    served: response.status() === 200,
    moved: moved.hero.z < initial.hero.z - .2,
    meaningful_revision: revised.motion === 'Run' && revised.environment === 'dawn',
    rigged_character: exports['warden.glb'].skins > 0 && exports['warden.glb'].animations.length === 4,
    complete_scene: exports['arena.glb'].skins > exports['warden.glb'].skins,
    phone_fits: phoneFits && frameFits,
    no_browser_errors: errors.length === 0,
  };
  const report = {record_type: 'creative_arena_browser_check/v1', base, checks, initial, moved, revised, exports, errors,
    webmcp_available: await actualFrame.evaluate(() => Boolean(document.modelContext?.registerTool)),
    passed: Object.values(checks).every(Boolean),
    limits: ['Software-rendered desktop Chromium and a resized viewport, not physical-device coverage.',
      'Browser controls and exported data are checked; Blender reopen and renderer qualification are separate.']};
  await writeFile(output + '/report.json', JSON.stringify(report, null, 2) + '\n', {flag: 'wx'});
  console.log(JSON.stringify(report));
  process.exitCode = report.passed ? 0 : 1;
} finally {
  await browser.close();
}
