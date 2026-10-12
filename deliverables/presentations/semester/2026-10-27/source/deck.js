// Meeting 4 of 7 — October 27, 2026: Noise and mitigation (Phases 3B and 4, completed Oct 7, 2026).
const { FaWaveSquare, FaGaugeHigh, FaTemperatureHalf, FaEye, FaScaleBalanced, FaCoins, FaRoute } = require("react-icons/fa6");

const meta = {
  id: "2026-10-27",
  index: 3,
  dateLong: "October 27, 2026",
  topic: "Noise and mitigation",
  file: "Q-TRACE_2026-10-27_Noise-and-Mitigation",
  split: "Tushar: slides 1–3 · Mayank: slides 4–5",
  splitStatus: "proposed, alternating the opener across meetings; team to confirm",
  presenterLine: "Proposed split: Tushar (slides 1–3) · Mayank (slides 4–5) · about 5 minutes",
  status: "Ready for review. Presents Phases 3B and 4, completed on Oct 7, 2026, in more depth than the Oct 13 overview.",
  delivery: [
    "Say 'discrimination' (AUPRC, AUROC, the top-ranked frauds), not 'ranking': noise did slightly reorder scores among legitimate transactions.",
    "The asymmetric readout profiles are synthetic stress tests, not device data.",
    "These results were completed on Oct 7; present them as completed findings.",
  ],
};

const slides = [
  {
    master: "TITLE",
    title: "Noise breaks calibration; mitigation repairs it",
    speaker: "Tushar",
    script: `Good afternoon. Today we go deeper into two completed phases of Q-TRACE: how simulated noise affects our quantum fraud classifier, and what error mitigation does about it.

Both phases were completed on October 7. In short: noise damaged calibration and threshold decisions, not discrimination. Mitigation repaired calibration, and simply buying three times the shots did not.`,
    keyPoints: ["Phases 3B and 4, completed Oct 7", "noise damaged calibration, not discrimination", "mitigation repaired calibration; extra shots did not"],
    transition: "First, how we simulated noise.",
    build: async (s, { C, D, meta }) => {
      await D.titleSlide(s, C, meta, {
        headline: "Noise breaks calibration; mitigation repairs it",
        subtitle: "Noise models · calibration vs discrimination · readout mitigation · zero-noise extrapolation · resource-matched tests",
        message: "Deeper analysis of Phases 3B and 4 (completed Oct 7, 2026). Noise damaged calibration and threshold decisions, not discrimination. Mitigation repaired calibration; three times the shots did not.",
        MessageIcon: FaWaveSquare,
      });
    },
  },
  {
    title: "How we simulated noise",
    kicker: "Phase 3B  ·  exact density-matrix simulation  ·  completed October 7, 2026",
    speaker: "Tushar",
    script: `We simulate the frozen classifier exactly, with Qiskit Aer density matrices, so every effect we see comes from the noise model and not from sampling.

There are three noise sources. Depolarizing errors follow one- and two-qubit gates. Thermal relaxation acts during 35-nanosecond and 300-nanosecond gates. Readout confusion flips measured bits. Each source has low, medium and high anchors, and a combined profile uses all three, which gives twelve conditions. Finite-shot experiments then use 1,024 shots and 20 replicates per condition.

Symmetric readout noise also serves as a negative control: in theory it is an exact rescaling of parity scores, so it cannot change their ranking, and in simulation the ranking metrics did not change at all. Three asymmetric readout profiles are synthetic stress tests, not device data.`,
    keyPoints: ["Qiskit Aer density matrices: exact", "depolarizing, thermal relaxation, readout; low/medium/high + combined = 12 anchors", "symmetric readout negative control passed (ranking change 0; affine residual ≤ 4.4e-16); asymmetric profiles are synthetic"],
    transition: "So what did noise actually change?",
    sources: "configs/noise/anchors_rr_v1.yaml; p3b_noise_matrix.csv; p3b_negative_control.csv.",
    build: async (s, { C, D }) => {
      const src = [
        [FaGaugeHigh, "Depolarizing", "after every 1- and 2-qubit gate", "two-qubit error 0.005 · 0.010 · 0.020"],
        [FaTemperatureHalf, "Thermal relaxation", "during 35 ns and 300 ns gates", "T₁ 200 · 100 · 50 µs"],
        [FaEye, "Readout confusion", "bit flips at measurement", "flip probability 0.005 · 0.02 · 0.05"],
      ];
      for (let i = 0; i < 3; i++) {
        const x = 0.6 + i * 4.1;
        D.card(s, { x, y: 1.5, w: 3.9, h: 2.45 }, D.HEX.lt2, `src-${i}`);
        await D.icon(s, src[i][0], x + 0.25, 1.72, 0.75, D.HEX.dk2, `src-icon-${i}`);
        D.text(s, src[i][1], { x: x + 1.15, y: 1.72, w: 2.6, h: 0.42 }, { fontSize: 17, bold: true, color: C.text2 });
        D.text(s, src[i][2], { x: x + 1.15, y: 2.12, w: 2.6, h: 0.42 }, { fontSize: 12.5, color: C.text1 });
        D.text(s, "low · medium · high", { x: x + 0.25, y: 2.8, w: 3.4, h: 0.3 }, { fontSize: 11.5, color: C.accent5, bold: true });
        D.text(s, src[i][3], { x: x + 0.25, y: 3.1, w: 3.4, h: 0.6 }, { fontSize: 14.5, color: C.text1 });
      }
      D.flow(s, C, [
        { head: "12 anchor conditions", body: "3 sources × 3 severities + 3 combined" },
        { head: "Exact simulation", body: "Qiskit Aer density matrices" },
        { head: "Finite shots", body: "1,024 shots × 20 replicates" },
        { head: "Negative control passed", body: "symmetric readout: ranking metrics unchanged (Δ = 0)", fill: "D7EEEE" },
      ], { y: 4.2, h: 1.05, size: 14 });
      D.text(s, "Plus 3 synthetic asymmetric-readout stress profiles (mean error 0.005–0.05). These are an assumption, not device calibration data.", { x: 0.6, y: 5.4, w: 12.1, h: 0.4 }, { fontSize: 12.5, italic: true, color: C.accent5 });
      await D.takeaway(s, C, "Exact simulation at the registered anchor severities: effects come from the noise model, not from sampling.", { Icon: FaWaveSquare });
      D.source(s, C, "configs/noise/anchors_rr_v1.yaml, p3b_noise_matrix.csv, p3b_negative_control.csv");
    },
  },
  {
    title: "Noise damages calibration, not discrimination",
    kicker: "Phase 3B  ·  frozen P3A-R model, validation partition  ·  completed October 7, 2026",
    speaker: "Tushar",
    script: `Here is the main characterization result. On the left, AUPRC barely moves under any anchor condition: at most 0.003, and every interval contains zero. At least 46 of the 47 top-ranked frauds stay on top.

On the right, calibration collapses. Under combined high noise the Brier score rises from 0.0093 to 0.121, about thirteen times worse, and expected calibration error rises from 0.083 to 0.346. Noise pulls the scores toward one half. Because fraud alerts fire at a fixed threshold, precision falls from 0.53 to 0.03.

So the problem mitigation must solve is calibration, not discrimination. Noise does reorder some legitimate transactions, with Kendall tau between 0.96 and 0.99, but the frauds at the top survive. Mayank will now explain the two mitigation tools.`,
    keyPoints: ["ΔAUPRC ≤ 0.003, all CIs contain 0; ≥ 46 of 47 top frauds kept", "Brier 0.0093 → 0.121; ECE 0.083 → 0.346; precision 0.53 → 0.03", "some bulk reordering (Kendall τ 0.96–0.99)"],
    transition: "Hand-off to Mayank: the mitigation tools.",
    sources: "p3b_exact_metrics.csv (model p3a_r); p4_exact_diagnostics.csv (clean precision 0.532).",
    build: async (s, { C, D, F }) => {
      D.img(s, F("fig3_noise_effects.png"), { x: 0.5, y: 1.4, w: 8.0, h: 4.5 });
      const st = [
        ["≤ 0.003", "change in AUPRC; ≥ 46 of 47 top frauds kept", C.accent1],
        ["0.0093 → 0.121", "Brier score, combined-high noise (13×)", C.accent3],
        ["0.083 → 0.346", "expected calibration error", C.accent3],
        ["0.53 → 0.03", "precision at the frozen alert threshold", C.accent3],
      ];
      st.forEach(([v, l, c], i) => D.stat(s, C, { x: 8.85, y: 1.45 + i * 1.12, w: 3.9, value: v, label: l, color: c, valueSize: 26, labelH: 0.45 }));
      await D.takeaway(s, C, "Mitigation's job here is calibration and threshold decisions, not discrimination.", { Icon: FaScaleBalanced });
      D.source(s, C, "p3b_exact_metrics.csv (P3A-R, exact simulation), p4_exact_diagnostics.csv");
    },
  },
  {
    title: "Two mitigation tools, very different costs",
    kicker: "Phase 4  ·  pre-registered  ·  completed October 7, 2026",
    speaker: "Mayank",
    script: `We compare two standard mitigation techniques, and their combination.

Readout mitigation runs two calibration circuits per batch, all zeros and all ones. From their counts it estimates each qubit's confusion matrix, inverts it, and projects the result back onto valid probabilities. Once calibrated, it is almost free.

Zero-noise extrapolation, or ZNE, deliberately amplifies gate noise by folding the circuit, running it at noise scales one, three and five, and extrapolating linearly back to zero noise. That costs three times the shots and nine times the two-qubit-gate exposure. The combined action applies readout mitigation at every noise scale before extrapolating.

The fair comparison for ZNE is therefore not "no mitigation" but the same three-times shot budget spent on the unmitigated circuit. We call that the extra-shots action.`,
    keyPoints: ["readout: 2 calibration circuits per batch, tensored inverse + simplex projection", "ZNE: global folding λ = 1, 3, 5, linear extrapolation: 3× shots, 9× CX exposure", "fair baseline: same 3× shots, unmitigated"],
    transition: "So which one is worth paying for?",
    sources: "configs/mitigation/*.yaml; p4_costs.csv; zne_schematic is illustrative (labelled).",
    build: async (s, { C, D, S }) => {
      D.cardText(s, C, {
        x: 0.6, y: 1.45, w: 4.15, h: 2.75, head: "Readout mitigation (A1)",
        body: [
          { text: "2 calibration circuits per batch: |0000⟩ and |1111⟩", bullet: true },
          { text: "per-qubit confusion matrices from counts → tensored inverse", bullet: true },
          { text: "project negative quasi-probabilities onto the simplex", bullet: true },
        ], size: 13.5,
      });
      D.img(s, S("zne_schematic.png"), { x: 4.9, y: 1.35, w: 4.6, h: 2.95 });
      D.cardText(s, C, {
        x: 9.65, y: 1.45, w: 3.1, h: 2.75, head: "ZNE (A2)",
        body: [
          { text: "fold the circuit: λ = 1, 3, 5", bullet: true },
          { text: "linear fit to λ = 0", bullet: true },
          { text: "A3 = readout mitigation at every scale, then ZNE", bullet: true },
        ], size: 13.5,
      });
      D.table(s, [
        [D.HEAD("Action"), D.HEAD("What it does"), D.HEAD("Shots per inference"), D.HEAD("Two-qubit-gate exposure")],
        ["A0", "nothing", "S", "1×"],
        ["A1", "readout mitigation", "S + 2S/N", "1×"],
        ["A4", "three times the shots, unmitigated", "3S", "3×"],
        ["A2", "zero-noise extrapolation", "3S", "9×"],
        ["A3", "readout mitigation + ZNE", "3S + 2S/N", "9×"],
      ], { y: 4.4, w: 12.1, colW: [1.0, 5.0, 3.0, 3.1], fontSize: 12.5 });
      D.text(s, "S = shots per circuit · N = transactions per batch · the extrapolation curve is illustrative", { x: 0.6, y: 6.4, w: 12.1, h: 0.3 }, { fontSize: 10.5, italic: true, color: C.accent5 });
      D.source(s, C, "configs/mitigation/*.yaml, p4_costs.csv");
    },
  },
  {
    title: "Mitigation repairs calibration; extra shots do not",
    kicker: "Phase 4  ·  8 conditions × 2 shot budgets × 20 replicates  ·  completed October 7, 2026",
    speaker: "Mayank",
    script: `Here is the resource-matched comparison at 1,024 shots.

Mitigation restores calibration where its noise type is present. Readout mitigation cuts the Brier score from 0.053 to 0.011 under high readout noise. ZNE cuts it from 0.055 to 0.038 under high depolarizing noise. Combined mitigation cuts it from 0.122 to 0.054 under combined high noise. Three times the shots leaves it at 0.121, because shots reduce variance, not bias.

Mitigation never improved AUPRC beyond its shot-matched comparator, which fits the previous slide.

And the best action depended on the noise type: none, readout mitigation, ZNE or both. That made selective mitigation look like a real decision. Whether that decision needs to be learned is the topic of our next meeting. Thank you.`,
    keyPoints: ["Brier 0.053 → 0.011 (readout), 0.055 → 0.038 (ZNE), 0.122 → 0.054 (both); 3× shots 0.121", "no AUPRC gain over the resource-matched comparator", "best action depends on the noise type → selection question (Nov 10)"],
    transition: "Questions.",
    sources: "p4_summary.csv (s1024); p4_resource_matched.csv; p4_best_action.csv.",
    build: async (s, { C, D, F }) => {
      D.img(s, F("fig4_mitigation.png"), { x: 0.5, y: 1.4, w: 7.6, h: 4.45 });
      const rows = [
        ["Readout noise, high", "0.053", "0.011", "A1 readout", "0.053"],
        ["Depolarizing, high", "0.055", "0.038", "A2 ZNE", "0.055"],
        ["Combined, high", "0.122", "0.054", "A3 both", "0.121"],
      ];
      D.table(s, [
        [D.HEAD("Brier (1,024 shots)"), D.HEAD("None"), D.HEAD("Best"), D.HEAD("Action"), D.HEAD("3× shots")],
        ...rows.map((r) => [r[0], r[1], { text: r[2], options: { bold: true, color: "0F8B8D" } }, r[3], r[4]]),
      ], { x: 8.35, y: 1.5, w: 4.4, colW: [1.55, 0.6, 0.6, 0.95, 0.7], fontSize: 11 });
      D.cardText(s, C, {
        x: 8.35, y: 3.2, w: 4.4, h: 2.65, head: "What it means",
        body: [
          { text: "Three times the shots: Brier unchanged (shots cut variance, not bias)", bullet: true },
          { text: "No action improved AUPRC over its resource-matched comparator", bullet: true },
          { text: "Linear ZNE recovered 13–70% of the exact Brier gap", bullet: true },
          { text: "The best action depended on the noise type", bullet: true },
        ], size: 13,
      });
      await D.takeaway(s, C, "Mitigation removes a bias that extra shots cannot. Which action pays depends on the noise type, which is the Nov 10 topic.", { Icon: FaRoute });
      D.source(s, C, "p4_summary.csv (1,024 shots), p4_resource_matched.csv, p4_best_action.csv");
    },
  },
];

module.exports = { meta, slides };
