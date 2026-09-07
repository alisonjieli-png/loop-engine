// Trusted observation worker. Expected values stay in the host controller.
import { readFileSync } from 'node:fs';
import { clamp } from './clamp.mjs';

const decode = value => {
  if (value && typeof value === 'object' && !Array.isArray(value)
      && Object.keys(value).length === 1 && 'number' in value) {
    if (value.number === 'NaN') return NaN;
    if (value.number === 'Infinity') return Infinity;
    if (value.number === '-Infinity') return -Infinity;
  }
  return value;
};
const input = JSON.parse(readFileSync('audit-input.json', 'utf8'));
const observations = [];
for (const item of input.cases) {
  let value = null;
  let error = null;
  try {
    value = clamp(...item.arguments.map(decode));
    if (typeof value !== 'number' || !Number.isFinite(value)) {
      value = { invalid_return_type: typeof value };
    }
  } catch (caught) {
    error = caught && typeof caught.name === 'string' ? caught.name : 'UnknownError';
  }
  observations.push({ case_id: item.case_id, value, error });
}
process.stdout.write(JSON.stringify({ cases: observations }) + '\n');
