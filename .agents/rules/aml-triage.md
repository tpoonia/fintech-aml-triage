---
trigger: always_on
description: Project conventions for the AML alert triage pipeline and investigator tools.
---

# AML Alert Triage Project Rules

- Follow the existing patterns in the specific pipeline, API, or dashboard component being changed. Verify the target component's actual interfaces before changing it.
- Treat alert scores and model explanations as decision support for investigators, not as determinations that a customer or transaction is suspicious. Preserve human review and avoid language that implies a score alone proves wrongdoing.
- Keep the hidden `is_suspicious` ground-truth field out of model features and training inputs. Use it only where existing synthetic-data workflows require it to generate evaluation or investigation outcomes.
- Use synthetic data for development and tests. Do not add credentials, real customer or transaction data, or generated datasets and model artifacts to version control.
- Preserve reproducibility and traceability: follow existing seed, provenance, and artifact-handling conventions when changing data generation, training, scoring, or evaluation.
- Add or update focused tests for behavior changes, and follow the commands and environment requirements documented in `README.md` and `requirements.txt`.
