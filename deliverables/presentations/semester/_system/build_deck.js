// Build one meeting deck and its speaking materials from <folder>/source/deck.js.
//   node build_deck.js ../2026-10-27
// Writes <folder>/<file>.pptx, script.md (word for word), speaker_notes.md and manifest.json.
// The PPTX notes, the script and the speaker notes come from the same source, so they always match.
const path = require("path");
const fs = require("fs");
// Deck sources live outside _system/; let them resolve packages from _system/node_modules.
process.env.NODE_PATH = [path.join(__dirname, "node_modules"), process.env.NODE_PATH].filter(Boolean).join(path.delimiter);
require("module").Module._initPaths();
const D = require("./design");
const { applyTheme } = require("./theme");

const WPM = 140;

// Spoken-length estimate: numerals are read as several words ("0.0093" → "zero point zero zero
// nine three"), so each numeric token counts as ~0.8 words per digit, plus one for a decimal point.
function words(s) {
  const toks = s.match(/[A-Za-z0-9][A-Za-z0-9'’.,%–-]*/g) || [];
  let n = 0;
  for (const t of toks) {
    const digits = (t.match(/[0-9]/g) || []).length;
    if (!digits) n += 1;
    else n += Math.max(1, Math.round(digits * 0.8)) + (/[0-9]\.[0-9]/.test(t) ? 1 : 0) + (t.includes("%") ? 1 : 0);
  }
  return n;
}
function mmss(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec - 60 * m);
  return s === 60 ? `${m + 1}:00` : `${m}:${String(s).padStart(2, "0")}`;
}

async function build(folder) {
  const deck = require(path.join(folder, "source", "deck.js"));
  const { meta, slides } = deck;
  const { pres, C } = D.newDeck(meta);
  const ctx = {
    pres, C, D, meta,
    F: (n) => path.join(D.FIG, n),
    R: (n) => path.join(D.RES_FIG, n),
    S: (n) => path.join(D.SEM_FIG, n),
  };

  let t = 0;
  let section = null;
  const timing = [];
  for (let i = 0; i < slides.length; i++) {
    const sl = slides[i];
    const sec = sl.section || "Main";
    if (sec !== section) {
      pres.addSection({ title: sec });
      section = sec;
    }
    const master = sl.master || "CONTENT";
    const s = pres.addSlide({ masterName: master, sectionTitle: sec });
    if (master !== "TITLE") {
      if (sl.kicker) D.kicker(s, master === "CLOSE" ? { ...C, accent1: "7FD6D3" } : C, sl.kicker);
      s.addText(sl.title, { placeholder: "title" });
    }
    await sl.build(s, ctx);
    const n = sl.backup ? 0 : words(sl.script);
    const dur = (n / WPM) * 60;
    const range = sl.backup ? "backup" : `${mmss(t)}–${mmss(t + dur)}`;
    timing.push({ i: i + 1, title: sl.title, speaker: sl.speaker, range, words: n, seconds: dur, backup: !!sl.backup });
    t += dur;
    const notes =
      `[${sl.speaker}${sl.backup ? " · backup, for questions" : ` · ${range}`}]\n\n` +
      sl.script.trim() +
      (sl.keyPoints && sl.keyPoints.length ? `\n\nKey points: ${sl.keyPoints.join("; ")}.` : "") +
      (sl.sources ? `\n\nSources: ${sl.sources}` : "");
    s.addNotes(notes);
  }

  const out = path.join(folder, `${meta.file}.pptx`);
  await pres.writeFile({ fileName: out });
  await applyTheme(out, D.THEME);

  const core = timing.filter((x) => !x.backup);
  const total = core.reduce((a, x) => a + x.seconds, 0);
  const totalWords = core.reduce((a, x) => a + x.words, 0);
  const bySpeaker = {};
  core.forEach((x) => {
    for (const sp of x.speaker.split(/\s*(?:&|and|\+)\s*/)) {
      bySpeaker[sp] = (bySpeaker[sp] || 0) + x.seconds / x.speaker.split(/\s*(?:&|and|\+)\s*/).length;
    }
  });
  const manifest = {
    id: meta.id, date: meta.dateLong, topic: meta.topic, file: meta.file, retrospective: !!meta.retrospective,
    slides: slides.length, coreSlides: core.length, backupSlides: slides.length - core.length,
    words: totalWords, minutes: +(total / 60).toFixed(2), speakers: Object.fromEntries(Object.entries(bySpeaker).map(([k, v]) => [k, +(v / 60).toFixed(2)])),
    split: meta.split, splitStatus: meta.splitStatus,
  };
  fs.writeFileSync(path.join(folder, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");

  // ---------------------------------------------------------------- script.md (word for word)
  const head = (title) => [
    `# ${title}`,
    "",
    "| | |",
    "|-----------|-------------------------------------------------------------|",
    `| **Meeting** | ${meta.dateLong} (meeting ${meta.index + 1} of 7): ${meta.topic} |`,
    `| **Deck** | \`${meta.file}.pptx\` (${core.length} slides${slides.length > core.length ? ` + ${slides.length - core.length} backup` : ""}) |`,
    `| **Speakers** | ${meta.split} (${meta.splitStatus}) |`,
    `| **Length** | ≈ ${mmss(total)} of speech (≈ ${totalWords} spoken words at ${WPM} words per minute, numerals expanded); ${Object.entries(bySpeaker).map(([k, v]) => `${k} ≈ ${mmss(v)}`).join(", ")} |`,
    meta.retrospective ? `| **Status** | Retrospective reconstruction prepared in October 2026; see the note below |` : `| **Status** | ${meta.status} |`,
    "",
  ];
  const md = head(`Q-TRACE — ${meta.topic}: word-for-word script`);
  if (meta.scriptNote) md.push(`> ${meta.scriptNote}`, "");
  slides.forEach((sl, i) => {
    const tm = timing[i];
    md.push(`## Slide ${i + 1}: ${sl.title}`, "", `**${sl.speaker}**${tm.backup ? " · backup slide, for questions only" : ` · ${tm.range}`}`, "");
    sl.script.trim().split(/\n\s*\n/).forEach((p) => md.push(`> ${p.trim()}`, ">"));
    md.pop();
    md.push("");
  });
  if (meta.delivery && meta.delivery.length) {
    md.push("## Delivery notes", "");
    meta.delivery.forEach((d) => md.push(`- ${d}`));
    md.push("");
  }
  fs.writeFileSync(path.join(folder, "script.md"), md.join("\n"));

  // ---------------------------------------------------------------- speaker_notes.md
  const sn = head(`Q-TRACE — ${meta.topic}: speaker notes`);
  sn.push("| # | Slide | Speaker | Time | Key points | Transition |", "|--|----------------|-------|---------|----------------------------------|--------------|");
  slides.forEach((sl, i) => {
    const tm = timing[i];
    const kp = (sl.keyPoints || []).join("; ").replace(/\|/g, "/");
    sn.push(`| ${i + 1} | ${sl.title.replace(/\|/g, "/")} | ${sl.speaker} | ${tm.range} | ${kp} | ${(sl.transition || "—").replace(/\|/g, "/")} |`);
  });
  sn.push("", "## Sources for the numbers on these slides", "");
  slides.forEach((sl, i) => {
    if (sl.sources) sn.push(`- **Slide ${i + 1}:** ${sl.sources}`);
  });
  sn.push("", "Every number traces to `results/tables/`; see `../FIGURES.md` and `deliverables/figures/FIGURES.md`.", "");
  fs.writeFileSync(path.join(folder, "speaker_notes.md"), sn.join("\n"));

  console.log(`${meta.id}: ${slides.length} slides, ${totalWords} words, ${mmss(total)}  ->  ${path.relative(process.cwd(), out)}`);
}

const folders = process.argv.slice(2);
if (!folders.length) {
  console.error("usage: node build_deck.js <meeting-folder> [...]");
  process.exit(2);
}
(async () => {
  for (const f of folders) await build(path.resolve(f));
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
