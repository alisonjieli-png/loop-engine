import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {allowRequest, checkTargets, PAGES, VIEWPORTS, MAX_IMAGES, MAX_IMAGE_BYTES} from './capture-screenshots.mjs';

test('only GET and HEAD to a declared HTTPS origin are allowed', () => {
  assert.equal(allowRequest('GET', 'https://baltor.ai/library'), true);
  assert.equal(allowRequest('HEAD', 'https://agentfeeds.si/'), true);
  const refused = [
    ['POST', 'https://baltor.ai/api/v1/waitlist'], ['PUT', 'https://agentfeeds.si/'], ['GET', 'https://example.com/'],
    ['GET', 'http://baltor.ai/'], ['GET', 'https://baltor.ai.example.com/'], ['GET', 'not an address'],
  ];
  for (const [method, url] of refused) assert.equal(allowRequest(method, url), false, `${method} ${url}`);
});

test('the declared set is twelve images at most, on declared origins, without repeats', () => {
  assert.deepEqual(checkTargets(), []);
  assert.ok(PAGES.length * VIEWPORTS.length <= MAX_IMAGES);
  assert.ok(checkTargets([...PAGES, {id: 'docs', url: 'https://baltor.ai/docs'}]).some(text => text.includes('images')));
  assert.ok(checkTargets([{id: 'other', url: 'https://example.com/'}]).some(text => text.includes('origin')));
  assert.ok(checkTargets([PAGES[0], PAGES[0]]).some(text => text.includes('repeated')));
  assert.equal(MAX_IMAGE_BYTES, 409600);
});

test('the viewports are the declared desktop and phone sizes', () => {
  assert.deepEqual(VIEWPORTS.map(({width, height}) => `${width}x${height}`), ['1440x900', '390x844']);
});

test('the capture script fills no form, clicks nothing and reads no stored state', async () => {
  const source = await readFile(new URL('./capture-screenshots.mjs', import.meta.url), 'utf8');
  for (const forbidden of ['.fill(', '.click(', '.check(', 'localStorage', 'sessionStorage', 'document.cookie', 'storageState'])
    assert.ok(!source.includes(forbidden), forbidden);
});
