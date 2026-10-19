// Meeting 6 of 7 — November 24, 2026: Final experimental findings (sealed test, Oct 8, 2026).
const { FaLock, FaScaleBalanced, FaTriangleExclamation, FaBookOpen, FaCircleCheck } = require("react-icons/fa6");

const meta = {
  id: "2026-11-24",
  index: 5,
  dateLong: "November 24, 2026",
  topic: "Final experimental findings",
  file: "Q-TRACE_2026-11-24_Final-Findings",
  split: "Tushar: slides 1–3 · Mayank: slides 4–5",
  splitStatus: "proposed, alternating the opener across meetings; team to confirm",
  presenterLine: "Proposed split: Tushar (slides 1–3) · Mayank (slides 4–5) · about 5 minutes",
  status: "Ready for review. Reports the one-time sealed test of Oct 8, 2026. Before presenting, update slide 5 with any author decisions made since Oct 8 (venue, author order, references).",
  delivery: [
    "Lead with the registered endpoint (material failure) and immediately disclose the raw-disagreement result; do not let a question surface it first.",
    "Say 'only four held-out structures' whenever an interval is quoted.",
    "Nothing has been submitted; the manuscript is a draft for review, not accepted or under review.",
  ],
};

const slides = [
  {
    master: "TITLE",
    title: "One sealed test: the simple rule held",
    speaker: "Tushar",
    script: `Good afternoon. Today we report the final experimental findings of Q-TRACE: the one-time sealed held-out test, which we ran on October 8.

All four pre-registered hypotheses were supported. The two-threshold probe rule was near the Oracle on unseen models, and fixed learned comparators did not reduce material errors. Only four structures were held out, so we will also be careful about what these results cannot show.`,
    keyPoints: ["one-time sealed test, Oct 8", "H1–H4 supported", "only four held-out structures"],
    transition: "How the test was protected.",
    build: async (s, { C, D, meta }) => {
      await D.titleSlide(s, C, meta, {
        headline: "One sealed test: the simple rule held",
        subtitle: "Sealed held-out evaluation · rule vs learned comparators · reliability–resource trade-offs · limits · publication",
        message: "The one-time sealed test (Oct 8, 2026) supported all four pre-registered hypotheses: the probe rule was near-Oracle on unseen models, and fixed learned comparators did not reduce material errors. Only four structures were held out.",
        MessageIcon: FaLock,
      });
    },
  },
  {
    title: "The one-time sealed evaluation",
    kicker: "Final test  ·  unlocked once, October 8, 2026 (21:28 UTC)",
    speaker: "Tushar",
    script: `The test used 16 models from four structures that no policy had ever seen, including one with a mean-Z readout.

Before opening it, we froze the rule and four learned comparators, recorded fingerprints of their decisions, and pushed the full protocol. A guard then allowed exactly one unlock and logged every read. The stored outcomes matched their committed hashes.

Under continuous joint noise, the rule made material errors in 2.0 percent of decisions, with a confidence interval of 1.4 to 2.6 percent. Its Brier score was within 0.03 percent of the Oracle's, at 0.6 percent more shots. Under categorical noise its material errors were 8.8 percent, inside the pre-registered ten-percent bound.`,
    keyPoints: ["16 unseen models, 4 structures (one mean-Z)", "frozen + fingerprinted + pushed, then one guarded unlock", "material 2.0% [1.4, 2.6]; Brier −0.03%; +0.6% shots; 5B 8.8% ≤ 10%"],
    transition: "How did the learned comparators compare?",
    sources: "final_metadata.json (unlock record, hypotheses); final_policies_5c_test.csv and final_policies_5b_test.csv (R_thr, arm all).",
    build: async (s, { C, D, F }) => {
      D.flow(s, C, [
        { head: "Freeze", body: "rule + 4 learned comparators" },
        { head: "Fingerprint", body: "hash of every frozen decision" },
        { head: "Push protocol", body: "hypotheses, metrics, statistics" },
        { head: "Unlock once", body: "guard refuses a second unlock", fill: "FBEFD9" },
        { head: "Evaluate", body: "16 unseen models · reads logged" },
      ], { y: 1.45, h: 0.95, size: 13.5 });
      D.img(s, F("fig8_final_heldout.png"), { x: 0.5, y: 2.6, w: 8.0, h: 3.45 });
      D.stat(s, C, { x: 8.85, y: 2.6, w: 3.9, value: "2.0%", valueSize: 30, label: "material errors, 95% CI 1.4–2.6% (4 held-out structures; likely too narrow)", labelH: 0.5 });
      D.stat(s, C, { x: 8.85, y: 3.75, w: 3.9, value: "−0.03%  ·  +0.6%", valueSize: 26, color: C.accent6, label: "Brier regret vs Oracle · shots vs Oracle", labelH: 0.45 });
      D.stat(s, C, { x: 8.85, y: 4.8, w: 3.9, value: "8.8%", valueSize: 30, color: C.accent2, label: "material errors, categorical test (bound: 10%)", labelH: 0.5 });
      ["H1", "H2", "H3", "H4"].forEach((h, i) => D.chip(s, C, `${h} supported`, { x: 0.6 + i * 1.75, y: 6.2, w: 1.6, h: 0.36, fill: D.HEX.accent1, fontSize: 11 }));
      D.text(s, "16 unseen models from 4 never-used structures", { x: 7.7, y: 6.2, w: 5.05, h: 0.36 }, { fontSize: 12, italic: true, color: C.accent5, align: "right", valign: "middle" });
      D.source(s, C, "final_metadata.json, final_policies_5c_test.csv, final_policies_5b_test.csv");
    },
  },
  {
    title: "The rule versus learned comparators",
    kicker: "Final test, October 8, 2026  ·  paired, two-stage cluster bootstrap over 4 held-out structures",
    speaker: "Tushar",
    script: `Here are paired differences between each comparator and the rule. Positive values favour the rule; the shaded band is the pre-registered margin.

On the registered endpoint, material errors, the best learned comparator, gradient boosting, tied the rule: 2.1 versus 2.0 percent. Its interval excludes an advantage as large as the margin.

But we want to be precise. On any disagreement with the Oracle, gradient boosting was better: 6.5 percent against 21.9 percent. Most of the rule's extra disagreements came from the unseen mean-Z structure and cost only two calibration circuits per batch, so they were not material. Structure by structure, gradient boosting made fewer material errors on the three parity structures and more on the mean-Z one. The learned models were also unstable: gradient boosting made 10.7 percent material errors on validation. Under categorical noise, learned models reached 12 to 44 percent.`,
    keyPoints: ["material: GBT 2.1% vs 2.0%, diff +0.0005 [−0.016, +0.027] → H2 non-superiority", "raw disagreement: GBT 6.5% vs rule 21.9% (mostly mean-Z; cheap, not material)", "learned unstable: GBT 10.7% on validation; 12–44% under categorical noise"],
    transition: "Hand-off to Mayank: resources and limits.",
    sources: "final_paired_vs_rthr_5c_test.csv, final_paired_vs_rthr_5b_test.csv; final_policies_5c_test.csv (failure); p7_policies_5c_val.csv (L_gbt 0.107).",
    build: async (s, { C, D, F }) => {
      D.img(s, F("fig7_learned_vs_rule.png"), { x: 0.5, y: 1.4, w: 7.4, h: 3.9 });
      D.cardText(s, C, {
        x: 8.15, y: 1.45, w: 4.6, h: 1.55, head: "Registered endpoint: material errors",
        body: "Best learned (gradient boosting) 2.1% vs rule 2.0%; difference +0.0005 [−0.016, +0.027]. 4 structures: intervals likely too narrow.", fill: "E3F2F1", size: 13,
      });
      D.cardText(s, C, {
        x: 8.15, y: 3.15, w: 4.6, h: 1.55, head: "Any disagreement with the Oracle",
        body: "Gradient boosting 6.5% vs rule 21.9%, mostly on the unseen mean-Z structure, where the rule's extra choices cost 2 calibration circuits: not material.", fill: "FBEFD9", headColor: "8A5A00", size: 13,
      });
      D.cardText(s, C, {
        x: 8.15, y: 4.85, w: 4.6, h: 1.2, head: "Stability",
        body: "Gradient boosting: 10.7% material on validation vs 2.1% on test. Rule: 2.0% on both.", size: 13,
      });
      await D.takeaway(s, C, "Overall, learning did not reduce material errors: fewer on the three parity structures, more on the unseen mean-Z one.", { y: 6.1, Icon: FaScaleBalanced });
      D.source(s, C, "final_paired_vs_rthr_5c_test.csv, final_paired_vs_rthr_5b_test.csv, final_policies_5c_test.csv, p7_policies_5c_val.csv", 6.74);
    },
  },
  {
    title: "Reliability, resources, and what the test cannot show",
    kicker: "Final test, October 8, 2026  ·  cost accounting and statistical limits",
    speaker: "Mayank",
    script: `This chart puts reliability against cost. Never mitigating uses about a third of the shots but makes material errors almost everywhere. Always using combined mitigation is reliable but overspends. The rule sits next to the Oracle: 0.6 percent more shots and 3.4 percent fewer than always-combined.

Now the limits. Always-combined's 5.9 percent material errors equal exactly the one gate-free setting in our seventeen, so the saving depends on how often batches are gate-free. Only four structures were held out, so the intervals are probably too narrow. H2 is a non-superiority result on material errors, not proof that learning cannot help. And everything is simulated, at four qubits, with a gate probe that barely sees thermal noise. We state these limits next to every headline number, in the paper and in the report.`,
    keyPoints: ["rule: +0.6% shots vs Oracle, −3.4% vs always-combined; never-mitigate 0.35× shots, 96% material errors", "always-A3 5.9% = 1/17 gate-free design share", "4 structures → CIs too narrow; H2 is non-superiority; simulation only; thermal blind spot"],
    transition: "So what is the contribution, and where does it go next?",
    sources: "final_policies_5c_test.csv (mean_total_shots_per_inference, material_failure; chart: semester cost_reliability_slide); p5c_design.csv (17 gate settings, one gate-free); p5c_probe_validity.csv.",
    build: async (s, { C, D, S }) => {
      D.img(s, S("cost_reliability_slide.png"), { x: 0.5, y: 1.4, w: 7.3, h: 3.75 });
      D.stat(s, C, { x: 0.6, y: 5.25, w: 2.35, value: "+0.6%", valueSize: 26, color: C.accent2, label: "shots vs Oracle", labelH: 0.4 });
      D.stat(s, C, { x: 3.0, y: 5.25, w: 2.35, value: "−3.4%", valueSize: 26, label: "shots vs always-combined", labelH: 0.4 });
      D.stat(s, C, { x: 5.4, y: 5.25, w: 2.4, value: "0.35×", valueSize: 26, color: C.accent3, label: "shots, never mitigate (96% material)", labelH: 0.4 });
      D.card(s, { x: 8.1, y: 1.45, w: 4.65, h: 4.65 }, "FBEDEB", "limits-bg");
      D.text(s, "What the test cannot show", { x: 8.35, y: 1.6, w: 4.2, h: 0.4 }, { fontSize: 15.5, bold: true, color: C.accent3 });
      D.bullets(s, C, [
        "Always-combined's 5.9% = the 1 gate-free setting in 17: the saving depends on the design",
        "Only 4 held-out structures: intervals likely too narrow",
        "H2 is non-superiority on material errors, not proof learning cannot help",
        "Simulation only · 4 qubits · gate probe nearly blind to thermal noise",
      ], { x: 8.35, y: 2.05, w: 4.25, h: 3.95 }, { fontSize: 13.5, space: 8 });
      D.source(s, C, "final_policies_5c_test.csv, p5c_design.csv, p5c_probe_validity.csv");
    },
  },
  {
    title: "Contribution and the path to publication",
    kicker: "Manuscript and package prepared October 8, 2026  ·  nothing submitted",
    speaker: "Mayank",
    script: `Our contribution has three parts. First, a characterization showing that noise damaged calibration, not discrimination, and that mitigation repaired it while extra shots could not. Second, a leakage-safe counterfactual benchmark across 64 models. Third, a pre-registered test of learning against simple rules, which found that, in this setting, a simple probe rule performed competitively with learned comparators.

The manuscript and capstone report are complete drafts for review, built from the same verified numbers as these slides; nothing has been submitted. Our recommended route is an arXiv preprint and then TMLR, which judges whether claims match the evidence and charges no fees. IEEE Quantum Week and Quantum Machine Intelligence are alternatives. Remaining decisions are ours: confirm the references, author order, venue and an arXiv endorser. Thank you.`,
    keyPoints: ["three contributions; no quantum-advantage claim", "manuscript + report drafted; nothing submitted", "plan: arXiv → TMLR; alternatives QCE27, QMI", "author decisions pending"],
    transition: "Questions; next meeting: the final defense.",
    sources: "deliverables/README.md; deliverables/submission/VENUES.md and SUBMISSION_PLAN.md.",
    build: async (s, { C, D }) => {
      const contrib = [
        ["Characterization", "Noise damaged calibration, not discrimination; mitigation repaired it; extra shots did not."],
        ["Benchmark", "Leakage-safe counterfactual benchmark: 64 VQCs × noise × budget × 5 actions."],
        ["Pre-registered test", "In this setting, a simple probe rule performed competitively with learned comparators."],
      ];
      contrib.forEach(([h, b], i) => D.cardText(s, C, { x: 0.6, y: 1.45 + i * 1.5, w: 5.6, h: 1.35, head: `${i + 1}. ${h}`, body: b, size: 13.5, fill: i === 2 ? "E3F2F1" : D.HEX.lt2 }));
      D.cardText(s, C, {
        x: 6.45, y: 1.45, w: 6.3, h: 2.05, head: "Status",
        body: [
          { text: "Manuscript (LaTeX, 18 pp) and capstone report: complete drafts for review", bullet: true },
          { text: "References checked against publisher records; team confirmation pending", bullet: true },
          { text: "Nothing submitted · no acceptance claimed", bullet: true },
        ], size: 13,
      });
      D.text(s, "Recommended route (authors decide)", { x: 6.45, y: 3.7, w: 6.3, h: 0.35 }, { fontSize: 14.5, bold: true, color: C.text2 });
      D.flow(s, C, [
        { head: "arXiv", body: "needs an endorser" },
        { head: "TMLR", body: "claims vs evidence · no fees", fill: "D7EEEE" },
        { head: "If needed", body: "IEEE QCE27 or QMI" },
      ], { x: 6.45, y: 4.1, w: 6.3, h: 0.95, size: 13.5 });
      D.text(s, "Pending author decisions: references, author order, venue, arXiv endorser, AI-use disclosure.", { x: 6.45, y: 5.2, w: 6.3, h: 0.6 }, { fontSize: 12.5, italic: true, color: C.accent5 });
      await D.takeaway(s, C, "In the studied setting, a simple observable probe rule was enough. No quantum advantage is claimed.", { y: 6.08, Icon: FaBookOpen });
      D.source(s, C, "deliverables/README.md, deliverables/submission/VENUES.md, deliverables/submission/SUBMISSION_PLAN.md", 6.74);
    },
  },
];

module.exports = { meta, slides };
