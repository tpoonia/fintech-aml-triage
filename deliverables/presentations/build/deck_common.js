// Shared theme, layouts and helpers for the Q-TRACE decks (pptxgenjs, structured deck).
// Every number shown on a slide comes from results/tables (see deliverables/figures/FIGURES.md).
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const FIG = path.join(ROOT, "deliverables", "figures");
const RES_FIG = path.join(ROOT, "results", "figures");

const THEME = {
  name: "Q-TRACE",
  headFontFace: "Cambria",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1A1F2B", // text
    lt1: "FFFFFF",
    dk2: "1B2A49", // navy (dominant)
    lt2: "EEF2F7", // light panel
    accent1: "0F8B8D", // teal: mitigation / the probe rule
    accent2: "E8A33D", // amber: cost / attention
    accent3: "C0392B", // red: failure
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
const FOOTER = "Q-TRACE  ·  Pokhriyal & Poonia  ·  Katz School, Yeshiva University";

function newDeck(title) {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = title;
  pres.author = "Mayank Kumar Pokhriyal; Tushar Poonia";
  pres.company = "Katz School of Science and Health, Yeshiva University";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "TITLE_DARK",
    background: { color: HEX.dk2 },
    objects: [],
    slideNumber: undefined,
  });
  pres.defineSlideMaster({
    title: "CONTENT",
    background: { color: HEX.lt1 },
    objects: [
      {
        text: {
          text: FOOTER,
          options: { x: 0.6, y: 7.05, w: 9, h: 0.3, fontSize: 9, color: C.accent5, margin: 0 },
        },
      },
      {
        placeholder: {
          options: {
            name: "title",
            type: "title",
            x: 0.6,
            y: 0.35,
            w: 12.1,
            h: 0.85,
            fontSize: 32,
            bold: true,
            color: C.text2,
            fontFace: THEME.headFontFace,
            valign: "middle",
            margin: 0,
          },
          text: "",
        },
      },
    ],
    slideNumber: { x: 12.2, y: 7.0, w: 0.6, h: 0.35, fontSize: 9, color: C.accent5, align: "right" },
  });
  pres.defineSlideMaster({
    title: "SECTION_DARK",
    background: { color: HEX.dk2 },
    objects: [
      {
        text: {
          text: FOOTER,
          options: { x: 0.6, y: 7.05, w: 9, h: 0.3, fontSize: 9, color: "AFC2DC", margin: 0 },
        },
      },
      {
        placeholder: {
          options: {
            name: "title",
            type: "title",
            x: 0.6,
            y: 0.35,
            w: 12.1,
            h: 0.85,
            fontSize: 32,
            bold: true,
            color: C.background1,
            fontFace: THEME.headFontFace,
            valign: "middle",
            margin: 0,
          },
          text: "",
        },
      },
    ],
    slideNumber: { x: 12.2, y: 7.0, w: 0.6, h: 0.35, fontSize: 9, color: "AFC2DC", align: "right" },
  });
  return { pres, C };
}

function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}

// Place an image inside a box, preserving aspect ratio; anchored top-left or centered.
function addImageFit(slide, file, box, { center = true, name } = {}) {
  const { w, h } = pngSize(file);
  const r = w / h;
  let iw = box.w;
  let ih = iw / r;
  if (ih > box.h) {
    ih = box.h;
    iw = ih * r;
  }
  const x = center ? box.x + (box.w - iw) / 2 : box.x;
  const y = center ? box.y + (box.h - ih) / 2 : box.y;
  slide.addImage({ path: file, x, y, w: iw, h: ih, objectName: name || path.basename(file) });
  return { x, y, w: iw, h: ih };
}

async function iconPng(Icon, color = "#FFFFFF", size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(Icon, { color, size: String(size) })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// Icon in a filled circle (the deck's motif).
async function iconCircle(slide, C, Icon, x, y, d, fill, name) {
  slide.addShape("ellipse", {
    x,
    y,
    w: d,
    h: d,
    fill: { color: fill },
    line: { color: fill },
    objectName: (name || "icon") + "-circle",
  });
  const data = await iconPng(Icon);
  const pad = d * 0.24;
  slide.addImage({ data, x: x + pad, y: y + pad, w: d - 2 * pad, h: d - 2 * pad, objectName: name || "icon" });
}

// Big number + label (stat callout).
function stat(slide, C, { x, y, w, value, label, color, valueSize = 40, name }) {
  slide.addText(value, {
    x,
    y,
    w,
    h: 0.8,
    fontSize: valueSize,
    bold: true,
    color: color || C.accent1,
    fontFace: THEME.headFontFace,
    margin: 0,
    isTextBox: true,
    objectName: (name || "stat") + "-value",
  });
  slide.addText(label, {
    x,
    y: y + 0.82,
    w,
    h: 0.75,
    fontSize: 13,
    color: C.text1,
    margin: 0,
    valign: "top",
    isTextBox: true,
    objectName: (name || "stat") + "-label",
  });
}

function caption(slide, C, text, box, name) {
  slide.addText(text, {
    ...box,
    fontSize: 10.5,
    italic: true,
    color: C.accent5,
    margin: 0,
    valign: "top",
    isTextBox: true,
    objectName: name || "caption",
  });
}

function bullets(slide, C, items, box, { fontSize = 16, name, color } = {}) {
  const runs = items.map((it, i) => {
    const t = typeof it === "string" ? { text: it } : it;
    return {
      text: t.text,
      options: {
        bullet: t.sub ? { indent: 18 } : true,
        indentLevel: t.sub ? 1 : 0,
        bold: !!t.bold,
        color: t.color || color || C.text1,
        fontSize: t.sub ? fontSize - 2 : fontSize,
        breakLine: i < items.length - 1,
        paraSpaceAfter: 6,
      },
    };
  });
  slide.addText(runs, { ...box, valign: "top", margin: 0.05, isTextBox: true, objectName: name || "bullets" });
}

function card(slide, C, box, fill, name) {
  slide.addShape("roundRect", {
    ...box,
    rectRadius: 0.08,
    fill: { color: fill || HEX.lt2 },
    line: { color: fill || HEX.lt2 },
    objectName: name || "card",
  });
}

module.exports = {
  THEME,
  HEX,
  W,
  H,
  FIG,
  RES_FIG,
  ROOT,
  newDeck,
  addImageFit,
  iconCircle,
  stat,
  caption,
  bullets,
  card,
};
