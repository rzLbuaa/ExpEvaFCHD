# ExpEvaFCHD

**Expert Evaluation of Fetal Congenital Heart Disease Risk**

ExpEvaFCHD combines structured fetal echocardiographic measurements with expert case evidence for screening support and report composition. Its four stages are deterministic field alignment, similar-case retrieval, polarity-controlled evidence aggregation and evidence-aligned constrained generation. The base language model is not fine-tuned. The workflow is described in the [manuscript, pp. 30–32](references/ExpEvaFCHD_Manuscript.pdf#page=30).

**This public repository is an illustrative pseudocode release.** It contains algorithm outlines, data contracts, configurations and explicitly synthetic examples. The complete, detailed implementation is available from the corresponding authors upon reasonable request. The included example viewer displays authored JSON; it does not perform inference or reproduce the manuscript's clinical results. See [Code availability](CODE_AVAILABILITY.md).

[中文说明](README.zh-CN.md)

## Manuscript

**A Large Language Model Paradigm Integrating Expert Diagnostic Data for Fetal Congenital Heart Disease Screening and Prenatal Diagnosis in Low-Resourced Healthcare Settings**

Yingying Zhang, Runze Liu, Yuxuan Guan, Hao Sheng, Jingyi Wang, Xiaoyan Gu, Jiancheng Han, Xuefei Huang, Jia Gu, Yihua He and Haogang Zhu.

The supplied [manuscript](references/ExpEvaFCHD_Manuscript.pdf) and [supplementary information](references/ExpEvaFCHD_Supplementary.pdf) are retained as the scientific sources for this update. Bibliographic metadata are provided in [CITATION.cff](CITATION.cff); no DOI or publication status has been inferred.

## Contents

| Path | Purpose |
|---|---|
| [ExpEvaFCHD_main.py](ExpEvaFCHD_main.py) | Python-style inference pseudocode with explicitly supplied operations |
| [ExpEvaFCHD_eval.py](ExpEvaFCHD_eval.py) | Evaluation pseudocode with separate case, family, statement and workflow units |
| [configs](configs) | Study metadata, six model backends, experiment conditions and illustrative settings |
| [schemas](schemas) | Public data contracts and disease-family definitions |
| [examples](examples) | Authored synthetic records, outputs and a standard-library JSON viewer |
| [templates/Structured_Data_Standard_Template.xlsx](templates/Structured_Data_Standard_Template.xlsx) | Structured data-entry template and field documentation |
| [docs/methods.md](docs/methods.md) | Workflow, equations, decision boundaries and abstract dependencies |
| [docs/data_contract.md](docs/data_contract.md) | Input, evidence, output and label conventions |
| [docs/evaluation.md](docs/evaluation.md) | Evaluation endpoints, statistical procedures and comparator scope |
| [docs/manuscript_alignment.md](docs/manuscript_alignment.md) | Source-to-repository mapping and provenance |
| [references](references) | Supplied manuscript, supplement and January 2026 taxonomy reference |
| [CODE_AVAILABILITY.md](CODE_AVAILABILITY.md) | Public release scope and full-implementation contact details |

Explanations are placed in documentation. Python source contains no comments or docstrings.

## View the examples

Run the viewer from the repository directory using Python 3:

```bash
python examples/show_example.py
python examples/show_example.py --case multifamily --section output
python examples/show_example.py --case insufficient --section trace
```

The viewer uses the Python standard library. No model download, API key, external service or package installation is required. It displays fixed examples and does not calculate a diagnostic prediction.

The two main files are readable algorithm outlines. Their clinical operations are supplied through an abstract `ops` interface; the public package does not implement those operations. Running either file displays its scope notice:

```bash
python ExpEvaFCHD_main.py
python ExpEvaFCHD_eval.py
```

The retained requirement files are empty because the public viewer has no third-party dependencies.

## Workflow

| Stage | Operation | Output |
|---|---|---|
| Structured alignment | Resolve aliases, canonical units, missing values and field formats | Canonical measurements and alignment provenance |
| Similar-case retrieval | Compare available query measurements with a local expert case database | Ranked reference cases and retrieval status |
| Evidence aggregation | Extract concepts with negation handling and aggregate weighted support | Evidence package and attribution references |
| Constrained generation and validation | Compose a report, verify values and statement support, and handle failures | Screening output, candidate findings, narrative, attribution and workflow status |

The manuscript specifies top-10 retrieval with a minimum similarity of 0.22, weighted standardized numerical distance and radial-basis similarity. A highest-similarity fallback is retained when threshold filtering returns no references, but that fallback does not establish sufficient abnormality support. No usable numerical input leads to an insufficient-evidence report. The governing equations and unresolved implementation details are documented in [Methods](docs/methods.md).

The report layer supports physician-facing and patient-facing explanations from the same evidence. In the research workflow, physicians review the reports and make final diagnoses. This release illustrates those information flows; it is not a clinical service.

## Study cohorts and label units

| Cohort | Unique cases | Positive cases | Negative cases |
|---|---:|---:|---:|
| FetalCardioDB | 50,093 | 7,632 | 42,461 |
| Prospective single-center validation | 1,458 | 340 | 1,118 |
| Multicenter validation | 3,370 | 316 | 3,054 |

These are manuscript-reported cohort counts, not records distributed with this repository. The FetalCardioDB positive count is the arithmetic difference between its reported total and negative count. The historical database covers January 2016–November 2025; both validation cohorts cover December 1, 2025–March 1, 2026. The multicenter cohort spans 15 hospitals in five Chinese provinces. The study applies temporal separation and patient-level deduplication across cohorts. Sources: [manuscript, pp. 3–5](references/ExpEvaFCHD_Manuscript.pdf#page=3) and [pp. 29–30](references/ExpEvaFCHD_Manuscript.pdf#page=29).

Seven disease families encompass 73 disease entities. A positive case may belong to multiple families, so family counts must not be summed as independent patients. The reported differential-diagnosis evaluation is at the seven-family level. Binary screening, family-set agreement and abnormality-statement support are distinct endpoints with different denominators. See [Data contract](docs/data_contract.md) and [Evaluation](docs/evaluation.md).

## Model and experiment scope

The six studied backends are Kimi-K2, DeepSeek-V3.2, GLM-4.5, Llama-3.1-70B, Qwen3-Max and GPT-5. The first four were accessed through Beihang University's Hangzhou computing platform; Qwen3-Max and GPT-5 used research-team test APIs. [Supplementary Table S17](references/ExpEvaFCHD_Supplementary.pdf#page=42) reports those access arrangements without exact checkpoints, quantization settings or API revisions. The repository records the reported names and leaves unreported values unspecified.

The experiment catalog includes direct generation, gestational-age rules, kNN, logistic regression, text RAG, structured RAG without validation, component ablations and template comparisons. In the manuscript, matched-evidence templates and the full Qwen3-Max system have identical binary confusion matrices in both cohorts; report quality differs. This observation does not imply identical predictions across all six backends. Sources: [manuscript, pp. 12–14](references/ExpEvaFCHD_Manuscript.pdf#page=12), [Supplementary Table S6](references/ExpEvaFCHD_Supplementary.pdf#page=20) and [S16](references/ExpEvaFCHD_Supplementary.pdf#page=41).

## Full implementation and data

The complete, detailed implementation is available from the corresponding authors upon reasonable request:

| Corresponding author | Email |
|---|---|
| Yihua He | [heyihuaecho@hotmail.com](mailto:heyihuaecho@hotmail.com) |
| Haogang Zhu | [haogangzhu@buaa.edu.cn](mailto:haogangzhu@buaa.edu.cn) |

Clinical data are available subject to applicable regulatory and ethical requirements and the necessary approvals. Private patient records, the expert retrieval database, production prompts, clinical rules, fitted calibration objects, model credentials and case-level experimental outputs are not included in this illustrative package. Source: [manuscript, pp. 1 and 34](references/ExpEvaFCHD_Manuscript.pdf#page=34).

## License and update

The original [MIT license](LICENSE) is retained unchanged. It does not grant access to restricted clinical data, external model assets or implementation materials that are not distributed here.

Repository update date: **2026-11-03**. This date identifies the package update, not the manuscript's publication date. Changes are recorded in [CHANGELOG.md](CHANGELOG.md).
