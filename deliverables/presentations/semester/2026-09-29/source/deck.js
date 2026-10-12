// Meeting 2 of 7 — September 29, 2026: Research design.
// RETROSPECTIVE RECONSTRUCTION (prepared Oct 2026). The repository record begins on Oct 6, 2026.
// Pre-October record: docs/DECISIONS.md Q1 (generic QML on Iris/QM9/WDBC, binary mitigate-or-not
// decision) and the early-October research plan's description of the deck of that time (benefit-minus-
// cost rule, VQC, Qiskit Aer, ZNE/readout mitigation, Never/Always/Fixed/Q-TRACE comparison, "current
// accuracy" as an example input). The fraud application was adopted on Oct 6, so it is NOT presented
// here as the Sept 29 design; slide 2 says so explicitly. No results existed on this date.
const { FaClockRotateLeft, FaLayerGroup, FaMicrochip, FaGaugeHigh, FaClipboardList } = require("react-icons/fa6");

const meta = {
  id: "2026-09-29",
  index: 1,
  retrospective: true,
  dateLong: "September 29, 2026",
  topic: "Research design",
  file: "Q-TRACE_2026-09-29_Research-Design",
  split: "Tushar: slides 1–3 · Mayank: slides 4–5",
  splitStatus: "proposed; no presenter record exists for this date; team to confirm",
  presenterLine: "Retrospective deck · proposed split: Tushar (slides 1–3) · Mayank (slides 4–5) · about 5 minutes",
  scriptNote:
    "Retrospective reconstruction, prepared in October 2026. The repository record begins on Oct 6, 2026. It preserves the pre-October design as a generic QML study (Iris, QM9, WDBC) with a binary mitigate-or-not decision (docs/DECISIONS.md, Q1). The early-October research plan (docs/research/deep-research-report.md) describes the deck of that time: a benefit-minus-cost rule, a VQC, Qiskit Aer, ZNE and readout mitigation, a Never/Always/Fixed/Q-TRACE comparison, and 'current accuracy' as an example input. The fraud-detection application was adopted on Oct 6, so this deck describes it as a later change, not as the Sept 29 design. Technical background cites published literature. If the team has the original September materials, they take precedence.",
  delivery: [
    "If shown, introduce it as a reconstruction of the design stage prepared in October.",
    "Do not present the fraud application, the five-action design or any metric values as decided on Sept 29: the record dates them to Oct 6 or later.",
  ],
};

const slides = [
  {
    master: "TITLE",
    title: "Designing the study: model, mitigation and evaluation",
    speaker: "Tushar",
    script: `Good afternoon. This is the research-design stage of Q-TRACE: how we intended to build the study before any experiment ran. As with our proposal deck, this version was reconstructed in October from the project record, so it contains no results.

We cover the scope as it was recorded at this stage, the general shape of a variational quantum classifier, how zero-noise extrapolation works, and how the decision would be evaluated.`,
    keyPoints: ["design stage, no results", "scope as recorded, VQC template, ZNE, evaluation plan"],
    transition: "First, the scope as recorded.",
    build: async (s, { C, D, meta }) => {
      await D.titleSlide(s, C, meta, {
        headline: "Designing the study: model, mitigation and evaluation",
        subtitle: "Research design: scope, variational classifier template, zero-noise extrapolation, evaluation plan",
        message: "Reconstructed in Oct 2026 from the project record, which begins Oct 6. It preserves this stage as a generic QML design (Iris, QM9, WDBC) with a mitigate-or-not decision. The fraud application came on Oct 6.",
        MessageIcon: FaClockRotateLeft,
      });
    },
  },
  {
    title: "Scope as recorded before October 6",
    kicker: "Design stage  ·  what the record shows, and what came later",
    speaker: "Tushar",
    script: `At this stage, as the record shows, the design was generic. The models were quantum machine-learning models on standard benchmarks: Iris and the Wisconsin breast-cancer data for classification, and QM9 for molecular properties, simulated with Qiskit Aer. The decision was whether to mitigate, with zero-noise extrapolation or readout mitigation. Q-TRACE would make that decision by weighing expected benefit against cost, and be compared with never mitigating, always mitigating and a fixed rule.

We want to be transparent about one point. The application to credit-card fraud detection, and a design with several mitigation actions, were adopted later, on October 6. They are not part of this stage, and we do not present them as if they were.`,
    keyPoints: ["benchmarks: Iris, WDBC, QM9; Qiskit Aer", "mitigate or not (ZNE / readout); benefit-minus-cost rule", "compared with Never / Always / Fixed", "fraud application + multi-action design adopted Oct 6 (not this stage)"],
    transition: "The model template.",
    sources: "docs/DECISIONS.md Q1 (answered 2026-10-06); docs/PROJECT_SPEC.md §2; docs/research/deep-research-report.md (description of the pre-October deck).",
    build: async (s, { C, D }) => {
      const rec = [
        [FaLayerGroup, "Benchmarks", "Iris and WDBC (classification), QM9 (molecular properties); Qiskit Aer"],
        [FaGaugeHigh, "Decision", "mitigate or not (ZNE / readout mitigation)"],
        [FaMicrochip, "Approach", "Q-TRACE: benefit-minus-cost rule vs Never / Always / Fixed"],
      ];
      D.text(s, "Recorded for this stage", { x: 0.6, y: 1.45, w: 7, h: 0.4 }, { fontSize: 15.5, bold: true, color: C.text2 });
      for (let i = 0; i < rec.length; i++) {
        const y = 1.95 + i * 1.12;
        D.card(s, { x: 0.6, y, w: 7.2, h: 0.98 }, D.HEX.lt2, `rec-${i}`);
        await D.icon(s, rec[i][0], 0.8, y + 0.17, 0.64, D.HEX.dk2, `rec-icon-${i}`);
        D.text(s, [
          { text: rec[i][1], options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } },
          { text: rec[i][2], options: { fontSize: 13.5, color: C.text1 } },
        ], { x: 1.65, y, w: 6.0, h: 0.98 }, { valign: "middle" });
      }
      D.cardText(s, C, {
        x: 8.15, y: 1.45, w: 4.6, h: 3.85, head: "Adopted later, on Oct 6, 2026", fill: "FBEFD9", headColor: "8A5A00",
        body: [
          { text: "Application: credit-card fraud detection", bullet: true },
          { text: "Several mitigation actions instead of a binary choice", bullet: true },
          { text: "Label-free decision inputs only (A01, A12)", bullet: true },
          { text: "Pre-registered, gated phases", bullet: true },
          { text: "Source: docs/DECISIONS.md (Q1, A01, A12), docs/PROJECT_SPEC.md", size: 11.5, color: C.accent5 },
        ], size: 13.5,
      });
      await D.takeaway(s, C, "We present this stage as recorded; the fraud application is a later decision, not part of it.", { y: 5.6, Icon: FaClipboardList });
      D.source(s, C, "docs/DECISIONS.md (Q1, answered 2026-10-06), docs/PROJECT_SPEC.md §2, docs/research/deep-research-report.md", 6.3);
    },
  },
  {
    title: "The variational quantum classifier template",
    kicker: "Design stage  ·  general template from the literature",
    speaker: "Tushar",
    script: `The classification models in the design are variational quantum classifiers, a well-established template.

Input data are first encoded into qubit rotations by an encoding circuit, U of x. A trainable circuit, V of theta, follows, repeated in layers. Measuring the qubits gives an expectation value that becomes the class score. A classical optimizer then adjusts theta to reduce the training loss. Because the output is estimated from repeated measurements, called shots, it always carries sampling noise as well as hardware noise.

The specific circuit, with its encoding, depth and readout, was chosen later, on the fraud data. What matters for our question is that the output is a measured expectation value, exactly the quantity noise distorts and mitigation tries to repair. Mayank will explain the mitigation side.`,
    keyPoints: ["encoding U(x) → trainable ansatz V(θ) → measurement → score", "hybrid loop: classical optimizer updates θ", "output is an expectation value, the quantity noise distorts"],
    transition: "Hand-off to Mayank: zero-noise extrapolation.",
    sources: "Havlíček et al. (2019) Nature 567:209; Schuld et al. (2020) PRA 101:032308. Figure: generic template, no project-specific choices.",
    build: async (s, { C, D, S }) => {
      D.img(s, S("circuit_generic.png"), { x: 0.5, y: 1.4, w: 8.3, h: 3.75 });
      D.cardText(s, C, {
        x: 9.05, y: 1.45, w: 3.7, h: 3.75, head: "Why it matters here",
        body: [
          { text: "The model's output is a measured expectation value", bullet: true },
          { text: "Noise distorts exactly that quantity", bullet: true },
          { text: "Mitigation tries to repair it, at a cost", bullet: true },
        ], size: 13.5,
      });
      await D.takeaway(s, C, "A standard, well-studied model template, so the study is about the mitigation decision, not a new classifier.", { y: 5.45, Icon: FaMicrochip });
      D.source(s, C, "Havlíček et al. 2019 (Nature 567:209) · Schuld et al. 2020 (PRA 101:032308). Generic template.", 6.15);
    },
  },
  {
    title: "Mitigation strategy: zero-noise extrapolation",
    kicker: "Design stage  ·  method from the literature",
    speaker: "Mayank",
    script: `The mitigation in this design is zero-noise extrapolation.

It works in two steps. First, amplify the noise on purpose, for example by folding the circuit: running a gate, its inverse and the gate again leaves the ideal result unchanged but multiplies the noise. Second, measure at several noise levels and extrapolate the trend back to zero noise. Folding adds a gate and its inverse in pairs, so common choices use odd scale factors, such as one, three and five.

The cost is the reason for our project. Each extra noise level is another circuit to run, so ZNE multiplies shots and gate exposure. The record also lists readout mitigation, which corrects measurement errors with a few calibration circuits and costs far less. The decision the design asks for is therefore whether the expected improvement is worth those extra resources in a given setting.`,
    keyPoints: ["fold gates (G G† G) to amplify noise without changing the ideal result", "measure at several levels, extrapolate to zero", "extra circuits = extra shots and gate exposure → the decision"],
    transition: "How we would evaluate the decision.",
    sources: "Temme et al. (2017) PRL 119:180509; Giurgica-Tiron et al. (2020) IEEE QCE 306–316. Figure: illustrative.",
    build: async (s, { C, D, S }) => {
      D.flow(s, C, [
        { head: "1. Amplify", body: "fold: U → U U† U (same ideal result, more noise)" },
        { head: "2. Measure", body: "at several noise levels" },
        { head: "3. Extrapolate", body: "fit the trend back to zero noise", fill: "D7EEEE" },
      ], { x: 0.6, y: 1.5, w: 6.2, h: 1.25, size: 13.5 });
      D.img(s, S("zne_schematic.png"), { x: 7.0, y: 1.4, w: 5.75, h: 3.9 });
      D.cardText(s, C, {
        x: 0.6, y: 3.05, w: 6.2, h: 2.05, head: "The cost behind the decision", fill: "FBEFD9", headColor: "8A5A00",
        body: [
          { text: "Every extra noise level is another circuit to run", bullet: true },
          { text: "More shots and more two-qubit-gate exposure", bullet: true },
          { text: "So: is the expected improvement worth it here?", bullet: true },
        ], size: 13.5,
      });
      await D.takeaway(s, C, "ZNE can remove noise-induced bias, but always at a resource cost.", { y: 5.6, Icon: FaGaugeHigh });
      D.source(s, C, "Temme et al. 2017 (PRL 119:180509) · Giurgica-Tiron et al. 2020 (IEEE QCE). Curve illustrative.", 6.3);
    },
  },
  {
    title: "How the decision would be evaluated",
    kicker: "Design stage  ·  reconstructed at the level the record supports",
    speaker: "Mayank",
    script: `Finally, the evaluation design.

For each benchmark and noise setting, we would run the model with and without mitigation, and record both the change in task quality and the extra resources used. Q-TRACE's benefit-minus-cost decision would then be compared with three simple policies: never mitigate, always mitigate, and a fixed rule. It is only worth building if it beats all three.

One detail from the record is instructive. The deck at the time used "current accuracy" as an example input. That needs labels a deployed system would not have, and it was removed on October 6.

The specific metrics and noise models were not recorded at this stage. They were fixed when the study was narrowed on October 6, and the following meetings report that study. Thank you.`,
    keyPoints: ["per setting: with vs without mitigation → quality change and extra cost", "compare Q-TRACE with Never / Always / Fixed", "example input then: current accuracy (needs labels; removed Oct 6)", "metrics fixed later (Oct 6 onward)"],
    transition: "Questions.",
    sources: "docs/DECISIONS.md Q1, A12; docs/research/deep-research-report.md (pre-October deck: Never/Always/Fixed/Q-TRACE, current accuracy input); wording is ours.",
    build: async (s, { C, D }) => {
      D.flow(s, C, [
        { head: "Settings", body: "benchmark × noise level" },
        { head: "Run twice", body: "with and without mitigation" },
        { head: "Record", body: "quality change + extra resources" },
        { head: "Compare policies", body: "Never · Always · Fixed · Q-TRACE", fill: "D7EEEE" },
      ], { y: 1.5, h: 1.15, size: 14.5 });
      D.cardText(s, C, { x: 0.6, y: 2.95, w: 2.9, h: 1.6, head: "Never", body: "cheapest; leaves noise-induced bias", size: 13 });
      D.cardText(s, C, { x: 3.65, y: 2.95, w: 2.9, h: 1.6, head: "Always", body: "pays the full cost every time", size: 13 });
      D.cardText(s, C, { x: 6.7, y: 2.95, w: 2.9, h: 1.6, head: "Fixed rule", body: "one preset threshold", size: 13 });
      D.cardText(s, C, { x: 9.75, y: 2.95, w: 3.0, h: 1.6, head: "Q-TRACE", body: "mitigate when expected benefit exceeds cost", size: 13, fill: "E3F2F1" });
      D.card(s, { x: 0.6, y: 4.8, w: 12.1, h: 0.85 }, "FBEFD9", "retro-note-bg");
      D.text(s, [
        { text: "Not recorded at this stage:  ", options: { bold: true, color: "8A5A00" } },
        { text: "exact metrics, noise models and thresholds (fixed from Oct 6). The example input then, \"current accuracy\", needs labels and was removed on Oct 6 (A12).", options: { color: C.text1 } },
      ], { x: 0.85, y: 4.8, w: 11.6, h: 0.85 }, { fontSize: 13.5, valign: "middle" });
      await D.takeaway(s, C, "Evaluate Q-TRACE against never, always and a fixed rule.", { y: 5.9, Icon: FaClipboardList });
      D.source(s, C, "docs/DECISIONS.md (Q1, A12), docs/research/deep-research-report.md (pre-October deck); wording is ours.", 6.6);
    },
  },
];

module.exports = { meta, slides };
