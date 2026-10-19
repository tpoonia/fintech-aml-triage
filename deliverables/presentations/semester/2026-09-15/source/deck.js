// Meeting 1 of 7 — September 15, 2026: Research proposal.
// RETROSPECTIVE RECONSTRUCTION (prepared Oct 2026). The repository record begins on Oct 6, 2026.
// What the record preserves about the pre-October project:
//   - docs/DECISIONS.md Q1 / PROJECT_SPEC §2: a generic QML scope (Iris, QM9, WDBC) with a binary
//     (mitigate or not) decision, superseded on Oct 6;
//   - docs/research/deep-research-report.md (written ~Oct 5) describes "your current presentation":
//     a benefit-minus-cost rule, a VQC, Qiskit Aer, ZNE/readout mitigation, a Never/Always/Fixed/Q-TRACE
//     comparison, and "current accuracy" shown as an example input.
// The record does not say which of these appeared on Sept 15 versus Sept 29. Nothing here reports a
// result; background claims cite published literature only.
const { FaClockRotateLeft, FaWaveSquare, FaCoins, FaCodeBranch, FaListCheck } = require("react-icons/fa6");

const meta = {
  id: "2026-09-15",
  index: 0,
  retrospective: true,
  dateLong: "September 15, 2026",
  topic: "Research proposal",
  file: "Q-TRACE_2026-09-15_Research-Proposal",
  split: "Mayank: slides 1–3 · Tushar: slides 4–5",
  splitStatus: "proposed; no presenter record exists for this date; team to confirm",
  presenterLine: "Retrospective deck · proposed split: Mayank (slides 1–3) · Tushar (slides 4–5) · about 5 minutes",
  scriptNote:
    "Retrospective reconstruction, prepared in October 2026. The repository record begins on Oct 6, 2026. It preserves the pre-October project as a generic QML study (Iris, QM9, WDBC) with a binary mitigate-or-not decision (docs/DECISIONS.md, Q1). The early-October research plan (docs/research/deep-research-report.md) describes the deck of that time: a benefit-minus-cost rule, a VQC, Qiskit Aer, ZNE and readout mitigation, a Never/Always/Fixed/Q-TRACE comparison, and 'current accuracy' as an example input. The record does not say which of these were shown on Sept 15. Background slides use published literature, and no results existed on this date. If the team has the original September slides, they take precedence.",
  delivery: [
    "This deck is a record of the proposal stage, not a recording of what was said on Sept 15. If shown, say so.",
    "Do not add any result: none existed on this date.",
  ],
};

const slides = [
  {
    master: "TITLE",
    title: "When is quantum error mitigation worth its cost?",
    speaker: "Mayank",
    script: `Good afternoon. We are Mayank and Tushar, and this is our research proposal. One note first: this version of the deck was reconstructed in October from our project record, so it shows the proposal stage and nothing later.

Quantum machine-learning models run on noisy hardware, and error mitigation can correct some of that noise, at a price. Our question is simple to state: when is that price worth paying, and can a decision layer tell the difference?`,
    keyPoints: ["proposal stage: no results", "noise → mitigation → cost", "question: when is mitigation worth its cost, and can a decision layer decide?"],
    transition: "Why noise matters.",
    build: async (s, { C, D, meta }) => {
      await D.titleSlide(s, C, meta, {
        headline: "When is quantum error mitigation worth its cost?",
        subtitle: "Research proposal: noise in quantum machine learning, the cost of mitigation, and a cost-aware decision layer",
        message: "Reconstructed in Oct 2026 from the project record, which begins Oct 6. It preserves the pre-October project as a generic QML study (Iris, QM9, WDBC) with a mitigate-or-not decision. No results existed on this date.",
        MessageIcon: FaClockRotateLeft,
      });
    },
  },
  {
    title: "Why quantum noise matters",
    kicker: "Background from the literature  ·  no project data",
    speaker: "Mayank",
    script: `Today's quantum processors are noisy, the so-called NISQ era described by Preskill.

A quantum machine-learning model produces its output from measured expectation values. Gate errors, decoherence and imperfect measurement pull those values toward zero, and the effect grows with circuit depth. The left panel shows this for a simple illustrative noise model.

For a classifier, the result is that its probabilities drift toward one half. A decision that depends on those probabilities, such as an alert above a threshold, can then change even if the underlying model is good. So noise is not only a hardware problem; it changes what the model tells us. And the damage is not the same everywhere: it depends on the circuit, the type of noise and its strength. That variation is what makes a context-dependent decision worth studying.`,
    keyPoints: ["NISQ hardware is noisy (Preskill 2018)", "noise shrinks expectation values, more with depth", "probabilities drift toward 0.5 → threshold decisions change"],
    transition: "Mitigation can help, but it is not free.",
    sources: "Preskill (2018) Quantum 2:79. Figure: illustrative global-depolarizing model, not project data.",
    build: async (s, { C, D, S }) => {
      D.img(s, S("noise_concept.png"), { x: 0.5, y: 1.4, w: 8.4, h: 4.35 });
      D.cardText(s, C, {
        x: 9.15, y: 1.45, w: 3.6, h: 4.3, head: "In brief",
        body: [
          { text: "NISQ processors are noisy", bullet: true },
          { text: "Noise shrinks the expectation values a QML model outputs", bullet: true },
          { text: "Probabilities drift toward 0.5, so threshold decisions can flip", bullet: true },
        ], size: 14,
      });
      await D.takeaway(s, C, "Noise changes what a quantum model tells us, not only how the hardware behaves.", { y: 6.0, Icon: FaWaveSquare });
      D.source(s, C, "Preskill (2018), Quantum 2:79. Illustrative model only; no project data.", 6.72);
    },
  },
  {
    title: "Why error mitigation is expensive",
    kicker: "Background from the literature  ·  no project data",
    speaker: "Mayank",
    script: `Error mitigation reduces the bias that noise introduces, without full error correction. Two widely used techniques matter here.

Zero-noise extrapolation, or ZNE, runs the same circuit at several deliberately amplified noise levels, for example by folding gates, and extrapolates the results back to zero noise, as shown on the right. That means extra circuits: more shots, and more exposure to two-qubit gates. Readout mitigation is cheaper: it corrects measurement errors using a few calibration circuits.

And the benefit is not guaranteed. A resource-normalized evaluation across hardware platforms found mitigation beneficial on average but strongly platform-dependent. Applying it everywhere, every time, can waste resources. Tushar will describe what we propose.`,
    keyPoints: ["ZNE: amplify noise, extrapolate to zero (Temme 2017; Kandala 2019; Giurgica-Tiron 2020)", "readout mitigation: calibration-based, cheaper (Bravyi 2021)", "benefit is platform-dependent (Russo 2023)"],
    transition: "Hand-off to Tushar: the proposed approach.",
    sources: "Temme et al. (2017) PRL 119:180509; Kandala et al. (2019) Nature 567:491; Giurgica-Tiron et al. (2020) IEEE QCE; Bravyi et al. (2021) PRA 103:042605; Russo et al. (2023) IEEE TQE 4:1–18. Figure: illustrative.",
    build: async (s, { C, D, S }) => {
      D.cardText(s, C, {
        x: 0.6, y: 1.45, w: 5.6, h: 1.65, head: "Zero-noise extrapolation (ZNE)",
        body: "Run the circuit at several amplified noise levels, then extrapolate to zero noise (Temme et al. 2017; Kandala et al. 2019; Giurgica-Tiron et al. 2020).", size: 13.5,
      });
      D.cardText(s, C, {
        x: 0.6, y: 3.25, w: 5.6, h: 1.25, head: "The cost",
        body: "ZNE: several circuits instead of one. Readout mitigation: a few calibration circuits (Bravyi et al. 2021).", size: 13.5, fill: "FBEFD9", headColor: "8A5A00",
      });
      D.cardText(s, C, {
        x: 0.6, y: 4.65, w: 5.6, h: 1.25, head: "The benefit is not guaranteed",
        body: "Beneficial on average but strongly platform-dependent (Russo et al. 2023).", size: 13.5, fill: "F7E3E1", headColor: C.accent3,
      });
      D.img(s, S("zne_schematic.png"), { x: 6.45, y: 1.4, w: 6.3, h: 4.5 });
      await D.takeaway(s, C, "Mitigation buys accuracy with extra quantum resources, so whether to use it is a real decision.", { y: 6.05, Icon: FaCoins });
      D.source(s, C, "Temme 2017 · Kandala 2019 · Giurgica-Tiron 2020 · Bravyi 2021 (PRA 103:042605) · Russo 2023 (IEEE TQE 4). Curve illustrative.", 6.72);
    },
  },
  {
    title: "Proposed approach: Q-TRACE",
    kicker: "Proposal as recorded  ·  generic QML benchmarks, mitigate-or-not decision",
    speaker: "Tushar",
    script: `We propose Q-TRACE, a decision layer that sits on top of a quantum machine-learning model.

For each run, Q-TRACE decides whether mitigation is worth applying, using a simple principle: mitigate only when the expected benefit outweighs the extra cost. The mitigation techniques are zero-noise extrapolation and readout mitigation, and the models are simulated with Qiskit Aer.

As recorded, the benchmarks were standard tasks: Iris and the Wisconsin breast-cancer data for classification, and QM9 for molecular properties. And Q-TRACE would be compared with three simple policies: never mitigate, always mitigate, and a fixed rule.`,
    keyPoints: ["decision layer on a QML model: mitigate only if benefit exceeds cost", "mitigation: ZNE and readout; simulation: Qiskit Aer", "benchmarks: Iris, WDBC, QM9; compared with Never / Always / Fixed"],
    transition: "Which questions we will answer, and how.",
    sources: "docs/DECISIONS.md Q1; docs/PROJECT_SPEC.md §2; docs/research/deep-research-report.md (description of the pre-October deck).",
    build: async (s, { C, D }) => {
      D.flow(s, C, [
        { head: "QML model", body: "on a benchmark task" },
        { head: "Noisy execution", body: "simulated with Qiskit Aer" },
        { head: "Q-TRACE decides", body: "benefit − cost > 0 ?", fill: "D7EEEE" },
        { head: "Mitigate or not", body: "ZNE / readout mitigation" },
      ], { y: 1.55, h: 1.35, size: 15 });
      D.text(s, "Benchmarks named in the record", { x: 0.6, y: 3.2, w: 6, h: 0.4 }, { fontSize: 15, bold: true, color: C.text2 });
      [["Iris", "small classification benchmark"], ["WDBC", "breast-cancer classification"], ["QM9", "molecular-property regression"]]
        .forEach(([h, b], i) => D.cardText(s, C, { x: 0.6 + i * 4.1, y: 3.65, w: 3.9, h: 1.3, head: h, body: b, size: 14 }));
      await D.takeaway(s, C, "Compared with three simple policies: never mitigate, always mitigate, and a fixed rule.", { y: 5.3, Icon: FaCodeBranch });
      D.caption(s, C, "Recorded in docs/DECISIONS.md (Q1) and the early-October research plan's description of the deck of that time. The fraud application came later, on Oct 6, 2026.", { x: 0.6, y: 6.05, w: 12.1, h: 0.5 });
    },
  },
  {
    title: "Research questions and planned method",
    kicker: "Reconstructed at the level the record supports",
    speaker: "Tushar",
    script: `We have two research questions. First, when does error mitigation improve a quantum model's output enough to justify its extra cost? Second, can Q-TRACE's benefit-versus-cost decision do better than never mitigating, always mitigating, or a fixed rule?

Our plan has four steps. We simulate noisy quantum models on the benchmark tasks. For each setting we measure what mitigation changes and what it costs. Q-TRACE then decides by weighing benefit against cost. And we compare it with the three simple policies.

For the record: this deck was reconstructed in October. The project was narrowed on October 6 to credit-card fraud detection with several mitigation actions, which is what the following meetings report. Thank you.`,
    keyPoints: ["RQ1: when is mitigation worth its cost?", "RQ2: can the benefit-vs-cost decision beat never / always / fixed?", "plan: simulate → measure benefit and cost → decide → compare", "note: scope narrowed Oct 6 (fraud, several actions)"],
    transition: "Questions.",
    sources: "Reconstructed from docs/DECISIONS.md Q1 and the research plan's description of the pre-October deck; wording is ours.",
    build: async (s, { C, D }) => {
      D.cardText(s, C, { x: 0.6, y: 1.45, w: 6.0, h: 1.2, head: "RQ1", body: "When does error mitigation improve a quantum model's output enough to justify its extra cost?", size: 14, fill: "E3F2F1" });
      D.cardText(s, C, { x: 6.75, y: 1.45, w: 6.0, h: 1.2, head: "RQ2", body: "Can Q-TRACE's benefit-versus-cost decision beat never, always, or a fixed rule?", size: 14, fill: "E3F2F1" });
      D.flow(s, C, [
        { head: "1. Simulate", body: "noisy QML models (Qiskit Aer)" },
        { head: "2. Measure", body: "benefit and cost of mitigating vs not" },
        { head: "3. Decide", body: "weigh benefit against cost" },
        { head: "4. Compare", body: "vs never / always / fixed rule" },
      ], { y: 2.95, h: 1.15, size: 14.5 });
      D.card(s, { x: 0.6, y: 4.45, w: 12.1, h: 1.25 }, "FBEFD9", "retro-note-bg");
      D.text(s, [
        { text: "Note added in October 2026.  ", options: { bold: true, color: "8A5A00" } },
        { text: "On Oct 6 the scope was narrowed to credit-card fraud detection, with several mitigation actions, label-free decision inputs and pre-registered phases (docs/DECISIONS.md: Q1, A01, A12). Later meetings report that study.", options: { color: C.text1 } },
      ], { x: 0.85, y: 4.45, w: 11.6, h: 1.25 }, { fontSize: 13.5, valign: "middle" });
      await D.takeaway(s, C, "A practical question: spend quantum resources on mitigation only when it pays.", { y: 5.95, Icon: FaListCheck });
      D.source(s, C, "Reconstructed from docs/DECISIONS.md (Q1) and docs/research/deep-research-report.md (pre-October deck); wording is ours.", 6.72);
    },
  },
];

module.exports = { meta, slides };
