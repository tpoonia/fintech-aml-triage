// Meeting 3 of 7 — October 13, 2026: Implementation progress (Phases 1–3B).
// Build: node ../../_system/build_deck.js ..   (or ../_system/build_all.sh)
const { FaFlagCheckered, FaScaleBalanced, FaWrench, FaCircleCheck } = require("react-icons/fa6");

const meta = {
  id: "2026-10-13",
  index: 2,
  dateLong: "October 13, 2026",
  topic: "Implementation progress",
  file: "Q-TRACE_2026-10-13_Implementation-Progress",
  split: "Mayank: slides 1–3 · Tushar: slides 4–5",
  splitStatus: "same first-half/second-half pattern as the committed Oct 13 script; team to confirm",
  presenterLine: "Proposed split: Mayank (slides 1–3) · Tushar (slides 4–5) · about 5 minutes",
  status: "Ready for review. Reports work completed on Oct 6–7, 2026 (Phases 1–3B); the full study was completed on Oct 8, 2026.",
  delivery: [
    "Say the completion dates out loud: these milestones were finished on Oct 6–7, and the whole study, including the sealed test, was finished on Oct 8. Nothing is still running.",
    "If asked about later results, give the one-line answer (a simple probe rule was enough) and point to the Nov 10 and Nov 24 meetings.",
    "Do not claim quantum advantage: classical models on the same four inputs score higher.",
  ],
};

const slides = [
  {
    master: "TITLE",
    title: "From data to a working quantum classifier",
    speaker: "Mayank",
    script: `Good afternoon. We are Mayank and Tushar, and this is our implementation progress update for Q-TRACE.

Today we cover the implementation milestones: the data pipeline, the classical baselines, the frozen quantum classifier, a repair to its encoding, and our first noise characterization. All of this was completed on October 6 and 7. The full study, including the sealed held-out test, was completed on October 8, and we will present those results in depth at the next meetings.`,
    keyPoints: ["implementation milestones, Phases 1–3B", "completed Oct 6–7; full study completed Oct 8", "later meetings go deeper"],
    transition: "Start with the data.",
    build: async (s, { C, D, meta }) => {
      await D.titleSlide(s, C, meta, {
        headline: "From data to a working quantum classifier",
        subtitle: "Data pipeline · classical baselines · frozen VQC · encoding repair · first noise characterization",
        message: "Today: implementation milestones completed Oct 6–7, 2026 (Phases 1–3B). The whole study, including the one-time sealed test, was completed on Oct 8; later meetings present those results in depth.",
        MessageIcon: FaFlagCheckered,
      });
    },
  },
  {
    title: "Leakage-safe data and strong classical baselines",
    kicker: "Phases 1–2  ·  completed October 6, 2026",
    speaker: "Mayank",
    script: `We use the public European credit-card fraud dataset: 284,807 transactions, of which 492 are frauds.

We removed exact duplicates, which leaves 283,726 rows and 473 frauds, or 0.17 percent. Rows that differ only in their timestamp are kept together, so they can never straddle partitions. That gives five disjoint partitions. All preprocessing is fitted on the training partition only, and the controller test partition is sealed from the start.

Classical models then set the bar. On all thirty features, random forest reaches an AUPRC of 0.805. On the same four inputs and training rows the quantum model uses, classical models reach about 0.59 to 0.62.`,
    keyPoints: ["284,807 → 283,726 rows, 473 frauds (0.17%)", "group-aware split, 0 groups cross partitions", "classical AUPRC 0.805 (30 features); 0.59–0.62 on the VQC's inputs"],
    transition: "Next, the quantum model we froze.",
    sources: "ulb_v1_dataset_summary.csv; ulb_v1_phase1_metadata.json; phase2_classical_metrics.csv (a-full, draw 0); p3ar_validation_comparison.csv.",
    build: async (s, { C, D, S }) => {
      D.flow(s, C, [
        { head: "284,807 transactions", body: "492 frauds · public ULB data" },
        { head: "Exact deduplication", body: "1,081 duplicate rows removed (773 groups)" },
        { head: "283,726 rows", body: "473 frauds · 0.17% prevalence" },
        { head: "Group-aware split", body: "timestamp-only duplicates kept together", fill: "D7EEEE" },
      ], { y: 1.45, h: 0.95, size: 14 });
      D.table(s, [
        [D.HEAD("Partition"), D.HEAD("Rows"), D.HEAD("Frauds"), D.HEAD("Role")],
        ["VQC train", "127,677", "213", "fit every quantum model"],
        ["VQC validation", "28,372", "47", "qualification, thresholds"],
        ["Controller train", "42,559", "71", "fit mitigation policies"],
        ["Controller validation", "28,372", "47", "validate policies"],
        [{ text: "Controller test", options: { bold: true } }, "56,746", "95", { text: "sealed until the final test", options: { bold: true } }],
      ], { y: 2.72, w: 5.75, colW: [1.85, 1.0, 0.8, 2.1], fontSize: 12.5 });
      D.img(s, S("baselines_auprc.png"), { x: 6.55, y: 2.6, w: 6.2, h: 3.4 });
      D.text(s, "VQC inputs = the same 4 features and 1,065 training rows the quantum model uses.", { x: 0.6, y: 5.45, w: 5.75, h: 0.5 }, { fontSize: 11.5, italic: true, color: C.accent5 });
      await D.takeaway(s, C, "Classical models set the bar: AUPRC 0.805 on all 30 features, 0.59–0.62 on the quantum model's four inputs.", { Icon: FaScaleBalanced });
      D.source(s, C, "ulb_v1_dataset_summary.csv, ulb_v1_phase1_metadata.json, phase2_classical_metrics.csv, p3ar_validation_comparison.csv");
    },
  },
  {
    title: "The frozen quantum classifier",
    kicker: "Phase 3A-R  ·  selected and frozen October 6, 2026",
    speaker: "Mayank",
    script: `This is the frozen classifier, which every later experiment uses as its reference model.

Four features, chosen on the training data, are encoded as angles on four qubits. A ZZ feature map entangles every pair of qubits, a two-layer RealAmplitudes ansatz carries the 12 trainable parameters, and we read out the four-qubit parity, which maps to a fraud probability. After transpilation the circuit has 18 two-qubit gates.

We train it with COBYLA on a balanced subset: all 213 training frauds plus four legitimate transactions for each fraud. Its parameters and circuit are hashed, and retraining reproduces it exactly. Tushar will now explain the repair that made it work.`,
    keyPoints: ["4 qubits: ZZ feature map + RealAmplitudes (reps 2), parity readout", "12 parameters, 18 CX after transpilation", "COBYLA on 1,065 balanced training rows; frozen and hashed"],
    transition: "Hand-off to Tushar: why the first encoding failed.",
    sources: "configs/vqc/vqc3a_top4_ra1.yaml; configs/repair/p3ar_v1.yaml; p5a_pool_metrics.csv (anchor p3a_r: 18 CX, 12 parameters).",
    build: async (s, { C, D, S }) => {
      D.img(s, S("circuit_p3ar.png"), { x: 0.6, y: 1.4, w: 12.1, h: 3.6 });
      const cards = [
        ["Inputs", "Top-4 features by ANOVA F on training data (V17, V14, V12, V10), angle-encoded."],
        ["Training", "COBYLA, exact simulation, 1,065 rows: all 213 training frauds + 4 legitimate per fraud."],
        ["Frozen", "Parameters and circuit hashed; retraining is bitwise identical."],
      ];
      cards.forEach(([h, b], i) => D.cardText(s, C, { x: 0.6 + i * 4.1, y: 5.2, w: 3.9, h: 1.35, head: h, body: b, size: 13.5 }));
      D.source(s, C, "configs/vqc/vqc3a_top4_ra1.yaml, configs/repair/p3ar_v1.yaml, p5a_pool_metrics.csv (anchor p3a_r)");
    },
  },
  {
    title: "Encoding repair: AUPRC 0.104 → 0.507",
    kicker: "Phase 3A → 3A-R  ·  completed October 6, 2026",
    speaker: "Tushar",
    script: `Our first quantum model learned almost nothing: its validation AUPRC was only 0.104.

Diagnostics on the training data showed why. The original encoding clipped values at three interquartile ranges and mapped them to the full minus pi to pi range. Most fraud values were clipped, 123 frauds were clipped on all four features, and only 91 of the 213 training frauds remained distinct inputs. The wide angle range also caused phase aliasing.

A pre-registered repair, selected by cross-validation on training data only, clips at fifteen interquartile ranges and uses a quarter of the angle range. Now 212 frauds stay distinct, and validation AUPRC rises to 0.507, with an AUROC of 0.957. Classical models on the same inputs still reach 0.59 to 0.62, so we make no quantum-advantage claim.`,
    keyPoints: ["first encoding: saturation + aliasing; 91 of 213 fraud inputs distinct", "pre-registered, training-only repair: 212 distinct", "AUPRC 0.104 → 0.507 (AUROC 0.957); classical 0.59–0.62 on the same inputs"],
    transition: "With a working model, we could study noise.",
    sources: "p3ar_encoding_diagnostics.csv (e0, e3); p3ar_validation_comparison.csv.",
    build: async (s, { C, D, S }) => {
      D.img(s, S("encoding_repair.png"), { x: 0.5, y: 1.4, w: 8.6, h: 4.45 });
      D.stat(s, C, { x: 9.45, y: 1.5, w: 3.3, value: "0.104 → 0.507", valueSize: 30, label: "validation AUPRC (AUROC 0.957 after the repair)" });
      D.stat(s, C, { x: 9.45, y: 2.95, w: 3.3, value: "91 → 212", valueSize: 30, color: C.accent6, label: "distinct fraud inputs, of 213 training frauds" });
      D.stat(s, C, { x: 9.45, y: 4.4, w: 3.3, value: "0.59–0.62", valueSize: 30, color: C.accent3, label: "classical AUPRC on the same 4 inputs: no quantum advantage" });
      await D.takeaway(s, C, "A pre-registered, training-data-only repair fixed saturation and aliasing; the model works, but classical models stay ahead.", { Icon: FaWrench });
      D.source(s, C, "p3ar_encoding_diagnostics.csv (encodings e0, e3), p3ar_validation_comparison.csv");
    },
  },
  {
    title: "First noise result, and where the project stands",
    kicker: "Phase 3B  ·  completed October 7, 2026  ·  full study completed October 8, 2026",
    speaker: "Tushar",
    script: `Our first noise characterization used exact density-matrix simulation of the frozen model, under depolarizing, thermal and readout noise.

Discrimination barely moved: across the twelve anchor conditions, AUPRC changed by at most 0.003, and every interval contains zero. Calibration did not survive. Under combined high noise the Brier score rose from 0.0093 to 0.121, and precision at the frozen threshold fell from 0.53 to 0.03. So noise mainly damages calibrated probabilities and threshold decisions. That reframed the whole project.

On the right is where the project stands. Every experimental phase was completed by October 8, including the one-time sealed test, so nothing is still running. What remains is analysis, review and writing. The coming meetings present the noise and mitigation results, the policy study and the final findings in depth. Thank you.`,
    keyPoints: ["AUPRC change ≤ 0.003, every CI contains 0", "Brier 0.0093 → 0.121; precision 0.53 → 0.03 (combined-high)", "all phases complete by Oct 8; next meetings go deeper"],
    transition: "Questions.",
    sources: "p3b_exact_metrics.csv; p4_exact_diagnostics.csv (clean precision 0.532); git history for completion dates.",
    build: async (s, { C, D, F }) => {
      D.img(s, F("fig3_noise_effects.png"), { x: 0.5, y: 1.4, w: 7.0, h: 3.35 });
      D.stat(s, C, { x: 0.6, y: 4.85, w: 1.9, value: "≤ 0.003", valueSize: 24, label: "change in AUPRC", labelH: 0.5 });
      D.stat(s, C, { x: 2.55, y: 4.85, w: 2.75, value: "0.009 → 0.121", valueSize: 24, color: C.accent3, label: "Brier, combined-high noise", labelH: 0.5 });
      D.stat(s, C, { x: 5.4, y: 4.85, w: 2.3, value: "0.53 → 0.03", valueSize: 24, color: C.accent3, label: "precision at the frozen threshold", labelH: 0.5 });
      D.card(s, { x: 7.85, y: 1.4, w: 4.9, h: 4.55 }, "F4F6FA", "status-bg");
      D.text(s, "Project status", { x: 8.1, y: 1.52, w: 4.4, h: 0.4 }, { fontSize: 16, bold: true, color: C.text2 });
      const rows = [
        ["Oct 6", "Data, baselines, frozen VQC, repair", true],
        ["Oct 7", "Noise · mitigation · 64-model pool · categorical study", true],
        ["Oct 8", "Continuous-noise study · one-time sealed test", true],
        ["Oct 27", "Meeting: noise and mitigation in depth", false],
        ["Nov 10", "Meeting: policy selection", false],
        ["Nov 24", "Meeting: final findings, manuscript", false],
        ["Dec 8", "Final capstone defense", false],
      ];
      rows.forEach(([d, t, done], i) => {
        const y = 2.0 + i * 0.54;
        D.chip(s, C, d, { x: 8.1, y: y + 0.04, w: 0.95, h: 0.34, fill: done ? D.HEX.accent1 : D.HEX.accent2, color: done ? "FFFFFF" : D.HEX.dk1, fontSize: 10.5 });
        D.text(s, t, { x: 9.2, y, w: 3.45, h: 0.48 }, { fontSize: 12.5, color: C.text1, valign: "middle" });
      });
      await D.takeaway(s, C, "Noise mainly damaged calibration, not discrimination. Every experiment was complete by Oct 8; nothing is still running.", { Icon: FaCircleCheck });
      D.source(s, C, "p3b_exact_metrics.csv, p4_exact_diagnostics.csv; completion dates from the repository history");
    },
  },
];

module.exports = { meta, slides };
