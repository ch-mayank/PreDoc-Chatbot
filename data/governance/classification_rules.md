# PreDoc Enterprise Clinical Knowledge Base: Taxonomy, Classification & Routing Matrix

> **Document Type**: Knowledge Engineering Taxonomy & Classification Specification  
> **Version**: 2.2 (Demographic Filtering & Clinical Probing Standard)  
> **Effective Date**: 2026-09-03  
> **Governance Authority**: PreDoc Clinical AI Data Working Group  
> **Clinical Lead**: Mayank Choudhary  

---

## 1. Purpose & Scope

When extracting clinical entities from unstructured medical textbooks (e.g., `Handbook_of_Signs_and_Symptoms.pdf`) or clinical literature, an automated ingestion agent or clinician must deterministically determine:
1. **Which Specialty Category file** in `data/knowledge_base/` the disease belongs to.
2. **What ID Prefix and Number** must be assigned.
3. **How to resolve cross-disciplinary overlap** (e.g., whether *Diabetic Nephropathy* belongs in Endocrine or Renal).
4. **What Triage Priority Tier** must be applied.
5. **How Demographic Matching (Age & Sex)** and **Clinical Probing Questions** are utilized by the conversational chatbot.

---

## 2. Master Category & ID Prefix Registry (20 Clinical Specialties)

Every medical condition MUST be routed to exactly one of the 20 official specialty files in `data/knowledge_base/`:

| # | Specialty Category | Markdown File | ID Prefix | Target Count | Primary Organ / System Scope |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Cardiovascular** | `cardiovascular.md` | `CVD-` | 100 | Heart, coronary arteries, valves, aorta, peripheral vascular, arrhythmias |
| **2** | **Dermatological** | `dermatological.md` | `DERM-` | 100 | Skin, hair, nails, cutaneous immune bullae, severe drug eruptions |
| **3** | **Endocrine & Metabolic** | `endocrine_metabolic.md` | `ENDO-` | 100 | Pituitary, thyroid, adrenals, pancreas, gonads, systemic metabolic crises |
| **4** | **Gastrointestinal** | `gastrointestinal.md` | `GI-` | 100 | Esophagus, stomach, small/large bowel, liver, biliary tree, pancreas |
| **5** | **Hematology & Immunology** | `hematology_immunology.md` | `HEM-` | 100 | Bone marrow, RBCs, WBCs, platelets, coagulation, primary immunodeficiencies |
| **6** | **Infectious & Parasitic** | `infectious_parasitic.md` | `INF-` | 100 | Systemic bacterial, viral, fungal, parasitic, vector-borne, tropical diseases |
| **7** | **Mental & Behavioral** | `mental_behavioral.md` | `MH-` | 100 | Psychiatric disorders, psychosis, mood, anxiety, addiction, personality |
| **8** | **Musculoskeletal** | `musculoskeletal.md` | `MSK-` | 100 | Bones, joints, ligaments, tendons, systemic autoimmune rheumatology |
| **9** | **Neurological** | `neurological.md` | `NEURO-` | 100 | Brain, spinal cord, cranial nerves, peripheral nerves, neuromuscular junction |
| **10** | **Obstetrics & Gynecology** | `obstetrics_gynecology.md` | `OBGYN-` | 100 | Pregnancy, labor, delivery, puerperium, female reproductive organs, contraception |
| **11** | **Oncological (Cancers)** | `oncological.md` | `ONC-` | 100 | Solid tumors, hematologic malignancies, metastatic disease, paraneoplastic |
| **12** | **Ophthalmology & ENT** | `ophthalmology_ent.md` | `HENT-` | 100 | Eyes, orbits, ears, nose, paranasal sinuses, pharynx, larynx, neck spaces |
| **13** | **Pediatrics & Neonatology** | `pediatrics_neonatology.md` | `PED-` | 100 | Neonatal diseases, inborn genetic/developmental conditions in children <18 |
| **14** | **Renal & Urological** | `renal_urological.md` | `REN-` | 100 | Kidneys, nephrons, ureters, bladder, male genitalia, fluid/acid-base |
| **15** | **Respiratory** | `respiratory.md` | `RESP-` | 100 | Upper/lower airways, lungs, pleura, mediastinum, chest wall, gas exchange |
| **16** | **Toxicology & Environmental** | `toxicology_environmental.md` | `TOX-` | 100 | Poisonings, toxidromes, overdoses, envenomations, hyper/hypothermia, barotrauma |
| **17** | **Geriatrics & Age-Related** | `geriatrics_age_related.md` | `GER-` | 100 | Frailty, delirium vs dementia, polypharmacy, falls, sarcopenia, elder syndromes |
| **18** | **Critical Care & Anesthesia** | `critical_care_anesthesia.md` | `ICU-` | 100 | ARDS, septic shock, ventilator emergencies, malignant hyperthermia, resuscitation |
| **19** | **Clinical Genetics & Rare** | `clinical_genetics_rare.md` | `GEN-` | 100 | Chromosomal, single-gene disorders, inborn errors of metabolism, orphan diseases |
| **20** | **Pain & Palliative Care** | `pain_palliative_care.md` | `PAL-` | 100 | Neuropathic pain, complex regional pain, intractable cancer pain, end-of-life care |

---

## 3. Cross-Domain Collision Resolution (Tie-Breaking Rules)

Many clinical conditions affect multiple organ systems. Automated agents MUST use the following hierarchy:

```
                      Is the condition an acute Overdose, Poisoning,
                      Envenomation, or Environmental exposure?
                                    │
                       YES ─────────┴───────── NO
                        │                      │
                        ▼                      ▼
               [TOXICOLOGY]         Is the condition primarily an acute
                                    critical care / ICU ventilator crisis?
                                               │
                                  YES ─────────┴───────── NO
                                   │                      │
                                   ▼                      ▼
                           [CRITICAL CARE]      Is it an active malignancy
                                                or primary neoplasm?
                                                           │
                                              YES ─────────┴───────── NO
                                               │                      │
                                               ▼                      ▼
                                         [ONCOLOGY]         Apply Organ-System
                                                            Rules (Below)
```

### Rule 1: The "Primary Organ / Manifestation" Rule
- **Diabetic Ketoacidosis** ➔ `endocrine_metabolic.md` (Primary endocrine hormone deficit).
- **Diabetic Nephropathy / End-Stage Renal Disease** ➔ `renal_urological.md` (Primary organ failure is kidney).
- **Diabetic Retinopathy** ➔ `ophthalmology_ent.md` (Primary manifestation is ocular).
- **Cardiorenal Syndrome** ➔ `cardiovascular.md` if driven by heart failure; `renal_urological.md` if driven by primary renal failure.

### Rule 2: Multi-System Autoimmune Diseases
- **Systemic Lupus Erythematosus (SLE)** ➔ `hematology_immunology.md` (Systemic immune complex dysregulation).
- **Lupus Nephritis** ➔ `renal_urological.md` (Direct glomerular target).
- **Rheumatoid Arthritis** ➔ `musculoskeletal.md` (Primary articular/synovial target).
- **Giant Cell Arteritis** ➔ `musculoskeletal.md` / `ophthalmology_ent.md` (Systemic vasculitis affecting temporal artery).

### Rule 3: Age-Specific Partitioning
- **Congenital & Neonatal Conditions** occurring exclusively or predominantly in infants/children (<18 yrs) ➔ `pediatrics_neonatology.md`.
- **Syndromes of Aging, Frailty, & Polypharmacy** in older adults (>=65 yrs) ➔ `geriatrics_age_related.md`.

---

## 4. Patient Demographic Matching & Bayesian Filtering

When a user interacts with the PreDoc Chatbot, they provide their **Age**, **Biological Sex / Gender**, and **Symptoms**. The AI uses these inputs as primary Bayesian prior probability filters:

```
+-------------------------------------------------------------------------+
|                  USER INPUT: Age + Gender + Symptoms                    |
+-------------------------------------------------------------------------+
                                     │
                                     ▼
+-------------------------------------------------------------------------+
|                      STEP 1: Demographic Filtering                      |
|  - Exclude anatomical impossibilities (e.g. Ovarian torsion in males)    |
|  - Exclude incompatible age brackets (e.g. Neonatal sepsis in adults)   |
|  - Weight conditions with high demographic predilection (e.g. GCA >50)  |
+-------------------------------------------------------------------------+
                                     │
                                     ▼
+-------------------------------------------------------------------------+
|                    STEP 2: Symptom Vector Matching                      |
|  - Match user symptoms against Primary & Secondary Presentations        |
|  - Retrieve candidate differential diagnoses                            |
+-------------------------------------------------------------------------+
                                     │
                                     ▼
+-------------------------------------------------------------------------+
|              STEP 3: Need Additional Information? (Check Ambiguity)     |
|  - If symptoms match multiple high-acuity conditions:                   |
|    Retrieve 'Clarifying Probing Questions' from Column 10               |
|    Ask 1 to 3 targeted, empathetic follow-up questions                  |
+-------------------------------------------------------------------------+
```

### Demographic Rules:
1. **Absolute Biological Exclusions**:
   - Never consider pregnancy-related conditions (`OBGYN`) in biological males.
   - Never consider prostatic conditions (`BPH`, `Prostate Cancer`) in biological females.
2. **Age-Restricted Syndromes**:
   - `Croup`, `Bronchiolitis`, `Intussusception`, `Pyloric Stenosis` are prioritized in infants and toddlers.
   - `Giant Cell Arteritis`, `Polymyalgia Rheumatica`, `Normal Pressure Hydrocephalus`, `Atypical Silent MI` are prioritized in patients >=50–65 years old.
3. **Sex Predilection Modifiers**:
   - Strongly factor conditions with skewed sex ratios (e.g., Autoimmune diseases in young females 9:1; Gout in adult males 3:1).

---

## 5. Conversational Clinical Probing & Follow-Up Question Engine

When a patient's symptoms are ambiguous, vague, or match multiple competing diagnoses, the AI must NOT guess. Instead, it accesses **Column 10: Clarifying Probing Questions**.

### How the AI Formulates Follow-Up Inquiries:
1. **Rule Out Immediate Red Flags First**:
   - If chest pain is mentioned, immediately ask: *"Does the pain radiate to your arm, neck, or jaw, and are you feeling short of breath, sweaty, or nauseated?"*
2. **Assess Timing, Onset, and Character**:
   - *"Did this pain begin suddenly like a thunderclap, or did it build up gradually over hours or days?"*
3. **Assess Aggravating / Relieving Factors**:
   - *"Does the discomfort get worse when you take a deep breath, cough, or bend forward?"*
4. **Conversational Rules for the Agent**:
   - Ask a **maximum of 2 to 3 questions at one time** to prevent cognitive overload.
   - Use warm, patient-friendly, accessible language.
   - Never provide a definitive diagnosis or prescribe treatment; clearly explain that information is educational.
