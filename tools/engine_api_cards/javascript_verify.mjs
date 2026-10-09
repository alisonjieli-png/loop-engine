// Ask a JavaScript library's published module about every class an expectations file lists, and write what it
// answered.
//
//     node javascript_verify.mjs MODULE expectations.json results.json
//
// For each class: the module exports it as a constructor; its parent is the expected one (by identity with the
// module's own export of that name, else by the parent constructor's name); every listed method is callable on the
// class (static), its prototype or a new instance; every listed property is held on the class (static), its
// prototypes or a new instance, or named in the source of the class or of a class it extends. A new instance is
// made with no arguments; a class that cannot be made that way is answered from its prototypes and sources alone.
// The answer lists what is missing; the caller decides what a missing property means for a card.
import { readFileSync, writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const RECORD_TYPE = 'javascript_class_check_results/v1';
const [modulePath, expectationsPath, resultsPath] = process.argv.slice(2);
if (!modulePath || !expectationsPath || !resultsPath) {
	console.error('usage: node javascript_verify.mjs MODULE expectations.json results.json');
	process.exit(2);
}
const library = await import(pathToFileURL(modulePath).href);
const expected = JSON.parse(readFileSync(expectationsPath, 'utf8'));
const exportedNames = new Map(Object.keys(library).map((name) => [library[name], name]));
const results = {};

for (const entry of expected.classes) {
	const value = library[entry.name];
	if (typeof value !== 'function') {
		results[entry.name] = { known: false };
		continue;
	}
	let instance = null;
	try {
		instance = new value();
	} catch (error) {
		instance = null;
	}
	const parent = Object.getPrototypeOf(value);
	const parentName = parent === Function.prototype || parent === null ? '' : (exportedNames.get(parent) ?? parent.name ?? '');
	// The source text of the class and of every class it extends, as the running module holds them: a property one
	// of them names ("this.name", or "Class.name" for a static) is confirmed there when no instance could be made
	// without arguments, when a parent's constructor assigns it, or when the class only reads a property a caller
	// assigns (an onSuccess callback).
	const named = { instance: new Set(), static: new Set() };
	for (let owner = value; typeof owner === 'function' && owner !== Function.prototype;
		owner = Object.getPrototypeOf(owner)) {
		const source = Function.prototype.toString.call(owner);
		for (const match of source.matchAll(/\bthis\.([A-Za-z_$][\w$]*)/g)) named.instance.add(match[1]);
		if (owner === value && value.name) {
			for (const match of source.matchAll(/(?<![\w$.])([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)/g)) {
				if (match[1] === value.name) named.static.add(match[2]);
			}
		}
	}
	const referenced = (name, isStatic) => (isStatic ? named.static : named.instance).has(name);
	const present = (name, isStatic) => (isStatic ? name in value || referenced(name, true)
		: name in value.prototype || (instance !== null && name in Object(instance)) || referenced(name, false));
	const callable = (name, isStatic) => (isStatic ? typeof value[name] === 'function'
		: typeof value.prototype[name] === 'function' || (instance !== null && typeof instance[name] === 'function')
			|| referenced(name, false));
	results[entry.name] = {
		known: true,
		parent: parentName,
		constructible: instance !== null,
		missing: {
			methods: entry.methods.filter((row) => !callable(row.name, row.static)).map((row) => row.name),
			members: entry.members.filter((row) => !present(row.name, row.static)).map((row) => row.name),
		},
	};
}

writeFileSync(resultsPath, JSON.stringify({ record_type: RECORD_TYPE, node: process.version, classes: results }));
