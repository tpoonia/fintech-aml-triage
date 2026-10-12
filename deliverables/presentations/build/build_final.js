// Final capstone presentation (~12-15 minutes, 16 slides + 2 backup).
// node build_final.js  ->  ../Q-TRACE_Final_Capstone.pptx
const path = require("path");
const {
  FaCoins, FaWaveSquare, FaGaugeHigh, FaBullseye, FaFlask, FaDatabase, FaMicrochip, FaLock,
  FaFingerprint, FaListCheck, FaTriangleExclamation, FaCompass, FaLayerGroup, FaRuler,
  FaChartLine, FaCircleCheck, FaQuestion, FaUserCheck,
} = require("react-icons/fa6");
const { applyTheme } = require("./theme");
const D = require("./deck_common");

const OUT = path.resolve(__dirname, "..", "Q-TRACE_Final_Capstone.pptx");
const F = (n) => path.join(D.FIG, n);
const R = (n) => path.join(D.RES_FIG, n);

function tableOpts(C, colW, extra = {}) {
  return {
    colW, fontSize: 12.5, color: "1A1F2B", border: { type: "solid", pt: 0.5, color: "D5DBE5" },
    margin: [0.04, 0.08, 0.04, 0.08], valign: "middle", ...extra,
  };
}
const HEAD = (t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: "1B2A49" } } });

async function main() {
  const { pres, C } = D.newDeck("Q-TRACE final capstone: when is quantum error mitigation worth paying for?");

  // 1 ---------------------------------------------------------------- title
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
  s.addText("When is quantum error mitigation worth paying for?", {
    x: 0.8, y: 1.7, w: 11.7, h: 1.6, fontSize: 40, bold: true, color: C.background1,
    fontFace: D.THEME.headFontFace, margin: 0, isTextBox: true, objectName: "title",
  });
  s.addText("A pre-registered study of selective error mitigation for noisy variational quantum fraud classifiers", {
    x: 0.8, y: 3.35, w: 11.0, h: 0.9, fontSize: 20, color: "CADCFC", margin: 0, isTextBox: true, objectName: "subtitle",
  });
  s.addText([
    { text: "Mayank Kumar Pokhriyal  ·  Tushar Poonia", options: { bold: true, breakLine: true } },
    { text: "M.S. in Artificial Intelligence capstone  ·  Katz School of Science and Health, Yeshiva University", options: { breakLine: true } },
    { text: "Final capstone presentation  ·  Fall 2026" },
  ], { x: 0.8, y: 5.1, w: 11.7, h: 1.2, fontSize: 15, color: "E6ECF5", margin: 0, isTextBox: true, objectName: "authors" });
  s.addNotes("[Mayank] Introduce the team and the one-sentence question: when is quantum error mitigation worth its cost, and does learning that decision beat a simple rule? Preview the answer: a simple probe rule was enough, confirmed on a sealed held-out test. (~40 s)");

  // 2 ---------------------------------------------------------------- motivation
  pres.addSection({ title: "Motivation" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
  s.addText("A noisy quantum classifier faces a spending decision", { placeholder: "title" });
  const costs = [
    [FaWaveSquare, "Readout mitigation", "≈ 2 calibration circuits per batch"],
    [FaGaugeHigh, "Zero-noise extrapolation", "3× shots · 9× two-qubit-gate exposure"],
    [FaCoins, "Extra shots", "3× shots · removes variance, not bias"],
  ];
  for (let i = 0; i < costs.length; i++) {
    const x = 0.6 + i * 4.15;
    D.card(s, C, { x, y: 1.5, w: 3.85, h: 1.85 }, D.HEX.lt2, "cost-card-" + i);
    await D.iconCircle(s, C, costs[i][0], x + 0.3, 1.75, 0.85, D.HEX.dk2, "cost-icon-" + i);
    s.addText(costs[i][1], { x: x + 1.3, y: 1.75, w: 2.4, h: 0.85, fontSize: 17, bold: true, color: C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: "cost-head-" + i });
    s.addText(costs[i][2], { x: x + 0.3, y: 2.8, w: 3.3, h: 0.8, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "cost-body-" + i });
  }
  D.bullets(s, C, [
    "Fraud scoring needs calibrated probabilities and reliable alerts at a fixed threshold, not just good ranking.",
    "Mitigation can repair noisy probabilities, but every technique costs circuits, shots and gate exposure.",
    { text: "So the operational question is: per execution context, run nothing, readout mitigation, ZNE, both, or more shots?", bold: true },
  ], { x: 0.6, y: 3.8, w: 12.1, h: 2.9 }, { fontSize: 19, name: "motivation-bullets" });
  s.addNotes("[Mayank] Mitigation methods differ in cost by an order of magnitude. Readout mitigation is nearly free once calibrated; ZNE triples shots and multiplies two-qubit-gate exposure by nine; extra shots only reduce variance. In fraud scoring calibrated probabilities matter because alerts fire at a fixed threshold. So there is a real per-context decision. (~60 s)");

  // 3 ---------------------------------------------------------------- RQ + hypotheses
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
  s.addText("Research question and hypotheses", { placeholder: "title" });
  await D.iconCircle(s, C, FaBullseye, 0.6, 1.5, 0.9, D.HEX.accent1, "rq-icon");
  s.addText("When should a noisy QML fraud model spend additional quantum resources on mitigation, and is learning that decision better than a simple observable rule?", {
    x: 1.75, y: 1.45, w: 10.9, h: 1.05, fontSize: 19, bold: true, color: C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: "rq",
  });
  const hyp = [
    ["H-control (original)", "A learned controller (Q-TRACE) using only label-free probes beats fixed policies on a reliability–cost trade-off."],
    ["H-rule (registered alternative)", "A simple probe rule matches the cost-aware Oracle; learning adds no meaningful value."],
    ["Characterization", "Noise mainly damages calibration; mitigation repairs calibration but not AUPRC beyond a shot-matched baseline."],
  ];
  for (let i = 0; i < hyp.length; i++) {
    const y = 2.85 + i * 1.3;
    D.card(s, C, { x: 0.6, y, w: 12.1, h: 1.1 }, i === 1 ? "E3F2F1" : D.HEX.lt2, "hyp-card-" + i);
    s.addText(hyp[i][0], { x: 0.85, y, w: 3.4, h: 1.1, fontSize: 16, bold: true, color: C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: "hyp-head-" + i });
    s.addText(hyp[i][1], { x: 4.3, y, w: 8.2, h: 1.1, fontSize: 15, color: C.text1, margin: 0, valign: "middle", isTextBox: true, objectName: "hyp-body-" + i });
  }
  s.addNotes("[Mayank] Our question, and the hypotheses we registered before running anything. We wrote down the alternative, that a simple rule suffices, as a legitimate result. (~45 s)");

  // 4 ---------------------------------------------------------------- literature & novelty
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Motivation" });
  s.addText("Literature and novelty boundary", { placeholder: "title" });
  const rows = [
    [HEAD("Work"), HEAD("Selects"), HEAD("Context used"), HEAD("Compared against")],
    ["GSC-QEMit (Szachara et al., 2026)", "abstract mitigation intensity", "telemetry incl. ideal-state fidelity, simulator drift", "unmitigated, static-severe"],
    ["CMAB-ZNE (Rahman & Nguyen, 2026)", "ZNE scale-factor sets", "loss / accuracy (label-dependent)", "fixed and grid-search ZNE, other QEM"],
    ["APGEM (Majid et al., 2026; QRL routing)", "none / ZNE / PEC / CDR / readout", "fidelity, reward, noise level", "fixed techniques, Oracle"],
    ["Rao et al., 2026", "none / DD / ZNE (fuzzy rules)", "label-free circuit + hardware features", "not stated in abstract"],
    [{ text: "This work", options: { bold: true } }, { text: "none / readout / ZNE / both / extra shots", options: { bold: true } }, { text: "label-free probes only (leakage-tested)", options: { bold: true } }, { text: "simple rules + learned, held-out, pre-registered", options: { bold: true } }],
  ];
  s.addTable(rows, { x: 0.6, y: 1.45, w: 12.1, ...tableOpts(C, [3.3, 2.9, 3.0, 2.9], { fontSize: 14 }), objectName: "lit-table" });
  D.card(s, C, { x: 0.6, y: 4.75, w: 12.1, h: 1.25 }, "E3F2F1", "gap-card");
  await D.iconCircle(s, C, FaBullseye, 0.85, 4.95, 0.85, D.HEX.accent1, "gap-icon");
  s.addText("Gap we address: to our knowledge, prior selectors were not tested against simple observable rules, on held-out models, under pre-registration, with extra shots and combined mitigation in the action space.", {
    x: 1.95, y: 4.8, w: 10.5, h: 1.15, fontSize: 16, color: C.text2, margin: 0, valign: "middle", isTextBox: true, objectName: "gap-text",
  });
  D.caption(s, C, "References agent-checked against publisher, arXiv and Crossref records; team confirmation pending before submission.", { x: 0.6, y: 6.2, w: 12.1, h: 0.4 }, "lit-caption");
  s.addNotes("[Mayank] Adaptive mitigation selection is not new: bandit and orchestration approaches exist. What we add, to our knowledge, is extra shots and combined mitigation in one action space, a context restricted to cheap label-free probes, and a pre-registered held-out test of learning against simple rules. We do not claim to be first to adapt mitigation. (~60 s)");

  // 5 ---------------------------------------------------------------- dataset
  pres.addSection({ title: "Methods" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methods" });
  s.addText("Dataset and leakage-safe design", { placeholder: "title" });
  const parts = [
    [HEAD("Partition"), HEAD("Rows"), HEAD("Frauds"), HEAD("Role")],
    ["VQC train", "127,677", "213", "fit every VQC + preprocessing"],
    ["VQC validation", "28,372", "47", "qualification, thresholds, characterization"],
    ["Controller train", "42,559", "71", "fit policies (training models)"],
    ["Controller validation", "28,372", "47", "validate policies"],
    ["Controller test", "56,746", "95", "sealed; opened once"],
  ];
  s.addTable(parts, { x: 0.6, y: 1.45, w: 8.2, ...tableOpts(C, [2.3, 1.2, 1.0, 3.7], { fontSize: 14 }), objectName: "partition-table" });
  D.stat(s, C, { x: 0.6, y: 4.55, w: 2.6, value: "283,726", label: "transactions after deduplication", valueSize: 30, name: "d-rows" });
  D.stat(s, C, { x: 3.4, y: 4.55, w: 2.4, value: "0.17%", label: "fraud prevalence (473 frauds)", valueSize: 30, color: C.accent2, name: "d-prev" });
  D.stat(s, C, { x: 6.0, y: 4.55, w: 2.8, value: "0", label: "feature groups crossing partitions", valueSize: 30, color: C.accent6, name: "d-groups" });
  await D.iconCircle(s, C, FaDatabase, 9.3, 1.5, 0.8, D.HEX.dk2, "data-icon");
  D.bullets(s, C, [
    "European credit-card fraud data: 284,807 rows → 283,726 after deduplication (473 frauds, 0.17%).",
    "Rows identical except timestamp never straddle partitions.",
    "True noise parameters, labels and IDs are offline-only, enforced by a feature registry and tests.",
  ], { x: 9.3, y: 2.5, w: 3.45, h: 3.9 }, { fontSize: 14, name: "data-bullets" });
  s.addNotes("[Tushar] Five disjoint partitions, group-aware so near-duplicates cannot leak. Policies are fitted and evaluated on controller partitions only, and the controller test partition was sealed until the end. (~50 s)");

  // 6 ---------------------------------------------------------------- QML methodology
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methods" });
  s.addText("QML methodology: VQCs and a 64-model pool", { placeholder: "title" });
  D.addImageFit(s, R("p3ar_pr_comparison.png"), { x: 0.5, y: 1.3, w: 5.4, h: 4.9 }, { name: "repair-figure" });
  D.caption(s, C, "Pre-registered encoding repair, validation precision–recall (Phase 3A-R).", { x: 0.6, y: 6.25, w: 5.2, h: 0.5 }, "repair-caption");
  await D.iconCircle(s, C, FaMicrochip, 6.3, 1.45, 0.8, D.HEX.dk2, "vqc-icon");
  D.bullets(s, C, [
    "4 qubits: angle encoding → ZZ feature map → RealAmplitudes / EfficientSU2; parity or mean-Z readout.",
    { text: "Encoding repair: AUPRC 0.104 → 0.507 (AUROC 0.957); classical models on the same inputs: 0.59–0.62.", bold: true },
    "64 frozen VQCs = 16 structures × 4 seeds; median AUPRC 0.235 (0.047–0.538).",
    "Split by structure 8 / 4 / 4: test structures never seen by any policy.",
  ], { x: 7.3, y: 1.4, w: 5.45, h: 5.0 }, { fontSize: 15, name: "vqc-bullets" });
  s.addNotes("[Tushar] Our first VQC learned weak signal because its angle encoding saturated and aliased; a pre-registered repair fixed it. Classical models score higher on the same inputs (clearly so for logistic regression), so we make no quantum-advantage claim. We then trained 64 independent VQCs so that models, not transactions, are the unit of analysis, and split them by structure. (~60 s)");

  // 7 ---------------------------------------------------------------- noise simulations
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methods" });
  s.addText("Noise breaks calibration, not discrimination", { placeholder: "title" });
  D.addImageFit(s, F("fig3_noise_effects.png"), { x: 0.5, y: 1.3, w: 7.3, h: 3.1 }, { name: "noise-figure" });
  D.addImageFit(s, R("p5c_a_design.png"), { x: 0.5, y: 4.45, w: 7.3, h: 2.4 }, { name: "design-figure" });
  D.bullets(s, C, [
    "Qiskit Aer density matrices: depolarizing, thermal relaxation, readout confusion; finite-shot draws paired across actions.",
    { text: "AUPRC moves ≤ 0.003; Brier up to 13× (0.009 → 0.121).", bold: true },
    "Phase 5B: 8 near-categorical conditions.",
    "Phase 5C: 68 continuous joint-noise points (split-plot Latin hypercube) within validated ranges; 256–4,096 shots.",
    "Asymmetric readout is a synthetic assumption.",
  ], { x: 8.1, y: 1.4, w: 4.65, h: 5.4 }, { fontSize: 14, name: "noise-bullets" });
  s.addNotes("[Tushar] Noise reshapes calibration, not discrimination: the top panel shows AUPRC essentially flat, and the top-ranked frauds stay on top, while Brier rises up to 13-fold. Scores do reorder slightly among legitimate transactions. The bottom panel is the Phase 5C design: 17 gate settings crossed with four readout settings each, never beyond the validated 'high' anchors. (~60 s)");

  // 8 ---------------------------------------------------------------- mitigation methods
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Methods" });
  s.addText("Error-mitigation methods and their costs", { placeholder: "title" });
  const acts = [
    [HEAD("Action"), HEAD("Method"), HEAD("Shots / inference"), HEAD("CX exposure")],
    ["A0", "none", "S", "1×"],
    ["A1", "tensored readout inversion + simplex projection", "S + 2S/N", "1×"],
    ["A4", "3× shots, unmitigated", "3S", "3×"],
    ["A2", "ZNE: global folding λ = 1, 3, 5; linear fit", "3S", "9×"],
    ["A3", "readout mitigation + ZNE", "3S + 2S/N", "9×"],
  ];
  s.addTable(acts, { x: 0.6, y: 1.45, w: 6.3, ...tableOpts(C, [0.8, 3.1, 1.3, 1.1], { fontSize: 12 }), objectName: "action-table" });
  D.caption(s, C, "S = shots per circuit; N = transactions per batch. Probe cost (66·S shots per batch) is charged to probing policies.", { x: 0.6, y: 4.05, w: 6.3, h: 0.6 }, "action-caption");
  D.bullets(s, C, [
    "No action improves AUPRC over its shot-matched baseline.",
    { text: "Brier restored: 0.053 → 0.011 (readout), 0.055 → 0.038 (ZNE), 0.122 → 0.054 (both); 3× shots: unchanged.", bold: true },
  ], { x: 0.6, y: 4.75, w: 6.3, h: 1.9 }, { fontSize: 15, name: "mitigation-bullets" });
  D.addImageFit(s, F("fig4_mitigation.png"), { x: 7.1, y: 1.45, w: 5.75, h: 5.1 }, { name: "mitigation-figure" });
  s.addNotes("[Tushar] Five actions with very different costs. Mitigation never improved AUPRC beyond simply spending the same shots, but it restored calibration, and extra shots could not. Which mitigation helps depends on the noise type: readout noise needs readout mitigation, gate noise needs ZNE. (~60 s)");

  // 9 ---------------------------------------------------------------- integrity
  pres.addSection({ title: "Design" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Design" });
  s.addText("Experimental design and integrity", { placeholder: "title" });
  D.addImageFit(s, F("fig2_workflow.png"), { x: 0.5, y: 1.3, w: 8.0, h: 3.9 }, { name: "workflow-figure" });
  const integ = [
    [FaListCheck, "Pre-registered", "config + code pushed before every outcome"],
    [FaLock, "Sealed test", "unlocked once, by a guard; reads logged"],
    [FaFingerprint, "Frozen comparators", "decision fingerprints verified at test"],
    [FaFlask, "Reproducible", "16 slow tests re-run Phases 1–5C and the final test"],
  ];
  for (let i = 0; i < integ.length; i++) {
    const y = 1.4 + i * 1.3;
    await D.iconCircle(s, C, integ[i][0], 8.85, y, 0.75, D.HEX.accent1, "integ-icon-" + i);
    s.addText(integ[i][1], { x: 9.8, y: y - 0.05, w: 3.0, h: 0.4, fontSize: 15, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "integ-head-" + i });
    s.addText(integ[i][2], { x: 9.8, y: y + 0.35, w: 3.0, h: 0.6, fontSize: 13, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "integ-body-" + i });
  }
  D.caption(s, C, "Gates decide whether to proceed; negative outcomes are reported as results.", { x: 0.6, y: 5.35, w: 7.8, h: 0.5 }, "workflow-caption");
  s.addNotes("[Mayank] Every phase was pre-registered with its code and pushed before outcomes existed. Our controller-test data were generated into a sealed store and opened exactly once, by a guard that refuses unsafe states. Learned comparators were frozen by fingerprints of their decisions. (~60 s)");

  // 10 ---------------------------------------------------------------- controller + baselines + gates
  pres.addSection({ title: "Results" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Controllers, baselines and two failed gates", { placeholder: "title" });
  D.card(s, C, { x: 0.6, y: 1.45, w: 5.9, h: 4.0 }, D.HEX.lt2, "policy-card");
  s.addText("Policies compared (all fitted on training models)", { x: 0.85, y: 1.6, w: 5.5, h: 0.45, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "policy-head" });
  D.bullets(s, C, [
    "Never / always A1–A4; best single action",
    "R_cat: 5B category thresholds (0.005, 0.90)",
    { text: "R_thr: 2 probe thresholds per budget (deployable)", bold: true },
    "R_obs: R_thr per readout type",
    "Learned (fixed specs): logistic, depth-3 tree, gradient boosting; GBT predicting per-action Brier",
    "Oracle: cheapest action within 10% of best Brier",
  ], { x: 0.85, y: 2.15, w: 5.5, h: 3.2 }, { fontSize: 14, name: "policy-bullets" });
  D.stat(s, C, { x: 7.0, y: 1.5, w: 5.7, value: "99.7%", label: "G3B (categorical noise): a 4-cell probe rule recovers the best action. FAIL → no controller.", name: "g3b" });
  D.stat(s, C, { x: 7.0, y: 3.35, w: 5.7, value: "2.0%", label: "G3C (continuous joint noise): material errors of the best rule [1.6, 2.7]. FAIL → no controller.", name: "g3c" });
  D.stat(s, C, { x: 7.0, y: 5.2, w: 5.7, value: "0%", label: "contexts where 3× shots was the best action, in either environment.", color: C.accent2, name: "a4" });
  s.addNotes("[Mayank] We compared fixed policies, three simple probe rules and four learned comparators whose hyperparameters were fixed in advance. Two pre-registered gates asked whether any material decision structure was left for learning. Both found only a small, statistically detectable but non-material residual, so both failed and no Q-TRACE controller was trained. Extra shots were never the best action. (~60 s)");

  // 11 ---------------------------------------------------------------- held-out
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Statistical results on the sealed held-out test", { placeholder: "title" });
  D.addImageFit(s, F("fig8_final_heldout.png"), { x: 0.5, y: 1.3, w: 8.4, h: 4.9 }, { name: "final-figure" });
  D.stat(s, C, { x: 9.2, y: 1.4, w: 3.6, value: "2.0%", label: "material errors, R_thr (95% CI 1.5–2.6%), 16 unseen models", name: "f-mat" });
  D.stat(s, C, { x: 9.2, y: 3.0, w: 3.6, value: "−0.03%", label: "Brier regret vs Oracle (CI −1.7 to +1.2%)", name: "f-reg" });
  D.stat(s, C, { x: 9.2, y: 4.6, w: 3.6, value: "8.8%", label: "material errors under categorical noise (5B test; H4 ≤ 10%)", color: C.accent6, name: "f-5b" });
  D.caption(s, C, "Two-stage cluster bootstrap over only 4 held-out structures, so CIs are likely too narrow. H1–H4 all supported.", { x: 0.6, y: 6.3, w: 8.2, h: 0.4 }, "final-caption");
  s.addNotes("[Tushar] The sealed test: 16 models from four unseen structures, opened once. A material error means a Brier score more than 20 percent above the best, or at least one extra shot-set per inference. The probe rule made material errors in 2 percent of decisions and matched the Oracle's Brier; the regret can be slightly negative because the Oracle is allowed to be up to 10 percent worse in exchange for being cheaper. Under categorical noise it stayed within the pre-registered 10 percent bound. All four hypotheses held, but with only four test structures the intervals are likely too narrow. (~60 s)");

  // 12 ---------------------------------------------------------------- learned vs rule
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("No learned comparator reduces material errors", { placeholder: "title" });
  D.addImageFit(s, F("fig7_learned_vs_rule.png"), { x: 0.5, y: 1.3, w: 8.6, h: 4.6 }, { name: "paired-figure" });
  D.bullets(s, C, [
    { text: "Best learned on 5C test (gradient boosting): 2.1% vs 2.0%; difference +0.0005 [−0.016, +0.027].", bold: true },
    "It agrees with the Oracle more often (6.5% vs 21.9% disagreement); the rule's extra choices are cheap.",
    "Categorical noise: learned 12–44%; R_cat beats R_thr (6.4% vs 8.8%).",
    "Unseen mean-Z structure: learned 5–30%, rule 1.4%.",
  ], { x: 9.35, y: 1.4, w: 3.45, h: 4.9 }, { fontSize: 13, name: "paired-bullets" });
  D.caption(s, C, "Comparator − R_thr; positive favours the rule; shaded band = pre-registered ±0.02 margin.", { x: 0.6, y: 6.0, w: 8.4, h: 0.5 }, "paired-caption");
  s.addNotes("[Tushar] Paired differences against the rule, with cluster-bootstrap intervals. On the registered endpoint, material errors, no learned comparator is meaningfully better. Be precise here: gradient boosting does disagree with the Oracle less often, but the rule's extra disagreements cost two calibration circuits and are not material. The learned models were also unstable between validation and test, and generalized worse to a readout type seen only once in training. Under categorical noise the older category rule beats R_thr. (~55 s)");

  // 13 ---------------------------------------------------------------- cost–reliability
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Cost–reliability trade-offs", { placeholder: "title" });
  D.addImageFit(s, F("fig6_cost_reliability.png"), { x: 0.5, y: 1.3, w: 8.6, h: 4.6 }, { name: "cost-figure" });
  D.stat(s, C, { x: 9.4, y: 1.4, w: 3.4, value: "+0.6%", label: "shots vs the Oracle (R_thr, 5C test)", color: C.accent2, name: "c-ora" });
  D.stat(s, C, { x: 9.4, y: 3.0, w: 3.4, value: "−3.4%", label: "shots vs always-combined; its 5.9% errors = the gate-free share of our design", color: C.accent1, name: "c-a3" });
  D.stat(s, C, { x: 9.4, y: 4.6, w: 3.4, value: "0.35×", label: "shots for never-mitigating, at 96% material errors", color: C.accent3, name: "c-a0" });
  s.addNotes("[Mayank] Cost versus reliability. Never mitigating is cheap but almost always wrong; always using combined mitigation is reliable but overspends. The probe rule sits next to the Oracle: 0.6 percent more shots, 3.4 percent fewer than always-combined. Note that always-combined's 5.9 percent material errors are exactly the one gate-free setting in 17 of our design, so this saving would shrink on a device where gate noise is always present. (~50 s)");

  // 14 ---------------------------------------------------------------- ablations
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Results" });
  s.addText("Ablations: the gate probe carries the decision", { placeholder: "title" });
  D.addImageFit(s, F("fig9_probe_ablation.png"), { x: 0.5, y: 1.3, w: 8.4, h: 4.4 }, { name: "ablation-figure" });
  D.stat(s, C, { x: 9.2, y: 1.4, w: 3.6, value: "1.8%", label: "material errors with the gate probe alone (5C validation)", name: "a-gate" });
  D.stat(s, C, { x: 9.2, y: 3.0, w: 3.6, value: "≈ 645–685", label: "batch size below which probing does not pay (5C; depends on gate-free share)", valueSize: 30, color: C.accent2, name: "a-be" });
  D.bullets(s, C, [
    "Shot budget changes the best action in < 3% of cases.",
    "Tolerance 0.05–0.20: rule material errors 2.0–7.5%.",
  ], { x: 9.2, y: 4.65, w: 3.6, h: 1.8 }, { fontSize: 13, name: "ablation-bullets" });
  D.caption(s, C, "Validation data only; the sealed test was not reused.", { x: 0.6, y: 5.85, w: 8.2, h: 0.4 }, "ablation-caption");
  s.addNotes("[Mayank] Ablations on validation data only. The gate probe alone recovers the rule on material errors: the material question is whether to pay for ZNE. Probing pays only above roughly 645 to 685 transactions per batch under continuous noise, about 80 under categorical noise, and that break-even depends on how often batches are gate-free. Results are stable across budgets and tolerances. (~55 s)");

  // 15 ---------------------------------------------------------------- limitations
  pres.addSection({ title: "Close" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Close" });
  s.addText("Limitations and threats to validity", { placeholder: "title" });
  const lim = [
    [FaMicrochip, "Simulation only", "No hardware run; asymmetric readout is synthetic; no crosstalk, drift or coherent errors."],
    [FaRuler, "Small scale", "4 qubits, shallow circuits, one public dataset (0.17% fraud, inherited PCA)."],
    [FaTriangleExclamation, "No quantum advantage", "Classical models score higher on the same inputs."],
    [FaLayerGroup, "Narrow mitigation set", "Readout inversion and linear ZNE only; no PEC, CDR or dynamical decoupling."],
    [FaCompass, "Probe and design", "Gate probe barely sees thermal noise (Spearman −0.12); 16 of 17 gate settings carry gate noise."],
    [FaChartLine, "Few held-out structures", "Only 4: CIs likely too narrow; thresholds tuned on clean validation data."],
  ];
  for (let i = 0; i < lim.length; i++) {
    const col = i % 2;
    const row = Math.floor(i / 2);
    const x = 0.6 + col * 6.15;
    const y = 1.45 + row * 1.75;
    await D.iconCircle(s, C, lim[i][0], x, y, 0.8, D.HEX.accent3, "lim-icon-" + i);
    s.addText(lim[i][1], { x: x + 1.0, y: y - 0.03, w: 4.9, h: 0.42, fontSize: 16, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "lim-head-" + i });
    s.addText(lim[i][2], { x: x + 1.0, y: y + 0.42, w: 4.9, h: 0.95, fontSize: 14, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "lim-body-" + i });
  }
  s.addNotes("[Tushar] Our evidence is simulation-only, at four qubits, on one dataset, with two mitigation techniques. The advantage over always-combined depends on how often our design is gate-free, and with four test structures the intervals are likely optimistic. We make no quantum-advantage claim and no claim of universal generalization; hardware validation is the main gap. (~50 s)");

  // 16 ---------------------------------------------------------------- conclusion + future
  s = pres.addSlide({ masterName: "SECTION_DARK", sectionTitle: "Close" });
  s.addText("Conclusions and future research", { placeholder: "title" });
  await D.iconCircle(s, C, FaCircleCheck, 0.6, 1.5, 0.8, D.HEX.accent1, "concl-icon");
  s.addText([
    { text: "What we found", options: { bold: true, fontSize: 19, color: "FFFFFF", breakLine: true } },
    { text: "Mitigation fixes calibration, not discrimination; extra shots never substitute.", options: { bullet: true, breakLine: true } },
    { text: "In our joint-noise design the material decision is: is gate noise present?", options: { bullet: true, breakLine: true } },
    { text: "A two-threshold probe rule is near-Oracle on unseen models; fixed learned comparators did not reduce material errors.", options: { bullet: true } },
  ], { x: 1.6, y: 1.45, w: 5.5, h: 4.4, fontSize: 15.5, color: "E6ECF5", margin: 0, valign: "top", paraSpaceAfter: 8, isTextBox: true, objectName: "concl-text" });
  await D.iconCircle(s, C, FaQuestion, 7.4, 1.5, 0.8, D.HEX.accent2, "future-icon");
  s.addText([
    { text: "Next questions", options: { bold: true, fontSize: 19, color: "FFFFFF", breakLine: true } },
    { text: "Hardware validation with real readout asymmetry and drift.", options: { bullet: true, breakLine: true } },
    { text: "Richer mitigation (PEC, CDR, DD) and a thermal-sensitive probe.", options: { bullet: true, breakLine: true } },
    { text: "Larger circuits, where noise may also degrade discrimination.", options: { bullet: true } },
  ], { x: 8.4, y: 1.45, w: 4.4, h: 4.4, fontSize: 15.5, color: "E6ECF5", margin: 0, valign: "top", paraSpaceAfter: 8, isTextBox: true, objectName: "future-text" });
  s.addText("Answer: in the studied setting, a simple probe rule performed competitively with learned controllers.", {
    x: 0.6, y: 6.15, w: 12.1, h: 0.55, fontSize: 18, bold: true, italic: true, color: "7FD6D3", margin: 0, isTextBox: true, objectName: "answer",
  });
  s.addNotes("[Mayank] Our answer: spend resources on mitigation when probes detect noise that biases calibration, choose the technique by noise type with a simple rule, and, in this setting, learning that decision did not pay off. Next steps are hardware, richer mitigation and larger circuits. Thank you; questions welcome. (~60 s)");

  // backup ------------------------------------------------------------- B1, B2
  pres.addSection({ title: "Backup" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Backup" });
  s.addText("Backup: per-structure held-out results", { placeholder: "title" });
  D.addImageFit(s, R("final_b_structures.png"), { x: 0.5, y: 1.4, w: 12.3, h: 4.6 }, { name: "structures-figure" });
  D.caption(s, C, "The unseen mean-Z structure explains R_thr's higher raw disagreement (non-material: two calibration circuits); R_obs absorbs it.", { x: 0.6, y: 6.15, w: 12.1, h: 0.5 }, "structures-caption");
  s.addNotes("Backup for questions about the test-set disagreement rate and the mean-Z structure.");
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Backup" });
  s.addText("Backup: Phase 5C preferred-action map", { placeholder: "title" });
  D.addImageFit(s, R("p5c_b_preferred_map.png"), { x: 0.5, y: 1.3, w: 12.3, h: 5.4 }, { name: "map-figure" });
  s.addNotes("Backup for questions about where ZNE versus combined mitigation wins in the continuous noise space.");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, D.THEME);
  console.log("wrote", OUT);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
