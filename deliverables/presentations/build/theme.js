// Write the deck theme (colour scheme + heading/body fonts) into ppt/theme/theme*.xml, so that
// scheme colours used by pptxgenjs resolve to the Q-TRACE palette in PowerPoint and LibreOffice.
const fs = require("fs");
const JSZip = require("jszip");

const ORDER = ["dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink"];

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

async function applyTheme(file, theme) {
  const zip = await JSZip.loadAsync(fs.readFileSync(file));
  const parts = Object.keys(zip.files).filter((n) => /^ppt\/theme\/theme\d+\.xml$/.test(n));
  if (!parts.length) throw new Error("no theme part found");
  const scheme =
    `<a:clrScheme name="${esc(theme.name)}">` +
    ORDER.map((k) => {
      const v = theme.colors[k];
      if (!/^[0-9A-Fa-f]{6}$/.test(v)) throw new Error(`theme colour ${k} must be 6-digit hex`);
      return `<a:${k}><a:srgbClr val="${v.toUpperCase()}"/></a:${k}>`;
    }).join("") +
    `</a:clrScheme>`;
  for (const part of parts) {
    let xml = await zip.file(part).async("string");
    xml = xml.replace(/<a:clrScheme[\s\S]*?<\/a:clrScheme>/, scheme);
    xml = xml.replace(/(<a:majorFont>\s*<a:latin typeface=")[^"]*(")/, `$1${esc(theme.headFontFace)}$2`);
    xml = xml.replace(/(<a:minorFont>\s*<a:latin typeface=")[^"]*(")/, `$1${esc(theme.bodyFontFace)}$2`);
    xml = xml.replace(/(<a:theme [^>]*name=")[^"]*(")/, `$1${esc(theme.name)}$2`);
    zip.file(part, xml);
  }
  const buf = await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
  fs.writeFileSync(file, buf);
}

module.exports = { applyTheme };
