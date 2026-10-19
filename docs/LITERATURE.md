# Q-TRACE — Literature and Source Verification Register

| | |
|---|---|
| **Status** | Created 2026-10-06 (Phase 0). **2026-10-08: every §A row was located and its claim checked against the abstract by an AI web check (AGENT-CHECKED); team confirmation is still pending (rule 3).** §D–F added. |
| **Owner** | The separate research/project-guidance workflow (DECISIONS `Q3`). |
| **Source** | [RR] = [`research/deep-research-report.md`](research/deep-research-report.md), SHA-256 `e1a8d071…74f1`. |

## Rules

1. Every row reproduces **only what [RR] states**: title, year/venue and the claim [RR] attributes to the source. The raw citation token is copied verbatim.
2. [RR]'s citation tokens (`citeturn…`, `fileciteturn…`) are opaque export artefacts. They carry **no** DOI, arXiv ID, URL or author list. They must **not** be fabricated, inferred or "repaired" (e.g. by guessing a DOI from a title).
3. A row becomes `VERIFIED` only when the workflow supplies a DOI, arXiv ID or publisher URL **and** a team member confirms that the source says what [RR] claims. A source that exists but says something different is `VERIFIED — CLAIM DIFFERS`, with a note.
4. **Nothing marked UNVERIFIED may be cited in slides, reports or the paper**, and no novelty claim may rest on it.
5. The novelty boundary (PROJECT_SPEC §6) depends most on **L15–L17**. Verify them first.

**Status values:** `UNVERIFIED` · `AGENT-CHECKED` · `VERIFIED` · `VERIFIED — CLAIM DIFFERS` · `NOT FOUND`.

6. **`AGENT-CHECKED`** (E61, 2026-10-08): an AI web check found the identifier on a publisher, arXiv, Crossref or OpenAlex page and read the abstract, which supports the claim. Agent-checked sources may be cited in **drafts** (report, manuscript, slides), each draft carrying the note "references agent-checked; team confirmation pending". A team member must confirm them (→ `VERIFIED`) before any external submission. Exact figures quoted from a paper body (not its abstract) must be re-read first.

## A. Scholarly references ([RR] §Literature matrix and novelty boundary)

The *verified identifier*, *verified by* and *date* columns are empty for every row until verification.

| ID | Title (as written in [RR]) | Year / venue (as claimed) | Claim [RR] attributes to it | [RR] token | Also cited in [RR] at | Status | Verified identifier | Verified by / date |
|---|---|---|---|---|---|---|---|---|
| L01 | Comparative Analysis and Noise Robustness Study of Quantum Kernel Methods and VQCs for Financial Fraud Detection | 2026, *Electronics* | ULB fraud; 4-qubit PCA space; 15 fits; VQC/QSVM vs classical; depolarizing-noise study; AUPRC primary; VQC AUPRC non-monotonic under noise; classical baselines ahead of the small VQC; EfficientSU2/RealAmplitudes VQCs | `citeturn15search1` | Exec. summary; Dataset recommendation; Transaction preprocessing; VQC architecture; Metrics; Main risks | AGENT-CHECKED (team confirmation pending) | DOI 10.3390/electronics15112489 (Dinuț et al., *Electronics* 15(11):2489, 2026) | Claude Code web check, 2026-10-08 |
| L02 | Comparative performance analysis of QML architectures for credit-card fraud detection | 2026, *Applied Intelligence* | VQC, SQNN, EQNN across two fraud datasets; robustness under five noise types | `citeturn15search7` | Exec. summary | AGENT-CHECKED (team confirmation pending) | DOI 10.1007/s10489-026-07110-7; arXiv:2412.19441 (El Alami et al., *Appl. Intell.* 56(3), article 83, 2026; full title "Comparative performance analysis of quantum machine learning architectures for credit card fraud detection"; uses the ULB/European dataset and BankSim) | Claude Code web check, 2026-10-08 |
| L03 | Evaluating the computational advantages of the VQC model in Financial Fraud Detection | 2024, *IEEE Access* | VQC fraud study on a large bank dataset; classical comparisons; NISQ dimensionality reduction | `citeturn3search1` | — | AGENT-CHECKED (team confirmation pending) | DOI 10.1109/ACCESS.2024.3432312 (Tudisco et al., *IEEE Access* 12:102918–102940, 2024; full title "…of the Variational Quantum Circuit Model…"; private bank data; reports better recall than classical methods) | Claude Code web check, 2026-10-08 |
| L04 | QFDNN: A Resource-Efficient Variational Quantum Feature Deep Neural Networks for Fraud Detection and Loan Prediction | 2025, *IEEE TCSS* | Resource-efficient quantum fraud architecture; robustness under six noise models | `citeturn15search0` | — | AGENT-CHECKED (team confirmation pending) | DOI 10.1109/TCSS.2025.3568618; arXiv:2504.19632 (Das et al., *IEEE TCSS* 12(6):5266–5277, Dec 2025) | Claude Code web check, 2026-10-08 |
| L05 | Unsupervised quantum machine learning for fraud detection | 2022, arXiv | Quantum-kernel anomaly detection, simulated up to 20 qubits; average precision emphasized | `citeturn15academia44` | — | AGENT-CHECKED (team confirmation pending) | arXiv:2208.01203 (Kyriienko & Magnusson, 2022) | Claude Code web check, 2026-10-08 |
| L06 | HQRNN-FD: A Hybrid Quantum Recurrent Neural Network for Fraud Detection | 2025, *Entropy* | Hybrid VQC/recurrent model under depolarizing, bit-flip, phase noise | `citeturn15search12` | — | AGENT-CHECKED (team confirmation pending) | DOI 10.3390/e27090906 (Li et al., *Entropy* 27(9):906, 2025) | Claude Code web check, 2026-10-08 |
| L07 | Rethinking noise in quantum machine learning: When noise improves learning | 2026, *APL Computational Physics* | QGNNs: heterogeneous, initialization-dependent noise response; ≈⅓ improved under moderate noise; r = −0.62 between baseline performance and noise benefit | `citeturn19search7` | The hypotheses (H1 motivation) | AGENT-CHECKED (team confirmation pending) | DOI 10.1063/5.0331090 (Zhu et al., *APL Comput. Phys.* 2(3), article 030901, 2026; QGNNs for molecular properties) | Claude Code web check, 2026-10-08 |
| L08 | Noisy HQNNs: A Comprehensive Analysis of Noise Robustness in Hybrid QNNs | 2025, arXiv | Five noise channels; architecture-dependent robustness; some settings benefit from noise | `citeturn18academia36` | — | AGENT-CHECKED (team confirmation pending) | arXiv:2505.03378; DOI 10.1109/IJCNN64981.2025.11229153 (Ahmed et al., IJCNN 2025, pp. 1–10) | Claude Code web check, 2026-10-08 |
| L09 | Robustness Evaluation of HQNNs under Noise Models via System-Level Error Mitigation | 2026, arXiv | Compares ZNE, DDD, LRE, PEC; benefit strongly noise-model- and strength-dependent | `citeturn18academia38` | — | AGENT-CHECKED (team confirmation pending) | arXiv:2604.17515 (Mingue Njiki et al., 2026; current version v2, 2026-07-24; 6 authors; Iris only; mitigation benefits limited) | Claude Code web check, 2026-10-08 |
| L10 | Learning-Based Quantum Error Mitigation | 2021, *PRX Quantum* | Learns a compensation strategy from training circuits; simulated and IBM hardware noise | `citeturn16search1` | — | AGENT-CHECKED (team confirmation pending) | DOI 10.1103/PRXQuantum.2.040330; arXiv:2005.07601 (Strikis et al., 2021) | Claude Code web check, 2026-10-08 |
| L11 | Scalable error mitigation for noisy quantum circuits produces competitive expectation values | 2023, *Nature Physics* | Scalable ZNE up to 26 qubits | `citeturn16search2` | — | AGENT-CHECKED (team confirmation pending) | DOI 10.1038/s41567-022-01914-3; arXiv:2108.09197 (Kim et al., *Nat. Phys.* 19(5):752–759, 2023; noise amplified by pulse stretching) | Claude Code web check, 2026-10-08 |
| L12 | Probabilistic error cancellation with sparse Pauli–Lindblad models | 2023, *Nature Physics* | Practical PEC with learned sparse noise models | `citeturn16search4` | Precise research question; Main risks (PEC overhead) | AGENT-CHECKED (team confirmation pending) | DOI 10.1038/s41567-023-02042-2; arXiv:2201.09866 (van den Berg et al., *Nat. Phys.* 19(8):1116–1121, 2023; full title ends "…sparse Pauli–Lindblad models on noisy quantum processors") | Claude Code web check, 2026-10-08 |
| L13 | Machine learning for practical quantum error mitigation | 2024, *Nature Machine Intelligence* | Linear/RF/MLP/GNN models learn QEM; hardware experiments up to 100 qubits | `citeturn16search0` | Exec. summary | AGENT-CHECKED (team confirmation pending) | DOI 10.1038/s42256-024-00927-2; arXiv:2309.17368 (Liao et al., 2024) | Claude Code web check, 2026-10-08 |
| L14 | Real-time error mitigation for variational optimization on quantum hardware | 2026, *Physical Review Research* | Real-time mitigation integrated with variational optimization on hardware | `citeturn17search0` | — | AGENT-CHECKED (team confirmation pending) | DOI 10.1103/zyb2-zl2d (Robbiati et al., PRR 8:013262, 2026; hardware is single-qubit) | Claude Code web check, 2026-10-08 |
| **L15** | GSC-QEMit | 2026, IJCNN/arXiv | Telemetry + forecasting + cost-aware contextual bandit selects mitigation intensity (GHZ/QFT/Grover) | `citeturn17academia42` | Exec. summary; Overall assessment; Literature matrix; Main risks; Novelty boundary | AGENT-CHECKED (team confirmation pending) — **novelty-critical** | arXiv:2604.24551 (Szachara et al., 2026; full title "GSC-QEMit: A Telemetry-Driven Hierarchical Forecast-and-Bandit Framework for Adaptive Quantum Error Mitigation"; 6 authors; 8 simulated workloads, of which GHZ/QFT/Grover are 3; abstract action levels NONE/MODERATE/SEVERE; IJCNN 2026 per arXiv comment; no Xplore DOI found) | Claude Code web check, 2026-10-08 |
| **L16** | Quantum Noise Mitigation with Adaptive ZNE: A Contextual Multi-Armed Bandits Approach | 2026, arXiv | VQC-aware contextual bandit selects ZNE folding levels; reduced round trips and cost | `citeturn17academia43` | Same as L15 | AGENT-CHECKED (team confirmation pending) — **novelty-critical** | arXiv:2608.06426; DOI 10.1109/JSAC.2026.3721807 (Rahman & Nguyen, IEEE JSAC 44:5600–5614, 2026; full title "Quantum Noise Mitigation With Adaptive Zero-Noise Extrapolation: A Contextual Multi-Armed Bandits Approach"; baselines include grid-search ZNE, noise-aware folding, Adaptive KIK, RL-based mitigation, CDR, VD, PEC and RC, not only fixed folding) | Claude Code web check, 2026-10-08 |
| **L17** | Context-Aware Error Mitigation Orchestration for Hybrid QRL on NISQ Systems | Oct. 2026, arXiv | Selects among ZNE, PEC, CDR, readout using learning-level indicators and utility; near-oracle in QRL | `citeturn17academia44` | Same as L15 | AGENT-CHECKED (team confirmation pending) — **novelty-critical** | arXiv:2610.01253 (Majid, Sofi, Yousuf, 2026; the pool also contains NoMitigation; the task is the Capacitated Vehicle Routing Problem, not TSP (TSP is R02); LinUCB controller; not distinguishable from fixed ZNE, Wilcoxon p = 0.57, at 94.2% of oracle reward) | Claude Code web check, 2026-10-08 |
| L18 | Machine Learning of Noise-Resilient Quantum Circuits | 2021, *PRX Quantum* | ML optimizes circuits against task-specific device noise | `citeturn16search7` | — | AGENT-CHECKED (team confirmation pending) | DOI 10.1103/PRXQuantum.2.010324; arXiv:2007.01210 (Cincio et al., 2021) | Claude Code web check, 2026-10-08 |

## D. Foundational references (AGENT-CHECKED 2026-10-08; team confirmation pending)

| Key | Reference | Identifier | Used for |
|---|---|---|---|
| temme2017error | Temme, Bravyi, Gambetta. Error Mitigation for Short-Depth Quantum Circuits. *PRL* 119, 180509 (2017) | DOI 10.1103/PhysRevLett.119.180509; arXiv:1612.02058 | ZNE (Richardson), quasi-probability cancellation |
| kandala2019error | Kandala et al. Error mitigation extends the computational reach of a noisy quantum processor. *Nature* 567, 491–495 (2019) | DOI 10.1038/s41586-019-1040-7; arXiv:1805.04492 | hardware ZNE |
| giurgicatiron2020digital | Giurgica-Tiron et al. Digital zero noise extrapolation for quantum error mitigation. IEEE QCE 2020, 306–316 | DOI 10.1109/QCE49297.2020.00045; arXiv:2005.10921 | unitary folding (our A2) |
| bravyi2021mitigating | Bravyi et al. Mitigating measurement errors in multiqubit experiments. *PRA* 103, 042605 (2021) | DOI 10.1103/PhysRevA.103.042605; arXiv:2006.14044 | tensored readout inversion (our A1) |
| maciejewski2020mitigation | Maciejewski, Zimborás, Oszmaniec. Mitigation of readout noise ... detector tomography. *Quantum* 4, 257 (2020) | DOI 10.22331/q-2020-04-24-257; arXiv:1907.08518 | readout mitigation |
| cai2023quantum | Cai et al. Quantum error mitigation. *Rev. Mod. Phys.* 95, 045005 (2023) | DOI 10.1103/RevModPhys.95.045005; arXiv:2210.00921 | review; method choice by dominant noise |
| havlicek2019supervised | Havlíček et al. Supervised learning with quantum-enhanced feature spaces. *Nature* 567, 209–212 (2019) | DOI 10.1038/s41586-019-0980-2; arXiv:1804.11326 | VQC / ZZ feature map |
| schuld2020circuit | Schuld et al. Circuit-centric quantum classifiers. *PRA* 101, 032308 (2020) | DOI 10.1103/PhysRevA.101.032308; arXiv:1804.00633 | variational classifiers |
| preskill2018quantum | Preskill. Quantum Computing in the NISQ era and beyond. *Quantum* 2, 79 (2018) | DOI 10.22331/q-2018-08-06-79; arXiv:1801.00862 | NISQ |
| dalpozzolo2015calibrating | Dal Pozzolo et al. Calibrating Probability with Undersampling for Unbalanced Classification. IEEE SSCI 2015, 159–166 | DOI 10.1109/SSCI.2015.33 | dataset; undersampling biases calibration, not ranking |
| brier1950verification | Brier. Verification of forecasts expressed in terms of probability. *Mon. Weather Rev.* 78(1), 1–3 (1950) | DOI 10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2 | Brier score |
| guo2017calibration | Guo et al. On Calibration of Modern Neural Networks. ICML 2017, PMLR 70:1321–1330 | arXiv:1706.04599 | calibration |
| javadiabhari2024quantum | Javadi-Abhari et al. Quantum computing with Qiskit (2024, preprint) | arXiv:2405.08810 | software |
| russo2023testing | Russo et al. Testing platform-independent quantum error mitigation on noisy quantum computers. *IEEE TQE* 4, 1–18 (2023) | DOI 10.1109/TQE.2023.3305232; arXiv:2210.07194 | resource-normalized mitigation evaluation (finds mitigation beneficial on average after resource normalization, platform-dependent; not that it is worse) |

## E. Related work on selecting mitigation per context (AGENT-CHECKED 2026-10-08)

| ID | Reference | Identifier | What it does |
|---|---|---|---|
| R01 | Rao, Indu, B.J., J. (Rao et al.). Adaptive Hardware-Aware QEM Policy Selection Framework on Edge Devices. IEEE I3CTCON 2026 | DOI 10.1109/I3CTCON68242.2026.11508107 | DNN-predicted fidelity and entropy + fuzzy policy choosing none / DD / ZNE per circuit from circuit and hardware features; Raspberry Pi 5 edge controller with IBM Quantum hardware |
| R02 | Majid, Sofi, Jabeen. Noise resilient quantum learning: Adaptive policy guided error mitigation in quantum reinforcement learning for the traveling salesman problem. *Appl. Soft Comput.* 187, 114279 (2026) | DOI 10.1016/j.asoc.2025.114279 | adaptive mitigation selection in QRL for the TSP (abstract not read; described via L17, a separate paper on vehicle routing) |
| R03 | Scavino (first name "Vicenzo" on arXiv). Decision Kernels for Quantum Error Mitigation: Why Accuracy Gains Need Not Improve Downstream Decisions (2026) | arXiv:2607.02888 | theory-based decision-aware selection among Raw / ZNE / CDR / PEC under a shot budget; often retains Raw |
| R04 | Zhang et al. When Error Mitigation Makes Things Worse: Budget-Aware Evaluation, Extrapolation Failure, and the Calibration Trust Boundary (2026; 6 authors; accepted at the NeurIPS 2026 SaTQuML workshop per arXiv comment) | arXiv:2609.38713 | shot-matched comparison; unconstrained ZNE often worse than raw |
| R05 | Sarkar. QBalance: multi-objective workflow for compilation, suppression and mitigation-strategy selection (2026) | arXiv:2605.02966 | per-dataset strategy selection including shot budget |
| R06 | Mitiq Calibrator (software documentation; LaRose et al., *Quantum* 6, 774, 2022, DOI 10.22331/q-2022-08-11-774) | mitiq.readthedocs.io/en/stable/guide/calibrators.html | global (not per-context) choice of ZNE/PEC settings from benchmark circuits |

## F. Novelty boundary (2026-10-08; supersedes the [RR] wording)

**Not new (must not be claimed):** contextual bandits or learned policies for choosing QEM (L15–L17); cost-aware selection among several techniques including "no mitigation" (L17, R01, R02); bandit-tuned mitigation for VQC classifiers (L16); shot-budget-matched comparison of mitigation with raw estimates (R03, R04); downstream-decision-aware method selection (R03).

**Defensible, stated "to our knowledge":** (a) the action space treats *extra shots* as a first-class alternative to mitigation and includes a combined readout + ZNE arm; (b) decisions use only cheap label-free probes and static descriptors, with true noise parameters and labels excluded from policy inputs by a feature-registry guard and tests (L15–L17 use labels, ideal fidelities or simulator parameters; R01 also uses label-free features); (c) evaluation on calibrated fraud-classification decisions across 64 independently trained VQCs with structure-level held-out models; (d) a **pre-registered test of whether a learned policy beats a simple probe rule** — none of L15–L17 compares against a rule baseline, and L17 reports its learned policy is not distinguishable from always-ZNE (confirmed from the full text: Wilcoxon p = 0.57 against ZNE, at 94.2% of the oracle reward).

## B. Non-scholarly sources (documentation, datasets, pricing, hardware)

These support engineering and planning statements, not scientific claims. They still must be checked before being quoted, and many are time-sensitive (prices, quotas, device fleets).

| ID | Subject (as used in [RR]) | Claim [RR] attributes to it | [RR] token(s) | Status |
|---|---|---|---|---|
| S01 | ULB/Kaggle credit-card fraud dataset page | 284,807 transactions, 492 frauds (0.172%); `V1`–`V28` are PCA components; `Time`/`Amount` not transformed; AUPRC recommended; ULB and Kaggle are the same dataset | `citeturn18search0` | AGENT-CHECKED (team confirmation pending; Kaggle API record checked 2026-10-08; Phase 1 records URL, licence, SHA-256) |
| S02 | BankSim analyses | 594,643 simulated transactions, 7,200 frauds | `citeturn18search14` | UNVERIFIED |
| S03 | Kaggle "Transaction Fraud Detection" competition | > 1.4M simulated training transactions; MIT licence | `citeturn18search6` | UNVERIFIED |
| S04 | IBM Quantum error-mitigation documentation (ZNE, PEC, resilience options) | ZNE default 3 noise factors ≈ 3× sampling overhead, not guaranteed unbiased; PEC overhead grows with depth; measurement mitigation and PEC exposed via resilience options | `citeturn20search0`, `citeturn20search1` | UNVERIFIED |
| S05 | Qiskit Aer noise documentation | `NoiseModel`, `depolarizing_error`, `ReadoutError`, `thermal_relaxation_error`, `from_backend`; T2 ≤ 2T1 requirement | `citeturn21search0`, `citeturn21search2`, `citeturn21search9`, `citeturn21search10`, `citeturn21search12` | UNVERIFIED (API behaviour exercised by the Phase 0 smoke test on Aer 0.17.2) |
| S06 | Qiskit Aer GPU packaging | GPU simulator targets CUDA on x86-64 Linux; covers statevector, density-matrix and unitary methods | `citeturn21search1`, `citeturn21search3` | UNVERIFIED |
| S07 | Google Colab resource limits | Resources not guaranteed; limits fluctuate | `citeturn21search4` | UNVERIFIED |
| S08 | Apple M5 Pro specifications | Up to 64 GB unified memory; up to 307 GB/s bandwidth | `citeturn22search0`, `citeturn22search2` | UNVERIFIED (development machine has 24 GB, measured locally) |
| S09 | IBM Quantum Open Plan | Up to 10 QPU minutes per rolling 28-day window; 2026 opt-in promotion | `citeturn14search0` | UNVERIFIED (time-sensitive) |
| S10 | GCP `g2-standard-4` / `g2-standard-8` pricing | ≈ $0.7068/h and ≈ $0.8536/h in one pricing configuration | `citeturn14search2`, `citeturn14search8` | UNVERIFIED (time-sensitive) |
| S11 | IBM processor fleet | Heron r3 systems (`ibm_boston`, `ibm_pittsburgh`, `ibm_aachen`); Nighthawk revisions | `citeturn22search1`, `citeturn22search5` | UNVERIFIED (time-sensitive) |
| S12 | IEEE QCE / Quantum Week call | Accepts peer-reviewed technical work across quantum computing and engineering | `citeturn22search8` | UNVERIFIED |

## C. Internal references

| ID | Reference | Note | Token | Status |
|---|---|---|---|---|
| I01 | Earlier Q-TRACE presentation deck | [RR] says it established the benefit-minus-cost rule and the Never/Always/Fixed/Q-TRACE comparison, and showed "current accuracy" as an input (now forbidden, A12). **Not present in this repository.** Add it to `docs/research/` if it contains requirements. | `fileciteturn0file0` | NOT IN REPOSITORY |

## Verification log

| Date | ID | Result | Identifier | By |
|---|---|---|---|---|
| 2026-10-08 | L01–L18, §D, §E | All located; claims consistent with abstracts (caveats in identifiers column). Status AGENT-CHECKED; team confirmation pending. Exact figures from paper bodies (L15–L17, R03) to be re-read before quoting. | see rows | Claude Code (web check: arXiv, Crossref, OpenAlex, publisher pages) |
| 2026-10-08 | L02–L17, §D russo2023testing, §E R01–R04, S01 | Bibliographic metadata re-checked against Crossref, arXiv, DataCite, OpenAlex, PMLR, Europe PMC and the Kaggle API; corrected titles, volumes, pages and claim notes added to the rows above (status wording unchanged). L15–L17 and R03 were re-read in full text. The dataset page (S01) was located as Kaggle `mlg-ulb/creditcardfraud`, version 3, and is cited in the manuscript as `mlgulb2018creditcardfraud`. Details: `deliverables/paper/REFERENCES_VERIFICATION.md`. | see rows | Claude Code (bibliography verification) |
