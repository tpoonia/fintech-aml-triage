// Meeting 7 of 7 — December 8, 2026: Final capstone defense (18 core slides + 6 backup).
const {
  FaWaveSquare, FaGaugeHigh, FaCoins, FaBookOpen, FaBullseye, FaListCheck, FaLock, FaFingerprint,
  FaFlask, FaMicrochip, FaRuler, FaTriangleExclamation, FaLayerGroup, FaCompass, FaChartLine,
  FaCircleCheck, FaQuestion, FaScaleBalanced, FaRoute, FaDatabase, FaTemperatureHalf, FaEye, FaCodeBranch,
} = require("react-icons/fa6");

const meta = {
  id: "2026-12-08",
  index: 6,
  dateLong: "December 8, 2026",
  topic: "Final capstone defense",
  file: "Q-TRACE_2026-12-08_Final-Defense",
  split: "Mayank: slides 1–5, 10–11, 17–18 · Tushar: slides 6–9, 12–16",
  splitStatus: "proposed for roughly equal time; team to confirm",
  presenterLine: "Proposed split: Mayank (1–5, 10–11, 17–18) · Tushar (6–9, 12–16) · about 13–14 minutes",
  status: "Ready for review. Complete study (completed Oct 6–8, 2026). Confirm the allowed length with the instructor: the research plan records a 3–5-slide limit for the biweekly meetings.",
  delivery: [
    "Hand-offs: before slide 6 (to Tushar), before slide 10 (to Mayank), before slide 12 (to Tushar), before slide 17 (to Mayank).",
    "Keep the registered endpoint (material errors) and the raw-disagreement result together; do not let a question surface the second.",
    "Use 'in the studied setting', 'in simulation' and 'to our knowledge'. Never claim quantum advantage, hardware validation or general applicability.",
    "Backup slides B1–B6 are for questions only; see Technical_QA_Guide.md.",
  ],
};

const HEX = {
  tealLight: "E3F2F1", amberLight: "FBEFD9", redLight: "F7E3E1",
};

function ruleDiagram(s, C, D, x, y) {
  const box = (bx, by, w, h, head, body, fill, dark) => {
    D.card(s, { x: bx, y: by, w, h }, fill, "rule-box");
    D.text(s, [
      { text: head, options: { bold: true, fontSize: 12.5, color: dark ? "FFFFFF" : C.text2, breakLine: !!body } },
      ...(body ? [{ text: body, options: { fontSize: 10.5, color: dark ? "E6ECF5" : C.text1 } }] : []),
    ], { x: bx + 0.05, y: by, w: w - 0.1, h }, { align: "center", valign: "middle" });
  };
  const line = (x1, y1, x2, y2) => s.addShape("line", { x: x1, y: y1, w: x2 - x1 || 0.001, h: y2 - y1 || 0.001, line: { color: D.HEX.accent5, width: 1.5, endArrowType: "triangle" } });
  const lab = (lx, ly, t) => D.text(s, t, { x: lx, y: ly, w: 0.55, h: 0.25 }, { fontSize: 10, bold: true, color: C.accent5, align: "center" });
  box(x, y, 2.8, 0.78, "Gate probe", "contraction ≤ t_g (≈ 0.97–0.98)?", D.HEX.lt2);
  box(x + 3.3, y, 2.8, 0.78, "Readout probe", "error ≥ t_r (≈ 0.4%)?", D.HEX.lt2);
  box(x, y + 1.25, 2.8, 0.78, "A1 readout mitigation", "A0 at 256 shots if readout is low", "0072B2", true);
  box(x + 3.3, y + 1.25, 1.32, 0.78, "A3", "combined", "CC79A7", true);
  box(x + 4.78, y + 1.25, 1.32, 0.78, "A2", "ZNE", "D55E00", true);
  line(x + 2.8, y + 0.39, x + 3.3, y + 0.39);
  lab(x + 2.77, y + 0.1, "yes");
  line(x + 1.4, y + 0.78, x + 1.4, y + 1.25);
  lab(x + 1.45, y + 0.88, "no");
  line(x + 3.96, y + 0.78, x + 3.96, y + 1.25);
  lab(x + 3.4, y + 0.88, "yes");
  line(x + 5.44, y + 0.78, x + 5.44, y + 1.25);
  lab(x + 5.5, y + 0.88, "no");
}

const slides = [
  // 1 ------------------------------------------------------------------ research problem
  {
    section: "Problem",
    master: "TITLE",
    title: "When is quantum error mitigation worth paying for?",
    speaker: "Mayank",
    script: `Good afternoon. We are Mayank and Tushar, and this is our capstone defense.

Our research problem: a noisy quantum classifier can spend extra quantum resources on error mitigation. When is that worth paying for, and does deciding it require a learned controller? Our answer, from a pre-registered study confirmed on a sealed held-out test, is that in the studied setting a simple probe rule was enough.`,
    keyPoints: ["the research problem", "answer preview: a simple probe rule was enough in the studied setting"],
    transition: "Why this is a real decision.",
    build: async (s, { C, D, meta }) => {
      await D.titleSlide(s, C, meta, {
        headline: "When is quantum error mitigation worth paying for?",
        subtitle: "A pre-registered study of selective error mitigation for noisy variational quantum fraud classifiers",
        message: "Research problem: when should a noisy quantum classifier spend extra quantum resources on error mitigation, and is learning that decision better than a simple observable rule?",
        MessageIcon: FaBullseye,
      });
    },
  },
  // 2 ------------------------------------------------------------------ motivation
  {
    title: "A noisy quantum classifier faces a spending decision",
    kicker: "Motivation",
    speaker: "Mayank",
    script: `Mitigation options differ in cost by an order of magnitude. Readout mitigation needs about two calibration circuits per batch. Zero-noise extrapolation needs three times the shots and nine times the two-qubit-gate exposure. Buying extra shots only reduces variance, not bias.

In fraud scoring this matters, because alerts fire at a fixed threshold: a model whose probabilities are biased raises the wrong alerts even if it ranks transactions well. So for every execution context there is a real choice: nothing, readout mitigation, ZNE, both, or more shots. Paying for the wrong one either wastes quantum resources or leaves the alerts unreliable.`,
    keyPoints: ["readout ≈ 2 calibration circuits per batch; ZNE 3× shots, 9× CX; extra shots fix variance, not bias", "fraud alerts need calibrated probabilities", "per-context choice among five actions"],
    transition: "What the literature already offers.",
    sources: "p5c_costs.csv; configs/mitigation/*.yaml.",
    build: async (s, { C, D }) => {
      const costs = [
        [FaWaveSquare, "Readout mitigation", "≈ 2 calibration circuits per batch", "nearly free once calibrated"],
        [FaGaugeHigh, "Zero-noise extrapolation", "3× shots · 9× two-qubit-gate exposure", "removes gate-noise bias"],
        [FaCoins, "Extra shots", "3× shots on the same circuit", "removes variance, not bias"],
      ];
      for (let i = 0; i < 3; i++) {
        const x = 0.6 + i * 4.1;
        D.card(s, { x, y: 1.5, w: 3.9, h: 2.35 }, D.HEX.lt2, `cost-${i}`);
        await D.icon(s, costs[i][0], x + 0.25, 1.72, 0.78, D.HEX.dk2, `cost-icon-${i}`);
        D.text(s, costs[i][1], { x: x + 1.15, y: 1.72, w: 2.6, h: 0.78 }, { fontSize: 16, bold: true, color: C.text2, valign: "middle" });
        D.text(s, costs[i][2], { x: x + 0.25, y: 2.7, w: 3.45, h: 0.45 }, { fontSize: 14, bold: true, color: C.text1 });
        D.text(s, costs[i][3], { x: x + 0.25, y: 3.12, w: 3.45, h: 0.45 }, { fontSize: 13, color: C.accent5 });
      }
      D.cardText(s, C, { x: 0.6, y: 4.15, w: 12.1, h: 1.1, head: "Why fraud scoring cares", body: "Alerts fire at a fixed threshold, so biased probabilities raise the wrong alerts even when transactions are ranked well.", size: 14, fill: HEX.tealLight });
      await D.takeaway(s, C, "For every execution context: nothing, readout mitigation, ZNE, both, or more shots?", { y: 5.55, Icon: FaRoute });
      D.source(s, C, "p5c_costs.csv, configs/mitigation/*.yaml", 6.3);
    },
  },
  // 3 ------------------------------------------------------------------ literature
  {
    title: "What the literature offers",
    kicker: "Literature review  ·  references checked against publisher, arXiv or Crossref records (team confirmation pending)",
    speaker: "Mayank",
    script: `Four strands of work frame our study.

The foundations of mitigation are established: zero-noise extrapolation, readout inversion, and probabilistic error cancellation, which removes bias at an exponential sampling cost.

Whether mitigation pays is less settled. A resource-normalized evaluation found it beneficial on average but strongly platform-dependent, and at a matched shot budget ZNE can be worse than the raw estimate.

Adaptive selection already exists: bandit and orchestration methods choose mitigation per context.

And for fraud, quantum classifiers have been tested on the same dataset, with tuned classical baselines ahead; other studies report quantum or hybrid models matching classical ones on particular metrics. So the comparison results are mixed.`,
    keyPoints: ["foundations: ZNE, readout inversion, PEC", "does it pay? platform-dependent; can be worse at matched budget", "adaptive selectors exist", "QML fraud: classical baselines ahead on this dataset"],
    transition: "So what is missing?",
    sources: "deliverables/paper/references.bib; deliverables/paper/REFERENCES_VERIFICATION.md.",
    build: async (s, { C, D }) => {
      const cols = [
        ["Mitigation foundations", ["ZNE: Temme 2017 · Kandala 2019 · Giurgica-Tiron 2020 · Kim 2023", "Readout inversion: Bravyi 2021 · Maciejewski 2020", "PEC at exponential cost: van den Berg 2023", "Review: Cai 2023"], D.HEX.lt2],
        ["Does mitigation pay?", ["Beneficial on average, platform-dependent: Russo 2023", "At a matched shot budget, ZNE can be worse than raw: Zhang 2026", "Select by downstream decisions: Scavino 2026"], HEX.amberLight],
        ["Adaptive selection", ["Telemetry + Thompson sampling: Szachara 2026", "Contextual bandit over ZNE scales: Rahman & Nguyen 2026", "Orchestration in quantum RL: Majid 2026", "Fuzzy rules on circuit features: Rao 2026"], HEX.tealLight],
        ["QML for fraud", ["Same dataset; tuned classical baselines ahead: Dinuț 2026", "Architecture comparisons: El Alami 2026", "Better recall on bank data: Tudisco 2024", "Quantum kernels: Kyriienko 2022"], D.HEX.lt2],
      ];
      cols.forEach(([h, items, fill], i) => {
        D.cardText(s, C, { x: 0.6 + i * 3.075, y: 1.45, w: 2.95, h: 4.3, head: h, body: items.map((t) => ({ text: t, bullet: true })), size: 13.5, headSize: 15.5, fill });
      });
      await D.takeaway(s, C, "Adaptive mitigation is not new; whether it beats simple rules was untested.", { y: 6.0, Icon: FaBookOpen });
      D.source(s, C, "full references on backup slide B6; verification in deliverables/paper/REFERENCES_VERIFICATION.md", 6.72);
    },
  },
  // 4 ------------------------------------------------------------------ gap
  {
    title: "Research gap",
    kicker: "Novelty boundary  ·  stated 'to our knowledge'",
    speaker: "Mayank",
    script: `This table compares the closest selectors with our work. The learned selectors condition on information that is label-dependent or unavailable at deployment, such as ideal-state fidelity, simulator noise parameters, loss or reward, and they report gains mainly over static choices.

To our knowledge, none puts extra shots and combined mitigation in one action space, restricts itself to label-free probes, and tests learning against a simple rule on held-out models under pre-registration. That is our gap. We do not claim to be the first to adapt mitigation; we claim a stricter comparison.`,
    keyPoints: ["learned selectors use label-dependent or simulator-only context", "gains reported mainly over static choices", "gap: extra shots + combined actions, label-free probes, pre-registered held-out test vs simple rules"],
    transition: "Our original hypothesis.",
    sources: "deliverables/paper/REFERENCES_VERIFICATION.md (claim checks a–m).",
    build: async (s, { C, D }) => {
      const H = D.HEAD;
      D.table(s, [
        [H("Work"), H("Selects"), H("Context used"), H("Compared against")],
        ["GSC-QEMit (Szachara et al. 2026)", "abstract mitigation intensity", "telemetry incl. ideal-state fidelity, simulator drift", "unmitigated, static-severe"],
        ["CMAB-ZNE (Rahman & Nguyen 2026)", "ZNE scale-factor sets", "loss / accuracy (label-dependent)", "fixed and grid-search ZNE, other QEM"],
        ["APGEM (Majid et al. 2026)", "none / ZNE / PEC / CDR / readout", "fidelity, reward, noise level", "fixed techniques, Oracle"],
        ["Rao et al. 2026", "none / DD / ZNE (fuzzy rules)", "label-free circuit + hardware features", "not stated in abstract"],
        [{ text: "This work", options: { bold: true } }, { text: "none / readout / ZNE / both / extra shots", options: { bold: true } }, { text: "label-free probes only (leakage-tested)", options: { bold: true } }, { text: "simple rules + learned, held-out, pre-registered", options: { bold: true } }],
      ], { y: 1.5, w: 12.1, colW: [3.2, 2.9, 3.1, 2.9], fontSize: 13 });
      [["1", "Extra shots and combined mitigation in one action space"], ["2", "Label-free probes only: no labels, no simulator parameters"], ["3", "Learning vs simple rules on held-out models, pre-registered"]].forEach(([n, t], i) => {
        D.chip(s, C, n, { x: 0.6 + i * 4.1, y: 4.25, w: 0.45, h: 0.45, fill: D.HEX.accent1, fontSize: 13 });
        D.text(s, t, { x: 1.15 + i * 4.1, y: 4.15, w: 3.45, h: 0.65 }, { fontSize: 14, bold: true, color: C.text2, valign: "middle" });
      });
      await D.takeaway(s, C, "Gap: a pre-registered, held-out test of learned selection against simple observable rules.", { y: 5.55, Icon: FaBullseye });
      D.source(s, C, "deliverables/paper/REFERENCES_VERIFICATION.md", 6.3);
    },
  },
  // 5 ------------------------------------------------------------------ hypothesis
  {
    title: "Original hypothesis and how we tested it",
    kicker: "Original hypothesis (Oct 6)  ·  gates and H1–H4 registered before their outcomes",
    speaker: "Mayank",
    script: `Our original hypothesis was that a learned controller, Q-TRACE, using only label-free probes, would beat fixed policies and a fairly tuned threshold rule on the reliability-cost trade-off. From the start we committed to report it as a result if a simple threshold rule matched it.

We tested this in three stages. Two gates asked whether any material structure was left for learning; a controller would be trained only if one passed. Then one sealed test checked four hypotheses: the rule is near-Oracle, learning adds no meaningful value, the rule beats fixed policies, and it transfers to categorical noise. Tushar will now walk through the model and data.`,
    keyPoints: ["H-control vs the committed alternative (a simple rule suffices)", "two gates decide whether to train a controller", "sealed test: H1 near-Oracle, H2 learning adds nothing meaningful, H3 beats fixed policies, H4 transfers"],
    transition: "Hand-off to Tushar: the architecture.",
    sources: "docs/PREREG_P5B.md, docs/PREREG_P5C.md, docs/PREREG_FINAL.md; configs/final_test/final_v1.yaml.",
    build: async (s, { C, D }) => {
      D.cardText(s, C, { x: 0.6, y: 1.45, w: 5.95, h: 1.4, head: "H-control (original)", body: "A learned controller using only label-free probes beats fixed policies and a fairly tuned threshold rule.", size: 14 });
      D.cardText(s, C, { x: 6.8, y: 1.45, w: 5.95, h: 1.4, head: "The alternative we committed to report", body: "A simple threshold rule matches the learned controller; formalized for the sealed test as H1–H4.", size: 14, fill: HEX.tealLight });
      D.flow(s, C, [
        { head: "Gate G3B", body: "categorical noise: residual for learning?" },
        { head: "Gate G3C", body: "continuous joint noise: residual for learning?" },
        { head: "Sealed test", body: "opened once: H1–H4", fill: HEX.amberLight },
      ], { y: 3.1, h: 1.05, size: 14 });
      const hs = [
        ["H1", "rule near-Oracle: material failure ≤ 0.05, Brier regret ≤ 2%"],
        ["H2", "no learned comparator meaningfully better (non-superiority)"],
        ["H3", "rule beats every universal policy, ≤ always-A3 shots"],
        ["H4", "rule transfers to categorical noise: material ≤ 0.10"],
      ];
      hs.forEach(([h, t], i) => {
        const x = 0.6 + (i % 2) * 6.1;
        const y = 4.4 + Math.floor(i / 2) * 0.62;
        D.chip(s, C, h, { x, y: y + 0.06, w: 0.62, h: 0.36, fill: D.HEX.accent1, fontSize: 11.5 });
        D.text(s, t, { x: x + 0.75, y, w: 5.25, h: 0.5 }, { fontSize: 13.5, color: C.text1, valign: "middle" });
      });
      await D.takeaway(s, C, "Negative outcomes were registered as reportable results before any data existed.", { y: 5.85, Icon: FaListCheck });
      D.source(s, C, "docs/PREREG_P5B.md, docs/PREREG_P5C.md, docs/PREREG_FINAL.md, configs/final_test/final_v1.yaml", 6.55);
    },
  },
  // 6 ------------------------------------------------------------------ architecture
  {
    section: "Methods",
    title: "QML fraud-classification architecture",
    kicker: "Frozen reference model P3A-R  ·  4 qubits  ·  frozen October 6, 2026",
    speaker: "Tushar",
    script: `Our reference classifier uses four features encoded as angles on four qubits, a ZZ feature map, a two-layer RealAmplitudes ansatz with 12 trainable parameters, and a parity readout that maps to a fraud probability. It has 18 two-qubit gates after transpilation.

A pre-registered encoding repair raised its validation AUPRC from 0.104 to 0.507. Classical models on the same inputs reach 0.59 to 0.62, so we make no quantum-advantage claim: the classifier is the noisy workload whose mitigation decisions we study. Its output is an expectation value, the very quantity noise distorts and mitigation repairs.`,
    keyPoints: ["ZZ map + RealAmplitudes (reps 2) + parity; 12 parameters, 18 CX", "repair: AUPRC 0.104 → 0.507", "classical 0.59–0.62 on the same inputs: no quantum advantage"],
    transition: "The data behind it.",
    sources: "configs/repair/p3ar_v1.yaml; p5a_pool_metrics.csv (anchor); p3ar_validation_comparison.csv.",
    build: async (s, { C, D, S }) => {
      D.img(s, S("circuit_p3ar.png"), { x: 0.6, y: 1.35, w: 12.1, h: 3.3 });
      D.stat(s, C, { x: 0.6, y: 4.75, w: 3.9, value: "0.104 → 0.507", valueSize: 26, label: "validation AUPRC after the pre-registered encoding repair (AUROC 0.957)", labelH: 0.6 });
      D.stat(s, C, { x: 4.7, y: 4.75, w: 3.9, value: "0.59–0.62", valueSize: 26, color: C.accent3, label: "classical AUPRC on the same 4 inputs: no quantum advantage", labelH: 0.6 });
      D.stat(s, C, { x: 8.8, y: 4.75, w: 3.95, value: "64 variants", valueSize: 26, color: C.accent6, label: "16 structures × 4 seeds for the benchmark (slide 12)", labelH: 0.6 });
      await D.takeaway(s, C, "The VQC is the noisy workload under study, not a competitor to classical fraud models.", { y: 6.1, Icon: FaMicrochip });
      D.source(s, C, "configs/repair/p3ar_v1.yaml, p5a_pool_metrics.csv, p3ar_validation_comparison.csv", 6.72);
    },
  },
  // 7 ------------------------------------------------------------------ dataset
  {
    title: "Dataset and leakage-safe preprocessing",
    kicker: "Phase 1  ·  public European credit-card fraud data  ·  completed October 6, 2026",
    speaker: "Tushar",
    script: `We use the public European credit-card fraud dataset: 284,807 transactions. After removing exact duplicates, 283,726 rows remain, with 473 frauds, or 0.17 percent.

Rows that differ only in their timestamp are kept together, and a group-aware split creates five disjoint partitions. Preprocessing is fitted on the training partition only. The controller test partition was sealed until the final evaluation. True noise parameters, labels and identifiers never enter a policy, as enforced by a feature registry and tests. The probes are deployable measurements that estimate the noise by design.`,
    keyPoints: ["284,807 → 283,726 rows, 473 frauds (0.17%)", "group-aware split into 5 partitions; preprocessing fitted on training only", "controller test sealed; registry + tests prevent leakage"],
    transition: "How we simulated noise.",
    sources: "ulb_v1_dataset_summary.csv; ulb_v1_phase1_metadata.json.",
    build: async (s, { C, D }) => {
      D.flow(s, C, [
        { head: "284,807 transactions", body: "492 frauds" },
        { head: "Exact deduplication", body: "1,081 duplicate rows removed (773 groups)" },
        { head: "283,726 rows", body: "473 frauds · 0.17%" },
        { head: "Group-aware split", body: "0 groups cross partitions", fill: "D7EEEE" },
      ], { y: 1.45, h: 0.95, size: 14 });
      D.table(s, [
        [D.HEAD("Partition"), D.HEAD("Rows"), D.HEAD("Frauds"), D.HEAD("Used for")],
        ["VQC train", "127,677", "213", "fitting every VQC and the preprocessing"],
        ["VQC validation", "28,372", "47", "qualification, thresholds, characterization"],
        ["Controller train", "42,559", "71", "policy fitting (training models)"],
        ["Controller validation", "28,372", "47", "policy validation (validation models)"],
        [{ text: "Controller test", options: { bold: true } }, "56,746", "95", { text: "sealed; opened once (test models)", options: { bold: true } }],
      ], { y: 2.7, w: 8.2, colW: [2.2, 1.2, 1.0, 3.8], fontSize: 13 });
      D.cardText(s, C, { x: 9.05, y: 2.7, w: 3.7, h: 2.55, head: "Leakage controls", body: [
        { text: "Preprocessing fitted on VQC train only", bullet: true },
        { text: "Offline-only: true noise, labels, IDs", bullet: true },
        { text: "Feature registry + automated tests", bullet: true },
      ], size: 13, fill: HEX.tealLight });
      await D.takeaway(s, C, "Five disjoint, group-aware partitions; the controller test stayed sealed until the end.", { y: 5.55, Icon: FaDatabase });
      D.source(s, C, "ulb_v1_dataset_summary.csv, ulb_v1_phase1_metadata.json", 6.3);
    },
  },
  // 8 ------------------------------------------------------------------ noise models
  {
    title: "Noise models",
    kicker: "Qiskit Aer density matrices  ·  registered anchor severities",
    speaker: "Tushar",
    script: `We simulate noise exactly with density matrices: depolarizing errors after gates, thermal relaxation during gates, and readout confusion. Each has low, medium and high anchors; asymmetric readout is a synthetic stress test, not device data.

We used two environments. Phase 5B used eight near-categorical conditions. Phase 5C varied all sources continuously and jointly: 17 gate settings, one of them gate-free, times four readout settings, giving 68 noise points, shown on the right. The first finding, on the right: across the twelve anchor conditions, noise changed AUPRC by at most 0.003 but raised the Brier score up to thirteen-fold. Noise pulls scores toward one half, so calibration and threshold alerts suffer, while the top-ranked frauds stay on top.`,
    keyPoints: ["depolarizing, thermal relaxation, readout; low/medium/high anchors", "5B: 8 conditions; 5C: 68 continuous joint points (17 gate × 4 readout, one gate-free)", "AUPRC ≤ 0.003 change; Brier up to 13× worse"],
    transition: "What mitigation does about it.",
    sources: "configs/noise/anchors_rr_v1.yaml; p5c_design.csv; p3b_exact_metrics.csv (figure: deliverables/figures/fig3_noise_effects).",
    build: async (s, { C, D, F }) => {
      const src = [
        [FaGaugeHigh, "Depolarizing", "two-qubit error 0.005–0.020"],
        [FaTemperatureHalf, "Thermal relaxation", "T₁ 200 → 50 µs"],
        [FaEye, "Readout confusion", "flip probability 0.005–0.05"],
      ];
      for (let i = 0; i < 3; i++) {
        const y = 1.5 + i * 1.08;
        D.card(s, { x: 0.6, y, w: 5.6, h: 0.95 }, D.HEX.lt2, `n-${i}`);
        await D.icon(s, src[i][0], 0.78, y + 0.15, 0.65, D.HEX.dk2, `n-icon-${i}`);
        D.text(s, [
          { text: src[i][1], options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } },
          { text: src[i][2], options: { fontSize: 13, color: C.text1 } },
        ], { x: 1.6, y, w: 4.5, h: 0.95 }, { valign: "middle" });
      }
      D.img(s, F("fig3_noise_effects.png"), { x: 6.45, y: 1.4, w: 6.3, h: 3.4 });
      D.stat(s, C, { x: 0.6, y: 4.85, w: 2.8, value: "≤ 0.003", valueSize: 26, label: "change in AUPRC", labelH: 0.4 });
      D.stat(s, C, { x: 3.5, y: 4.85, w: 2.8, value: "13×", valueSize: 26, color: C.accent3, label: "worse Brier (0.0093 → 0.121)", labelH: 0.4 });
      D.cardText(s, C, { x: 6.45, y: 4.85, w: 6.3, h: 0.85, head: "", body: "5B: 8 near-categorical conditions · 5C: 17 gate settings (one gate-free) × 4 readout = 68 points", size: 12.5, fill: "E3F2F1" });
      await D.takeaway(s, C, "Noise damaged calibration, not discrimination.", { y: 5.9, Icon: FaWaveSquare });
      D.source(s, C, "configs/noise/anchors_rr_v1.yaml, p5c_design.csv, p3b_exact_metrics.csv", 6.62);
    },
  },
  // 9 ------------------------------------------------------------------ mitigation
  {
    title: "Error-mitigation methods",
    kicker: "Phase 4  ·  resource-matched comparison  ·  completed October 7, 2026",
    speaker: "Tushar",
    script: `We compare five actions: none, readout mitigation, ZNE by global folding at noise scales one, three and five with linear extrapolation, both combined, and three times the shots as the resource-matched baseline.

Mitigation restored calibration: under combined high noise, the Brier score fell from 0.122 to 0.054 with combined mitigation, while three times the shots left it at 0.121. No action improved AUPRC beyond its shot-matched comparator, and the best action depended on the noise type: readout mitigation for readout noise, ZNE for gate noise, both for combined noise. Mayank will explain how we tested the decision.`,
    keyPoints: ["A0–A4 with explicit shot and CX costs", "Brier 0.122 → 0.054 (combined); 3× shots 0.121", "no AUPRC gain; best action depends on noise type"],
    transition: "Hand-off to Mayank: the experimental design.",
    sources: "p4_summary.csv (s1024); p5c_costs.csv.",
    build: async (s, { C, D, F }) => {
      D.table(s, [
        [D.HEAD("Action"), D.HEAD("Method"), D.HEAD("Shots / inference"), D.HEAD("CX exposure")],
        ["A0", "none", "S", "1×"],
        ["A1", "tensored readout inversion + simplex projection", "S + 2S/N", "1×"],
        ["A4", "3× shots, unmitigated (resource-matched)", "3S", "3×"],
        ["A2", "ZNE: global folding λ = 1, 3, 5; linear fit", "3S", "9×"],
        ["A3", "readout mitigation + ZNE", "3S + 2S/N", "9×"],
      ], { y: 1.5, w: 6.2, colW: [0.8, 3.1, 1.3, 1.0], fontSize: 12 });
      D.caption(s, C, "S = shots per circuit · N = transactions per batch", { x: 0.6, y: 4.0, w: 6.2, h: 0.3 });
      D.img(s, F("fig4_mitigation.png"), { x: 7.0, y: 1.4, w: 5.75, h: 3.6 });
      D.stat(s, C, { x: 0.6, y: 4.45, w: 3.0, value: "0.122 → 0.054", valueSize: 24, label: "Brier, combined-high, combined mitigation", labelH: 0.5 });
      D.stat(s, C, { x: 3.75, y: 4.45, w: 3.0, value: "0.121", valueSize: 24, color: C.accent3, label: "Brier with 3× shots: unchanged", labelH: 0.5 });
      await D.takeaway(s, C, "Mitigation removes a bias that shots cannot; which action pays depends on the noise.", { y: 5.75, Icon: FaScaleBalanced });
      D.source(s, C, "p4_summary.csv (1,024 shots), p5c_costs.csv", 6.48);
    },
  },
  // 10 ----------------------------------------------------------------- experimental design
  {
    section: "Design",
    title: "Experimental design and integrity",
    kicker: "Pre-registration, gates and a one-time sealed test  ·  October 6–8, 2026",
    speaker: "Mayank",
    script: `From Phase 3A-R on, every phase was pre-registered and committed before its own outcomes existed; for Phases 5B, 5C and the final test the code was pushed together with the registration. Gates decided whether to continue, and negative outcomes count as results.

The controller test outcomes were written to a sealed store. A guard allowed exactly one unlock, after the protocol and frozen comparators were pushed, and logged every read. Learned comparators were frozen by fingerprints of their decisions. Sixteen slow tests re-run Phases 1 to 5C and the final test. Every reported run records its commit, configuration hash, package versions and seeds.`,
    keyPoints: ["from Phase 3A-R: registered before each phase's outcomes", "sealed test: one guarded unlock, reads logged", "comparators fingerprinted; 16 slow reproduction tests"],
    transition: "How we scored decisions.",
    sources: "docs/PREREG_*.md; final_metadata.json (unlock record); tests/ (16 slow tests).",
    build: async (s, { C, D, S }) => {
      D.img(s, S("workflow_slide.png"), { x: 0.5, y: 1.4, w: 8.1, h: 4.1 });
      const integ = [
        [FaListCheck, "Pre-registered", "from 3A-R on, before each phase's outcomes"],
        [FaLock, "Sealed test", "one guarded unlock; reads logged"],
        [FaFingerprint, "Frozen comparators", "decision fingerprints verified"],
        [FaFlask, "Reproducible", "16 slow tests re-run Phases 1–5C + final"],
      ];
      for (let i = 0; i < integ.length; i++) {
        const y = 1.5 + i * 1.07;
        await D.icon(s, integ[i][0], 8.9, y, 0.72, D.HEX.accent1, `integ-${i}`);
        D.text(s, [
          { text: integ[i][1], options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } },
          { text: integ[i][2], options: { fontSize: 12.5, color: C.text1 } },
        ], { x: 9.8, y: y - 0.06, w: 2.95, h: 0.9 }, {});
      }
      await D.takeaway(s, C, "Gates decided whether to proceed; negative outcomes were reported as results.", { y: 5.8, Icon: FaListCheck });
      D.source(s, C, "docs/PREREG_*.md, final_metadata.json, tests/", 6.52);
    },
  },
  // 11 ----------------------------------------------------------------- metrics
  {
    title: "Evaluation metrics",
    kicker: "Brier-primary, cost-aware, cluster-level statistics",
    speaker: "Mayank",
    script: `Because noise acts on calibration, the primary endpoint is the Brier score. The Oracle picks the cheapest action within ten percent of the best Brier score. A policy fails when it disagrees with the Oracle; the failure is material when its Brier score is more than twenty percent above the best, or it spends at least one extra shot-set per inference.

Costs are counted in shots, including the probes for probing policies. Models nested in structures are the independent units, so intervals come from a two-stage cluster bootstrap, resampling structures and then models. One subtlety: Brier regret can be slightly negative, because the Oracle may trade some reliability for a lower cost. Tushar will now present the results.`,
    keyPoints: ["Brier primary; Oracle = cheapest within 10%", "failure vs material failure (Brier > 1.2× best, or ≥ 1 extra shot-set)", "shots incl. probes (66·S per batch); two-stage cluster bootstrap"],
    transition: "Hand-off to Tushar: the 64-model benchmark.",
    sources: "configs/mixed_noise_study/p5c_v1.yaml; configs/final_test/final_v1.yaml.",
    build: async (s, { C, D }) => {
      const defs = [
        ["Primary endpoint", "Brier score of the mitigated fraud probabilities, mean of 20 finite-shot replicates", D.HEX.lt2],
        ["Oracle p*", "cheapest action whose Brier score is within ε = 10% of the best (evaluation only)", HEX.tealLight],
        ["Failure", "any disagreement with p*", D.HEX.lt2],
        ["Material failure", "Brier > (1 + 2ε) × best, or ≥ 1 extra shot-set (S) per inference", HEX.amberLight],
        ["Cost", "shots per inference, including 66·S probe shots per batch for probing policies", D.HEX.lt2],
        ["Uncertainty", "two-stage cluster bootstrap: structures, then models (2,000 resamples)", D.HEX.lt2],
      ];
      defs.forEach(([h, b, fill], i) => {
        const x = 0.6 + (i % 3) * 4.1;
        const y = 1.5 + Math.floor(i / 3) * 1.95;
        D.cardText(s, C, { x, y, w: 3.9, h: 1.8, head: h, body: b, size: 13.5, fill });
      });
      await D.takeaway(s, C, "Brier regret can be slightly negative: the Oracle may trade up to 10% of reliability for a lower cost.", { y: 5.6, Icon: FaRuler });
      D.source(s, C, "configs/mixed_noise_study/p5c_v1.yaml, configs/final_test/final_v1.yaml", 6.32);
    },
  },
  // 12 ----------------------------------------------------------------- benchmark
  {
    section: "Results",
    title: "The 64-model benchmark",
    kicker: "Phases 5A–5C  ·  every model under every action  ·  completed October 7–8, 2026",
    speaker: "Tushar",
    script: `To make models, not transactions, the unit of analysis, we trained 64 classifiers: 16 structures times four seeds, varying features, encoding, ansatz and readout. All qualified, with a median AUPRC of 0.235. Structures were split eight, four and four, and the four test structures were sealed.

Every model was run under every action, noise context, budget and replicate: about 1.4 million paired outcomes. A policy sees only static descriptors and two probes: the readout calibration circuits, and a gate probe of 32 fixed inputs at fold factors one and three. Together they cost 66 circuits per batch, charged to every probing policy.`,
    keyPoints: ["64 VQCs; median AUPRC 0.235 (0.047–0.538); split 8/4/4", "≈ 1.4 M paired outcomes (102,400 + 1,305,600)", "probes: readout calibration + 32-binding gate probe, 66 circuits per batch"],
    transition: "What the policies made of it.",
    sources: "p5a_pool_metrics.csv; p5b_split.csv; Phase 5B/5C row counts (EXPERIMENT_PROTOCOL §3.12–3.13); p5b_feature_definitions.csv.",
    build: async (s, { C, D, S }) => {
      D.img(s, S("pool_auprc.png"), { x: 0.5, y: 1.4, w: 7.0, h: 4.6 });
      D.stat(s, C, { x: 7.85, y: 1.45, w: 4.9, value: "64 models", valueSize: 28, label: "16 structures × 4 seeds; median clean AUPRC 0.235 (0.047–0.538)", labelH: 0.55 });
      D.stat(s, C, { x: 7.85, y: 2.75, w: 4.9, value: "≈ 1.4 million", valueSize: 28, color: C.accent6, label: "paired counterfactual outcomes (5B 102,400; 5C 1,305,600)", labelH: 0.55 });
      D.stat(s, C, { x: 7.85, y: 4.05, w: 4.9, value: "66 circuits", valueSize: 28, color: C.accent2, label: "probe cost per batch: 2 readout calibration + 32 gate bindings × folds 1, 3", labelH: 0.55 });
      await D.takeaway(s, C, "Models, nested in structures, are the independent units; 4 test structures stayed sealed.", { y: 6.1, Icon: FaLayerGroup });
      D.source(s, C, "p5a_pool_metrics.csv, p5b_split.csv, p5b_feature_definitions.csv; row counts per docs/EXPERIMENT_PROTOCOL.md §3.12–3.13", 6.76);
    },
  },
  // 13 ----------------------------------------------------------------- policy comparison
  {
    title: "Policy comparison: the gates failed, a simple rule emerged",
    kicker: "Gates G3B and G3C  ·  validation data  ·  decided October 7–8, 2026",
    speaker: "Tushar",
    script: `Under categorical noise, the best action was a lookup on the noise type, and a four-cell probe rule was wrong in only 0.33 percent of validation cases. Under continuous joint noise, where 16 of 17 gate settings carry gate noise by design, combined mitigation or ZNE was almost always best, and the two-threshold rule on the left made material errors in only 2.0 percent of validation decisions.

Both were below the five-percent gates. The remaining structure was detectable, mostly from mean-Z readouts, but not material, so, as registered, no learned controller was trained. Instead we froze four learned comparators with fixed settings for the sealed test.`,
    keyPoints: ["G3B: category rule wrong in 0.33% → fail", "G3C: R_thr material 2.0% [1.6, 2.7] → fail", "residual detectable, not material → no controller trained"],
    transition: "The sealed test.",
    sources: "p5b_metadata.json; p5c_metadata.json (R_thr cells/thresholds, g3c); fig5 source tables.",
    build: async (s, { C, D, F }) => {
      D.text(s, "The probe rule R_thr", { x: 0.6, y: 1.45, w: 6.2, h: 0.35 }, { fontSize: 14.5, bold: true, color: C.text2 });
      ruleDiagram(s, C, D, 0.6, 1.9);
      D.cardText(s, C, { x: 0.6, y: 4.15, w: 3.0, h: 1.4, head: "G3B → FAIL", body: "category rule wrong in 0.33% of validation cases", fill: HEX.redLight, headColor: C.accent3, size: 12.5 });
      D.cardText(s, C, { x: 3.75, y: 4.15, w: 3.0, h: 1.4, head: "G3C → FAIL", body: "R_thr material failure 2.0% [1.6, 2.7]", fill: HEX.redLight, headColor: C.accent3, size: 12.5 });
      D.img(s, F("fig5_preferred_actions.png"), { x: 7.0, y: 1.4, w: 5.75, h: 4.2 });
      await D.takeaway(s, C, "As registered, no learned controller was trained; fixed learned comparators were tested instead.", { y: 5.8, Icon: FaCodeBranch });
      D.source(s, C, "p5b_metadata.json, p5c_metadata.json, final_metadata.json", 6.52);
    },
  },
  // 14 ----------------------------------------------------------------- held-out results
  {
    title: "Final held-out results",
    kicker: "One-time sealed test, October 8, 2026  ·  16 unseen models, 4 unseen structures",
    speaker: "Tushar",
    script: `On the sealed test, all four hypotheses were supported. Under continuous joint noise the rule made material errors in 2.0 percent of decisions, with an interval of 1.4 to 2.6 percent, and its Brier score was within 0.03 percent of the Oracle's. Under categorical noise: 8.8 percent, inside the ten-percent bound.

The best learned comparator, gradient boosting, tied the rule on material errors at 2.1 percent. To be precise: it disagreed with the Oracle less often, 6.5 against 21.9 percent, but most of the rule's extra choices came from the unseen mean-Z structure, cost only two calibration circuits and were not material. The learned models were also unstable: gradient boosting made 10.7 percent material errors on validation.`,
    keyPoints: ["R_thr material 2.0% [1.4, 2.6]; Brier −0.03%; 5B 8.8%", "H1–H4 supported", "GBT 2.1% material; better raw agreement (6.5% vs 21.9%) but not material"],
    transition: "What it costs.",
    sources: "final_policies_5c_test.csv; final_policies_5b_test.csv; final_paired_vs_rthr_5c_test.csv; final_metadata.json.",
    build: async (s, { C, D, F }) => {
      D.img(s, F("fig8_final_heldout.png"), { x: 0.5, y: 1.4, w: 8.0, h: 4.3 });
      D.stat(s, C, { x: 8.8, y: 1.45, w: 3.95, value: "2.0%", valueSize: 30, label: "material errors, rule (95% CI 1.4–2.6%; 4 structures, likely too narrow)", labelH: 0.45 });
      D.stat(s, C, { x: 8.8, y: 2.6, w: 3.95, value: "2.1%", valueSize: 30, color: C.accent3, label: "best learned (gradient boosting): a tie", labelH: 0.45 });
      D.stat(s, C, { x: 8.8, y: 3.75, w: 3.95, value: "8.8%", valueSize: 30, color: C.accent2, label: "rule, categorical test (bound 10%)", labelH: 0.45 });
      ["H1", "H2", "H3", "H4"].forEach((h, i) => D.chip(s, C, `${h} ✓`, { x: 8.8 + i * 0.98, y: 4.95, w: 0.88, h: 0.36, fill: D.HEX.accent1, fontSize: 11.5 }));
      await D.takeaway(s, C, "Any disagreement: gradient boosting 6.5% vs rule 21.9%, mostly on mean-Z, where the rule's extra choices were cheap.", { y: 5.9, Icon: FaScaleBalanced });
      D.source(s, C, "final_policies_5c_test.csv, final_policies_5b_test.csv, final_paired_vs_rthr_5c_test.csv, final_metadata.json", 6.62);
    },
  },
  // 15 ----------------------------------------------------------------- cost-reliability
  {
    title: "Cost–reliability findings",
    kicker: "Sealed test, October 8, 2026  ·  shots per inference including probes",
    speaker: "Tushar",
    script: `Against cost, the rule sits next to the Oracle: 0.6 percent more shots, and 3.4 percent fewer than always using combined mitigation, with about a third of its material errors. Never mitigating uses about a third of the shots, but makes material errors 96 percent of the time.

One disclosure matters here: always-combined's 5.9 percent material errors are exactly the one gate-free setting out of 17 in our design. So this saving, and the case for probing, depend on how often batches are gate-free. Probing pays for itself only above about 645 to 685 transactions per batch, a validation estimate.`,
    keyPoints: ["rule: +0.6% vs Oracle, −3.4% vs always-combined", "never mitigate: 0.35× shots, 96% material errors", "always-A3 5.9% = 1/17 gate-free design share"],
    transition: "The limits of these findings.",
    sources: "final_policies_5c_test.csv; p5c_design.csv.",
    build: async (s, { C, D, S }) => {
      D.img(s, S("cost_reliability_slide.png"), { x: 0.5, y: 1.4, w: 8.0, h: 4.15 });
      D.stat(s, C, { x: 8.8, y: 1.45, w: 3.95, value: "+0.6%", valueSize: 30, color: C.accent2, label: "shots vs the Oracle (rule)", labelH: 0.4 });
      D.stat(s, C, { x: 8.8, y: 2.55, w: 3.95, value: "−3.4%", valueSize: 30, label: "shots vs always-combined", labelH: 0.4 });
      D.stat(s, C, { x: 8.8, y: 3.65, w: 3.95, value: "0.35× · 96%", valueSize: 30, color: C.accent3, label: "never mitigate: shots · material errors", labelH: 0.4 });
      D.cardText(s, C, { x: 8.8, y: 4.75, w: 3.95, h: 0.85, head: "", body: "Always-combined's 5.9% = 1 gate-free setting in 17", fill: HEX.amberLight, size: 12.5 });
      await D.takeaway(s, C, "The saving over always-combined depends on how often batches are gate-free.", { y: 5.85, Icon: FaCoins });
      D.source(s, C, "final_policies_5c_test.csv, p5c_design.csv", 6.58);
    },
  },
  // 16 ----------------------------------------------------------------- limitations
  {
    section: "Close",
    title: "Limitations and threats to validity",
    kicker: "What the evidence cannot show",
    speaker: "Tushar",
    script: `Our evidence is simulation-only, at four qubits, on one dataset, with two mitigation techniques. The held-out test has only four structures, so its intervals are probably too narrow, and H2 is a non-superiority result on material errors, not proof that learning cannot help. On raw agreement with the Oracle, learned models did better. The gate probe barely sees thermal noise, and gate noise was present in 16 of 17 settings by design. Per-model alert thresholds were tuned on clean validation data, which is optimistic. We claim no quantum advantage and no general applicability.`,
    keyPoints: ["simulation only; 4 qubits; one dataset; two techniques", "4 held-out structures; H2 non-superiority; raw-endpoint caveat", "thermal blind spot; design dependence; no quantum advantage"],
    transition: "Hand-off to Mayank: the contribution.",
    sources: "final_policies_5c_test.csv; final_paired_vs_rthr_5c_test.csv; p5c_probe_validity.csv; p3ar_validation_comparison.csv.",
    build: async (s, { C, D }) => {
      const lim = [
        [FaMicrochip, "Simulation only", "no hardware run; asymmetric readout synthetic; no crosstalk, drift or coherent errors"],
        [FaRuler, "Small scale", "4 qubits, shallow circuits, one public dataset"],
        [FaTriangleExclamation, "No quantum advantage", "classical models score higher on the same inputs"],
        [FaLayerGroup, "Narrow mitigation set", "readout inversion and linear ZNE only; no PEC, CDR or DD"],
        [FaChartLine, "Few held-out structures", "only 4: intervals likely too narrow; H2 is non-superiority"],
        [FaCompass, "Probe, design and endpoint", "thermal blind spot; 16 of 17 gate settings noisy; learned better on raw agreement"],
      ];
      for (let i = 0; i < lim.length; i++) {
        const x = 0.6 + (i % 2) * 6.15;
        const y = 1.5 + Math.floor(i / 2) * 1.55;
        await D.icon(s, lim[i][0], x, y, 0.75, D.HEX.accent3, `lim-${i}`);
        D.text(s, [
          { text: lim[i][1], options: { bold: true, fontSize: 15.5, color: C.text2, breakLine: true } },
          { text: lim[i][2], options: { fontSize: 13, color: C.text1 } },
        ], { x: x + 0.95, y: y - 0.05, w: 4.95, h: 1.3 }, {});
      }
      D.source(s, C, "final_policies_5c_test.csv, final_paired_vs_rthr_5c_test.csv, p5c_probe_validity.csv, p3ar_validation_comparison.csv", 6.6);
    },
  },
  // 17 ----------------------------------------------------------------- contribution
  {
    title: "Research contribution",
    kicker: "What this capstone adds, to our knowledge",
    speaker: "Mayank",
    script: `Our contribution has three parts. A characterization: noise damaged calibration, not discrimination, and mitigation repaired calibration where extra shots could not. A leakage-safe counterfactual benchmark across 64 independently trained models. And a pre-registered, held-out test of learned selection against simple rules, which found that a two-threshold probe rule performed competitively.

Every result is reproducible from the repository, and the manuscript and report are complete drafts for review; nothing has been submitted. The broader lesson is methodological: adaptive mitigation should be evaluated against simple probe rules and a cost-aware Oracle.`,
    keyPoints: ["characterization: calibration, not discrimination", "leakage-safe benchmark: 64 models, ≈ 1.4 M outcomes", "pre-registered learning-vs-rule test", "reproducible; manuscript drafted, nothing submitted"],
    transition: "Our answer and what comes next.",
    sources: "deliverables/paper/main.tex; deliverables/README.md.",
    build: async (s, { C, D }) => {
      const cs = [
        [FaWaveSquare, "Characterization", "Noise damaged calibration, not discrimination; mitigation repaired calibration; extra shots did not."],
        [FaDatabase, "Benchmark", "Leakage-safe counterfactual benchmark: 64 VQCs × noise × budget × 5 actions, ≈ 1.4 M outcomes."],
        [FaScaleBalanced, "Pre-registered test", "A held-out, one-time test of learned selection against simple rules: the rule was competitive."],
      ];
      for (let i = 0; i < 3; i++) {
        const x = 0.6 + i * 4.1;
        D.card(s, { x, y: 1.5, w: 3.9, h: 3.4 }, i === 2 ? HEX.tealLight : D.HEX.lt2, `c-${i}`);
        await D.icon(s, cs[i][0], x + 0.25, 1.75, 0.8, i === 2 ? D.HEX.accent1 : D.HEX.dk2, `c-icon-${i}`);
        D.text(s, cs[i][1], { x: x + 0.25, y: 2.75, w: 3.4, h: 0.45 }, { fontSize: 17, bold: true, color: C.text2 });
        D.text(s, cs[i][2], { x: x + 0.25, y: 3.25, w: 3.45, h: 1.5 }, { fontSize: 13.5, color: C.text1 });
      }
      D.text(s, "Artifacts: manuscript (LaTeX), capstone report, pre-registrations, code and aggregate tables, 16 reproduction tests. Nothing has been submitted.", { x: 0.6, y: 5.1, w: 12.1, h: 0.5 }, { fontSize: 13, italic: true, color: C.accent5 });
      await D.takeaway(s, C, "Evaluate adaptive mitigation against simple probe rules and a cost-aware Oracle, on held-out models.", { y: 5.75, Icon: FaCircleCheck });
      D.source(s, C, "deliverables/README.md", 6.47);
    },
  },
  // 18 ----------------------------------------------------------------- conclusions
  {
    master: "CLOSE",
    title: "Conclusions and future work",
    kicker: "Answer",
    speaker: "Mayank",
    script: `So, our answer. Spend on mitigation when the probes detect noise that biases calibration, choose the technique by noise type with a simple rule, and in this setting do not learn that decision.

Next steps: validate on hardware, where readout asymmetry, drift and crosstalk are real; add richer mitigation such as probabilistic error cancellation and a thermal-sensitive probe; and test larger circuits, where noise may also damage discrimination.

Thank you. We are happy to take your questions.`,
    keyPoints: ["answer: rule-based selective mitigation sufficed in the studied setting", "future: hardware, richer mitigation + thermal probe, larger circuits"],
    transition: "Questions (backup slides B1–B6).",
    build: async (s, { C, D }) => {
      await D.icon(s, FaCircleCheck, 0.6, 1.55, 0.8, D.HEX.accent1, "concl-icon");
      D.text(s, [
        { text: "What we found", options: { bold: true, fontSize: 19, color: "FFFFFF", breakLine: true } },
        { text: "Mitigation fixes calibration, not discrimination; extra shots never substitute.", options: { bullet: true, breakLine: true } },
        { text: "In our joint-noise design the material question is: is gate noise present?", options: { bullet: true, breakLine: true } },
        { text: "A two-threshold probe rule was near-Oracle on unseen models; fixed learned comparators did not reduce material errors.", options: { bullet: true } },
      ], { x: 1.6, y: 1.5, w: 5.4, h: 4.2 }, { fontSize: 15.5, color: "E6ECF5", paraSpaceAfter: 8 });
      await D.icon(s, FaQuestion, 7.4, 1.55, 0.8, D.HEX.accent2, "future-icon");
      D.text(s, [
        { text: "Future research", options: { bold: true, fontSize: 19, color: "FFFFFF", breakLine: true } },
        { text: "Hardware validation with real readout asymmetry, drift and crosstalk.", options: { bullet: true, breakLine: true } },
        { text: "Richer mitigation (PEC, CDR, DD) and a thermal-sensitive gate probe.", options: { bullet: true, breakLine: true } },
        { text: "Larger circuits, where noise may also degrade discrimination.", options: { bullet: true, breakLine: true } },
        { text: "Endpoints that weight fraud-operations costs.", options: { bullet: true } },
      ], { x: 8.4, y: 1.5, w: 4.4, h: 4.2 }, { fontSize: 15.5, color: "E6ECF5", paraSpaceAfter: 8 });
      D.text(s, "In the studied setting, a simple observable probe rule performed competitively with learned comparators.", { x: 0.6, y: 5.95, w: 12.1, h: 0.6 }, { fontSize: 18, bold: true, italic: true, color: "7FD6D3" });
    },
  },
  // backups -------------------------------------------------------------------------
  {
    section: "Backup",
    backup: true,
    title: "B1 · Per-structure held-out results",
    kicker: "Backup  ·  sealed test, continuous joint noise",
    speaker: "either",
    script: `If asked why the rule's raw disagreement is higher on the test: it comes from the unseen mean-Z structure, where the rule adds readout mitigation that mean-Z readouts barely need. That costs two calibration circuits per batch and is not material (1.4 percent). R_obs, which conditions on the readout type, absorbs it; learned comparators reached 5 to 30 percent material errors on that structure.`,
    keyPoints: ["mean-Z structure drives raw disagreement", "rule material 1.4% there; learned 5–30%"],
    sources: "final_by_structure_5c_test.csv.",
    build: async (s, { C, D, R }) => {
      D.img(s, R("final_b_structures.png"), { x: 0.5, y: 1.4, w: 12.3, h: 4.7 });
      D.source(s, C, "final_by_structure_5c_test.csv (results/figures/final_b_structures.png)", 6.4);
    },
  },
  {
    backup: true,
    title: "B2 · Where ZNE versus combined mitigation wins",
    kicker: "Backup  ·  Phase 5C preferred action by noise point",
    speaker: "either",
    script: `If asked where ZNE alone beats combined mitigation: at low readout severity under gate noise, readout error below about 0.003. Readout mitigation or no mitigation wins only on the gate-free setting.`,
    keyPoints: ["ZNE alone where readout error < ~0.003", "A0/A1 only on the gate-free setting"],
    sources: "p5c_preferred_by_point_train.csv, p5c_preferred_by_point_val.csv.",
    build: async (s, { C, D, R }) => {
      D.img(s, R("p5c_b_preferred_map.png"), { x: 0.5, y: 1.35, w: 12.3, h: 5.1 });
      D.source(s, C, "p5c_preferred_by_point_train.csv, p5c_preferred_by_point_val.csv", 6.6);
    },
  },
  {
    backup: true,
    title: "B3 · Probe ablation and probing break-even",
    kicker: "Backup  ·  validation data only; the sealed test was not reused",
    speaker: "either",
    script: `If asked which probe matters: the gate probe alone keeps material failure at 1.8 percent under continuous noise and 9.4 percent under categorical noise, though raw disagreement rises from 10 to 25 percent. A readout-only rule reaches 6.2 and 50 percent. Probing pays for itself relative to always-combined only above about 645 to 685 transactions per batch, or about 80 under categorical noise, and that break-even depends on the gate-free share.`,
    keyPoints: ["gate probe alone: 1.8% / 9.4% material", "break-even ≈ 645–685 transactions (≈ 80 categorical)"],
    sources: "ablation_probes.csv; ablation_probe_cost.csv.",
    build: async (s, { C, D, F }) => {
      D.img(s, F("fig9_probe_ablation.png"), { x: 0.5, y: 1.4, w: 8.0, h: 4.5 });
      D.stat(s, C, { x: 8.85, y: 1.5, w: 3.9, value: "1.8%", valueSize: 30, label: "material failure, gate probe alone (5C validation)", labelH: 0.5 });
      D.stat(s, C, { x: 8.85, y: 2.85, w: 3.9, value: "≈ 645–685", valueSize: 30, color: C.accent2, label: "transactions per batch to break even (≈ 80 categorical)", labelH: 0.5 });
      D.text(s, "The 66·S probe includes the 2 calibration circuits always-combined already pays, so the break-even is conservative and depends on the gate-free share.", { x: 8.85, y: 4.25, w: 3.9, h: 1.4 }, { fontSize: 12, italic: true, color: C.accent5 });
      D.source(s, C, "ablation_probes.csv, ablation_probe_cost.csv", 6.4);
    },
  },
  {
    backup: true,
    title: "B4 · Baselines and the encoding repair",
    kicker: "Backup  ·  Phases 2, 3A and 3A-R",
    speaker: "either",
    script: `If asked about classical baselines and the first quantum model: random forest on all thirty features reaches 0.805; on the VQC's four inputs classical models reach 0.59 to 0.62, and only the logistic-regression gap has an interval excluding zero. The first encoding saturated and aliased, leaving 91 distinct fraud inputs; the pre-registered repair keeps 212 and raises AUPRC from 0.104 to 0.507.`,
    keyPoints: ["RF 0.805 (30 features); 0.59–0.62 on VQC inputs", "repair: 91 → 212 distinct fraud inputs; 0.104 → 0.507"],
    sources: "phase2_classical_metrics.csv; p3ar_validation_comparison.csv; p3ar_encoding_diagnostics.csv.",
    build: async (s, { C, D, S }) => {
      D.img(s, S("baselines_auprc.png"), { x: 0.5, y: 1.4, w: 6.1, h: 4.6 });
      D.img(s, S("encoding_repair.png"), { x: 6.8, y: 1.4, w: 6.0, h: 4.6 });
      D.source(s, C, "phase2_classical_metrics.csv, p3ar_validation_comparison.csv, p3ar_encoding_diagnostics.csv", 6.4);
    },
  },
  {
    backup: true,
    title: "B5 · Statistical details",
    kicker: "Backup  ·  paired differences on the sealed test (R_thr − comparator; positive favours the comparator)",
    speaker: "either",
    script: `If asked about the statistics: these are the paired differences behind slides 14 and 15. On material errors no learned comparator is meaningfully better. On raw disagreement, gradient boosting, the depth-3 tree, the benefit model and R_obs are significantly closer to the Oracle. Learned comparators shifted between validation and test, while the rule did not. Only four structures were held out, so a cluster bootstrap over four clusters has few distinct resamples and its intervals are likely too narrow.`,
    keyPoints: ["material: no comparator meaningfully better", "raw: several comparators significantly closer to Oracle", "validation → test shifts; 4-cluster bootstrap caveat"],
    sources: "final_paired_vs_rthr_5c_test.csv; final_paired_vs_rthr_5b_test.csv; p7_policies_5c_val.csv.",
    build: async (s, { C, D }) => {
      D.table(s, [
        [D.HEAD("Comparator (5C test)"), D.HEAD("Material: R_thr − comp."), D.HEAD("Any disagreement: R_thr − comp."), D.HEAD("Material, validation → test")],
        ["Gradient boosting", "−0.0005 [−0.027, +0.016]", "+0.154 [+0.028, +0.391]", "0.107 → 0.021"],
        ["Tree, depth 3", "−0.006 [−0.026, +0.005]", "+0.133 [+0.003, +0.387]", "0.175 → 0.026"],
        ["GBT benefit model", "−0.006 [−0.029, +0.011]", "+0.069 [+0.007, +0.173]", "0.037 → 0.026"],
        ["Logistic regression", "−0.074 [−0.213, +0.011]", "+0.046 [−0.023, +0.152]", "0.065 → 0.094"],
        ["R_obs (rule + readout type)", "−0.001 [−0.007, +0.002]", "+0.130 [+0.001, +0.384]", "—"],
        [{ text: "R_thr (deployed rule)", options: { bold: true } }, "—", "—", { text: "0.020 → 0.020", options: { bold: true } }],
      ], { y: 1.5, w: 12.1, colW: [3.1, 3.0, 3.2, 2.8], fontSize: 13 });
      D.text(s, "5B categorical test: R_cat 0.064 vs R_thr 0.088 (paired 0.024 [0.011, 0.037]); learned comparators 0.118–0.439.", { x: 0.6, y: 4.75, w: 12.1, h: 0.4 }, { fontSize: 13, color: C.text1 });
      D.text(s, "Intervals: two-stage cluster bootstrap over only 4 held-out structures (likely too narrow; always-A3's is degenerate).", { x: 0.6, y: 5.2, w: 12.1, h: 0.4 }, { fontSize: 13, italic: true, color: C.accent3 });
      D.source(s, C, "final_paired_vs_rthr_5c_test.csv, final_paired_vs_rthr_5b_test.csv, p7_policies_5c_val.csv, final_policies_5c_test.csv", 6.4);
    },
  },
  {
    backup: true,
    title: "B6 · References",
    kicker: "Backup  ·  verified against publisher, arXiv and Crossref records (team confirmation pending)",
    speaker: "either",
    script: `Full references for the citations on the slides. The complete, verified bibliography is in the manuscript.`,
    keyPoints: ["references for slides 3–4 and the methods"],
    sources: "deliverables/paper/references.bib.",
    build: async (s, { C, D }) => {
      const refs = [
        "Bravyi et al. (2021) Phys. Rev. A 103:042605",
        "Cai et al. (2023) Rev. Mod. Phys. 95:045005",
        "Dal Pozzolo et al. (2015) IEEE SSCI, 159–166",
        "Dinuț et al. (2026) Electronics 15(11):2489",
        "El Alami et al. (2026) Appl. Intell. 56(3):83",
        "Giurgica-Tiron et al. (2020) IEEE QCE, 306–316",
        "Havlíček et al. (2019) Nature 567:209–212",
        "Kandala et al. (2019) Nature 567:491–495",
        "Kim et al. (2023) Nat. Phys. 19:752–759",
        "Kyriienko & Magnusson (2022) arXiv:2208.01203",
        "Maciejewski et al. (2020) Quantum 4:257",
        "Majid et al. (2026) arXiv:2610.01253",
        "Preskill (2018) Quantum 2:79",
        "Rahman & Nguyen (2026) IEEE JSAC 44:5600–5614",
        "Rao et al. (2026) IEEE I3CTCON, 1–6",
        "Russo et al. (2023) IEEE TQE 4:1–18",
        "Scavino (2026) arXiv:2607.02888",
        "Schuld et al. (2020) Phys. Rev. A 101:032308",
        "Szachara et al. (2026) arXiv:2604.24551",
        "Temme et al. (2017) Phys. Rev. Lett. 119:180509",
        "Tudisco et al. (2024) IEEE Access 12:102918",
        "van den Berg et al. (2023) Nat. Phys. 19:1116–1121",
        "Zhang et al. (2026) arXiv:2609.38713",
        "ULB ML Group (2018) Kaggle: mlg-ulb/creditcardfraud",
      ];
      const half = Math.ceil(refs.length / 2);
      [refs.slice(0, half), refs.slice(half)].forEach((col, j) => {
        D.text(s, col.map((r, i) => ({ text: r, options: { breakLine: i < col.length - 1 } })), { x: 0.6 + j * 6.15, y: 1.5, w: 5.95, h: 4.9 }, { fontSize: 12.5, color: C.text1, paraSpaceAfter: 5 });
      });
      D.source(s, C, "deliverables/paper/references.bib, deliverables/paper/REFERENCES_VERIFICATION.md", 6.55);
    },
  },
];

module.exports = { meta, slides };
