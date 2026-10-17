// Ask a CommonJS library's published module about every card an expectations file lists, and write what it
// answered.
//
//     node javascript_members_verify.mjs MODULE expectations.json results.json
//
// Each card names a property path from the module's export ([] is the export itself) and its kind. A function card's
// value must be a function. An object card's value must be an object or a function, and each listed method must be a
// function on it and each listed property must be held by it (its own, or by a prototype it inherits). A member card
// asks the same of one member. The answer lists what is missing; the caller decides what that means for a card.
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const RECORD_TYPE = 'javascript_member_check_results/v1';
const [modulePath, expectationsPath, resultsPath] = process.argv.slice(2);
if (!modulePath || !expectationsPath || !resultsPath) {
	console.error('usage: node javascript_members_verify.mjs MODULE expectations.json results.json');
	process.exit(2);
}
const require = createRequire(modulePath);
const library = require(modulePath);
const expected = JSON.parse(readFileSync(expectationsPath, 'utf8'));
const results = {};

const walk = (path) => {
	let value = library;
	for (const part of path) {
		if (value === null || value === undefined || !(part in Object(value))) return undefined;
		value = value[part];
	}
	return value;
};
// A method must be a function; a property must be held, which "in" answers without running a getter.
const holds = (value, row) => (row.kind === 'method'
	? typeof Object.getOwnPropertyDescriptor(value, row.name)?.value === 'function' || typeof value[row.name] === 'function'
	: row.name in Object(value));

for (const card of expected.cards) {
	const member = card.kind === 'method' || card.kind === 'property';
	// A member is asked of its owner: reading a getter (Express's req.fresh) on a prototype would run it.
	const value = walk(member ? card.path.slice(0, -1) : card.path);
	if (value === undefined) {
		results[card.card] = { known: false };
		continue;
	}
	if (member) {
		const row = { name: card.path[card.path.length - 1], kind: card.kind };
		results[card.card] = { known: true, kind_matches: holds(value, row), missing: [] };
		continue;
	}
	const kind = typeof value;
	if (card.kind === 'function') {
		results[card.card] = { known: true, kind_matches: kind === 'function', missing: [] };
		continue;
	}
	if (card.kind === 'object') {
		const matches = kind === 'object' || kind === 'function';
		const missing = matches ? card.members.filter((row) => !holds(value, row)).map((row) => row.name) : [];
		results[card.card] = { known: true, kind_matches: matches, missing };
		continue;
	}
	results[card.card] = { known: true, kind_matches: false, missing: [] };
}

writeFileSync(resultsPath, JSON.stringify({ record_type: RECORD_TYPE, node: process.version, cards: results }));
