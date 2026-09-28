// What 5etools' class page shows in each class table, with its own code, as the
// oracle for data/class_entries.py's class_progression and the cells
// mcp/tools/progression.py renders.
//
// Usage: node progression.mjs <5etools root> > result.json
// Prints [{name, source, subclass, labels, levels: [{level, pb, cells}]}] for
// every class, and again with each subclass that adds table columns. The
// rows follow ClassesPage._render_renderClassTable_getMetasTblRows
// (js/classes.js), which needs a DOM, with the header and cell HTML as text.
import fs from "fs";
import path from "path";

const root = path.resolve(process.argv[2]);
process.chdir(root);
await import(path.join(root, "js/parser.js"));
await import(path.join(root, "js/utils.js"));
await import(path.join(root, "js/render.js"));
await import(path.join(root, "js/render-dice.js"));
globalThis.VetoolsConfig = {get: () => "classic"};

const text = html => html.replace(/<[^>]+>/g, "").replace(/&amp;/g, "&").replace(/&quot;/g, "\"").replace(/&#39;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">");
const render = value => text(Renderer.get().render(value));

// _render_renderClassTable_getCellsGenericRow, without the spell point columns
const cells = (group, ixLvl) => {
	const prop = group.rowsSpellProgression?.[ixLvl] ? "rowsSpellProgression" : "rows";
	return (group[prop][ixLvl] || []).map(cell => cell === 0 ? "—" : render(cell));
};

const table = (cls, groups, subclass) => ({
	name: cls.name,
	source: cls.source,
	subclass,
	labels: groups.flatMap(group => group.colLabels.map(render)),
	// The page groups classFeatures into one list per level, 20 of them
	levels: Array.from({length: 20}, (_, ixLvl) => ({
		level: ixLvl + 1,
		pb: Math.ceil((ixLvl + 1) / 4) + 1,
		cells: groups.flatMap(group => cells(group, ixLvl)),
	})),
});

const out = [];
const index = JSON.parse(fs.readFileSync("data/class/index.json", "utf-8"));
for (const file of Object.values(index)) {
	const data = JSON.parse(fs.readFileSync(path.join("data/class", file), "utf-8"));
	for (const cls of data.class || []) {
		const groups = cls.classTableGroups || [];
		out.push(table(cls, groups, null));
		for (const sc of data.subclass || []) {
			if (!sc.subclassTableGroups || sc.className !== cls.name || sc.classSource !== cls.source) continue;
			out.push(table(cls, [...groups, ...sc.subclassTableGroups], {name: sc.name, shortName: sc.shortName, source: sc.source}));
		}
	}
}
process.stdout.write(JSON.stringify(out));
