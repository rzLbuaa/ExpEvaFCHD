# ExpEvaFCHD

**ExpEvaFCHD** is a *training-free, on-premise structured-evidence closed-loop* framework for prenatal fetal congenital heart disease (FCHD) screening with large language models (LLMs). It improves robustness without fine-tuning by (i) **column-wise alignment** of heterogeneous fetal echocardiography measurements, (ii) **local similar-case retrieval** from an institution-controlled expert casebase (**FetalCardioDB**), and (iii) **evidence-aligned constrained generation** with traceable attribution so that diagnostic statements are grounded in retrievable local evidence.

This repository provides:
- **ExpEvaFCHD_main.py**: end-to-end inference pipeline (alignment → retrieval → aggregation → constrained generation → structured outputs + attribution)
- **ExpEvaFCHD_eval.py**: evaluation utilities used in the paper
- **Structured Data Standard Template with Expert Diagnosis.xlsx**: canonical schema template for structured measurements + expert reports
- **Detailed Classification of Fetal Congenital Heart Disease in This Study (Updated January 2026).pdf**: disease subtype taxonomy used for evaluation
- **Supplementary Material.zip**: supplementary figures/examples
- **requirements_main.txt / requirements_text_eval.txt**: dependency sets for inference and evaluation

> **Clinical disclaimer:** This code is for research and auditing purposes only. It is **not** a certified medical device and must not be used as the sole basis for clinical decision-making.

---

## Repository Structure

- `ExpEvaFCHD_main.py`  
  Main pipeline: schema alignment → evidence retrieval → polarity-controlled aggregation → evidence-closed constrained generation → structured output + attribution.

- `ExpEvaFCHD_eval.py`  
  Evaluation pipeline (text quality + task metrics) consistent with the paper.

- `Structured Data Standard Template with Expert Diagnosis.xlsx`  
  Template to build local casebases and to standardize query inputs.

- `Detailed Classification of Fetal Congenital Heart Disease in This Study (Updated January 2026).pdf`  
  Disease subtype definitions used for lesion-set/subtype evaluation.

- `requirements_main.txt`, `requirements_text_eval.txt`  
  Python dependencies for the two modules.

- `Supplementary Material.zip`  
  Supplementary examples/figures referenced by the paper.

- `LICENSE`

---

## Environment Setup

### 1) Create a virtual environment

Using conda:
```bash
conda create -n expeva_fchd python=3.10 -y
conda activate expeva_fchd
```

Or using venv:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows PowerShell
```

### 2) Install dependencies

Inference:
```bash
pip install -r requirements_main.txt
```

Evaluation:
```bash
pip install -r requirements_text_eval.txt
```

---

## Data Preparation (FetalCardioDB)

ExpEvaFCHD assumes each case contains:
- a **structured measurement record** (up to 52 fetal echocardiography measurement fields; missingness allowed), and
- a corresponding **expert report** and labels (screening label + optional lesion set).

Use **`Structured Data Standard Template with Expert Diagnosis.xlsx`** as the canonical schema:
1. Populate your local expert casebase (historical cases) following the template columns.
2. Populate evaluation/query cases using the same schema.
3. Keep **unique case identifiers** and avoid duplicates across splits.

### Leakage control
To avoid hidden leakage when the retrieval base and evaluation cohorts come from related sources:
- enforce **patient-level** or **pregnancy-level** de-duplication when multiple exams exist,
- apply a clear **time split** if the study design is time-based,
- keep split manifests (case ID lists) and report the policy (near-duplicate matching, repeated exams, etc.).

---

## Running ExpEvaFCHD Inference

ExpEvaFCHD supports different deployment settings (fully local LLM, or a generic API endpoint). The inference script is designed to be driven by **configuration and command-line arguments**.

### 1) Inspect options
```bash
python ExpEvaFCHD_main.py --help
```

### 2) Typical workflow (conceptual)
1. **Column-wise alignment**: map raw measurement fields to a canonical schema
2. **Top-K retrieval**: retrieve similar cases from the local casebase in a weighted normalized space
3. **Evidence aggregation**: extract/compact evidence with polarity control (negation-aware cue handling)
4. **Constrained generation**: produce
   - screening decision (negative/positive)
   - lesion-set differential diagnosis (for positives)
   - auditable narrative with attribution to measurements and/or retrieved cases

### 3) Local vs API-backed LLM
- **Local LLM deployment** is recommended for strict on-premise governance.
- If a hosted API is used, follow institutional policies for de-identification and ensure that **case evidence** does not leave the permitted boundary.

---

## Running Evaluation

### 1) Inspect options
```bash
python ExpEvaFCHD_eval.py --help
```

### 2) Metrics reported
The evaluation code focuses on the paper’s metrics:
- **Text agreement** between generated vs expert reports:
  - Cosine similarity
  - TF–IDF cosine similarity
  - Relevance
  - Informativeness
  - Validity (entailment probability)
- **Case-level screening**: negative vs positive accuracy
- **Lesion-set differential diagnosis**:
  - micro sensitivity / set-level recall
  - mean Jaccard (optionally stratified by complexity)
- **Disease subtype** sensitivity using the taxonomy in `Detailed Classification ... (Updated January 2026).pdf`

---

## Key Design Choices

- **Training-free**: no parameter updates to the base LLM.
- **On-premise evidence closure**: retrieval and evidence assembly operate on an institution-controlled casebase.
- **Measurement-first control signal**: robustness is anchored in structured measurement alignment and similarity retrieval.
- **Auditable outputs**: generation is constrained to evidence, with attribution linking statements to aligned fields and/or retrieved cases.
- **Site-configurable retrieval**: feature weights and retrieval thresholds are configurable to match local protocols and prevalence.

---
