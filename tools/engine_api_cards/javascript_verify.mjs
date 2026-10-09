// Ask a JavaScript library's published module about every class an expectations file lists, and write what it
// answered.
//
//     node javascript_verify.mjs MODULE expectations.json results.json
//
// For each class: the module exports it as a constructor; its parent is the expected one (by identity with the
// module's own export of that name, else by the parent constructor's name); every listed method is callable on the
// class (static), its prototype or a new instance; every listed property is present on the class (static), its
// prototype or a new instance. A new instance is made with no arguments; a class that cannot be made that way is
// answered from its prototype alone.
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
	// The class's own source text, as the running module holds it: a member its constructor assigns
	// ("this.name = ...") is confirmed there when no instance could be made without arguments.
	const source = Function.prototype.toString.call(value);
	const assigned = (name) => new RegExp(`\\bthis\\.${name.replace(/[$]/g, '\\$&')}\\s*=(?!=)`).test(source);
	const present = (name, isStatic) => (isStatic ? name in value
		: name in value.prototype || (instance !== null && name in Object(instance)) || assigned(name));
	const callable = (name, isStatic) => (isStatic ? typeof value[name] === 'function'
		: typeof value.prototype[name] === 'function' || (instance !== null && typeof instance[name] === 'function')
			|| assigned(name));
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
