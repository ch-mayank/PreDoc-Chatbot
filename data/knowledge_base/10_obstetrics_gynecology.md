---
document_id: KB-OBGYN-2026-V2
category: Obstetrics & Gynecology
document_version: v2.2
effective_date: 2026-09-03
reviewed_by: Mayank Choudhary
source: WHO ICD-10-CM, Clinical Textbooks, Specialty Guidelines
purpose: Enterprise Clinical AI Knowledge Base for Demographic Matching, Symptom Triage, and Active Clinical Probing
---

# Clinical AI Knowledge Base Schema & Triage Taxonomy

### Field Data Dictionary
- **Condition ID**: Unique identifier (`OBGYN-001` to `OBGYN-100`).
- **ICD-10-CM**: Specific diagnostic classification code.
- **Triage Priority Tier**: Level 1 (Red), Level 2 (Yellow), Level 3 (Green).
- **Target Demographics (Age & Sex)**: Standardized age bracket and sex predilection.
- **Primary Presentation**: Hallmark symptoms present in >60% of cases.
- **Secondary / Atypical Presentation**: Non-classic variants in special populations.
- **Risk Factors & Triggers**: Underlying predisposing conditions and acute precipitants.
- **Red Flag / Escalation Markers**: Triggers forcing immediate Triage Tier escalation.
- **Clarifying Probing Questions**: 2 to 4 condition-tailored follow-up questions.
- **Key Differentials**: Overlapping diagnostic vectors used to rule out false positives.

---

# Top 100 Obstetrics & Gynecology Conditions Matrix

| ID | Disease / Condition | ICD-10-CM | Triage Priority Tier | Target Demographics (Age & Sex) | Primary Presentation | Secondary / Atypical Presentation | Risk Factors & Triggers | Red Flag / Escalation Markers | Clarifying Probing Questions | Key Differentials |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OBGYN-001** | Ectopic pregnancy | R69 | Level 1 (Red) | Females (15-49 yrs); 100% Female | Lower abdominal pain may be sharp, dull, or cramping and constant or intermittent in ectopic pregnancy, a potentially li | Atypical presentation with General Clinical Presentation | Prior clinical history, family predilection, acute systemic triggers | Sudden hemodynamic instability, severe intractable symptoms, loss of consciousness | 1) "Have you experienced hallmark signs of Ectopic pregnancy, particularly symptoms typical of ectopic pregnancy?" 2) "Did the onset of Ectopic pregnancy symptoms occur acutely within hours or develop over several days?" 3) "Are you experiencing any red flag warnings such as fever, rapid weight loss, or severe progressive weakness?" | Related Obstetrics & Gynecology disorders, secondary etiologies |
| **OBGYN-002** | Congenital absence of the uterus | R69 | Level 3 (Green) | Adults (18-65 yrs); Equal (1:1) | Primary amenorrhea occurs with congenital absence of the uterus. The patient may develop breasts. | Atypical presentation with General Clinical Presentation | Prior clinical history, family predilection, acute systemic triggers | Progressive symptom severity, failure to improve | 1) "Have you experienced hallmark signs of Congenital absence of the uterus, particularly symptoms typical of congenital absence of the uterus?" 2) "Did the onset of Congenital absence of the uterus symptoms occur acutely within hours or develop over several days?" 3) "Are you experiencing any red flag warnings such as fever, rapid weight loss, or severe progressive weakness?" | Related Obstetrics & Gynecology disorders, secondary etiologies |
| **OBGYN-003** | Uterine hypoplasia | R69 | Level 3 (Green) | Females (15-49 yrs); 100% Female | Primary amenorrhea results from underdevelopment of the uterus, which is detectable on physical examination. Other Cause | Atypical presentation with General Clinical Presentation | Prior clinical history, family predilection, acute systemic triggers | Progressive symptom severity, failure to improve | 1) "Have you experienced hallmark signs of Uterine hypoplasia, particularly symptoms typical of uterine hypoplasia?" 2) "Did the onset of Uterine hypoplasia symptoms occur acutely within hours or develop over several days?" 3) "Are you experiencing any red flag warnings such as fever, rapid weight loss, or severe progressive weakness?" | Related Obstetrics & Gynecology disorders, secondary etiologies |
| **OBGYN-004** | Surgery | R69 | Level 3 (Green) | Adults (18-65 yrs); Equal (1:1) | Surgical removal of both ovaries or the uterus produces amenorrhea. Special Considerations In patients with secondary am | Atypical presentation with General Clinical Presentation | Prior clinical history, family predilection, acute systemic triggers | Progressive symptom severity, failure to improve | 1) "Have you experienced hallmark signs of Surgery, particularly symptoms typical of surgery?" 2) "Did the onset of Surgery symptoms occur acutely within hours or develop over several days?" 3) "Are you experiencing any red flag warnings such as fever, rapid weight loss, or severe progressive weakness?" | Related Obstetrics & Gynecology disorders, secondary etiologies |
| **OBGYN-005** | Preeclampsia | O14.90 | Level 3 (Green) | Adults (18-65 yrs); Equal (1:1) | Clinical entity verified by US National Library of Medicine. Synonyms: Pre eclampsia, Preeclampsia | Atypical presentation with preeclampsia | Prior clinical history, family predilection, acute systemic triggers | Progressive symptom severity, failure to improve | 1) "Have you experienced hallmark signs of Preeclampsia, particularly preeclampsia?" 2) "Did the onset of Preeclampsia symptoms occur acutely within hours or develop over several days?" 3) "Are you experiencing any red flag warnings such as fever, rapid weight loss, or severe progressive weakness?" | Related Obstetrics & Gynecology disorders, secondary etiologies |
| **OBGYN-006** | Pregnancy - ectopic | O00.90 | Level 3 (Green) | Females (15-49 yrs); 100% Female | Clinical entity verified by US National Library of Medicine. Synonyms: pregnancy ectopic, tubal pregnancy | Atypical presentation with ectopic pregnancy | Prior clinical history, family predilection, acute systemic triggers | Progressive symptom severity, failure to improve | 1) "Have you experienced hallmark signs of Pregnancy - ectopic, particularly ectopic pregnancy?" 2) "Did the onset of Pregnancy - ectopic symptoms occur acutely within hours or develop over several days?" 3) "Are you experiencing any red flag warnings such as fever, rapid weight loss, or severe progressive weakness?" | Related Obstetrics & Gynecology disorders, secondary etiologies |
