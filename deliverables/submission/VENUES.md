# Venue options and recommendations

**Researched:** 2026-10-08, from official venue pages where they were reachable. Springer and ACM pages block automated access; for those, Internet Archive snapshots or search-engine extracts were used and the facts are marked *(secondary)*.

**Nothing has been submitted.** Every 2027 date below is unpublished or an estimate from 2025–2026 patterns. Each date is marked **CONFIRM** and must be checked against the venue's official call before it is relied on.

**Paper profile used to judge fit:**
- simulation-only (Qiskit Aer density matrices) with 4-qubit VQCs;
- a pre-registered, sealed one-time held-out test;
- a negative headline: in the studied setting, a two-threshold probe rule performed competitively with pre-specified learned comparators, and two pre-registered gates did not justify training a learned controller;
- no quantum-advantage or hardware claim.

## Recommendation

| Rank | Venue | Why it fits | Main risks |
|---|---|---|---|
| **1** | **TMLR** (*Transactions on Machine Learning Research*; rolling journal) | Acceptance criteria are "claims supported by accurate and convincing evidence" and interest to some readers. Novelty and significance are explicitly not grounds for rejection, which suits a rigorous negative result. Double-blind, **no fees**, arXiv allowed. Main text of 12 pages or less gets 2-week reviews. | ML reviewers need a self-contained quantum primer. Absence-of-effect claims will be probed, so keep the non-superiority margins, intervals and power caveats prominent. TMLR rejects expanded conference papers and anything already in an archival venue. |
| **2** | **IEEE QCE 2027** (Quantum Week): technical paper in the QML or QAPP track, with a poster as the low-risk fallback | The quantum-engineering audience cares about shot and mitigation costs. QCE26 aimed to accept about 40–50%. Full papers are 8–10 pp + 2 pp of references; short papers 4–6 + 1. Proceedings in IEEE Xplore. Single-blind, IEEEtran format. | The **QCE27 call is not published.** QCE26 papers were due Apr 20/27, 2026 and posters Jun 1/Jun 29, 2026. Attendance in person is required. Appendices count toward the page limit. QCE papers *and posters* are archival, which forecloses TMLR. QCE26 desk-rejected "generated papers", so the AI-assistance disclosure needs care. |
| **3** | **Quantum Machine Intelligence** (Springer; rolling journal) | The scope covers exactly "AI for quantum" and "quantum for AI". Hybrid journal, so the subscription route is free. Median first decision 27 days; impact factor 4.4 (2024). No length limit, so the full pre-registration fits in appendices. | The review model (single-blind) and the open-access fee come from secondary sources. LLM use must be documented in Methods (Springer policy). |

**Strong alternative to #2: IEEE QSW 2027** (Quantum Software). Its 2026 call explicitly listed "AI-assisted error mitigation and noise adaptation" and "Negative results, failure analyses, and lessons learned". It is double-blind with regular papers of 7–10 pp. The 2026 deadline was Mar 8, extended to Mar 22, 2026. **2027 dates and location: CONFIRM.**

## Suggested sequences

The two plans share the arXiv step and differ in which peer-reviewed venue comes first.

**Plan A (recommended): arXiv → TMLR, with non-archival visibility in parallel**

1. **Nov–Dec 2026, after the capstone revisions.**
   - Deposit the pre-registrations with an independent timestamp (OSF or Zenodo DOI).
   - Post to arXiv: quant-ph primary, cs.LG cross-list.
   - **Since 2026-01-21, arXiv requires prior arXiv authorship in the domain or a personal endorsement for new submitters.** A faculty mentor with quant-ph papers should submit or endorse.
2. **Dec 2026 – Jan 2027.** Submit to **TMLR** with the main text at 12 pages or less, anonymized.
3. **In parallel, non-archival venues only:**
   - an ICLR 2027 workshop, if a fitting one is accepted (the list is due Nov 29, 2026; suggested contribution deadline Feb 1, 2027 — **CONFIRM**);
   - a 2027 SaTQuML-style workshop;
   - QTML 2027.
4. **If TMLR rejects (around Mar–Apr 2027):** revise and submit to QCE27 (around April 2027 — **CONFIRM**) or to QMI (rolling).

**Plan B: arXiv → QCE27 → extended journal version**

QCE27 full or short paper (around April 2027 — **CONFIRM**), then after the conference an extended version with substantial new material to QMI or IEEE TQE. This forecloses TMLR.

**Avoid:** sending the same results to two archival venues. Archival venues here include TMLR, a QCE paper or poster, QSW, and workshops with archival proceedings such as the earlier AAAI QC+AI workshop (Springer CCIS).

## Other options considered

| Venue | Type | Review | Cost to authors | Fit | Notes |
|---|---|---|---|---|---|
| IEEE QCE 2027 poster | 2-pp paper + poster (archival) | program committee | registration + travel | High (low risk) | QCE26: Jun 1 / Jun 29, 2026 — **CONFIRM** |
| IEEE Trans. Quantum Engineering | journal | single-anonymous | APC US$2,160 on the IEEE list dated 2026-07-30; the TQE site still shows US$1,995 — **CONFIRM** | Medium | natural home for an extended QCE paper |
| ACM Trans. Quantum Computing | journal | single-blind *(secondary)* | ACM Open APC, about $950 / $1,450 subsidized for 2026 *(secondary)*; Yeshiva's ACM Open status unknown | Medium | CS and systems centre of gravity |
| Machine Learning: Science and Technology (IOP) | journal | author's choice | APC US$3,350 | Medium | papers up to 8,500 words; strict data-sharing policy |
| Quantum Information Processing (Springer) | journal | single-blind | free (subscription route) | Medium-Low | LLM use documented in Methods |
| EPJ Quantum Technology | journal | single-anonymous | APC US$2,190 (Nov 2025 snapshot) — **CONFIRM** | Medium-Low | physics-oriented audience |
| Quantum Science and Technology (IOP) | journal | author's choice | free (subscription route) | Low | "highly selective"; broad-impact bar |
| AAAI-27 workshops | workshop | varies | registration | Medium if a QC+AI workshop recurs | author deadline Nov 20, 2026; list by Oct 16, 2026 — **CONFIRM** |
| SaTQuML (NeurIPS 2026) | workshop (non-archival) | double-blind | — | High if repeated | 2026 deadline passed (Sep 5, 2026) |
| ICBINB (negative results) | workshop | — | — | Low | the 2026 edition was LLM-themed |
| *Quantum*, IEEE Access | journal | — | — | Not recommended | very high bar, or last-resort fallback only |

TMLR's reproducibility certification and the NeurIPS reproducibility track are for reproducing *others'* work, so they do not apply.

## Changes the paper needs for each option

- **TMLR:**
  - `tmlr` style, anonymized, with view-only anonymized repository and pre-registration links;
  - main text of 12 pages or less, with the pre-registration, frozen rules and extra tables moved to appendices or supplementary material (up to 100 MB);
  - a short primer on readout mitigation, ZNE and shot cost for ML readers;
  - the non-superiority margin, the raw-versus-material endpoint distinction and the 4-structure interval caveat kept prominent.
- **QCE27:**
  - `IEEEtran` conference format, 10 pt, not anonymized;
  - cut to 8–10 pp + 2 pp of references (or 4–6 + 1 for a short paper), with appendices moved to a DOI-archived repository;
  - the engineering framing led with shots saved against always-mitigate;
  - AI assistance disclosed in the acknowledgments (IEEE policy), with clearly author-produced writing.
- **QMI:**
  - Springer Nature `sn-jnl` template;
  - a Declarations block (funding, competing interests, ethics stating no human subjects, data and code availability, author contributions);
  - LLM use documented in Methods;
  - the full pre-registration in appendices.

## Course (AIM 5008) facts relevant to submission

| Item | Public information | Status |
|---|---|---|
| Course | AIM 5008, Capstone for Artificial Intelligence and Machine Learning, 3 credits, MS in AI ([catalog](https://yu.smartcatalogiq.com/en/current/university-catalog/courses-by-subject-area/aim-artificial-intelligence-machine-learning/5000/aim-5008)) | — |
| Components | A brief proposal and schedule, the main deliverable (a conference paper is an accepted example), and a final presentation, with faculty mentorship | No public rubric, format or length: **CONFIRM** with the instructor |
| Calendar | Fall 2026 classes end **Dec 21, 2026**; Spring 2027 ends May 11, 2027 ([Katz 2026–27 calendar](https://www.yu.edu/sites/default/files/inline-files/Katz%20GP1%202026-27%20Summer%20Fall%20Spring%20Academic%20Calendar%20rev.%200126-2_1.pdf)) | The Dec 8 target falls inside the Fall term; **CONFIRM** the actual presentation date |
| Generative AI | No explicit clause in the Katz graduate catalog; YU policies leave it to the instructor and require disclosure | **CONFIRM** the AIM 5008 policy. The project used an AI assistant extensively, and the paper and report disclose it. |
| Same work in several courses | Needs prior written approval from both faculty members (Katz graduate code of ethics) | Relevant if the work is reused elsewhere |
| Research training | YU requires Responsible Conduct of Research training (CITI) for students before research ([YU RCR](https://www.yu.edu/node/28350)) | **CONFIRM** that both authors have completed it |
| Human subjects | The study uses a public, de-identified (PCA-transformed) transaction dataset and runs only in simulation | **CONFIRM** whether YU wants a "not human-subjects research" determination |
| Dataset licence | Kaggle label: "Database: Open Database, Contents: Database Contents" | Confirm that it permits publishing the results (the repository does not redistribute the data) |

## Key sources

- TMLR: [acceptance criteria](https://jmlr.org/tmlr/acceptance-criteria.html), [author guide](https://jmlr.org/tmlr/author-guide.html), [editorial policies](https://jmlr.org/tmlr/editorial-policies.html)
- IEEE QCE: [QCE26 call for papers](https://qce.quantum.ieee.org/2026/call-for-technical-papers/), [QCE26 deadlines](https://qce.quantum.ieee.org/2026/submission-deadlines/), [QCE26 call for posters](https://qce.quantum.ieee.org/2026/call-for-posters/)
- IEEE QSW: [QSW 2026 call](https://services.conferences.computer.org/2026/qsw/qsw-call-for-papers/)
- QMI: [homepage snapshot, 2026-04-16](http://web.archive.org/web/20260416024338/https://link.springer.com/journal/42484)
- IEEE TQE: [submission process](https://tqe.ieee.org/submission-process/), [IEEE APC list, 2026-07-30](https://journals.ieeeauthorcenter.ieee.org/wp-content/uploads/sites/7/2026-07-30-IEEE-Article-Processing-Charges-List.pdf)
- arXiv: [endorsement policy update, 2026-01-21](https://blog.arxiv.org/2026/01/21/attention-authors-updated-endorsement-policy/)
- Workshops: [ICLR 2027 call for workshops](https://iclr.cc/Conferences/2027/CallForWorkshops), [AAAI-27 workshop call](https://aaai.org/conference/aaai/aaai-27/workshops-call/), [SaTQuML](https://satquml.github.io/)
