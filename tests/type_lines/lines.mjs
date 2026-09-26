// What 5etools shows around an entity's entries, with its own code, as the
// oracle for core/text/prerequisites.py and the type lines in core/compact.py.
//
// Usage: node lines.mjs <5etools root> > result.json
// Prints {"prerequisites": [...], "compact": {...}}: every prerequisite in the
// data in the classic and one styles, and for each type what 5etools shows in
// classic style, assembled as the list of entries core/compact.py builds.
import fs from "fs";
import path from "path";

const root = path.resolve(process.argv[2]);
process.chdir(root);
await import(path.join(root, "js/parser.js"));
await import(path.join(root, "js/utils.js"));
await import(path.join(root, "js/render.js"));
await import(path.join(root, "js/render-dice.js"));
globalThis.VetoolsConfig = {get: () => "classic"};
// utils-ui.js needs a DOM; this is its intToBonus
globalThis.UiUtil = {intToBonus: (int, {isPretty = false} = {}) => `${int >= 0 ? "+" : int < 0 ? (isPretty ? "\u2212" : "-") : ""}${Math.abs(int)}`};
// No prerelease or homebrew content
globalThis.PrereleaseUtil = globalThis.BrewUtil2 = {getBrewProcessedFromCache: () => [], getMetaLookup: () => null};

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

const STYLE = {styleHint: "classic"};
const italic = text => text ? [`{@i ${text}}`] : [];

const BUILDERS = {
	trap: ["trapshazards.json", ent => {
		const meta = Renderer.trap.getTrapRenderableEntriesMeta(ent, STYLE);
		const entries = ent.entries || [];
		const body = Renderer.trap.TRAP_TYPES_CLASSIC.includes(ent.trapHazType)
			? [...(meta.entriesHeader || []), ...entries]
			: [...entries, ...(meta.entriesAttributes || [])];
		return [...italic(Renderer.traphazard.getSubtitle(ent, STYLE)), ...body];
	}],
	feat: ["feats.json", ent => {
		const joined = Renderer.feat.getJoinedCategoryPrerequisites(ent.category, Renderer.utils.prerequisite.getEntry(ent.prerequisite, STYLE));
		const repeatable = ent.repeatableHidden ? null : Renderer.utils.getRepeatableEntry(ent);
		return [...italic(joined), ...(repeatable ? [repeatable] : []), ...Renderer.feat.getFeatRendereableEntriesMeta(ent).entryMain.entries];
	}],
	deity: ["deities.json", ent => [...Renderer.deity.getDeityRenderableEntriesMeta(ent).entriesAttributes, ...(ent.entries || [])]],
	optionalfeature: ["optionalfeatures.json", ent => [
		...italic(Renderer.utils.prerequisite.getEntry(ent.prerequisite, STYLE)),
		...[Renderer.optionalfeature.getCostEntry(ent)].filter(Boolean),
		...(ent.entries || []),
		Renderer.optionalfeature.getTypeEntry(ent),
	]],
	facility: ["bastions.json", ent => {
		const meta = Renderer.facility.getFacilityRenderableEntriesMeta(ent);
		return [...(meta.entryLevel ? [meta.entryLevel] : []), ...meta.entriesDescription];
	}],
	object: ["objects.json", ent => {
		const meta = Renderer.object.getObjectRenderableEntriesMeta(ent);
		return [
			meta.entrySize,
			...Renderer.object.RENDERABLE_ENTRIES_PROP_ORDER__ATTRIBUTES.map(prop => meta[prop]).filter(Boolean),
			...(ent.entries || []),
			...(ent.actionEntries || []),
		];
	}],
	background: ["backgrounds.json", ent => {
		const prerequisite = Renderer.utils.prerequisite.getEntry(ent.prerequisite, STYLE);
		return [...(prerequisite ? [prerequisite] : []), ...(ent.entries || [])];
	}],
	vehicleUpgrade: ["vehicles.json", ent => {
		const meta = Renderer.vehicleUpgrade.getVehicleUpgradeRenderableEntriesMeta(ent, STYLE);
		return [...(meta.entrySummary ? [meta.entrySummary] : []), ...(meta.entryCost ? [meta.entryCost] : []), ...(ent.entries || [])];
	}],
	language: ["languages.json", ent => {
		const meta = Renderer.language.getLanguageRenderableEntriesMeta(ent);
		return [
			...[meta.entryType, meta.entryTypicalSpeakers, meta.entryOrigin, meta.entryScript].filter(Boolean),
			...(meta.entriesContent || []),
		];
	}],
	hazard: ["trapshazards.json", ent => [...italic(Renderer.traphazard.getSubtitle(ent, STYLE)), ...(ent.entries || [])]],
};

BUILDERS.race = [null, ent => {
	const meta = Renderer.race.getRaceRenderableEntriesMeta(ent, STYLE);
	const hw = ent.heightAndWeight && !ent._isBaseRace ? Renderer.race.getHeightAndWeightEntries(ent, {isStatic: true}) : [];
	const out = [...(meta.entryAttributes ? [meta.entryAttributes] : []), ...(meta.entryMain.entries || []), ...hw];
	// A base race's list names a subrace's source in a <span> when two share a name
	return JSON.parse(JSON.stringify(out).replace(/<span title=\\"[^"\\]*\\">([^<]*)<\/span>/g, "$1"));
}];
const races = await DataUtil.race.loadJSON({isAddBaseRaces: true});

const compact = {};
for (const [prop, [file, build]] of Object.entries(BUILDERS)) {
	compact[prop] = (file ? (await load(file))[prop] || [] : races.race)
		.map(ent => ({name: ent.name, source: ent.source, entries: build(MiscUtil.copyFast(ent))}));
}

process.stdout.write(JSON.stringify({prerequisites, compact}));
