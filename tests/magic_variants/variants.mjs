// Build specific magic variants with 5etools' own code, as the oracle for magic_variants.py.
//
// Usage: node variants.mjs <5etools root> > result.json
// Loads items-base.json and magicvariants.json as the site does (resolving
// _copy) and prints every specific variant, with 5etools' private fields removed.
import fs from "fs";
import path from "path";

const root = path.resolve(process.argv[2]);
process.chdir(root);
await import(path.join(root, "js/parser.js"));
await import(path.join(root, "js/utils.js"));
await import(path.join(root, "js/render.js"));
await import(path.join(root, "js/render-dice.js"));
// The site's default style, not "classic"
globalThis.VetoolsConfig ||= {get: () => null};

const loaded = {};
DataUtil._pLoad = async ({url, id}) => (loaded[id] ||= JSON.parse(fs.readFileSync(path.join(root, url.split("?")[0]), "utf-8")));
const base = await DataUtil.loadJSON("data/items-base.json");
const variants = await DataUtil.loadJSON("data/magicvariants.json");
Renderer.item._addBasePropertiesAndTypes(base);
const [generic] = Renderer.item._getAndProcGenericVariants(variants);
const specific = Renderer.item._createSpecificVariants(base.baseitem, generic, {});

const out = specific.map(item => {
	const copy = {...item};
	if (copy._fullEntries) copy.entries = copy._fullEntries;
	for (const key of Object.keys(copy)) if (key.startsWith("_")) delete copy[key];
	return copy;
});
process.stdout.write(JSON.stringify(out));
