// Meeting 5 of 7 — November 10, 2026: Policy selection (Phases 5A–5C, completed Oct 7–8, 2026).
const { FaCodeBranch, FaBrain, FaFlask, FaRoute } = require("react-icons/fa6");

const meta = {
  id: "2026-11-10",
  index: 4,
  dateLong: "November 10, 2026",
  topic: "Policy selection",
  file: "Q-TRACE_2026-11-10_Policy-Selection",
  split: "Mayank: slides 1–3 · Tushar: slides 4–5",
  splitStatus: "proposed, alternating the opener across meetings; team to confirm",
  presenterLine: "Proposed split: Mayank (slides 1–3) · Tushar (slides 4–5) · about 5 minutes",
  status: "Ready for review. Presents Phases 5A–5C (completed Oct 7–8, 2026); the sealed-test results (test run Oct 8) are presented on Nov 24.",
  delivery: [
    "Be exact about the gates: the residual structure was statistically detectable but far below materiality, so 'no material residual', not 'no residual'.",
    "No Q-TRACE controller was ever trained. The learned models on Nov 24 are fixed comparators, specified in advance.",
    "Gate noise is present in 16 of 17 gate settings by design. Say 'in our design', not 'on real devices'.",
  ],
};

// Decision diagram for the two-threshold probe rule R_thr (cells from p5c_metadata.json).
function ruleDiagram(s, C, D, x, y) {
  const box = (bx, by, w, h, head, body, fill, dark) => {
    D.card(s, { x: bx, y: by, w, h }, fill, "rule-box");
    D.text(s, [
      { text: head, options: { bold: true, fontSize: 13, color: dark ? "FFFFFF" : C.text2, breakLine: !!body } },
      ...(body ? [{ text: body, options: { fontSize: 11, color: dark ? "E6ECF5" : C.text1 } }] : []),
    ], { x: bx + 0.06, y: by, w: w - 0.12, h }, { align: "center", valign: "middle" });
  };
  const line = (x1, y1, x2, y2) => s.addShape("line", { x: x1, y: y1, w: x2 - x1 || 0.001, h: y2 - y1 || 0.001, line: { color: D.HEX.accent5, width: 1.5, endArrowType: "triangle" } });
  const lab = (lx, ly, t) => D.text(s, t, { x: lx, y: ly, w: 0.6, h: 0.26 }, { fontSize: 10.5, bold: true, color: C.accent5, align: "center" });
  box(x, y, 3.0, 0.82, "Gate probe", "contraction ≤ t_g (≈ 0.97–0.98)?", D.HEX.lt2);
  box(x + 3.55, y, 3.0, 0.82, "Readout probe", "error ≥ t_r (≈ 0.4%)?", D.HEX.lt2);
  box(x, y + 1.35, 3.0, 0.82, "A1 readout mitigation", "A0 at 256 shots if readout is also low", "0072B2", true);
  box(x + 3.55, y + 1.35, 1.42, 0.82, "A3", "combined", "CC79A7", true);
  box(x + 5.13, y + 1.35, 1.42, 0.82, "A2", "ZNE", "D55E00", true);
  line(x + 3.0, y + 0.41, x + 3.55, y + 0.41);
  lab(x + 2.97, y + 0.12, "yes");
  line(x + 1.5, y + 0.82, x + 1.5, y + 1.35);
  lab(x + 1.55, y + 0.95, "no");
  line(x + 4.26, y + 0.82, x + 4.26, y + 1.35);
  lab(x + 3.7, y + 0.95, "yes");
  line(x + 5.84, y + 0.82, x + 5.84, y + 1.35);
  lab(x + 5.9, y + 0.95, "no");
}

const slides = [
  {
    master: "TITLE",
    title: "Does choosing mitigation need a learned controller?",
    speaker: "Mayank",
    script: `Good afternoon. Today's question is the heart of our original proposal: does deciding when and how to mitigate need a learned controller?

This covers Phases 5A to 5C, completed on October 7 and 8. Two pre-registered gates found no material structure left for a learned controller, so none was trained. A simple two-threshold probe rule emerged instead.`,
    keyPoints: ["Phases 5A–5C, completed Oct 7–8", "two gates found no material residual", "no controller trained; a two-threshold rule emerged"],
    transition: "Start with the decision we set out to learn.",
    build: async (s, { C, D, meta }) => {
      await D.titleSlide(s, C, meta, {
        headline: "Does choosing mitigation need a learned controller?",
        subtitle: "Learned-controller hypothesis · 64-model pool · label-free probes · categorical and continuous noise · gates",
        message: "Phases 5A–5C (completed Oct 7–8, 2026). Two pre-registered gates found no material structure left for a learned controller, so none was trained. A two-threshold probe rule emerged instead.",
        MessageIcon: FaCodeBranch,
      });
    },
  },
  {
    title: "The decision we proposed to learn",
    kicker: "Original hypothesis  ·  each stage registered before its own outcomes  ·  October 6–8, 2026",
    speaker: "Mayank",
    script: `For every context, meaning a model, a noise environment and a shot budget, the system must pick one of five actions: nothing, readout mitigation, ZNE, both, or three times the shots.

Our original hypothesis was that a learned controller, Q-TRACE, could make this choice from cheap label-free probes better than fixed policies and a fairly tuned threshold rule. From the start we committed to report it as a result if a simple threshold rule matched the learned controller.

The Oracle is evaluation-only. It picks the cheapest action whose Brier score is within ten percent of the best. A failure is any disagreement with it. A failure is material when the Brier score is more than twenty percent above the best, or when it costs at least one extra shot-set. And we committed to train a controller only if a gate found material structure that a simple rule missed.`,
    keyPoints: ["context → probes → policy → one of A0–A4", "H-control vs the committed alternative (a simple rule suffices)", "Oracle: cheapest within 10% of best Brier; material failure defined in advance", "train a controller only if the gate passes"],
    transition: "To test that fairly we needed many models and cheap probes.",
    sources: "docs/PREREG_P5B.md, docs/PREREG_P5C.md; configs/mixed_noise_study/p5c_v1.yaml (ε = 0.10, material multiple 2, overspend 1·S).",
    build: async (s, { C, D }) => {
      D.flow(s, C, [
        { head: "Context", body: "model · noise · shot budget · batch" },
        { head: "Label-free probes", body: "measured every batch" },
        { head: "Policy", body: "learned controller or simple rule", fill: "D7EEEE" },
        { head: "Action A0–A4", body: "none · readout · ZNE · both · 3× shots" },
      ], { y: 1.5, h: 1.0, size: 14 });
      D.cardText(s, C, { x: 0.6, y: 2.85, w: 3.9, h: 2.55, head: "H-control (original)", body: "A learned controller (Q-TRACE) using only label-free probes beats fixed policies and a fairly tuned threshold rule.", headColor: C.text2, size: 13.5 });
      D.cardText(s, C, { x: 4.7, y: 2.85, w: 3.9, h: 2.55, head: "The alternative we committed to report", body: "A simple threshold rule matches the learned controller. Formalized for the sealed test as: the rule is near the cost-aware Oracle.", fill: "E3F2F1", size: 13.5 });
      D.cardText(s, C, {
        x: 8.8, y: 2.85, w: 3.95, h: 2.55, head: "Oracle and failure (evaluation only)",
        body: [
          { text: "Oracle: cheapest action within 10% of the best Brier", bullet: true },
          { text: "Failure: any disagreement with the Oracle", bullet: true },
          { text: "Material: Brier > 1.2 × best, or ≥ 1 extra shot-set", bullet: true },
        ], size: 12.5,
      });
      await D.takeaway(s, C, "Registered rule: train a controller only if a gate finds material structure that a simple rule misses.", { y: 5.7, Icon: FaBrain });
      D.source(s, C, "docs/PREREG_P5B.md, docs/PREREG_P5C.md, configs/mixed_noise_study/p5c_v1.yaml", 6.42);
    },
  },
  {
    title: "64 independent models and two cheap probes",
    kicker: "Phases 5A–5C  ·  pool frozen October 7, 2026",
    speaker: "Mayank",
    script: `To make models, not transactions, the unit of analysis, we trained 64 quantum classifiers: 16 structures times four seeds. Structures vary the features, the encoding, the ansatz and the readout. All 64 qualified on clean data, with a median AUPRC of 0.235. Structures were split eight, four and four into training, validation and sealed test models.

A policy sees only static model descriptors and two label-free probes. The readout probe is the pair of calibration circuits that readout mitigation needs anyway. The gate probe runs 32 fixed synthetic inputs at fold factors one and three. Together they cost 66 circuits per batch. The readout probe tracks the true readout error almost perfectly, and the gate probe tracks depolarizing noise, but it barely sees thermal noise.`,
    keyPoints: ["64 VQCs = 16 structures × 4 seeds; median AUPRC 0.235 (0.047–0.538)", "split 8/4/4 by structure; test sealed", "readout probe ρ = 0.999; gate probe ρ = −0.89 (depolarizing), −0.12 (thermal); 66 circuits per batch"],
    transition: "Hand-off to Tushar: what the experiments showed.",
    sources: "p5a_pool_metrics.csv; p5b_split.csv; p5b_feature_definitions.csv; p5c_probe_validity.csv (train, all budgets).",
    build: async (s, { C, D, S }) => {
      D.img(s, S("pool_auprc.png"), { x: 0.5, y: 1.4, w: 6.9, h: 4.6 });
      D.cardText(s, C, {
        x: 7.65, y: 1.45, w: 5.1, h: 1.6, head: "Readout probe",
        body: "The 2 calibration circuits readout mitigation already needs. Tracks the true mean readout error: Spearman ρ = 0.999.", size: 13,
      });
      D.cardText(s, C, {
        x: 7.65, y: 3.2, w: 5.1, h: 1.6, head: "Gate probe",
        body: "32 fixed synthetic inputs at fold factors 1 and 3. Contraction tracks depolarizing noise (ρ = −0.89) but barely thermal noise (ρ = −0.12).", size: 13,
      });
      D.cardText(s, C, {
        x: 7.65, y: 4.95, w: 5.1, h: 1.05, head: "Cost and inputs",
        body: "66 circuits (66·S shots) per batch · 16 static descriptors + 11 probe features", size: 13,
      });
      await D.takeaway(s, C, "True noise parameters, labels and identifiers never enter a policy, as enforced by a feature registry and tests.", { y: 6.12, Icon: FaFlask });
      D.source(s, C, "p5a_pool_metrics.csv, p5b_split.csv, p5b_feature_definitions.csv, p5c_probe_validity.csv", 6.76);
    },
  },
  {
    title: "Categorical, then continuous joint noise",
    kicker: "Phase 5B (completed Oct 7)  ·  Phase 5C (completed Oct 8, 2026)",
    speaker: "Tushar",
    script: `We ran every model under every action in two noise environments.

In Phase 5B, with eight near-categorical noise conditions, the best action was simply a lookup on the noise type, and a four-cell probe rule was wrong in only 0.33 percent of validation cases.

We then asked whether that was too easy, and in Phase 5C varied readout, depolarizing and thermal noise continuously and jointly, across 68 noise points and three shot budgets. That removed most of the choice. In our design, 16 of 17 gate settings carry gate noise, and combined mitigation was the Oracle's choice in 67 to 71 percent of contexts and ZNE in 23 to 27 percent. The shot budget changed the choice in fewer than three percent of cases, and three times the shots was never chosen.`,
    keyPoints: ["5B: best action = lookup on noise type; 4-cell rule wrong in 0.33% (best single action wrong in 62.5%)", "5C: 68 points × 3 budgets; A3 67–71%, A2 23–27%; budget changes choice < 3%", "A4 never preferred; 16 of 17 gate settings carry gate noise (design)"],
    transition: "So what did the gates conclude?",
    sources: "p5b_metadata.json (category rule val failure 0.00332, best single 0.625); p5c_metadata.json (preferred_shares); p5c_budget_effect.csv; p5c_design.csv.",
    build: async (s, { C, D, F, R }) => {
      D.img(s, F("fig5_preferred_actions.png"), { x: 0.5, y: 1.4, w: 8.2, h: 3.6 });
      D.cardText(s, C, { x: 8.95, y: 1.45, w: 3.8, h: 1.6, head: "Phase 5B design", body: "8 near-categorical conditions · 1,024 and 4,096 shots · 20 replicates", size: 13 });
      D.cardText(s, C, { x: 8.95, y: 3.2, w: 3.8, h: 1.75, head: "Phase 5C design", body: "17 gate settings (one gate-free) × 4 readout settings = 68 points · 256–4,096 shots", size: 13, fill: "E3F2F1" });
      D.stat(s, C, { x: 0.6, y: 5.05, w: 2.9, value: "0.33%", valueSize: 26, label: "5B: category rule wrong (validation)", labelH: 0.45 });
      D.stat(s, C, { x: 3.6, y: 5.05, w: 3.0, value: "67–71%", valueSize: 26, color: C.accent2, label: "5C: combined mitigation is the Oracle's choice", labelH: 0.45 });
      D.stat(s, C, { x: 6.75, y: 5.05, w: 2.9, value: "< 3%", valueSize: 26, color: C.accent6, label: "contexts where the shot budget changes the choice", labelH: 0.45 });
      D.stat(s, C, { x: 9.8, y: 5.05, w: 2.95, value: "0%", valueSize: 26, color: C.accent3, label: "contexts where 3× shots is the Oracle's choice", labelH: 0.45 });
      D.caption(s, C, "Test bars come from the one-time sealed test (the Nov 24 topic).", { x: 0.6, y: 6.15, w: 12.1, h: 0.45 });
      D.source(s, C, "p5b_metadata.json, p5c_metadata.json, p5c_budget_effect.csv, p5c_design.csv, final_metadata.json");
    },
  },
  {
    title: "Both gates failed, and a simple rule emerged",
    kicker: "Gates G3B and G3C  ·  pre-registered  ·  decided October 7–8, 2026",
    speaker: "Tushar",
    script: `Both gates failed, as defined in advance.

Under categorical noise the category rule was nearly perfect. Under continuous noise the best rule, shown here, disagreed with the Oracle in 9.6 percent of validation decisions, but only 2.0 percent were material, well below the five percent gate. The remaining structure, mostly from mean-Z readouts, was statistically detectable but small.

The rule is two thresholds per shot budget. If the gate probe detects gate noise, use ZNE, and add readout mitigation when the readout probe exceeds about 0.4 percent error. Otherwise use readout mitigation alone. It works because mitigation removes a bias that shots cannot, and because in our design the material question is simply whether gate noise is present.

As registered, we trained no controller. Next time: the sealed-test results, from the test we ran on October 8. Thank you.`,
    keyPoints: ["G3B: 0.33% < 5% → fail; G3C: material 2.0% [1.6, 2.7] < 5% → fail", "residual detectable (MI 0.08 / 0.04 nats) but not material", "rule: gate probe → ZNE; readout probe ≥ ~0.4% → add readout mitigation", "no controller trained; fixed comparators evaluated on the sealed test (run Oct 8; presented Nov 24)"],
    transition: "Questions; next meeting: the sealed test.",
    sources: "p5b_metadata.json (g3b); p5c_metadata.json (g3c, rules/R_thr, structure_association); p5c_policy_eval.csv.",
    build: async (s, { C, D }) => {
      D.text(s, "The probe rule R_thr (fitted on training models only)", { x: 0.6, y: 1.45, w: 6.6, h: 0.35 }, { fontSize: 14.5, bold: true, color: C.text2 });
      ruleDiagram(s, C, D, 0.6, 1.95);
      D.text(s, "One readout-probe and one gate-probe threshold per shot budget. Thresholds are specific to this simulated 4-qubit setting.", { x: 0.6, y: 4.2, w: 6.6, h: 0.5 }, { fontSize: 11.5, italic: true, color: C.accent5 });
      D.cardText(s, C, { x: 0.6, y: 4.75, w: 3.2, h: 1.1, head: "Bias, not variance", body: "shots cannot fix it, so the budget rarely matters", size: 12, headSize: 13.5, fill: "E3F2F1" });
      D.cardText(s, C, { x: 4.0, y: 4.75, w: 3.2, h: 1.1, head: "One question decides", body: "in our design: is gate noise present?", size: 12, headSize: 13.5, fill: "E3F2F1" });
      D.cardText(s, C, { x: 7.45, y: 1.45, w: 5.3, h: 1.3, head: "G3B · categorical noise  →  FAIL", body: "4-cell category rule wrong in 0.33% of validation cases (gate threshold: 5%).", fill: "F7E3E1", headColor: C.accent3, size: 13 });
      D.cardText(s, C, { x: 7.45, y: 2.9, w: 5.3, h: 1.55, head: "G3C · continuous joint noise  →  FAIL", body: "Best rule: 9.6% disagreement, but only 2.0% [1.6, 2.7] material (threshold: 5%); Brier regret +0.3%.", fill: "F7E3E1", headColor: C.accent3, size: 13 });
      D.cardText(s, C, { x: 7.45, y: 4.6, w: 5.3, h: 1.25, head: "Residual structure", body: "Detectable (mutual information 0.08 and 0.04 nats), mostly mean-Z readouts, but not material.", size: 13 });
      await D.takeaway(s, C, "As registered, no learned controller was trained. Fixed learned comparators were evaluated on the sealed test instead (run Oct 8; Nov 24 topic).", { y: 6.05, Icon: FaRoute });
      D.source(s, C, "p5b_metadata.json (g3b), p5c_metadata.json (g3c, R_thr cells and thresholds, structure association), p5c_policy_eval.csv");
    },
  },
];

module.exports = { meta, slides };
