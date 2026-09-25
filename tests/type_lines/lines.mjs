// What 5etools shows around an entity's entries, with its own code, as the
// oracle for core/text/prerequisites.py and the type lines in core/compact.py.
//
// Usage: node lines.mjs <5etools root> > result.json
// Prints {"prerequisites": [...]}: every prerequisite in the data, in the
// classic and one styles.
import fs from "fs";
import path from "path";

const root = path.resolve(process.argv[2]);
process.chdir(root);
await import(path.join(root, "js/parser.js"));
await import(path.join(root, "js/utils.js"));
await import(path.join(root, "js/render.js"));
await import(path.join(root, "js/render-dice.js"));
globalThis.VetoolsConfig = {get: () => "classic"};

const loaded = {};
DataUtil._pLoad = async ({url, id}) => (loaded[id] ||= JSON.parse(fs.readFileSync(path.join(root, url.split("?")[0]), "utf-8")));
const load = async file => DataUtil.loadJSON(`data/${file}`);

const FILES = {
	feat: "feats.json",
	optionalfeature: "optionalfeatures.json",
	background: "backgrounds.json",
	facility: "bastions.json",
	charoption: "charcreationoptions.json",
	race: "races.json",
	reward: "rewards.json",
};

const prerequisites = [];
for (const [prop, file] of Object.entries(FILES)) {
	for (const ent of (await load(file))[prop] || []) {
		if (!ent.prerequisite) continue;
		for (const style of ["classic", "one"]) {
			prerequisites.push({
				prerequisite: ent.prerequisite,
				style,
				text: Renderer.utils.prerequisite.getEntry(ent.prerequisite, {styleHint: style}),
			});
		}
	}
}

process.stdout.write(JSON.stringify({prerequisites}));
