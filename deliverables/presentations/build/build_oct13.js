// October 13, 2026 capstone progress presentation (~5 minutes, 8 slides).
// node build_oct13.js  ->  ../Q-TRACE_Oct13_Progress.pptx
const path = require("path");
const {
  FaCoins,
  FaWaveSquare,
  FaGaugeHigh,
  FaBrain,
  FaScaleBalanced,
  FaFilter,
  FaShapes,
  FaCircleCheck,
} = require("react-icons/fa6");
const { applyTheme } = require("./theme");
const D = require("./deck_common");

const OUT = path.resolve(__dirname, "..", "Q-TRACE_Oct13_Progress.pptx");

async function main() {
  const { pres, C } = D.newDeck("Q-TRACE: When is quantum error mitigation worth paying for?");
  const F = (n) => path.join(D.FIG, n);

  // ---- 1 title
  pres.addSection({ title: "Opening" });
  let s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Opening" });
  s.addText("When is quantum error mitigation worth paying for?", {
    x: 0.8, y: 1.9, w: 11.7, h: 1.6, fontSize: 40, bold: true, color: C.background1,
    fontFace: D.THEME.headFontFace, margin: 0, isTextBox: true, objectName: "title",
  });
  s.addText("Q-TRACE: selective error mitigation for noisy quantum fraud classifiers", {
    x: 0.8, y: 3.55, w: 11.7, h: 0.6, fontSize: 20, color: "CADCFC", margin: 0, isTextBox: true,
    objectName: "subtitle",
  });
  s.addText(
    [
      { text: "Mayank Kumar Pokhriyal  ·  Tushar Poonia", options: { bold: true, breakLine: true } },
      { text: "M.S. in Artificial Intelligence capstone  ·  Katz School of Science and Health, Yeshiva University", options: { breakLine: true } },
      { text: "Progress presentation  ·  October 13, 2026" },
    ],
    { x: 0.8, y: 5.1, w: 11.7, h: 1.2, fontSize: 15, color: "E6ECF5", margin: 0, isTextBox: true, objectName: "authors" }
  );
  s.addNotes(
    "[Mayank, ~20 s] Good afternoon. Our capstone asks a practical question about near-term quantum machine learning: " +
      "error mitigation makes noisy quantum results more reliable, but it costs extra quantum resources. " +
      "So when is it actually worth paying for, and can a learned controller make that decision better than a simple rule?"
  );

  // ---- 2 cost of mitigation + hypothesis
  pres.addSection({ title: "Problem" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem" });
  s.addText("Mitigation is expensive, so use it selectively", { placeholder: "title" });
  const costs = [
    [FaWaveSquare, "Readout mitigation", "Inverts measurement errors. About two calibration circuits per batch: almost free."],
    [FaGaugeHigh, "Zero-noise extrapolation (ZNE)", "Amplifies gate noise and extrapolates back: 3× shots and 9× two-qubit-gate exposure."],
    [FaCoins, "Extra shots", "3× shots on the same circuit: lowers sampling variance, not bias."],
  ];
  for (let i = 0; i < costs.length; i++) {
    const y = 1.55 + i * 1.6;
    await D.iconCircle(s, C, costs[i][0], 0.6, y, 0.9, D.HEX.dk2, "cost-icon-" + i);
    s.addText(costs[i][1], { x: 1.7, y: y - 0.05, w: 5.4, h: 0.45, fontSize: 18, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "cost-head-" + i });
    s.addText(costs[i][2], { x: 1.7, y: y + 0.42, w: 5.4, h: 0.8, fontSize: 15, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "cost-body-" + i });
  }
  D.card(s, C, { x: 7.6, y: 1.55, w: 5.15, h: 4.6 }, D.HEX.lt2, "hypothesis-card");
  await D.iconCircle(s, C, FaBrain, 7.95, 1.85, 0.8, D.HEX.accent1, "hypothesis-icon");
  s.addText("Original hypothesis", { x: 8.95, y: 1.95, w: 3.6, h: 0.6, fontSize: 20, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "hypothesis-head" });
  s.addText(
    "A learned controller (Q-TRACE), seeing only cheap label-free probes, chooses none / readout / ZNE / both / extra shots per context better than fixed policies.",
    { x: 7.95, y: 2.9, w: 4.5, h: 1.8, fontSize: 16, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "hypothesis-body" }
  );
  s.addText("Pre-registered alternative: a simple rule is enough.", {
    x: 7.95, y: 4.95, w: 4.5, h: 0.8, fontSize: 15, italic: true, color: C.accent1, margin: 0, valign: "top", isTextBox: true, objectName: "hypothesis-alt",
  });
  s.addNotes(
    "[Mayank, ~40 s] Mitigation is not free. Readout mitigation is nearly free once calibrated, but zero-noise extrapolation needs three times the shots " +
      "and nine times the two-qubit-gate exposure, and simply buying more shots only reduces variance. " +
      "Our original hypothesis was that a learned controller, which we called Q-TRACE, could pick the right action per context from cheap probes. " +
      "From the start we pre-registered the alternative: that a simple rule might be just as good."
  );

  // ---- 3 setup
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Problem" });
  s.addText("Setup: 64 noisy quantum fraud classifiers", { placeholder: "title" });
  D.addImageFit(s, F("fig1_architecture.png"), { x: 0.5, y: 1.35, w: 8.3, h: 4.6 }, { name: "architecture" });
  D.caption(s, C, "Policies see only label-free probes and static model descriptors; true noise, labels and the sealed test are offline-only.", { x: 0.6, y: 6.05, w: 8.1, h: 0.6 }, "architecture-caption");
  D.stat(s, C, { x: 9.2, y: 1.4, w: 3.6, value: "283,726", label: "credit-card transactions, 0.17% fraud, in 5 leakage-safe partitions", name: "s-data" });
  D.stat(s, C, { x: 9.2, y: 3.05, w: 3.6, value: "64", label: "independent 4-qubit VQCs (16 structures × 4 seeds), frozen", name: "s-pool" });
  D.stat(s, C, { x: 9.2, y: 4.7, w: 3.6, value: "1.4 M", label: "counterfactual outcomes: every model × noise × budget × action", name: "s-rows" });
  s.addNotes(
    "[Mayank, ~40 s] We use the public European credit-card fraud dataset, about 284 thousand transactions with 0.17 percent fraud, " +
      "split into five leakage-safe partitions. We trained 64 independent four-qubit variational quantum classifiers, " +
      "and simulated every model under every noise context, shot budget and action, about 1.4 million counterfactual outcomes in total. " +
      "Crucially, the policy only sees cheap label-free probes; the true noise parameters, labels and our test set are kept offline."
  );

  // ---- 4 noise + mitigation findings
  pres.addSection({ title: "Findings" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Findings" });
  s.addText("Noise breaks calibration, and mitigation repairs it", { placeholder: "title" });
  D.addImageFit(s, F("fig4_mitigation.png"), { x: 0.5, y: 1.35, w: 8.4, h: 4.6 }, { name: "mitigation-figure" });
  D.caption(s, C, "Brier score by condition and action (1,024 shots, 20 replicates; Phase 4).", { x: 0.6, y: 6.05, w: 8.1, h: 0.4 }, "mitigation-caption");
  D.stat(s, C, { x: 9.2, y: 1.4, w: 3.6, value: "≤ 0.003", label: "change in AUPRC under gate noise: discrimination survives", color: C.accent6, name: "s-auprc" });
  D.stat(s, C, { x: 9.2, y: 3.05, w: 3.6, value: "13×", label: "worse Brier under combined noise (0.009 → 0.121)", color: C.accent3, name: "s-brier" });
  D.stat(s, C, { x: 9.2, y: 4.7, w: 3.6, value: "0.122 → 0.054", label: "Brier with combined mitigation; 3× shots leaves it at 0.121", valueSize: 30, name: "s-fix" });
  s.addNotes(
    "[Mayank, ~45 s] Our first finding reframed the project. Noise barely changes discrimination: AUPRC moves by at most 0.003, and the top-ranked frauds stay on top. " +
      "But calibration collapses: the Brier score gets up to 13 times worse. Mitigation fixes exactly that. " +
      "Under combined noise, readout mitigation plus ZNE cuts the Brier score from 0.122 to 0.054, while spending the same budget on extra shots does nothing. " +
      "And the best action depends on the type of noise. So it looked like a genuine selective decision problem. Tushar will take it from here."
  );

  // ---- 5 two gates
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Findings" });
  s.addText("Two pre-registered gates: nothing material left to learn", { placeholder: "title" });
  D.addImageFit(s, F("fig5_preferred_actions.png"), { x: 0.5, y: 1.3, w: 7.9, h: 4.4 }, { name: "preferred-figure" });
  D.caption(s, C, "Share of contexts where each action is the cost-aware best choice (cheapest within 10% of the best Brier).", { x: 0.6, y: 5.85, w: 7.7, h: 0.6 }, "preferred-caption");
  D.card(s, C, { x: 8.75, y: 1.4, w: 4.05, h: 2.25 }, D.HEX.lt2, "g3b-card");
  s.addText([
    { text: "Phase 5B · categorical noise", options: { bold: true, color: C.text2, fontSize: 16, breakLine: true } },
    { text: "Best action = lookup on noise type. A 4-cell probe rule is right in ", options: { fontSize: 15 } },
    { text: "99.7%", options: { bold: true, color: C.accent1, fontSize: 15 } },
    { text: " of validation cases.", options: { fontSize: 15 } },
  ], { x: 9.0, y: 1.55, w: 3.6, h: 1.95, margin: 0, valign: "top", color: C.text1, isTextBox: true, objectName: "g3b-text" });
  D.card(s, C, { x: 8.75, y: 3.9, w: 4.05, h: 2.25 }, D.HEX.lt2, "g3c-card");
  s.addText([
    { text: "Phase 5C · continuous joint noise", options: { bold: true, color: C.text2, fontSize: 16, breakLine: true } },
    { text: "ZNE or combined mitigation wins in 94% of contexts. A two-threshold rule makes material errors in ", options: { fontSize: 15 } },
    { text: "2.0%", options: { bold: true, color: C.accent1, fontSize: 15 } },
    { text: " of cases.", options: { fontSize: 15 } },
  ], { x: 9.0, y: 4.05, w: 3.6, h: 1.95, margin: 0, valign: "top", color: C.text1, isTextBox: true, objectName: "g3c-text" });
  s.addNotes(
    "[Tushar, ~45 s] We tested the controller hypothesis with pre-registered gates. First with categorical noise: the best action was simply a lookup on the noise type, " +
      "and a four-cell probe rule was right 99.7 percent of the time, so the gate failed. " +
      "Then readout, gate and thermal noise varied continuously together. " +
      "That actually removed most of the choice. In our design, 16 of 17 gate settings carry gate noise, and ZNE or combined mitigation wins in 94 percent of contexts. A two-threshold rule makes material mistakes only 2 percent of the time. " +
      "The second gate failed too, so as registered, we did not train a controller."
  );

  // ---- 6 held-out
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Findings" });
  s.addText("Sealed held-out test: the rule matches the Oracle", { placeholder: "title" });
  D.stat(s, C, { x: 0.6, y: 1.45, w: 3.9, value: "2.0%", label: "material errors on 16 unseen models (95% CI 1.5–2.6%)", name: "s-mat" });
  D.stat(s, C, { x: 0.6, y: 3.1, w: 3.9, value: "−0.03%", label: "Brier regret vs the cost-aware Oracle", name: "s-reg" });
  D.stat(s, C, { x: 0.6, y: 4.75, w: 3.9, value: "+0.6%", label: "shots vs the Oracle; 3.4% fewer than always-combined", color: C.accent2, name: "s-cost" });
  D.addImageFit(s, F("fig8_final_heldout.png"), { x: 4.7, y: 1.35, w: 8.2, h: 4.75 }, { name: "final-figure" });
  D.caption(s, C, "One-time evaluation of frozen policies on sealed test structures (continuous joint noise). Best learned comparator: 2.1% material errors.", { x: 4.8, y: 6.15, w: 8.0, h: 0.6 }, "final-caption");
  s.addNotes(
    "[Tushar, ~45 s] Finally, we froze everything and opened our sealed test set exactly once: 16 models from four structures the policies had never seen. " +
      "The simple probe rule made material errors in 2 percent of decisions, its Brier score was within 0.03 percent of the cost-aware Oracle, " +
      "and it spent only 0.6 percent more shots. The best learned comparator, gradient boosting, tied it at 2.1 percent on material errors; it disagreed with the Oracle less often, but the rule's extra disagreements were cheap ones. All four pre-registered hypotheses held."
  );

  // ---- 7 why
  pres.addSection({ title: "Interpretation" });
  s = pres.addSlide({ masterName: "CONTENT", sectionTitle: "Interpretation" });
  s.addText("Why the simpler policy prevailed", { placeholder: "title" });
  const why = [
    [FaScaleBalanced, "Bias, not variance", "Mitigation fixes a calibration bias that extra shots cannot remove, so the shot budget barely matters."],
    [FaFilter, "One question decides", "In our design, 16 of 17 gate settings carry gate noise, so the material choice is whether to pay for ZNE. The gate probe alone recovers the rule."],
    [FaShapes, "Models differ in magnitude, not in the winner", "Benefit varies a lot between models but rarely changes the winner. On an unseen readout type, learned models made 5–30% material errors; the rule 1.4%."],
  ];
  for (let i = 0; i < why.length; i++) {
    const y = 1.5 + i * 1.75;
    await D.iconCircle(s, C, why[i][0], 0.7, y, 0.95, i === 2 ? D.HEX.accent2 : D.HEX.accent1, "why-icon-" + i);
    s.addText(why[i][1], { x: 1.95, y: y - 0.02, w: 10.7, h: 0.45, fontSize: 19, bold: true, color: C.text2, margin: 0, isTextBox: true, objectName: "why-head-" + i });
    s.addText(why[i][2], { x: 1.95, y: y + 0.46, w: 10.7, h: 0.85, fontSize: 16, color: C.text1, margin: 0, valign: "top", isTextBox: true, objectName: "why-body-" + i });
  }
  s.addNotes(
    "[Tushar, ~40 s] Why did the simple rule win? Three reasons. First, mitigation removes a calibration bias, and extra shots cannot, so the budget rarely matters. " +
      "Second, in our joint-noise design, where 16 of 17 gate settings carry gate noise, the decision collapses to one question, is gate noise present, and the gate probe alone answers it. " +
      "Third, models differ in how much mitigation helps, but rarely in which action wins; and where they do, the learned models generalized worse than the rule."
  );

  // ---- 8 contribution + next steps
  pres.addSection({ title: "Next steps" });
  s = pres.addSlide({ masterName: "SECTION_DARK", sectionTitle: "Next steps" });
  s.addText("Contribution and remaining academic work", { placeholder: "title" });
  await D.iconCircle(s, C, FaCircleCheck, 0.7, 1.55, 0.8, D.HEX.accent1, "contrib-icon");
  s.addText(
    [
      { text: "What we contribute", options: { bold: true, fontSize: 19, color: "FFFFFF", breakLine: true } },
      { text: "Mitigation fixes calibration, not discrimination; extra shots never substitute.", options: { bullet: true, breakLine: true } },
      { text: "A leakage-safe benchmark: 64 VQCs × noise × budget × 5 actions.", options: { bullet: true, breakLine: true } },
      { text: "A pre-registered test: a simple probe rule is enough here; fixed learned comparators did not reduce material errors.", options: { bullet: true } },
    ],
    { x: 1.7, y: 1.5, w: 5.4, h: 4.2, fontSize: 15, color: "E6ECF5", margin: 0, valign: "top", paraSpaceAfter: 8, isTextBox: true, objectName: "contrib-text" }
  );
  const steps = [
    ["Oct 20", "Polished research manuscript"],
    ["Oct 27", "Updated capstone presentation"],
    ["Nov 10–24", "Revisions from professor feedback"],
    ["Dec 8", "Final presentation package"],
  ];
  s.addText("Planned milestones (to confirm with the course)", { x: 7.6, y: 1.5, w: 5.2, h: 0.5, fontSize: 17, bold: true, color: "FFFFFF", margin: 0, isTextBox: true, objectName: "steps-head" });
  for (let i = 0; i < steps.length; i++) {
    const y = 2.2 + i * 0.95;
    s.addShape("roundRect", { x: 7.6, y, w: 1.55, h: 0.7, rectRadius: 0.08, fill: { color: D.HEX.accent1 }, line: { color: D.HEX.accent1 }, objectName: "step-pill-" + i });
    s.addText(steps[i][0], { x: 7.6, y, w: 1.55, h: 0.7, fontSize: 14, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "step-date-" + i });
    s.addText(steps[i][1], { x: 9.35, y, w: 3.5, h: 0.7, fontSize: 15, color: "E6ECF5", valign: "middle", margin: 0, isTextBox: true, objectName: "step-text-" + i });
  }
  s.addNotes(
    "[Tushar, ~25 s] To summarize our contribution: mitigation fixes calibration, not discrimination; we built a leakage-safe benchmark across 64 models; " +
      "and our pre-registered test shows that a simple probe rule is enough in this setting. " +
      "Next we will polish the manuscript by October 20, update this presentation by October 27, revise after your feedback in November, " +
      "and deliver the final package in December. Thank you; we are happy to take questions."
  );

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, D.THEME);
  console.log("wrote", OUT);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
