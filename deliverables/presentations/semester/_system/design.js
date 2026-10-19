// Q-TRACE semester presentation design system (pptxgenjs, structured decks).
// One theme, three layouts (TITLE, CONTENT, CLOSE) and composable helpers shared by all seven
// meeting decks. Every number placed on a slide comes from results/tables/ (see ../FIGURES.md).
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

const SYSTEM = __dirname;
const ROOT = path.resolve(SYSTEM, "..", "..", "..", "..");
const FIG = path.join(ROOT, "deliverables", "figures"); // publication figures
const RES_FIG = path.join(ROOT, "results", "figures"); // phase-script figures
const SEM_FIG = path.join(SYSTEM, "figures"); // semester figures

const THEME = {
  name: "Q-TRACE",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1A1F2B",
    lt1: "FFFFFF",
    dk2: "1B2A49", // navy, dominant
    lt2: "EEF2F7", // light panel
    accent1: "0F8B8D", // teal: mitigation, the probe rule
    accent2: "E8A33D", // amber: cost, attention, "today"
    accent3: "C0392B", // red: failure, limitation
    accent4: "56B4E9", // sky
    accent5: "6B7280", // grey
    accent6: "0072B2", // blue
    hlink: "0F8B8D",
    folHlink: "1B2A49",
  },
};
const HEX = THEME.colors;
const W = 13.333;
const H = 7.5;
const MX = 0.6; // horizontal margin
const BODY_TOP = 1.5;
const BODY_BOTTOM = 6.75;

// The seven scheduled meetings (dates supplied by the team; see semester/README.md).
const MEETINGS = [
  { id: "2026-09-15", short: "Sep 15", topic: "Proposal" },
  { id: "2026-09-29", short: "Sep 29", topic: "Design" },
  { id: "2026-10-13", short: "Oct 13", topic: "Implementation" },
  { id: "2026-10-27", short: "Oct 27", topic: "Noise & mitigation" },
  { id: "2026-11-10", short: "Nov 10", topic: "Policy selection" },
  { id: "2026-11-24", short: "Nov 24", topic: "Final findings" },
  { id: "2026-12-08", short: "Dec 8", topic: "Final defense" },
];

const AUTHORS = "Mayank Kumar Pokhriyal  ·  Tushar Poonia";
const PROGRAM = "M.S. in Artificial Intelligence capstone  ·  Katz School of Science and Health, Yeshiva University";

function newDeck(meta) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = `Q-TRACE — ${meta.topic} (${meta.dateLong})`;
  pres.subject = meta.subject || meta.topic;
  pres.author = "Mayank Kumar Pokhriyal; Tushar Poonia";
  pres.company = "Katz School of Science and Health, Yeshiva University";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  const footer =
    `Q-TRACE  ·  ${meta.topic}  ·  ${meta.dateLong}` +
    (meta.retrospective ? "  ·  retrospective reconstruction, prepared Oct 2026" : "");

  pres.defineSlideMaster({ title: "TITLE", background: { color: HEX.dk2 }, objects: [] });
  const titleOpts = (color) => ({
    placeholder: {
      options: {
        name: "title", type: "title", x: MX, y: 0.5, w: W - 2 * MX, h: 0.8, fontSize: 28, bold: true,
        color, fontFace: THEME.headFontFace, valign: "middle", margin: 0,
      },
      text: "",
    },
  });
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: HEX.lt1 },
    objects: [
      { text: { text: footer, options: { x: MX, y: 7.06, w: 11.2, h: 0.28, fontSize: 9, color: C.accent5, margin: 0 } } },
      titleOpts(C.text2),
    ],
    slideNumber: { x: 12.15, y: 7.02, w: 0.6, h: 0.32, fontSize: 9, color: C.accent5, align: "right" },
  });
  pres.defineSlideMaster({
    title: "CLOSE",
    background: { color: HEX.dk2 },
    objects: [
      { text: { text: footer, options: { x: MX, y: 7.06, w: 11.2, h: 0.28, fontSize: 9, color: "AFC2DC", margin: 0 } } },
      titleOpts(C.background1),
    ],
    slideNumber: { x: 12.15, y: 7.02, w: 0.6, h: 0.32, fontSize: 9, color: "AFC2DC", align: "right" },
  });
  return { pres, C };
}

// ---------------------------------------------------------------------------- primitives

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

function img(slide, file, box, { center = true, name, valign = "middle" } = {}) {
  if (!fs.existsSync(file)) throw new Error(`missing image ${file}`);
  const { w, h } = pngSize(file);
  const r = w / h;
  let iw = box.w;
  let ih = iw / r;
  if (ih > box.h) {
    ih = box.h;
    iw = ih * r;
  }
  const x = center ? box.x + (box.w - iw) / 2 : box.x;
  const y = valign === "top" ? box.y : box.y + (box.h - ih) / 2;
  slide.addImage({ path: file, x, y, w: iw, h: ih, objectName: name || path.basename(file) });
  return { x, y, w: iw, h: ih };
}

const iconCache = new Map();
async function iconData(Icon, color = "#FFFFFF") {
  const key = Icon.name + color;
  if (!iconCache.has(key)) {
    const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Icon, { color, size: "256" }));
    const buf = await sharp(Buffer.from(svg)).png().toBuffer();
    iconCache.set(key, "image/png;base64," + buf.toString("base64"));
  }
  return iconCache.get(key);
}

async function icon(slide, Icon, x, y, d, fill, name, color = "#FFFFFF") {
  slide.addShape("ellipse", { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill }, objectName: (name || "icon") + "-circle" });
  const pad = d * 0.24;
  slide.addImage({ data: await iconData(Icon, color), x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: name || "icon" });
}

function text(slide, value, box, opts = {}) {
  slide.addText(value, { margin: 0, valign: "top", isTextBox: true, fontSize: 14, ...box, ...opts });
}

function kicker(slide, C, value) {
  text(slide, value.toUpperCase(), { x: MX, y: 0.2, w: W - 2 * MX, h: 0.3 }, {
    fontSize: 10.5, bold: true, color: C.accent1, charSpacing: 1.5, objectName: "kicker",
  });
}

function card(slide, box, fill = HEX.lt2, name, line) {
  slide.addShape("roundRect", { ...box, rectRadius: 0.07, fill: { color: fill }, line: { color: line || fill, width: line ? 1 : 0.5 }, objectName: name || "card" });
}

// Card with a bold heading and body text (array of runs or string).
function cardText(slide, C, { x, y, w, h, head, body, fill = HEX.lt2, headColor, size = 14, headSize = 15.5, name, line }) {
  card(slide, { x, y, w, h }, fill, (name || "card") + "-bg", line);
  const runs = [];
  if (head) runs.push({ text: head, options: { bold: true, fontSize: headSize, color: headColor || C.text2, breakLine: true, paraSpaceAfter: 4 } });
  const items = Array.isArray(body) ? body : [body];
  items.forEach((b, i) => {
    const t = typeof b === "string" ? { text: b } : b;
    runs.push({ text: t.text, options: { fontSize: t.size || size, bold: !!t.bold, color: t.color || C.text1, bullet: t.bullet ? { indent: 14 } : false, breakLine: i < items.length - 1, paraSpaceAfter: 4 } });
  });
  slide.addText(runs, { x: x + 0.2, y: y + 0.14, w: w - 0.4, h: h - 0.24, margin: 0, valign: "top", isTextBox: true, objectName: name || "card-text" });
}

function bullets(slide, C, items, box, { fontSize = 16, name, color, space = 7 } = {}) {
  const runs = items.map((it, i) => {
    const t = typeof it === "string" ? { text: it } : it;
    return {
      text: t.text,
      options: {
        bullet: t.sub ? { indent: 16 } : { indent: 16 },
        indentLevel: t.sub ? 1 : 0,
        bold: !!t.bold,
        color: t.color || color || C.text1,
        fontSize: t.sub ? fontSize - 2 : fontSize,
        breakLine: i < items.length - 1,
        paraSpaceAfter: space,
      },
    };
  });
  slide.addText(runs, { ...box, valign: "top", margin: 0.02, isTextBox: true, objectName: name || "bullets" });
}

// Big number with a label underneath.
function stat(slide, C, { x, y, w, value, label, color, valueSize = 34, labelSize = 12.5, name, labelH = 0.7 }) {
  text(slide, value, { x, y, w, h: valueSize / 52 }, { fontSize: valueSize, bold: true, color: color || C.accent1, fontFace: THEME.headFontFace, objectName: (name || "stat") + "-value" });
  text(slide, label, { x, y: y + valueSize / 52 + 0.04, w, h: labelH }, { fontSize: labelSize, color: C.text1, objectName: (name || "stat") + "-label" });
}

function caption(slide, C, value, box, name) {
  text(slide, value, box, { fontSize: 10.5, italic: true, color: C.accent5, objectName: name || "caption" });
}

function source(slide, C, value, y = 6.72) {
  text(slide, "Source: " + value, { x: MX, y, w: W - 2 * MX, h: 0.26 }, { fontSize: 9, color: C.accent5, objectName: "source" });
}

function chip(slide, C, value, { x, y, w, h = 0.32, fill = HEX.accent2, color = "FFFFFF", fontSize = 10.5, name }) {
  slide.addShape("roundRect", { x, y, w, h, rectRadius: 0.16, fill: { color: fill }, line: { color: fill }, objectName: (name || "chip") + "-bg" });
  text(slide, value, { x, y, w, h }, { fontSize, bold: true, color, align: "center", valign: "middle", objectName: name || "chip" });
}

// Highlighted one-line message at the bottom of a content slide.
async function takeaway(slide, C, value, { y = 6.08, h = 0.56, Icon, x = MX, w = W - 2 * MX } = {}) {
  card(slide, { x, y, w, h }, "E3F2F1", "takeaway-bg");
  if (Icon) await icon(slide, Icon, x + 0.14, y + (h - 0.38) / 2, 0.38, HEX.accent1, "takeaway-icon");
  text(slide, value, { x: x + (Icon ? 0.68 : 0.22), y, w: w - (Icon ? 0.86 : 0.4), h }, { fontSize: 15.5, bold: true, color: C.text2, valign: "middle", objectName: "takeaway" });
}

// Horizontal process: boxes joined by arrows.
function flow(slide, C, steps, { x = MX, y, w = W - 2 * MX, h = 1.0, gap = 0.32, size = 13, fills, name = "flow" }) {
  const n = steps.length;
  const bw = (w - gap * (n - 1)) / n;
  steps.forEach((s, i) => {
    const bx = x + i * (bw + gap);
    const st = typeof s === "string" ? { head: s } : s;
    const fill = st.fill || (fills ? fills[i] : HEX.lt2);
    card(slide, { x: bx, y, w: bw, h }, fill, `${name}-box-${i}`);
    const runs = [{ text: st.head, options: { bold: true, fontSize: size, color: st.dark ? "FFFFFF" : C.text2, breakLine: !!st.body } }];
    if (st.body) runs.push({ text: st.body, options: { fontSize: size - 2, color: st.dark ? "E6ECF5" : C.text1 } });
    slide.addText(runs, { x: bx + 0.08, y, w: bw - 0.16, h, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: `${name}-text-${i}` });
    if (i < n - 1) {
      slide.addShape("rightArrow", { x: bx + bw + 0.04, y: y + h / 2 - 0.11, w: gap - 0.08, h: 0.22, fill: { color: HEX.accent5 }, line: { color: HEX.accent5 }, objectName: `${name}-arrow-${i}` });
    }
  });
}

const HEAD = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 } } });
function table(slide, rows, { x = MX, y, w, colW, fontSize = 13, name = "table", rowH } = {}) {
  slide.addTable(rows, {
    x, y, w, colW, fontSize, color: HEX.dk1, rowH,
    border: { type: "solid", pt: 0.5, color: "D5DBE5" },
    margin: [0.035, 0.07, 0.035, 0.07], valign: "middle", objectName: name,
  });
}

// Seven-meeting semester tracker. Past = teal, today = amber, upcoming = outline.
function tracker(slide, C, current, { x = MX, y = 6.25, w = W - 2 * MX, dark = true } = {}) {
  const n = MEETINGS.length;
  const step = w / (n - 1);
  const lineColor = dark ? "5B6C8F" : "C9D1DE";
  slide.addShape("line", { x, y: y + 0.12, w, h: 0, line: { color: lineColor, width: 1.5 }, objectName: "tracker-line" });
  MEETINGS.forEach((m, i) => {
    const cx = x + i * step;
    const isNow = i === current;
    const d = isNow ? 0.3 : 0.22;
    const fill = isNow ? HEX.accent2 : i < current ? HEX.accent1 : dark ? HEX.dk2 : "FFFFFF";
    const lc = isNow ? HEX.accent2 : i < current ? HEX.accent1 : lineColor;
    slide.addShape("ellipse", { x: cx - d / 2, y: y + 0.12 - d / 2, w: d, h: d, fill: { color: fill }, line: { color: lc, width: 1.5 }, objectName: `tracker-node-${i}` });
    const tc = dark ? (isNow ? "FFFFFF" : "AFC2DC") : isNow ? HEX.dk2 : HEX.accent5;
    text(slide, [
      { text: m.short, options: { bold: true, fontSize: 10.5, color: tc, breakLine: true } },
      { text: m.topic, options: { fontSize: 9.5, color: tc } },
    ], { x: cx - 0.85, y: y + 0.32, w: 1.7, h: 0.5 }, { align: "center", objectName: `tracker-label-${i}` });
  });
}

// Dark title slide used by every meeting deck.
async function titleSlide(slide, C, meta, { headline, subtitle, message, MessageIcon }) {
  chip(slide, C, `Meeting ${meta.index + 1} of 7  ·  ${meta.dateLong}`, { x: MX, y: 0.45, w: 3.55, h: 0.36, fill: HEX.accent1, fontSize: 11 });
  if (meta.retrospective) {
    chip(slide, C, "Retrospective reconstruction  ·  prepared October 2026", { x: W - MX - 4.6, y: 0.45, w: 4.6, h: 0.36, fill: HEX.accent2, color: HEX.dk1, fontSize: 11 });
  }
  text(slide, meta.topic.toUpperCase(), { x: MX, y: 1.15, w: 11, h: 0.4 }, { fontSize: 13, bold: true, color: "7FD6D3", charSpacing: 2, objectName: "topic" });
  const lines = headline.length > 62 ? 2 : 1; // Cambria 34 pt bold: about 62 characters per line at this width
  text(slide, headline, { x: MX, y: 1.55, w: 12.1, h: 0.62 * lines }, { fontSize: 34, bold: true, color: "FFFFFF", fontFace: THEME.headFontFace, valign: "top", objectName: "headline" });
  if (subtitle) text(slide, subtitle, { x: MX, y: 1.55 + 0.62 * lines + 0.22, w: 11.6, h: 0.5 }, { fontSize: 17, color: "CADCFC", objectName: "subtitle" });
  if (message) {
    slide.addShape("roundRect", { x: MX, y: 3.65, w: 12.1, h: 1.05, rectRadius: 0.08, fill: { color: "243A63" }, line: { color: "3A5584", width: 1 }, objectName: "message-bg" });
    if (MessageIcon) await icon(slide, MessageIcon, MX + 0.22, 3.88, 0.6, HEX.accent1, "message-icon");
    text(slide, message, { x: MX + (MessageIcon ? 1.0 : 0.3), y: 3.65, w: 12.1 - (MessageIcon ? 1.25 : 0.55), h: 1.05 }, { fontSize: 16, color: "FFFFFF", valign: "middle", objectName: "message" });
  }
  text(slide, [
    { text: AUTHORS, options: { bold: true, breakLine: true } },
    { text: PROGRAM, options: { breakLine: true } },
    { text: meta.presenterLine, options: { color: "AFC2DC", fontSize: 11.5 } },
  ], { x: MX, y: 4.95, w: 12.1, h: 0.95 }, { fontSize: 13, color: "E6ECF5", objectName: "authors" });
  tracker(slide, C, meta.index, { y: 6.32 });
}

module.exports = {
  THEME, HEX, W, H, MX, BODY_TOP, BODY_BOTTOM, MEETINGS, ROOT, FIG, RES_FIG, SEM_FIG,
  newDeck, img, icon, text, kicker, card, cardText, bullets, stat, caption, source, chip,
  takeaway, flow, table, HEAD, tracker, titleSlide,
};
