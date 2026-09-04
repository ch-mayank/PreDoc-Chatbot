# PreDoc Enterprise Clinical Knowledge Base: Master Version Log & Provenance Audit Trail

> **Document Type**: Regulatory Audit Trail & Clinical Knowledge Provenance Log  
> **Current Version**: v2.2 (Demographic & Clinical Probing Matrix)  
> **Last Updated**: 2026-09-03  
> **Governance Authority**: PreDoc Clinical AI Data Working Group  
> **Clinical Lead**: Mayank Choudhary  

---

## 1. Governance Policy & Provenance Requirements

In healthcare and clinical decision-support AI, **traceability and provenance are mandatory**. Every modification, addition, or deprecation of clinical content in `data/knowledge_base/` must be logged in this audit trail.

### Mandatory Log Attributes:
- **Release Version**: Semantic versioning (`v1.0`, `v2.0`, `v2.1`, `v2.2`).
- **Date**: ISO-8601 date (`YYYY-MM-DD`).
- **Target File**: Specific category markdown file modified.
- **Condition ID(s)**: Range or list of IDs affected (`CVD-001..100`).
- **Action**: One of `ADD`, `MODIFY`, `DEPRECATE`, `MIGRATE`.
- **Source Citation**: Precise origin (e.g., `Handbook_of_Signs_and_Symptoms.pdf`, Page 142; or clinical guideline).
- **Reviewer / Agent ID**: Identity of human clinical reviewer or automated agent.
- **Clinical Justification**: Clinical rationale for change, update, or escalation tier adjustment.

---

## 2. Release History Summary

| Release | Effective Date | Categories Count | Conditions Count | Lead Reviewer | Major Milestones |
| :---: | :---: | :---: | :---: | :--- | :--- |
| **v1.0** | 2026-08-15 | 2 | ~150 | Clinical Team | Initial baseline prototype (`Cardiovascular`, `Dermatological`). |
| **v2.0** | 2026-09-01 | 16 | 1,600 | Mayank Choudhary | Enterprise expansion to 16 medical specialties with exactly 100 conditions each; standardized 9-column triage matrix and YAML frontmatter. |
| **v2.1** | 2026-09-03 | 16 | 1,600 | Mayank Choudhary | Restructured `data/` into 3 clean layers (`governance/`, `sources/raw_pdfs/`, `knowledge_base/`). Standardized POSIX snake_case filenames. |
| **v2.2** | 2026-09-03 | 20 | 2,000 | Mayank Choudhary | Upgraded to 11-column clinical matrix adding `Target Demographics (Age & Sex)` and `Clarifying Probing Questions` across all 20 specialties (2,000 conditions). Enforced single canonical `template.md` as industry standard (removed redundant `template.yaml`). |

---

## 3. Comprehensive Change & Ingestion Log

### Release v2.2 (2026-09-03) — 11-Column Matrix, Demographics & Probing Engine Upgrade (20 Specialties / 2,000 Conditions)

| Date | File Affected | IDs Affected | Action | Source Citation | Reviewer / Agent | Clinical Justification & Summary |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| 2026-09-03 | `governance/template.md` | All | `MODIFY` | Single Source of Truth Standard | Mayank Choudhary | Upgraded schema to 11 columns adding `Target Demographics (Age & Sex)` and `Clarifying Probing Questions`. |
| 2026-09-03 | `governance/template.yaml` | All | `DEPRECATE` | Clean Architecture (No Duplicates) | Mayank Choudhary | Deleted redundant YAML template to maintain `template.md` as sole authoritative industry standard. |
| 2026-09-03 | `governance/classification_rules.md` | All | `MODIFY` | Internal Governance | Mayank Choudhary | Added Bayesian Demographic Filtering rules, Probing Question engine, and 20-specialty taxonomy. |
| 2026-09-03 | `knowledge_base/geriatrics_age_related.md` | `GER-001..100` | `ADD` | AGS Beers Criteria, Geriatric Syndromes Guidelines | Mayank Choudhary | Added 100 geriatric conditions covering frailty, delirium, falls, polypharmacy, atypical presentations in 11 columns. |
| 2026-09-03 | `knowledge_base/critical_care_anesthesia.md` | `ICU-001..100` | `ADD` | SCCM Surviving Sepsis, ASA Difficult Airway Standards | Mayank Choudhary | Added 100 intensive care conditions covering ARDS, septic shock, ventilator emergencies, malignant hyperthermia in 11 columns. |
| 2026-09-03 | `knowledge_base/clinical_genetics_rare.md` | `GEN-001..100` | `ADD` | ACMG Practice Guidelines, OMIM, Orphanet | Mayank Choudhary | Added 100 genetic and rare diseases covering inborn errors of metabolism, connective tissue, storage disorders in 11 columns. |
| 2026-09-03 | `knowledge_base/pain_palliative_care.md` | `PAL-001..100` | `ADD` | IASP Pain Taxonomy, NCCN Palliative Care Standards | Mayank Choudhary | Added 100 conditions covering neuropathic pain, CRPS, palliative symptom management, end-of-life crises in 11 columns. |
| 2026-09-03 | `knowledge_base/*.md` (16 core) | All (1,600) | `SCHEMA_UPGRADE` | Clinical AI Interviewing Guidelines | Mayank Choudhary | Upgraded all 16 core knowledge base tables to include Demographic brackets and targeted follow-up probing questions. |

---

### Release v2.1 (2026-09-03) — Directory Architecture Standardization

| Date | File Affected | IDs Affected | Action | Source Citation | Reviewer / Agent | Clinical Justification & Summary |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| 2026-09-03 | `data/` layout | All | `MIGRATE` | Industry Standard Medallion Pattern | Mayank Choudhary | Separated concerns into `governance/`, `sources/raw_pdfs/`, and `knowledge_base/`. |
| 2026-09-03 | `sources/raw_pdfs/` | Reference PDFs | `MIGRATE` | Isolated Storage | Mayank Choudhary | Moved `Handbook_of_Signs_and_Symptoms.pdf` and `professional-guide-to-signs-and-symptoms-6th-edition.pdf` out of RAG ingestion path. |
| 2026-09-03 | `sources/source_catalog.json` | All Sources | `ADD` | Source Tracking | Mayank Choudhary | Created machine-readable catalog of source reference textbooks. |
| 2026-09-03 | `knowledge_base/*.md` | 16 files | `MIGRATE` | POSIX snake_case Standard | Mayank Choudhary | Converted file names to lowercase snake_case for Docker and cross-platform reliability. |

---

### Release v2.0 (2026-09-01) — Enterprise Standardization to 16 Categories (1,600 Conditions)

| Date | File Affected | IDs Affected | Action | Source Citation | Reviewer / Agent | Clinical Justification & Summary |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| 2026-09-01 | `cardiovascular.md` | `CVD-001..100` | `ADD` | AHA/ACC Guidelines, WHO ICD-10-CM | Mayank Choudhary | Standardized to 100 entries: ACS, dissection, shock, electrophysiology. |
| 2026-09-01 | `dermatological.md` | `DERM-001..100` | `ADD` | AAD Guidelines, Fitzpatrick Dermatology | Mayank Choudhary | Standardized to 100 entries: SJS/TEN, DRESS, autoimmune bullous, infectious rashes. |
| 2026-09-01 | `endocrine_metabolic.md` | `ENDO-001..100` | `ADD` | ADA Standards of Care, Endocrine Society | Mayank Choudhary | Full 100 entries: DKA, HHS, thyroid storm, myxedema, adrenal crisis. |
| 2026-09-01 | `gastrointestinal.md` | `GI-001..100` | `ADD` | ACG / AGA Clinical Practice Guidelines | Mayank Choudhary | Full 100 entries: Acute abdomen, peritonitis, variceal bleeding, liver failure. |
| 2026-09-01 | `hematology_immunology.md` | `HEM-001..100` | `ADD` | ASH Guidelines, AAAAI Standards | Mayank Choudhary | Full 100 entries: TTP-HUS, DIC, sickle cell, hemophilia, hereditary angioedema. |
| 2026-09-01 | `infectious_parasitic.md` | `INF-001..100` | `ADD` | IDSA Guidelines, CDC / WHO Infectious Standards | Mayank Choudhary | Full 100 entries: Sepsis, viral fevers, malaria, rabies, opportunistic bugs. |
| 2026-09-01 | `mental_behavioral.md` | `MH-001..100` | `ADD` | APA DSM-5-TR, NICE Guidelines | Mayank Choudhary | Full 100 entries: Suicidal crises, catatonia, psychosis, affective, addictions. |
| 2026-09-01 | `musculoskeletal.md` | `MSK-001..100` | `ADD` | ACR Guidelines, AAOS Orthopedic Standards | Mayank Choudhary | Full 100 entries: Compartment syndrome, necrotizing fasciitis, vasculitides. |
| 2026-09-01 | `neurological.md` | `NEURO-001..100` | `ADD` | AAN Practice Guidelines, Neurocritical Care | Mayank Choudhary | Full 100 entries: Stroke, status epilepticus, hemorrhages, GBS, myasthenia. |
| 2026-09-01 | `obstetrics_gynecology.md` | `OBGYN-001..100` | `ADD` | ACOG Practice Bulletins, FIGO Standards | Mayank Choudhary | Full 100 entries: Ectopic pregnancy, eclampsia, HELLP, abruption, torsion. |
| 2026-09-01 | `oncological.md` | `ONC-001..100` | `ADD` | ASCO / NCCN Clinical Guidelines | Mayank Choudhary | Full 100 entries: Tumor lysis syndrome, cord compression, solid tumors, leukemias. |
| 2026-09-01 | `ophthalmology_ent.md` | `HENT-001..100` | `ADD` | AAO Preferred Practice Patterns, AAO-HNS | Mayank Choudhary | Full 100 entries: Angle-closure glaucoma, CRAO, retinal detachment, Ludwig. |
| 2026-09-01 | `pediatrics_neonatology.md` | `PED-001..100` | `ADD` | AAP Clinical Guidelines, Nelson Pediatrics | Mayank Choudhary | Full 100 entries: Neonatal sepsis, HIE, NEC, congenital heart, pyloric stenosis. |
| 2026-09-01 | `renal_urological.md` | `REN-001..100` | `ADD` | KDIGO Clinical Practice Guidelines, AUA | Mayank Choudhary | Full 100 entries: AKI, glomerulonephritis, nephrotic syndrome, torsion, Fournier. |
| 2026-09-01 | `respiratory.md` | `RESP-001..100` | `ADD` | ATS / ERS / GOLD Guidelines | Mayank Choudhary | Full 100 entries: Tension pneumothorax, pulmonary embolism, ARDS, asthma. |
| 2026-09-01 | `toxicology_environmental.md` | `TOX-001..100` | `ADD` | ACMT Standards, CDC ATSDR Guidelines | Mayank Choudhary | Full 100 entries: Toxidromes, drug overdoses, antidotes, heavy metals, bites. |

---

### Release v1.0 (2026-08-15) — Initial Knowledge Base Prototype

| Date | File Affected | IDs Affected | Action | Source Citation | Reviewer / Agent | Clinical Justification & Summary |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- |
| 2026-08-15 | `Cardiovascular.md` | Variable | `ADD` | WHO Reference Data | Initial Build | Foundational cardiovascular symptoms and diagnoses. |
| 2026-08-15 | `Dermatological.md` | Variable | `ADD` | WHO Reference Data | Initial Build | Foundational dermatological presentations and lesions. |
