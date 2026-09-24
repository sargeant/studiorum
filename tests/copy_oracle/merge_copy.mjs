// Resolve _copy with 5etools' own code, as the oracle for merge_copy.py.
//
// Usage: node merge_copy.mjs <5etools root> < request.json > result.json
// The request is {"files": [path, ...]}. Every entity with a _copy is resolved
// against all entities of its prop across the files, in file order, and the
// result lists those entities as {prop, index, entity} or {prop, index, error}.
import fs from "fs";
import path from "path";

const root = path.resolve(process.argv[2]);
process.chdir(root);
await import(path.join(root, "js/parser.js"));
await import(path.join(root, "js/utils.js"));
await import(path.join(root, "js/render.js"));
await import(path.join(root, "js/hist.js"));

// Read files from disk, once each as the site's loader does; DataUtil.loadJSON
// still merges their internal copies
const loaded = {};
DataUtil._pLoad = async ({url, id}) => (loaded[id] ||= JSON.parse(fs.readFileSync(path.join(root, url.split("?")[0]), "utf-8")));

const request = JSON.parse(fs.readFileSync(0, "utf-8"));
const byProp = {};
for (const file of request.files) {
	const data = JSON.parse(fs.readFileSync(file, "utf-8"));
	for (const [prop, entities] of Object.entries(data)) {
		if (prop === "_meta" || !Array.isArray(entities)) continue;
		for (const ent of entities) {
			if (ent == null || typeof ent !== "object") continue;
			ent.__prop = prop;
			(byProp[prop] ||= []).push(ent);
		}
	}
}

const out = [];
for (const [prop, entities] of Object.entries(byProp)) {
	const copies = entities.map((ent, index) => [ent, index]).filter(([ent]) => ent._copy);
	for (const [ent, index] of copies) {
		try {
			const impl = DataUtil[prop];
			if (!impl?.pMergeCopy) throw new Error(`No _copy merge strategy for "${prop}"`);
			await impl.pMergeCopy(entities, ent, {isErrorOnMissing: true});
		} catch (e) {
			out.push({prop, index, error: String(e.message || e)});
			continue;
		}
	}
	for (const [ent, index] of copies) {
		if (out.some(it => it.prop === prop && it.index === index)) continue;
		delete ent.__prop;
		out.push({prop, index, entity: ent});
	}
}
process.stdout.write(JSON.stringify(out));
