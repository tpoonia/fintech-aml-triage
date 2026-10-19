# Bibliography verification for the Q-TRACE manuscript

Date: 2026-10-08. Inputs: `docs/MANUSCRIPT.md` (Related Work and References), `docs/FINAL_REPORT.md` §4, `docs/LITERATURE.md` §A, §D, §E and §F. No file in the repository was modified.

**Method.** Metadata comes from Crossref (`https://api.crossref.org/works/<DOI>`), the arXiv API (`https://export.arxiv.org/api/query?id_list=<id>`) and DataCite (arXiv DOIs). Gaps were filled from OpenAlex, PMLR, Europe PMC and the Kaggle API. Raw responses are saved in `raw/`.

**Claim checks.** Each claim was checked against the abstract. For L15, L16, L17, R03 and R04, it was also checked against the arXiv full text in `pdf/*.raw.txt`. Selected body text was read for Russo, van den Berg, Kim, Bravyi, El Alami and Li (Europe PMC, PMC12468836).

**Not used.** DBLP was blocked by a bot challenge, so PMLR was used for Guo et al. The IEEE Xplore and MDPI HTML pages were blocked, so OpenAlex and Europe PMC were used instead.

**Status values:**
- **VERIFIED:** every field in the .bib entry was confirmed from an authoritative record, and the manuscript's use of the source is accurate.
- **VERIFIED-WITH-CAVEAT:** the metadata is confirmed, but there is a name-parsing, venue or usage issue (see the note).
- **NOT FOUND:** the source could not be located. No entry has this status.

## 1. Reference table (34 manuscript keys + dataset)

| key | status | identifier | source URL used | note |
|---|---|---|---|---|
| temme2017error | VERIFIED | DOI 10.1103/PhysRevLett.119.180509; arXiv:1612.02058 | api.crossref.org/works/10.1103/PhysRevLett.119.180509; export.arxiv.org/api/query?id_list=1612.02058 | PRL 119(18):180509, 2017. Temme, Bravyi, Gambetta. |
| kandala2019error | VERIFIED | DOI 10.1038/s41586-019-1040-7; arXiv:1805.04492 | api.crossref.org/works/10.1038/s41586-019-1040-7; arXiv API | Nature 567(7749):491–495, 2019. 6 authors. The arXiv title differs ("Extending the computational reach of a noisy superconducting quantum processor"); the published title is used. |
| giurgicatiron2020digital | VERIFIED | DOI 10.1109/QCE49297.2020.00045; arXiv:2005.10921 | Crossref; arXiv API | IEEE QCE 2020, pp. 306–316. 5 authors. |
| bravyi2021mitigating | VERIFIED-WITH-CAVEAT | DOI 10.1103/PhysRevA.103.042605; arXiv:2006.14044 | Crossref; arXiv API; arXiv PDF p.1 | PRA 103(4):042605, 2021. The 4th author is spelled "David C. Mckay" in Crossref, arXiv and the paper itself, so that spelling is kept. The same person appears as "McKay" in other APS records; change it if the house style prefers. |
| maciejewski2020mitigation | VERIFIED | DOI 10.22331/q-2020-04-24-257; arXiv:1907.08518 | Crossref; arXiv API | Quantum 4:257, 2020. |
| cai2023quantum | VERIFIED | DOI 10.1103/RevModPhys.95.045005; arXiv:2210.00921 | Crossref; arXiv API | RMP 95(4):045005, 2023. 8 authors. |
| havlicek2019supervised | VERIFIED | DOI 10.1038/s41586-019-0980-2; arXiv:1804.11326 | Crossref; arXiv API | Nature 567(7747):209–212, 2019. 7 authors. |
| schuld2020circuit | VERIFIED | DOI 10.1103/PhysRevA.101.032308; arXiv:1804.00633 | Crossref; arXiv API | PRA 101(3):032308, 2020. Crossref gives "Krysta M. Svore"; arXiv gives "Krysta Svore". Crossref is used. |
| preskill2018quantum | VERIFIED-WITH-CAVEAT | DOI 10.22331/q-2018-08-06-79; arXiv:1801.00862 | Crossref; arXiv API | Quantum 2:79, 2018. **Listed in References but never cited in the manuscript body.** |
| dalpozzolo2015calibrating | VERIFIED-WITH-CAVEAT | DOI 10.1109/SSCI.2015.33 | Crossref; api.openalex.org/works/doi:10.1109/SSCI.2015.33; Kaggle API | 2015 IEEE SSCI, pp. 159–166, Dec 2015. Crossref mis-splits the first author (family "Pozzolo", given "Andrea Dal"); OpenAlex and the Kaggle page give "Andrea Dal Pozzolo", which is encoded as `{Dal Pozzolo}`. Kaggle labels the venue "CIDM 2015", a symposium within SSCI 2015; the DOI record says SSCI. The abstract supports "undersampling biases calibration, not ranking". |
| brier1950verification | VERIFIED-WITH-CAVEAT | DOI 10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2 | Crossref | Mon. Weather Rev. 78(1):1–3, 1950. The Crossref title is upper-case; it was converted to title case only. **Listed in References but never cited in the body.** |
| guo2017calibration | VERIFIED-WITH-CAVEAT | arXiv:1706.04599; PMLR v70 | proceedings.mlr.press/v70/guo17a.html; arXiv API | Proc. 34th ICML, PMLR 70:1321–1330, 2017. Editors: Precup and Teh. There is no publisher DOI. DBLP was inaccessible. **Listed in References but never cited in the body.** |
| javadiabhari2024quantum | VERIFIED | arXiv:2405.08810; DOI 10.48550/arXiv.2405.08810 | arXiv API; api.datacite.org; raw.githubusercontent.com/Qiskit/qiskit/main/CITATION.bib | 12 authors. A preprint only; Crossref has no journal version. This is Qiskit's official citation. |
| russo2023testing | VERIFIED-WITH-CAVEAT | DOI 10.1109/TQE.2023.3305232; arXiv:2210.07194 | Crossref; OpenAlex; arXiv API + full text | IEEE TQE 4:1–18, 2023. The IEEE article number was not confirmed and is omitted. **The manuscript and FINAL_REPORT misstate the finding** (see §2, claim g). |
| kim2023scalable | VERIFIED | DOI 10.1038/s41567-022-01914-3; arXiv:2108.09197 | Crossref; arXiv API + full text | Nat. Phys. 19(5):752–759, 2023 (online 2023-02-06). 7 authors. "Up to 26 qubits" is confirmed. Noise is amplified by **pulse stretching**, not folding (see optional fix M6). |
| vandenberg2023probabilistic | VERIFIED | DOI 10.1038/s41567-023-02042-2; arXiv:2201.09866 | Crossref; arXiv API + full text | Nat. Phys. 19(8):1116–1121, 2023. Full title ends "…on noisy quantum processors". The body gives sampling overhead γ = exp(Σ 2λ_k), which supports "exponential sampling cost". |
| strikis2021learning | VERIFIED | DOI 10.1103/PRXQuantum.2.040330; arXiv:2005.07601 | Crossref; arXiv API | PRX Quantum 2(4):040330, 2021. |
| liao2024machine | VERIFIED | DOI 10.1038/s42256-024-00927-2; arXiv:2309.17368 | Crossref; arXiv API | Nat. Mach. Intell. 6(12):1478–1486, 2024. The abstract confirms "linear regression, random forests, MLPs, GNNs" and "mimic traditional mitigation". |
| cincio2021machine | VERIFIED-WITH-CAVEAT | DOI 10.1103/PRXQuantum.2.010324; arXiv:2007.01210 | Crossref; arXiv API | PRX Quantum 2(1):010324, 2021. The manuscript lists it under "learns *the mitigation map itself*", but NACL learns noise-resilient **circuits**, not a mitigation map (fix M3). |
| szachara2026gsc | VERIFIED-WITH-CAVEAT | arXiv:2604.24551; DOI 10.48550/arXiv.2604.24551 | arXiv API + full text; api.datacite.org; Crossref title search | 6 authors. The arXiv comment says it was accepted to IJCNN 2026 (WCCI 2026), but Crossref has no proceedings DOI as of 2026-10-08, so it is cited as arXiv. The author "Dylan Jay Van Allen" is encoded as surname `{Van Allen}`; this is an assumption from the display name. |
| rahman2026adaptive | VERIFIED | DOI 10.1109/JSAC.2026.3721807; arXiv:2608.06426 | Crossref; OpenAlex; arXiv API + full text | IEEE JSAC 44:5600–5614, 2026. No issue number in Crossref. The published title says "Adaptive Zero-Noise Extrapolation", not "Adaptive ZNE". |
| majid2026context | VERIFIED | arXiv:2610.01253; DOI 10.48550/arXiv.2610.01253 | arXiv API + full text; DataCite | Majid, Sofi, Yousuf. arXiv v1, 2026-10-01; primary class cs.LG. No journal version. |
| rao2026adaptive | VERIFIED-WITH-CAVEAT | DOI 10.1109/I3CTCON68242.2026.11508107 | Crossref; OpenAlex (abstract) | IEEE I3CTCON 2026, pp. 1–6. Authors as deposited: Sathvik Rao, Ilaqquan Rajesh Indu, Sowmya B.J., Geetha J. The last two have initial-only surnames, kept verbatim in braces. The abstract comes from OpenAlex because Xplore was blocked. |
| scavino2026decision | VERIFIED | arXiv:2607.02888; DOI 10.48550/arXiv.2607.02888 | arXiv API + full text; DataCite | Single author. The first name is "Vicenzo" (sic) on arXiv and in the PDF; do not "correct" it to Vincenzo. |
| zhang2026worse | VERIFIED-WITH-CAVEAT | arXiv:2609.38713; DOI 10.48550/arXiv.2609.38713 | arXiv API + full text; DataCite | 6 authors (Workday AI Research). The arXiv comment says it was accepted at the NeurIPS 2026 SaTQuML workshop. The metadata is fine, but the manuscript intro groups it under "decision-aware analyses", which it is not (fix M1). |
| kyriienko2022unsupervised | VERIFIED-WITH-CAVEAT | arXiv:2208.01203; DOI 10.48550/arXiv.2208.01203 | arXiv API; DataCite; Crossref search | A preprint only. It reports a quantum-kernel **advantage** in average precision (15% at 20 simulated qubits), which contradicts the manuscript's "classical models remain competitive or better" (fix M5). |
| dinut2026comparative | VERIFIED | DOI 10.3390/electronics15112489 | Crossref (incl. abstract) | Electronics 15(11):2489, 2026. Authors: Ionuț-Cosmin Dinuț, Rodica-Claudia Constantinescu, Bogdan Alexandrescu. The name uses t-comma (ț); the .bib uses `{\c{t}}` (see the header note there). |
| elalami2026comparative | VERIFIED-WITH-CAVEAT | DOI 10.1007/s10489-026-07110-7; arXiv:2412.19441 | Crossref; arXiv API + full text | Appl. Intell. 56(3):83, 2026. It uses **both** the European (ULB, 284,807-transaction) dataset and BankSim, so FINAL_REPORT's "similar work exists on other fraud data" is only half right (fix F3). |
| das2025qfdnn | VERIFIED | DOI 10.1109/TCSS.2025.3568618; arXiv:2504.19632 | Crossref; OpenAlex; arXiv API | IEEE TCSS 12(6):5266–5277, Dec 2025. 6 authors. |
| li2025hqrnn | VERIFIED-WITH-CAVEAT | DOI 10.3390/e27090906 | Crossref; Europe PMC full text (PMC12468836) | Entropy 27(9):906, 2025. 5 authors. The body confirms depolarizing, bit-flip and phase-flip noise. The abstract says it outperforms conventional models by 2.4%, which contradicts "classical models remain competitive or better" (fix M5). |
| tudisco2024evaluating | VERIFIED-WITH-CAVEAT | DOI 10.1109/ACCESS.2024.3432312 | Crossref; OpenAlex (abstract) | IEEE Access 12:102918–102940, 2024. 7 authors. Intesa Sanpaolo data: 500,000 transactions, 15 features. It reports **better recall than classical models**, which contradicts the blanket statement (fix M5). |
| zhu2026rethinking | VERIFIED | DOI 10.1063/5.0331090 | Crossref (incl. abstract) | APL Comput. Phys. 2(3):030901, 2026. Zhu, Zhang, Dong, Li. OpenAlex also lists an arXiv preprint whose ID was not established, so it is omitted. |
| ahmed2025noisy | VERIFIED | DOI 10.1109/IJCNN64981.2025.11229153; arXiv:2505.03378 | Crossref; OpenAlex; arXiv API | IJCNN 2025, pp. 1–10. 4 authors. |
| minguenjiki2026robustness | VERIFIED-WITH-CAVEAT | arXiv:2604.17515; DOI 10.48550/arXiv.2604.17515 | arXiv API; DataCite | 6 authors; v2 dated 2026-07-24. The surname is encoded as `{Mingue Njiki}`, following LITERATURE.md and the display name "Jesse Roberta Mingue Njiki"; this split is not confirmed by a structured record. |
| mlgulb2018creditcardfraud (new) | VERIFIED | Kaggle `mlg-ulb/creditcardfraud`, version 3 | www.kaggle.com/api/v1/datasets/view/mlg-ulb/creditcardfraud | Title "Credit Card Fraud Detection"; owner "Machine Learning Group - ULB"; version 3, last updated 2018-03-23. Licence label: "Database: Open Database, Contents: Database Contents". The page confirms 284,807 transactions, 492 frauds (0.172%), PCA features V1–V28 and a recommendation of AUPRC, and asks users to cite Dal Pozzolo et al. 2015 (among others). |
| (Qiskit Aer) | SKIPPED | — | raw.githubusercontent.com/Qiskit/qiskit-aer/main/README.md | Aer has no separate citable paper or CITATION file. Its README ("Authors and Citation") says to cite Qiskit via Qiskit's CITATION.bib, which is javadiabhari2024quantum. The manuscript's current use is therefore correct. |

Summary:
- 35 entries were written: 34 manuscript keys plus the dataset.
- Of the 34 manuscript keys, 19 are VERIFIED and 15 are VERIFIED-WITH-CAVEAT. The dataset entry is also VERIFIED. None are NOT FOUND.
- Every FINAL_REPORT §4 reference is among the 34 keys.

## 2. Claim checks

### Requested checks (a)–(f)

**(a) GSC-QEMit (L15): "clusters telemetry, forecasts degradation and uses Thompson sampling to choose abstract mitigation intensities, in simulated GHZ, QFT and Grover workloads."**

**CONFIRMED.** Evidence from the full text:
- **Telemetry:** a Spark–GHSOM clusters 13-D telemetry.
- **Forecasting:** an SVGP forecasts short-horizon logical fidelity.
- **Bandit:** a cost-aware linear contextual bandit uses Thompson sampling (TS-CL).
- **Actions:** an explicitly "abstract intervention interface" with three levels, NONE, MODERATE and SEVERE.
- **Simulation:** a Qiskit Aer instrumented emulator with drifting noise.
- **Workloads:** eight, including GHZ, QFT and Grover.

Optional precision: "…on eight simulated benchmark workloads, including GHZ, QFT and Grover."

Supporting detail for the intro claim "information unavailable at deployment":
- The context includes ε_L, the TVD to the ideal distribution, and F_L = 1 − ε_L.
- It also includes p_eff, a simulator drift parameter. The authors say this would be replaced by proxies on hardware.
- The baselines are Unmitigated and Static Severe only.

**(b) Rahman & Nguyen (L16): "a cost-aware LinUCB chooses ZNE scale-factor sets for hybrid VQC image classifiers."**

**CONFIRMED.** Evidence from the full text:
- **Algorithm:** "Cost-aware LinUCB selection", with UCB_k(x) − λ_c·C̃_k.
- **Arms:** ZNE folding-scale sets {1,3}, {1,3,5}, {1,3,5,7}.
- **Model:** a hybrid model, a ResNet-18 RGB encoder plus a CNN encoder, then a VQC head and a linear classifier.
- **Data:** CIFAR-10 and EuroSAT.
- **Hardware:** limited validation on a Rigetti QPU.

Label dependence:
- The context includes "loss and accuracy at λ=1", which is label-dependent.
- The reward is the cross-entropy of the ZNE-corrected prediction ("true-class probability, per-example loss").

**(c) Majid et al. (L17): "APGEM selects among no mitigation, ZNE, PEC, CDR and readout mitigation in QRL, using fidelity-, reward- and noise-level context."**

**CONFIRMED.** Evidence from the full text:
- **Pool:** M = {NoMitigation, ZNE, PEC, CDR, REM}. The abstract lists only four techniques; "NoMitigation" appears in §4.6.
- **Base context, 9 features:** depolarizing level, readout rate, unmitigated fidelity, ΔF, policy entropy, depth, remaining shot budget, approximation ratio and reward trend, plus RBF features of the noise level.
- **Controller:** a LinUCB bandit.
- **Task:** the **Capacitated Vehicle Routing Problem** (CVRPLIB), not TSP. TSP is R02.
- **Setting:** simulation (Qiskit AerSimulator).

Optional precision: "…in quantum reinforcement learning for vehicle routing…".

LITERATURE §F's "L17 not distinguishable from always-ZNE" is also confirmed:
- §7.7 and Table 10: Wilcoxon p = 0.57 against ZNE.
- APGEM reaches 94.2% of the expected-utility oracle reward (0.602 vs 0.639) over 60 held-out conditions.

**(d) Rao et al. (R01): "choose none, dynamical decoupling or ZNE per circuit from circuit and hardware features."**

**CONFIRMED** (abstract via OpenAlex):
- "A deep neural network predicts circuit fidelity and entropy from circuit and hardware features, enabling an online fuzzy-logic policy selector to choose among no mitigation, dynamical decoupling, and zero-noise extrapolation."
- The system runs on a Raspberry Pi 5 edge controller with IBM Quantum hardware and uses an adaptive bias from hardware feedback.
- The abstract does not state what the baselines are, so that cannot be verified.

**(e) Scavino (R03): "argues that mitigation should be selected by downstream decision quality, and finds raw estimation often suffices."**

**CONFIRMED.** Optional hedge: add "in the evaluated regimes". Quotes:
- "select QEM methods through residual gap geometry, not from expectation-value accuracy alone".
- "Decision-aware selection modestly reduces static held-out failure relative to accuracy-based selection, often by retaining Raw, but the dynamic success target is not reached."
- "the experiments repeatedly recommend retaining Raw."

More precise wording: "argues that mitigation should be selected by its effect on downstream decisions rather than expectation-value accuracy, and in the regimes evaluated decision-aware selection often retains the raw (unmitigated) estimate."

**(f) FINAL_REPORT §4: "These works use richer or label-dependent context and compare against fixed policies, not simple rules."**

**NEEDS REWORDING.** The sentence is a blanket statement over five works, and it fails for three of them:
- **Rao et al.** use label-free circuit and hardware features. Their selector is itself a fuzzy-logic rule system.
- **Scavino** is a theory and decision-kernel analysis comparing decision-aware with accuracy-based selection. It is not a learned policy compared against fixed policies.
- **Rahman & Nguyen** compare against fixed-fold ZNE, **grid-search ZNE**, noise-aware (calibration-aware) folding, Adaptive KIK, RL-based mitigation, CDR, VD, PEC and RC. These are not only fixed policies.

It holds for GSC-QEMit (unmitigated / static-severe baselines) and APGEM (fixed techniques plus an oracle). Accurate wording is given in fix F2.

### Additional claim problems found

**(g) Russo et al. (MANUSCRIPT §2 and FINAL_REPORT §4): "show that mitigation can be worse than raw estimation at equal cost".**

**NEEDS REWORDING.** The paper's headline result is the opposite: "error mitigation is on average more beneficial than no error mitigation – even when normalized by the additional resources used". It also stresses dependence on the hardware. Worse-than-raw cases do exist; the body notes that on IonQ Harmony ZNE(R) "was generally worse to use than no error mitigation". But citing Russo for "can be worse at equal cost" without the average finding misrepresents it. See fixes M2 and F1.

**(h) Zhang et al. in the MANUSCRIPT intro: grouped with Scavino as "Decision-aware analyses…".**

**NEEDS REWORDING.** Zhang et al. is a budget-aware, tail-risk and calibration-integrity study. It shows unconstrained ZNE worse than raw on 38–63% of simulated instances under control-offset miscalibration, and on 80–88% of 18 IBM Heron instances. It compares methods at the same online shot budget. It is not a decision-aware analysis. Its use in §2, for shot-budget-matched comparison and worse-than-raw, is fine. See fix M1.

**(i) MANUSCRIPT §2 fraud: "These studies report that classical models remain competitive or better."**

**NEEDS REWORDING.** It is true only for Dinuț et al. (classical AUPRC 0.60–0.74 vs VQC 0.494 and QSVM 0.240). The other studies report otherwise:
- Kyriienko & Magnusson: quantum kernels show better average precision at 20 simulated qubits.
- Li et al.: outperform conventional models by 2.4%.
- Tudisco et al.: better recall than classical methods.
- Das et al.: "competitive accuracies".
- El Alami et al.: the abstract makes no classical comparison.

See fix M5.

**(j) MANUSCRIPT §2: cincio2021machine listed as learning "the mitigation map itself".**

**NEEDS REWORDING.** NACL "outputs an optimized circuit" that is resilient to a device noise model; it is not a mitigation map. See fix M3.

**(k) MANUSCRIPT §1: ZNE "amplifies gate noise, for example by unitary folding … [giurgicatiron2020digital; kim2023scalable]".**

**Minor.** Kim et al. amplify noise by pulse stretching (stretch factors c = 1, 1.3, 1.6). The sentence is hedged ("for example"), so this is optional fix M6.

**(l) Novelty point (i), "these works do not include extra shots … in the same action space".**

**CONFIRMED with a caveat.**
- None of the works has an extra-shots arm.
- GSC-QEMit's MODERATE level is implemented as "replicating circuit sampling and applying majority-vote decoding". That is adjacent to "more sampling", so keep the "to our knowledge" hedge.
- APGEM's context includes the remaining shot budget, but its pool has no extra-shots action.

**(m) Intro claim: "These works typically rely on information unavailable at deployment, such as labels, ideal-state fidelities or simulator noise parameters" [szachara; rahman; majid].**

**CONFIRMED** for all three:
- **GSC-QEMit:** TVD and fidelity to the ideal distribution, and p_eff.
- **Rahman & Nguyen:** loss and accuracy in the context; cross-entropy in the reward.
- **APGEM:** simulator depolarizing and readout levels, unmitigated fidelity, and an approximation ratio relative to the best-known solution.

### Other manuscript and report claims, all CONFIRMED against the abstract or body

- **Cai et al.:** a technique is chosen by the dominant noise ("mitigation methods can be chosen according to the primary type of noise present").
- **Temme et al.:** Richardson extrapolation.
- **Kandala et al.:** hardware ZNE.
- **Kim et al.:** 26 qubits.
- **Giurgica-Tiron et al.:** unitary folding.
- **van den Berg et al.:** PEC with sparse Pauli–Lindblad models; exponential sampling overhead (body).
- **Bravyi et al. and Maciejewski et al.:** readout inversion (tensored or correlated models; detector tomography).
- **Strikis et al.:** compensation learned from near-Clifford variants.
- **Liao et al.:** regression, forests, MLP and GNN that mimic ZNE at lower cost.
- **Dinuț et al.:** same dataset, depolarizing noise, AUPRC primary.
- **Kyriienko & Magnusson:** kernel anomaly detection.
- **El Alami et al., Das et al. and Li et al.:** several noise channels. Li's channels are confirmed from the body.
- **Tudisco et al.:** large private bank dataset.
- **Zhu et al. and Ahmed et al.:** noise can improve some models.
- **Mingue Njiki et al.:** noise-model-dependent mitigation effect, limited benefits.
- **Dal Pozzolo et al.:** dataset source requested by Kaggle; undersampling biases calibration, not ranking.
- **Qiskit / Aer:** citation via Javadi-Abhari et al. is correct.

## 3. Wording fixes

### MANUSCRIPT.md

**M1 (§1, paragraph "Recent work learns such decisions…").** Replace

> They compare against fixed single-technique policies, not against simple observable rules. Decision-aware analyses also suggest that accuracy gains from mitigation need not improve downstream decisions [scavino2026decision; zhang2026worse].

with

> They report gains mainly over fixed (static) mitigation choices and, in one case, over grid-search and other published ZNE variants [rahman2026adaptive]; to our knowledge none compares against a simple observable rule. A decision-aware analysis suggests that accuracy gains from mitigation need not improve downstream decisions [scavino2026decision], and a budget-aware evaluation shows that mitigation can increase error relative to the raw estimate [zhang2026worse].

**M2 (§2, Quantum error mitigation, last bullet).** Replace

> Resource-normalized evaluation of QEM [russo2023testing] and shot-budget-matched comparisons [zhang2026worse] show that mitigation can be worse than raw estimation at equal cost.

with

> A resource-normalized evaluation across hardware platforms finds mitigation beneficial on average but strongly platform-dependent, with some settings worse than no mitigation [russo2023testing]; at a matched online shot budget, unconstrained ZNE can be worse than the raw estimate on a large fraction of instances [zhang2026worse].

**M3 (§2, Learning for QEM).** Remove the third bullet "noise-aware circuit learning [cincio2021machine];" and add after the list:

> Relatedly, noise-aware circuit learning optimizes the circuit itself against a device's noise model [cincio2021machine].

**M4 (§2, Scavino bullet; optional precision).** Replace with

> **Scavino** [scavino2026decision] argues that mitigation should be selected by its effect on downstream decisions rather than by expectation-value accuracy, and finds that, in the regimes evaluated, decision-aware selection often retains the raw estimate.

**M5 (§2, QML for fraud detection).** Replace

> These studies report that classical models remain competitive or better.

with

> Comparisons with classical models are mixed: on the same dataset, tuned classical baselines outperform 4-qubit VQC and quantum-kernel classifiers [dinut2026comparative], whereas other studies report quantum or hybrid models matching or exceeding classical baselines on particular metrics or datasets [kyriienko2022unsupervised; li2025hqrnn; tudisco2024evaluating].

**M6 (§1, optional).** Replace

> which amplifies gate noise, for example by unitary folding, and extrapolates to the zero-noise limit [giurgicatiron2020digital; kim2023scalable]

with

> which amplifies gate noise, for example by pulse stretching [kim2023scalable] or unitary folding [giurgicatiron2020digital], and extrapolates to the zero-noise limit

**M7 (References).** `preskill2018quantum`, `guo2017calibration` and `brier1950verification` are listed but never cited. With BibTeX they will not print unless they are cited or `\nocite`d. Either cite them or drop them. Suggested places:
- "noisy hardware [preskill2018quantum]" in the first sentence of §1;
- "Brier score [brier1950verification]" in §3.6 "Primary endpoint";
- "calibration [guo2017calibration]" where calibration is first discussed (§4.1 or §5).

**M8 (optional, §2 GSC bullet).** Replace "in simulated GHZ, QFT and Grover workloads" with:

> on eight simulated benchmark workloads, including GHZ, QFT and Grover

**M9 (optional, §3.1).** Cite the dataset page `[mlgulb2018creditcardfraud]` next to `[dalpozzolo2015calibrating]` when the dataset is introduced.

### FINAL_REPORT.md §4

**F1.** Replace

> Budget-matched evaluations show mitigation can be worse than raw estimation at equal cost (Russo et al., TQE 2023; Zhang et al., 2026).

with

> Resource-normalized evaluation finds mitigation beneficial on average but platform-dependent (Russo et al., TQE 2023), and at a matched online shot budget unconstrained ZNE can be worse than the raw estimate (Zhang et al., 2026).

**F2.** Replace

> These works use richer or label-dependent context and compare against fixed policies, not simple rules.

with

> The three learned selectors (Szachara et al.; Rahman & Nguyen; Majid et al.) condition on information that is label-dependent or unavailable at deployment (ideal-state fidelity, simulator noise parameters, task loss, accuracy or reward) and report gains mainly over static mitigation choices; to our knowledge none compares against a simple probe-based rule. Rao et al. use label-free circuit and hardware features with a fuzzy-logic selector, and Scavino compares decision-aware with accuracy-based selection rather than learning a policy.

**F3.** Replace

> and similar work exists on other fraud data (El Alami et al., 2026; Tudisco et al., IEEE Access 2024).

with

> El Alami et al. (2026) compare QML architectures on the same dataset and on BankSim, and Tudisco et al. (IEEE Access 2024) report better recall than classical baselines on private bank data.

**F4 (optional).** Replace "a decision-aware analysis showing raw estimation is often adequate (Scavino, 2026)" with:

> a decision-aware analysis in which, in the evaluated regimes, selection often retains the raw estimate (Scavino, 2026)

## 4. Differences from LITERATURE.md

| Row | LITERATURE.md says | Authoritative record says |
|---|---|---|
| L02 (elalami2026comparative) | Title "…of QML architectures for credit-card fraud detection" | "Comparative performance analysis of quantum machine learning architectures for credit card fraud detection". Appl. Intell. **56(3), article 83**. Uses the ULB/European dataset **and** BankSim. |
| L03 (tudisco2024evaluating) | Title "…of the VQC model…" | "…of the Variational Quantum Circuit Model…". IEEE Access **12:102918–102940**. The reported advantage is recall over classical methods. |
| L04 (das2025qfdnn) | 2025, IEEE TCSS | Vol **12(6):5266–5277**, Dec 2025 |
| L07 (zhu2026rethinking) | 2026, APL Comput. Phys. | Vol **2(3), article 030901** (issue dated 2026-09-01, online 2026-09-11) |
| L08 (ahmed2025noisy) | IJCNN 2025 | pp. **1–10** |
| L09 (minguenjiki2026robustness) | arXiv:2604.17515 | The current version is **v2 (2026-07-24)**; 6 authors |
| L11 (kim2023scalable) | 2023, Nat. Phys. | **19(5):752–759**. Noise amplification is by pulse stretching. |
| L12 (vandenberg2023probabilistic) | Title "…sparse Pauli–Lindblad models" | The full title adds "**on noisy quantum processors**". 19(8):1116–1121. |
| L15 (szachara2026gsc) | Title "GSC-QEMit" | The full title is "GSC-QEMit: A Telemetry-Driven Hierarchical Forecast-and-Bandit Framework for Adaptive Quantum Error Mitigation". 6 authors. There are **8** workloads (GHZ/QFT/Grover are 3 of them). Actions are the abstract levels NONE/MODERATE/SEVERE. Still no IJCNN DOI. |
| L16 (rahman2026adaptive) | Title "…Adaptive ZNE…"; [RR] venue "arXiv" | Title "Quantum Noise Mitigation **With Adaptive Zero-Noise Extrapolation**: A Contextual Multi-Armed Bandits Approach". IEEE JSAC **44:5600–5614**, 2026. Baselines include grid-search ZNE, noise-aware folding, Adaptive KIK, RL-based mitigation, CDR, VD, PEC and RC, not only fixed folding. |
| L17 (majid2026context) | "Selects among ZNE, PEC, CDR, readout" | The pool also contains **NoMitigation**. The task is the **Capacitated Vehicle Routing Problem**; the controller is LinUCB. APGEM is not distinguishable from fixed ZNE (Wilcoxon p = 0.57) at 94.2% of oracle reward, which confirms §F. |
| D: kandala2019error | Title as published | Correct. The arXiv version carries a different title, which is not to be used. |
| D: bravyi2021mitigating | "Bravyi et al." | The 4th author is printed "David C. **Mckay**" in Crossref, arXiv and the paper. |
| D: dalpozzolo2015calibrating | IEEE SSCI 2015, 159–166 | Correct. Crossref mis-parses the surname; Kaggle calls the venue "CIDM 2015". |
| D: guo2017calibration | ICML 2017, PMLR 70:1321–1330 | Correct (PMLR page). Editors are Precup and Teh. |
| D: russo2023testing | IEEE TQE (2023) | **Vol 4, pp. 1–18**. Its finding is that mitigation is beneficial on average after resource normalization (platform-dependent), not that it is worse. |
| E R01 (rao2026adaptive) | "DNN-predicted fidelity + fuzzy policy…" | Correct. The DNN also predicts **entropy**. The setup is a Raspberry Pi 5 edge controller with IBM Quantum hardware. The authors are Rao, Indu, B.J., J. |
| E R02 (not cited) | Majid, Sofi, Jabeen, ASOC 187, 114279 (2026) | Correct (Crossref, Feb 2026). The full title is "Noise resilient quantum learning: Adaptive policy guided error mitigation in quantum reinforcement learning for the traveling salesman problem". |
| E R03 (scavino2026decision) | Scavino (2026) | Correct. The author's first name is "**Vicenzo**". The abstract also reports pre-registered device-noise and hardware micro-cell stress tests. |
| E R04 (zhang2026worse) | arXiv:2609.38713 | Correct. 6 authors. Accepted at the NeurIPS 2026 SaTQuML workshop (arXiv comment). |

No identifier in LITERATURE.md was wrong: every DOI and arXiv ID resolved to the stated work.
