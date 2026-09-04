# PreDoc Enterprise Clinical Knowledge Base: Canonical Extraction Contract & Schema Template

> **Document Type**: Knowledge Engineering Specification & Ingestion Agent Contract  
> **Version**: 2.2 (Demographic & Clinical Probing Standard)  
> **Effective Date**: 2026-09-03  
> **Governance Authority**: PreDoc Clinical AI Data Working Group  
> **Clinical Lead**: Mayank Choudhary  
> **Single Source of Truth (SSOT)**: This document is the sole official template for all clinical knowledge representations in PreDoc.  

---

## 1. Document Purpose & Architectural Standard

This document establishes the **single industry-standard contract** for all clinical condition datasets in the PreDoc ecosystem. 

In clinical decision support systems (such as NHS Pathways, Ada Health, and BMJ Best Practice), an effective triage AI requires more than just static disease descriptions—it must actively use the patient's **Age**, **Biological Sex/Gender**, and **Symptoms**, and dynamically guide the conversational agent on **what targeted follow-up questions to ask** when symptoms are underspecified.

Any automated LLM ingestion agent, clinician, or data engineer creating or updating knowledge files in `data/knowledge_base/` MUST adhere strictly to this 11-column matrix specification.

---

## 2. Standard Knowledge Base Document Structure

Every file in `data/knowledge_base/` must be a UTF-8 encoded Markdown document composed of:
1. **YAML Frontmatter Block** (Metadata header delimited by `---`).
2. **Clinical AI Knowledge Base Schema & Field Data Dictionary**.
3. **11-Column Clinical Conditions Matrix** (Single Markdown table).

```
+-------------------------------------------------------------+
|                     YAML Frontmatter Block                  |
|  (document_id, category, version, review, source, purpose)  |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|              Clinical Triage & Field Data Dictionary        |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|             11-Column Clinical Conditions Matrix            |
|  | ID | Disease | ICD-10 | Tier | Demographics | Primary |  |
|  | Secondary | Risk | Red Flags | Probing Qs | Differentials|
+-------------------------------------------------------------+
```

---

## 3. Required YAML Frontmatter Schema

Each document must begin on line 1 with `---` and contain the following metadata:

```yaml
---
document_id: KB-[PREFIX]-2026-V2
category: [Official Specialty Category Name]
document_version: v2.2
effective_date: 2026-09-03
reviewed_by: Mayank Choudhary
source: [Primary Clinical Practice Guidelines / CDC / WHO / Specialty Societies]
purpose: Enterprise Clinical AI Knowledge Base for Demographic Matching, Symptom Triage, and Active Clinical Probing
---
```

---

## 4. The 11-Column Clinical Matrix Data Dictionary

Every knowledge base file contains exactly one Markdown table with these 11 columns:

| Column # | Field Name | Data Type | Required | Description & Constraints |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **ID** | String | Yes | Unique condition code bolded: `**[PREFIX]-[001..100]**`. Must be sequentially ordered. |
| **2** | **Disease / Condition** | String | Yes | Formal clinical diagnosis name, followed by major eponyms, classification subtypes, or staging in parentheses. |
| **3** | **ICD-10-CM** | String | Yes | Valid WHO / CMS ICD-10-CM code (e.g., `I21.09`, `E11.01`, `J44.1`). |
| **4** | **Triage Priority Tier** | Enum | Yes | Exactly one of: `Level 1 (Red)`, `Level 2 (Yellow)`, or `Level 3 (Green)`. |
| **5** | **Target Demographics (Age & Sex)** | String | Yes | Specific age bracket and biological sex predilection (e.g., `Older Adults (>=65 yrs); Male > Female (2:1)` or `Reproductive Age Females (15-45 yrs); Female-exclusive`). |
| **6** | **Primary Presentation** | Text | Yes | Cardinal symptoms, signs, and physical findings present in >60% of patients. |
| **7** | **Secondary / Atypical Presentation** | Text | Yes | Less common presentations, prodromal signs, and atypical manifestations in special populations (females, diabetics, pediatrics, geriatrics). |
| **8** | **Risk Factors & Triggers** | Text | Yes | Pathophysiological causes, underlying comorbidities, genetic predispositions, medications, or acute precipitants. |
| **9** | **Red Flag / Escalation Markers** | Text | Yes | Explicit clinical triggers requiring immediate emergency escalation, diagnostic red flags, or complications. |
| **10** | **Clarifying Probing Questions** | Text | Yes | **2 to 4 high-yield, patient-friendly questions** the AI must ask to confirm or rule out the condition when symptoms are non-specific. |
| **11** | **Key Differentials** | Text | Yes | Comma-separated list of 4–6 overlapping conditions that the AI diagnostic engine must distinguish. |

---

## 5. Demographic Standardization Guidelines

When specifying **Target Demographics (Age & Sex)** in Column 5, use standardized clinical brackets:

### Standardized Age Brackets:
- `Neonates`: 0 to 28 days
- `Infants`: 1 to 12 months
- `Toddlers / Young Children`: 1 to 5 years
- `School-Age Children`: 6 to 12 years
- `Adolescents`: 13 to 18 years
- `Young Adults`: 18 to 39 years
- `Middle-Aged Adults`: 40 to 64 years
- `Older Adults / Geriatrics`: >=65 years (or >=75 years for very elderly)
- `All Ages`: Conditions with no distinct age predilection

### Standardized Sex Predilections:
- `Female-exclusive`: Anatomically or physiologically restricted to biological females (e.g., Ectopic Pregnancy, Ovarian Torsion, Cervical Cancer).
- `Male-exclusive`: Anatomically restricted to biological males (e.g., Benign Prostatic Hyperplasia, Testicular Torsion, Prostate Cancer).
- `Female predominance (X:Y)`: Higher incidence in females (e.g., `Female > Male (9:1)` for SLE, `Female > Male (3:1)` for Hashimoto's).
- `Male predominance (X:Y)`: Higher incidence in males (e.g., `Male > Female (4:1)` for Pyloric Stenosis, `Male > Female (2:1)` for Gout).
- `Equal (1:1)`: No significant biological sex disparity.

---

## 6. Clinical Probing Questions Guidance

Column 10 specifies **Clarifying Probing Questions** for the conversational agent. The AI should formulate follow-up questions following these clinical interviewing standards:

1. **Patient-Friendly Language**: Convert complex medical concepts into clear, empathetic questions (e.g., instead of "Do you have orthopnea?", ask: *"Do you need to prop yourself up with extra pillows to breathe comfortably while lying flat in bed?"*).
2. **Focused & High-Yield**: Target the single most distinguishing clinical feature (e.g., radiation of pain, sudden vs. gradual onset, relation to food/exertion).
3. **Red Flag Screening**: Always include at least one question probing for life-threatening instability (e.g., *"Are you experiencing any shortness of breath, dizziness, cold sweating, or feeling like you might faint?"*).
4. **Numbering & Structure**: Format questions as numbered inquiries:
   `1) [Onset/Radiation/Character question] 2) [Aggravating/Relieving question] 3) [Red Flag/Associated symptom question]`

---

## 7. Automated Agent Extraction System Prompt (Copy/Paste Ready)

When an AI Ingestion Agent reads a source text (e.g., `Handbook_of_Signs_and_Symptoms.pdf`), inject this prompt:

```markdown
SYSTEM PROMPT: CLINICAL KNOWLEDGE EXTRACTION & PROBING AGENT

You are an expert Clinical Decision Support Architect.
Extract medical conditions from the source text and output valid rows adhering strictly to the PreDoc 11-Column Clinical Matrix.

### EXTRACTION RULES:
1. ID: Generate sequentially using target specialty prefix: [PREFIX]-[XXX].
2. DISEASE / CONDITION: Official nomenclature + prominent eponyms/subtypes.
3. ICD-10-CM: Exact diagnostic code.
4. TRIAGE PRIORITY TIER: Strictly "Level 1 (Red)", "Level 2 (Yellow)", or "Level 3 (Green)".
5. TARGET DEMOGRAPHICS (AGE & SEX): Specify standardized age bracket and sex predilection (e.g., "Older Adults >=65 yrs; Male > Female (2:1)").
6. PRIMARY PRESENTATION: Hallmark symptoms present in >60% of cases.
7. SECONDARY / ATYPICAL PRESENTATION: Atypical presentations in females, diabetics, pediatrics, and geriatrics.
8. RISK FACTORS & TRIGGERS: Predisposing conditions, genetics, and acute triggers.
9. RED FLAG / ESCALATION MARKERS: Acute decompensation triggers requiring immediate emergency escalation.
10. CLARIFYING PROBING QUESTIONS: 2 to 4 concise, patient-friendly follow-up questions for the chatbot to ask the user.
11. KEY DIFFERENTIALS: 4 to 6 overlapping conditions to rule out.
12. OUTPUT FORMAT: A single Markdown table row:
| **[ID]** | [Disease] | [ICD] | [Tier] | [Demographics] | [Primary] | [Secondary] | [Risk] | [Red Flags] | [Probing Qs] | [Differentials] |
```

---

## 8. Quality Assurance & Validation Checklist

- [ ] Single canonical template file (`template.md`) maintained in `data/governance/`.
- [ ] Table has exactly 11 columns per row.
- [ ] Target Demographics specifies both Age bracket and Sex predilection.
- [ ] Clarifying Probing Questions contains 2–4 numbered, patient-friendly clinical questions.
- [ ] No empty cells or unclosed pipes.
- [ ] Changes logged in `data/version_log.md`.
