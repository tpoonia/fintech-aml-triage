---
title: "Q-TRACE: When Is Quantum Error Mitigation Worth Paying For?"
subtitle: "Final Capstone Report — A Pre-Registered Study of Selective Error Mitigation for Noisy Variational Quantum Fraud Classifiers"
author:
  - Mayank Kumar Pokhriyal
  - Tushar Poonia
date: "M.S. in Artificial Intelligence, Katz School of Science and Health, Yeshiva University — October 2026"
lang: en-US
bibliography: ../paper/references.bib
link-citations: true
numbersections: true
toc: true
toc-depth: 2
geometry: margin=1in
fontsize: 11pt
mainfont: texgyrepagella
mainfontoptions:
  - Extension=.otf
  - UprightFont=*-regular
  - BoldFont=*-bold
  - ItalicFont=*-italic
  - BoldItalicFont=*-bolditalic
sansfont: texgyreheros
sansfontoptions:
  - Extension=.otf
  - UprightFont=*-regular
  - BoldFont=*-bold
  - ItalicFont=*-italic
  - BoldItalicFont=*-bolditalic
mathfont: texgyrepagella-math.otf
colorlinks: true
linkcolor: "blue!50!black"
citecolor: "blue!50!black"
urlcolor: "blue!50!black"
header-includes:
  - \usepackage{float}
  - \floatplacement{figure}{H}
  - \usepackage{booktabs}
  - \AtBeginDocument{\sloppy}
  - \setlength{\LTcapwidth}{\textwidth}
  - \usepackage{needspace}
---

# Executive summary {.unnumbered}

**Question.** A noisy quantum classifier can spend extra quantum resources on error mitigation. Mitigation trades extra circuits and shots for less biased results, but its cost varies by an order of magnitude between techniques. We asked: *when should a noisy quantum fraud classifier spend additional quantum resources on mitigation, and is learning that decision better than a simple observable rule?*

**What we did.**

- We trained 64 independent 4-qubit variational quantum classifiers (VQCs) on the public European credit-card fraud dataset.
- We simulated each classifier exactly under depolarizing, thermal-relaxation and readout noise.
- We ran every classifier under every one of five actions: no mitigation, readout mitigation, zero-noise extrapolation (ZNE), both, or three times the shots. This gave about 1.4 million paired counterfactual outcomes.
- Policies could see only cheap label-free probes and static model descriptors.
- We compared each policy with a cost-aware Oracle: the cheapest action whose Brier score is within 10% of the best.
- Every stage was pre-registered. The final test used 16 models from four structures that had never been used. They were sealed until the end and evaluated exactly once.

**What we found.**

| Finding | Evidence |
|----------------------------|-----------------------------------------|
| Noise damaged calibration and fixed-threshold decisions, not discrimination | AUPRC changed by at most 0.003 (every interval contains 0); Brier rose from 0.0093 to 0.121; precision at the frozen threshold fell from 0.53 to 0.03 |
| Mitigation repaired calibration; extra shots did not | Brier 0.122 → 0.054 with combined mitigation under combined-high noise; three times the shots left it at 0.121; no action improved AUPRC beyond its shot-matched baseline |
| No *material* structure was left for a learned controller | Two pre-registered gates failed; no controller was trained |
| A two-threshold probe rule was near-Oracle on unseen models | Material errors 2.0% [1.5, 2.6] under continuous joint noise and 8.8% under categorical noise; Brier within 0.03% of the Oracle at 0.6% more shots |
| Pre-specified learned comparators did not reduce material errors | Best (gradient boosting) 2.1%; paired difference +0.0005 [−0.016, +0.027] |

**Answer.** In the studied setting, a simple observable probe rule performed competitively with learned mitigation controllers. The rule is: spend on ZNE when the gate probe detects gate noise, add readout mitigation when the readout probe exceeds about 0.4% error, and never buy extra shots to fix calibration. Learning the decision was not justified.

**Important caveats.** We state these wherever the results appear:

- The evidence is simulation-only, at 4 qubits, on one dataset, with two mitigation techniques.
- The held-out test has only four structures, so its intervals are likely too narrow.
- On the stricter, non-registered endpoint of *any* disagreement with the Oracle, some learned comparators were closer to the Oracle than the rule; the rule's extra disagreements were cheap.
- The rule's margin over "always use combined mitigation" is set by the share of gate-free settings in our design (1 of 17).
- We make no quantum-advantage claim.

**Status.**

- Every number in this report traces to a committed result table.
- The references were checked against publisher, arXiv and Crossref records by an AI assistant. The authors still need to confirm them before external submission.
- The manuscript (`deliverables/paper/`) is ready for professor review. It has not been peer reviewed.

# Introduction and objectives

Near-term quantum processors are noisy [@preskill2018quantum]. Quantum error mitigation (QEM) reduces the bias that noise introduces into estimated expectation values, at the price of additional quantum resources [@temme2017error; @kandala2019error; @cai2023quantum]. We study two widely used techniques:

- **Readout mitigation** inverts a calibrated model of measurement errors [@bravyi2021mitigating; @maciejewski2020mitigation].
- **Zero-noise extrapolation (ZNE)** amplifies gate noise and extrapolates measured values to the zero-noise limit [@giurgicatiron2020digital; @kim2023scalable].

ZNE multiplies shots and two-qubit-gate exposure, and the benefit of mitigation depends on the platform and the budget [@russo2023testing; @zhang2026worse].

For a deployed quantum classifier this creates a recurring decision. Should it spend extra resources in the current execution context, and on which technique, or simply on more shots? Our original hypothesis was that a learned controller, which we called Q-TRACE, could make this decision better than fixed policies, using only cheap, label-free probes. Before running anything, we registered the competing hypothesis that a simple rule suffices.

**Research question.** *When should a noisy QML fraud model spend additional quantum resources on mitigation, and is learning that decision better than a simple observable rule?*

**Objectives.**

1. Characterize what simulated noise does to a 4-qubit VQC fraud classifier, and what readout mitigation and ZNE repair.
2. Build a leakage-safe counterfactual benchmark across many independently trained models, noise contexts, shot budgets and actions.
3. Test, under pre-registration, whether the per-context decision has structure that a learned controller can exploit beyond simple observable rules.
4. Confirm the outcome once on sealed, never-used model structures.

**Hypotheses.** Table 1 lists the registered hypotheses and their outcomes.

\needspace{22\baselineskip}

| Hypothesis | Outcome |
|-----------------------------------|---------------------------------------|
| Phase 3B H1: noise degrades VQC discrimination | **Not supported** at the studied severities. Noise caused ranking reordering in the legitimate bulk and calibration and threshold distortion, with no discrimination degradation (G1 conditional pass) |
| H4.1: readout mitigation repairs calibration | **Supported** |
| H4.2: symmetric readout noise is rank-neutral | **Supported** (exactly, to $10^{-16}$) |
| H4.3: mitigation improves AUPRC beyond resource-matched shots | **Not supported** (G2 conditional pass) |
| H4.4: the best action depends on the noise context | **Supported** |
| Learned controller, categorical noise (gate G3B) | **Failed:** a fixed probe rule suffices |
| Learned controller, continuous joint noise (gate G3C) | **Failed:** negligible material regret |
| Final H1: the rule is near-Oracle on held-out structures | **Supported** (material failure 0.020; Brier regret −0.03%) |
| Final H2: learning adds no meaningful value (non-superiority on material failure) | **Supported** |
| Final H3: the rule beats every universal policy and uses no more shots than always-A3 | **Supported** |
| Final H4: the rule transfers to categorical noise (material failure ≤ 0.10) | **Supported** (0.088) |

: Pre-registered hypotheses and outcomes.

# Background and related work

**Error mitigation.**

- **ZNE.** Zero-noise extrapolation was introduced with Richardson extrapolation [@temme2017error] and demonstrated on hardware [@kandala2019error]. It has been scaled to tens of qubits using pulse stretching [@kim2023scalable]. Digital ZNE amplifies noise by unitary folding [@giurgicatiron2020digital].
- **PEC.** Probabilistic error cancellation with learned sparse noise models removes bias, at an exponential sampling cost [@vandenberg2023probabilistic].
- **Resource-normalized evaluation.** An evaluation across hardware platforms finds mitigation beneficial on average but strongly platform-dependent [@russo2023testing]. At a matched online shot budget, unconstrained ZNE can be worse than the raw estimate [@zhang2026worse]. In hybrid quantum neural networks, the benefit of system-level mitigation depends strongly on the noise model [@minguenjiki2026robustness].

**Learning and mitigation.** Learning-based QEM learns the mitigation map itself, for example from near-Clifford training circuits [@strikis2021learning] or by regression models that emulate ZNE [@liao2024machine]. Noise-aware circuit learning optimizes the circuit against a device's noise model [@cincio2021machine].

**Adaptive selection.** Recent selectors choose mitigation per context:

- GSC-QEMit combines telemetry clustering, forecasting and Thompson sampling [@szachara2026gsc].
- A cost-aware contextual bandit selects ZNE scale-factor sets [@rahman2026adaptive].
- APGEM orchestrates several techniques in quantum reinforcement learning [@majid2026context].
- A fuzzy-logic selector uses label-free circuit and hardware features [@rao2026adaptive].
- A decision-aware analysis argues for selecting mitigation by its downstream effect [@scavino2026decision].

The learned selectors condition on information that is label-dependent or unavailable at deployment. They report gains mainly over static choices; one also compares against grid-search ZNE and other published methods.

**The gap.** To our knowledge, three things had not been done together:

- extra shots and combined mitigation in one action space;
- a context restricted to label-free probes;
- a pre-registered, held-out comparison against simple rules.

**QML for fraud detection.** Variational, kernel and hybrid quantum classifiers have been applied to fraud data [@elalami2026comparative; @das2025qfdnn; @tudisco2024evaluating; @li2025hqrnn; @kyriienko2022unsupervised]. Comparisons with classical models are mixed. On the same dataset, tuned classical baselines outperform 4-qubit quantum classifiers [@dinut2026comparative], while other studies report quantum or hybrid models matching or exceeding classical baselines on particular metrics [@kyriienko2022unsupervised; @li2025hqrnn; @tudisco2024evaluating]. Noise can even improve some quantum models in specific regimes [@zhu2026rethinking; @ahmed2025noisy]. We use the VQC as a noisy workload, not as a competitor to classical fraud models.

# Data and models

**Dataset.** We use the public European credit-card fraud dataset [@dalpozzolo2015calibrating; @mlgulb2018creditcardfraud]. It has 284,807 transactions, of which 492 are frauds (0.17%).

- **Deduplication.** Removing 773 exact-duplicate groups leaves 283,726 rows and 473 frauds.
- **Near-duplicates.** Rows that are identical apart from the timestamp (4,383 groups, all legitimate) are kept together.
- **Partitions.** A group-aware stratified split assigns five disjoint partitions (Table 2), and no group crosses partitions.
- **Preprocessing.** All preprocessing is fitted on the VQC-training partition only.

\needspace{12\baselineskip}

| Partition | Rows | Frauds | Used for |
|----------------------|---------:|-------:|-----------------------------------------|
| VQC train | 127,677 | 213 | fitting every VQC and preprocessing |
| VQC validation | 28,372 | 47 | qualification, thresholds, characterization |
| Controller train | 42,559 | 71 | policy fitting (training models) |
| Controller validation | 28,372 | 47 | policy validation (validation models) |
| Controller test | 56,746 | 95 | sealed; opened once (test models) |

: Group-aware partitions after deduplication.

**Classifiers.** Each VQC angle-encodes four features into four qubits. It then applies a ZZ feature map [@havlicek2019supervised; @schuld2020circuit], a RealAmplitudes or EfficientSU2 ansatz, and a parity or mean-$Z$ readout, and is trained by COBYLA on balanced subsets of the VQC-training partition.

The first model, with a clipped $[-\pi, \pi]$ encoding, reached validation AUPRC 0.104. Training-data diagnostics traced this to saturation and phase aliasing. A pre-registered, cross-validated repair then selected a wide-range encoding with ansatz depth 2. The repaired model reached AUPRC 0.507 [0.363, 0.661], AUROC 0.957 and Brier 0.0093.

Classical models on the same inputs reach AUPRC 0.59–0.62. These are point estimates, and only the logistic-regression gap (+0.113 [0.021, 0.214]) has an interval excluding zero. The VQC is therefore a working but not advantageous classifier.

**Model pool.** To make models the independent unit of analysis, we trained a pre-registered pool of 64 VQCs: 16 structures × 4 seeds.

- **Structures** combine three feature sets, three alias-safe encodings, two ansatz families at two depths, and parity or mean-$Z$ readout.
- **Qualification.** All 64 qualified on clean validation data, with median AUPRC 0.235 (range 0.047–0.538) and AUROC 0.91–0.96.
- **Split.** Structures were split 8/4/4 into training, validation and test models, keeping all seeds of a structure together.
- **Thresholds.** Each model's decision threshold was tuned once on clean validation data and frozen.

# Methodology

## Decision layer and workflow

![The selective-mitigation decision layer. The policy observes only label-free probes and static model descriptors; quantities in the dashed box are offline-only (schematic).](fig1_architecture){width=100%}

![Pre-registered workflow with each gate's outcome (schematic). The sealed controller test was opened once, after the final protocol had been pushed.](fig2_workflow){width=100%}

## Noise simulation

Circuits are transpiled to $\{r_z, \sqrt{X}, X, \mathrm{CX}\}$ and simulated exactly with Qiskit Aer density matrices [@javadiabhari2024quantum]. The noise model has three parts:

- **Depolarizing channels** after one- and two-qubit gates.
- **Thermal relaxation** over gate durations of 35 ns and 300 ns.
- **Per-qubit readout confusion.** The asymmetric component is a synthetic stress-test assumption, not device data.

Finite-shot outcomes are multinomial draws, paired across actions within a replicate. Severities stay within a validated anchor grid ($p_2$ up to 0.02, $T_1$ down to 50 µs, mean readout error up to 0.05).

There are two environments:

- **Phase 5B: near-categorical.** Eight conditions: clean, three readout-only, two gate-only and two combined. Budgets of 1,024 and 4,096 shots.
- **Phase 5C: continuous and joint.** A split-plot design of 17 gate settings (one gate-free setting plus a 16-point maximin Latin hypercube in depolarizing × thermal severity), crossed with four readout settings each, giving 68 noise points. Budgets of 256, 1,024 and 4,096 shots.

Both environments used 20 replicates per context.

## Actions and costs

\needspace{12\baselineskip}

| Action | Description | Shots per inference | CX exposure |
|------|------------------------------------------------|----------------|----------|
| A0 | none | $S$ | 1× |
| A1 | tensored readout mitigation (2 calibration circuits per batch) | $S + 2S/N$ | 1× |
| A4 | three times the shots, unmitigated | $3S$ | 3× |
| A2 | ZNE: global folding at $\lambda \in \{1,3,5\}$, linear least-squares extrapolation | $3S$ | 9× |
| A3 | readout mitigation at every scale, then ZNE | $3S + 2S/N$ | 9× |

: Actions and resources per logical inference ($S$ shots per circuit, $N$ transactions per batch). The cost order is A0 < A1 < A4 < A2 < A3.

## Endpoints and the cost-aware Oracle

The primary endpoint is the Brier score [@brier1950verification] of the mitigated fraud probabilities, averaged over 20 finite-shot replicates per context.

- **Oracle.** For each context the Oracle chooses $p^*$, the cheapest action whose mean Brier score is within $\varepsilon = 0.10$ of the best.
- **Failure.** A policy *fails* when it disagrees with $p^*$.
- **Material failure.** A failure is *material* when the chosen action's Brier score exceeds $(1+2\varepsilon)$ times the best, or when it costs at least $S$ more shots per inference.
- **Brier regret.** Relative Brier regret can be slightly negative: the Oracle may lie up to 10% above the best Brier score, so a policy that overspends can be more reliable than the Oracle while costing more.
- **Cost measures.** Cost regret and the overspend criterion count action shots only. Reported total shots per inference also include probe shots.

## Observable context and policies

A policy sees two kinds of input:

- **16 static model descriptors.**
- **11 features from two label-free probes,** run on every batch:
  - a *readout probe*: the two calibration circuits;
  - a *gate probe*: 32 fixed synthetic parameter bindings at folding factors 1 and 3.

The probes cost $66S$ shots per batch, charged to every probing policy. True noise parameters, noise labels, identifiers, transaction labels and post-action outcomes are offline-only. A feature registry and automated tests keep them out of every policy input.

The policies compared are:

- **Universal policies:** always one action.
- **$R_{\mathrm{cat}}$:** a four-cell probe rule with a-priori thresholds.
- **$R_{\mathrm{thr}}$:** one readout-probe threshold and one gate-probe threshold per shot budget, fitted on training models.
- **$R_{\mathrm{obs}}$:** $R_{\mathrm{thr}}$ fitted separately for parity and mean-$Z$ readouts.
- **Four learned comparators** with hyperparameters fixed in advance:
  - multinomial logistic regression;
  - a depth-3 decision tree;
  - histogram gradient boosting;
  - gradient boosting predicting per-action Brier ratios.

All policies were fitted on training models only. The learned comparators were frozen by committed fingerprints of their decisions.

## Gates, statistics and integrity

**Gates.** A learned controller was to be trained only if a residual-complexity gate found material decision structure that the best simple rule could not capture.

- **G3B (Phase 5B)** failed if the category rule's validation failure was below 5%.
- **G3C (Phase 5C)** failed if the best rule's material failure was below 5%.

**Statistics.** Models, nested in structures, are the independent units. Intervals are two-stage cluster bootstraps: structures are resampled, then models within each structure, with 2,000 resamples. Policy comparisons use paired per-decision differences.

**The sealed test.** The controller-test outcomes were written to a version-control-ignored store; only row counts and content hashes were committed. A guard permitted a single unlock, after the protocol, code and frozen comparators had been pushed, and logged every read.

# Results

## What noise and mitigation do

On the repaired base model (validation partition, exact simulation), noise left discrimination essentially unchanged:

- **Discrimination.** AUPRC changed by at most 0.003 under depolarizing, thermal and combined noise, with every 95% interval containing zero. At least 46 of the 47 top-ranked frauds were preserved.
- **Bulk ranking.** Noise reordered scores within the legitimate bulk (Kendall $\tau$ 0.96–0.99).
- **Calibration.** Calibration [@guo2017calibration] collapsed: the Brier score rose from 0.0093 to 0.121, and precision at the frozen threshold fell from 0.53 to 0.03.

![Noise changes calibration, not discrimination. Left: change in AUPRC with 95% paired bootstrap intervals. Right: Brier score (dashed line: clean model). Source: `p3b_exact_metrics.csv`.](fig3_noise_effects){width=100%}

With 1,024 shots and 20 replicates, no action improved AUPRC over its resource-matched comparator, whereas mitigation restored calibration:

\needspace{9\baselineskip}

| Condition (1,024 shots) | No mitigation | Best mitigation | 3× shots |
|-------------------------------|------------:|--------------------------:|---------:|
| High symmetric readout noise | 0.053 | 0.011 (readout mitigation) | 0.053 |
| High depolarizing noise | 0.055 | 0.038 (ZNE) | 0.055 |
| Combined-high noise | 0.122 | 0.054 (both) | 0.121 |

: Brier score by condition: mitigation removes calibration bias; extra shots do not.

Linear ZNE recovered 13–70% of the exact Brier gap to the clean model. Fixed-threshold F1 recovered by up to +0.30 at 1,024 shots and +0.34 at 4,096 shots. The best action depended on the noise family and was the same at both budgets.

![Brier score by condition and action (1,024 shots, mean of 20 replicates). Source: `p4_summary.csv`.](fig4_mitigation){width=100%}

## Phase 5B: categorical noise

Under near-categorical noise, the Oracle action was a lookup on the noise family: clean → none, readout → readout mitigation, gate → ZNE, combined → both.

- **Rule performance.** A four-cell category rule fitted on training structures failed in 0.33% of validation replicates. The best single action failed in 62.5%.
- **Model dependence.** Mitigation benefit was strongly model-specific in magnitude: the intraclass correlation was about 0.98 for the readout-based actions. But the noise context explained 82–99% of its variance and rarely changed the winning action.
- **Extra shots** were never preferred.
- **Residual structure.** The association between structure and preferred action was statistically detectable (mutual information 0.08 nats, $p = 0.001$) but far below materiality.

**G3B failed, so no controller was trained.**

## Phase 5C: continuous joint noise

Continuous joint noise removed most of the choice rather than creating a harder one.

- **Preferred actions.** In our design, 16 of the 17 gate settings carry gate noise. Across all contexts, combined mitigation was the Oracle action in 67–71% and ZNE alone in 23–27%. ZNE won where readout error was below about 0.003. Readout mitigation or no mitigation won only on the gate-free setting.
- **Budget.** Extra shots were never preferred at the registered tolerance, and the budget changed the Oracle action in under 3% of model–point pairs.
- **The best rule.** $R_{\mathrm{thr}}$ disagreed with the Oracle in 9.6% [8.0, 11.7] of validation replicates. Only 2.0% [1.6, 2.7] of its decisions were material, with relative Brier regret +0.3% [−0.4, +1.0].
- **Residual structure.** The structure–action association was again detectable (validation mutual information 0.04 nats, $p < 0.001$), driven by the mean-$Z$ readout, but small.

**G3C failed on its negligible-regret condition, so no controller was trained.**

![Share of contexts in which each action is the cost-aware Oracle choice. Source: `p5b_metadata.json`, `p5c_metadata.json`, `final_metadata.json`.](fig5_preferred_actions){width=100%}

## One-time held-out evaluation

The sealed controller test contains 16 models from four structures never used for fitting or selection, including a mean-$Z$ structure. It was opened once, on 2026-10-08 (21:28:24 UTC). The stored outcomes matched their committed hashes, and the refitted learned comparators reproduced their frozen decision fingerprints. **All four final hypotheses were supported.**

\needspace{22\baselineskip}

| Policy | Material failure | Any disagreement | Brier regret | Shots vs Oracle | 5B material |
|-----------------------------|-----------------:|-----------:|--------:|---------:|---------:|
| Never mitigate (A0) | 0.960 | 0.986 | +93.1% | 0.35× | 0.813 |
| Always A3 | 0.059 | 0.400 | −1.4% | 1.04× | 0.500 |
| 5B category rule $R_{\mathrm{cat}}$ | 0.045 | 0.249 | +1.0% | 0.99× | 0.064 |
| **Probe rule $R_{\mathrm{thr}}$** | **0.020 [0.015, 0.026]** | **0.219** | **−0.03%** | **1.006×** | **0.088** |
| $R_{\mathrm{obs}}$ (+ readout type) | 0.021 [0.017, 0.025] | 0.089 | +0.7% | 1.006× | 0.119 |
| Logistic (learned) | 0.094 | 0.173 | +2.4% | 0.95× | 0.177 |
| Tree, depth 3 (learned) | 0.026 | 0.086 | +0.7% | 1.008× | 0.118 |
| Gradient boosting (learned) | 0.021 [0.005, 0.044] | 0.065 | +0.3% | 1.009× | 0.363 |
| GBT benefit model (learned) | 0.026 | 0.150 | −0.26% | 1.013× | 0.439 |
| Oracle | 0 | 0 | 0 | 1× | 0 |

: One-time held-out evaluation, continuous joint noise (5C test, all budgets pooled) and categorical noise (5B test, material failure). Intervals: 95% two-stage cluster bootstrap over four structures. Sources: `final_policies_5c_test.csv`, `final_policies_5b_test.csv`.

**Continuous joint noise.**

- **The rule.** $R_{\mathrm{thr}}$ made material errors in 2.0% of decisions, with relative Brier regret −0.03% (95% CI −1.7% to +1.2%). It spent 0.6% more shots than the Oracle and 3.4% fewer than always using combined mitigation.
- **The best learned comparator.** Gradient boosting tied the rule at 2.1%. The paired difference in material failure (comparator − rule) was +0.0005 [−0.016, +0.027], so the interval excludes a comparator advantage as large as the registered 0.02 margin.

**Categorical noise.** $R_{\mathrm{thr}}$'s material failure was 8.8%, inside the registered bound. The category rule fitted on Phase 5B data did significantly better (6.4%; paired difference −0.024, 95% CI −0.037 to −0.011), and the learned comparators did worse (11.8–43.9%).

**Raw disagreement.** On the stricter, non-registered endpoint of any disagreement with the Oracle, the learned comparators had an advantage:

- Gradient boosting disagreed in 6.5% of decisions against $R_{\mathrm{thr}}$'s 21.9% (paired difference −0.154 [−0.391, −0.028]).
- The depth-3 tree and $R_{\mathrm{obs}}$ were also significantly closer to the Oracle.

**Where the rule's extra disagreements come from.** They come from the unseen mean-$Z$ structure, where the rule adds readout mitigation that mean-$Z$ readouts barely need. That costs two calibration circuits per batch and was not material there (1.4%). $R_{\mathrm{obs}}$, which conditions on the readout type, absorbs these disagreements. Learned comparators trained on a single mean-$Z$ structure reached 5–30% material failure on the new one.

**Stability between validation and test.** The learned comparators were unstable: gradient boosting's material failure was 10.7% on validation and 2.1% on test, and the depth-3 tree's was 17.5% and 2.6%. $R_{\mathrm{thr}}$'s was 2.0% on both.

![One-time held-out evaluation under continuous joint noise. Bars: any disagreement with the Oracle (left) and material failure (right), with 95% two-stage cluster intervals. Source: `final_policies_5c_test.csv`.](fig8_final_heldout){width=100%}

![Paired difference in material failure, comparator − $R_{\mathrm{thr}}$ (positive favours the rule; shaded band: registered ±0.02 margin). Source: `final_paired_vs_rthr_5c_test.csv`, `final_paired_vs_rthr_5b_test.csv`.](fig7_learned_vs_rule){width=100%}

**Cost and reliability.** Always-A3's material failure, 5.9%, equals the share of contexts on the gate-free design setting (1/17), where it pays $2S$ more than readout mitigation. H3's margin and the 3.4% shot saving therefore scale with the share of gate-free batches. On a device where gate noise is always present, both shrink to the choice between ZNE and combined mitigation, which differ by two calibration circuits per batch.

![Cost–reliability trade-off on the sealed test; off-scale policies are listed in each panel. Source: `final_policies_5c_test.csv`, `final_policies_5b_test.csv`.](fig6_cost_reliability){width=100%}

## Ablations (validation only)

The sealed test was not reused for the ablations.

- **Gate probe alone.** Refitting $R_{\mathrm{thr}}$ with only the gate probe left its material failure essentially unchanged: 1.8% under continuous noise and 9.4% under categorical noise. Its raw disagreement rose from 10% to 25%.
- **Other variants.** A readout-only rule (6.2%, 50%) and a probe-free fixed action per budget (5.9%, 50%) were much worse.
- **Interpretation.** The gate probe carries the material decision.
- **Probing break-even.** Probing pays for itself relative to always using combined mitigation only for batches above about 645–685 transactions under continuous noise (about 80 under categorical noise). This is conservative and depends on the gate-free share.
- **Tolerance.** Across $\varepsilon$ = 0.05–0.20, the rule's material failure stayed between 2.0% and 7.5%.

![Probe ablation on validation data. Source: `ablation_probes.csv`.](fig9_probe_ablation){width=100%}

# Discussion

**Observed.** On held-out models:

- A two-threshold probe rule was within 0.03% of the Oracle's Brier score, at 0.6% more shots and with 2.0% material errors.
- Fixed learned comparators did not reduce material errors, although some agreed with the Oracle more often.

**Interpreted.** We read this as follows:

1. **Bias, not variance.** Mitigation acts on a calibration bias that extra shots cannot remove, so the budget hardly matters.
2. **One question decides.** In our continuous joint-noise design, where 16 of 17 gate settings carry gate noise, combined mitigation is almost always within tolerance. The material decision therefore reduces to whether gate noise is present, and the remaining readout question is nearly free.
3. **Magnitude, not the winner.** Model heterogeneity is large in magnitude but rarely changes which action wins. Where it does (mean-$Z$ readout), one static descriptor captures it, while learners trained on one such structure did not extrapolate to another.

**Implications.** Adaptive mitigation selectors should be evaluated against simple probe rules and cost-aware Oracles, on held-out models and under pre-registration. For practitioners in a similar setting:

- run the gate probe;
- if gate noise is present, use ZNE, and add readout mitigation when the readout probe exceeds about 0.4% error;
- otherwise, use readout mitigation alone;
- never buy extra shots to fix calibration;
- for very small batches, skip probing and always combine.

The numeric thresholds are fitted to our simulated 4-qubit circuits and probes, and would need refitting elsewhere.

# Limitations and threats to validity

- **Simulation only.** The asymmetric readout component is synthetic. Crosstalk, drift, leakage and coherent errors are not modelled. Hardware validation is the main external-validity gap.
- **Scale.** The study uses four qubits, shallow circuits (15–18 CX) and one public dataset with features that are an inherited PCA.
- **Models.** The VQCs are weaker than classical models on the same inputs; no quantum advantage is claimed or implied.
- **Mitigation scope.** Only readout inversion and linear ZNE were studied. PEC, Clifford data regression and dynamical decoupling may produce richer decisions.
- **Probes and design.** The gate probe is nearly blind to thermal relaxation (Spearman −0.12). Gate noise was present in 16 of 17 gate settings, and the advantage over always-A3 scales with the gate-free share.
- **Power and intervals.** The held-out test spans four structures, one of them mean-$Z$. Cluster-bootstrap intervals over four clusters are likely too narrow, and the registered detectable effect (about 0.70 SD) assumed 16 independent models.
- **Endpoint choice.** The registered endpoint is material failure. On raw disagreement, two learned comparators and $R_{\mathrm{obs}}$ were closer to the Oracle.
- **Thresholds.** Per-model decision thresholds were tuned on clean validation data and are optimistic.

# Conclusion and future work

Mitigation mattered for calibrated decisions, not for discrimination, and the right technique was set by the noise type. Under both categorical and continuous joint noise, a two-threshold probe rule was near-Oracle on unseen models. Two pre-registered gates did not justify a learned controller, and pre-specified learned comparators did not improve on the rule in a one-time held-out test. In the studied setting, a simple observable probe rule performed competitively with learned mitigation controllers.

The conclusion should next be tested:

- on hardware, where readout asymmetry, drift and crosstalk are real;
- with richer mitigation and a thermal-sensitive gate probe;
- on larger circuits, where noise may also damage discrimination;
- with endpoints that weight fraud-operations costs.

# Reproducibility

All configurations, code, pre-registrations, execution records and aggregate result tables are version-controlled in the project repository (`MayankKumarPokhriyal/q-trace`, currently private). Every reported run records its commit, configuration hash, package versions, hardware and seeds.

The dataset is public. Transaction-level data, replicate-level outcomes and the sealed test store are not redistributed.

**Environment.** You need `uv`. Python 3.12 is pinned and every dependency version is locked in `uv.lock`.

```bash
uv sync --frozen
uv run pytest -q -m "not slow"          # fast suite
uv run ruff check . && uv run ruff format --check .
```

**Data.** Download `mlg-ulb/creditcardfraud` into `data/raw/`. The pipeline checks the file's SHA-256 against `configs/datasets/ulb_v1.yaml` and refuses any other file.

```bash
uvx kaggle datasets download -d mlg-ulb/creditcardfraud -p data/raw
unzip -o data/raw/creditcardfraud.zip -d data/raw
uv run python scripts/prepare_data.py
```

**Pipeline, in order.** Reported runs require a clean git tree.

```bash
uv run python scripts/run_classical_baselines.py   # Phase 2
uv run python scripts/train_vqc_3a.py              # Phase 3A
uv run python scripts/select_vqc_3ar.py            # Phase 3A-R (vqc_train only)
uv run python scripts/evaluate_vqc_3ar.py
uv run python scripts/run_noise_3b.py              # Phase 3B
uv run python scripts/run_mitigation_4.py          # Phase 4
uv run python scripts/build_pool_5a.py             # Phase 5A
uv run python scripts/build_counterfactual_5b.py   # Phase 5B (~2 h on 15 cores)
uv run python scripts/analyze_counterfactual_5b.py
uv run python scripts/build_mixed_5c.py            # Phase 5C (~7 h on 15 cores)
uv run python scripts/analyze_mixed_5c.py
uv run python scripts/phase7_validate.py           # validation comparison + freeze
uv run python scripts/final_test.py                # one-time sealed test (already spent)
uv run python scripts/ablations.py                 # validation-only ablations
```

**Verification.**

- `uv run pytest -m slow` runs 16 slow tests. They re-run Phases 1–5C and the final evaluation and compare their outputs with the committed tables. The final-evaluation test re-reads the sealed store, which the guard permits only after the single unlock, and logs the read.
- The sealed test cannot be re-opened for a new evaluation.

**This report's figures and documents** are regenerated as follows:

```bash
uv run python deliverables/figures/make_figures.py
deliverables/paper/build.sh              # manuscript PDF (tectonic)
deliverables/capstone_report/build.sh    # this report, PDF and DOCX (pandoc)
cd deliverables/presentations/build && npm ci && node build_oct13.js && node build_final.js
```

# Project record

\needspace{16\baselineskip}

**Timeline.**

| Date (2026) | Work |
|--------|------------------------------------------------------------------|
| Oct 6 | Phase 0 specification and environment; Phase 1 data pipeline with group-aware partitions; Phase 2 classical baselines; Phase 3A first VQC; Phase 3A-R pre-registered encoding repair |
| Oct 7 | Phase 3B noise characterization (G1 conditional pass); Phase 4 mitigation characterization (G2 conditional pass); Phase 5A 64-model pool (G3A pass); Phase 5B categorical counterfactual study (G3B fail) |
| Oct 8 | Phase 5C continuous mixed-noise study (G3C fail); Phase 7 validation comparison and frozen comparators; one-time held-out evaluation (H1–H4 supported); ablations |

: Project timeline from the version-control history. Each phase was pre-registered and pushed before its outcomes existed.

**Team contributions.** Contributions are recorded in the repository's contribution log (`docs/contribution_log.md`). *Author action required before submission: the log does not yet contain Tushar Poonia's entries; both authors should complete and confirm a contribution statement.*

**Use of AI assistance.** An AI coding assistant (Claude Code) helped with engineering, analysis scripting and drafting, under the authors' direction. Its work is logged in `docs/ai_tool_log.md`. The literature identifiers were checked against publisher, arXiv and Crossref records. All scientific decisions, pre-registrations and conclusions were reviewed by the authors, who take responsibility for the content.

# References {.unnumbered}

::: {#refs}
:::

\appendix

\needspace{20\baselineskip}

# Figure provenance

Every quantitative figure is generated by `deliverables/figures/make_figures.py` from committed tables in `results/tables/`; Figures 1 and 2 are schematics. See `deliverables/figures/FIGURES.md` for the full mapping.

| Figure | Source tables |
|--------------------|------------------------------------------------------|
| Noise effects | `p3b_exact_metrics.csv` |
| Mitigation | `p4_summary.csv` |
| Preferred actions | `p5b_metadata.json`, `p5c_metadata.json`, `final_metadata.json` |
| Cost–reliability | `final_policies_5c_test.csv`, `final_policies_5b_test.csv` |
| Learned vs rule | `final_paired_vs_rthr_5c_test.csv`, `final_paired_vs_rthr_5b_test.csv` |
| Held-out evaluation | `final_policies_5c_test.csv` |
| Probe ablation | `ablation_probes.csv` |

: Figure-to-table provenance.

# Glossary

- **Action.** A0 none; A1 readout mitigation; A2 ZNE; A3 both; A4 three times the shots.
- **Oracle ($p^*$).** The cheapest action within 10% of the best context-mean Brier score.
- **Failure.** Any disagreement with $p^*$.
- **Material failure.** Brier score more than $(1+2\varepsilon)$ times the best, or at least $S$ extra shots per inference.
- **Probe.** A cheap, label-free measurement run each batch: the readout probe (2 calibration circuits) and the gate probe (32 bindings at fold factors 1 and 3); $66S$ shots per batch in total.
- **Structure.** A combination of feature set, encoding, ansatz and readout. Four seeds of each structure form the 64-model pool.
- **Paired difference.** Comparator minus $R_{\mathrm{thr}}$, computed per decision; positive values favour the rule.
