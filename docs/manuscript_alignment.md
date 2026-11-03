# Source alignment and provenance

This repository update uses the supplied `ExpEvaFCHD_Manuscript.pdf` and `ExpEvaFCHD_Supplementary.pdf` as its current scientific sources. The original repository's January 2026 taxonomy PDF is retained as a taxonomy reference. Source PDFs are retained without rewriting. Repository update date: **2026-11-03**.

## Source-to-module map

| Scientific content | Source location | Repository representation |
|---|---|---|
| Title, author order and correspondence | [Manuscript p. 1](../references/ExpEvaFCHD_Manuscript.pdf#page=1) | README files, citation and availability documents |
| Cohort totals and overlapping family counts | [Manuscript Tables 1–2, pp. 4–5](../references/ExpEvaFCHD_Manuscript.pdf#page=4) | Study metadata and data contract |
| Cohort dates and patient separation | [Manuscript pp. 29–30](../references/ExpEvaFCHD_Manuscript.pdf#page=29) | Study configuration and isolation contracts |
| Four-stage inference and outputs | [Manuscript pp. 30–32](../references/ExpEvaFCHD_Manuscript.pdf#page=30) | `ExpEvaFCHD_main.py`, schemas and methods document |
| Retrieval equations and stated defaults | [Manuscript p. 31](../references/ExpEvaFCHD_Manuscript.pdf#page=31) | Inference pseudocode and illustrative settings |
| Backend access arrangements | [Supplementary Table S17, p. 42](../references/ExpEvaFCHD_Supplementary.pdf#page=42) | Model configuration catalog |
| Binary screening and comparisons | [Supplementary Tables S5–S6, pp. 19–21](../references/ExpEvaFCHD_Supplementary.pdf#page=19), [S12–S14, pp. 29–39](../references/ExpEvaFCHD_Supplementary.pdf#page=29) | Evaluation pseudocode and experiment catalog |
| Disease-family recognition and set prediction | [Supplementary Tables S3–S4, pp. 9–18](../references/ExpEvaFCHD_Supplementary.pdf#page=9) | Family definitions and family-set evaluation |
| Report quality and paired analyses | [Supplementary Tables S1–S2, pp. 1–8](../references/ExpEvaFCHD_Supplementary.pdf#page=1) | Report-quality interfaces and statistical design |
| Calibration and reliability | [Supplementary Tables S7–S8, pp. 22–24](../references/ExpEvaFCHD_Supplementary.pdf#page=22) | Calibration interface and evaluation specification |
| Workflow, errors and statement support | [Supplementary Tables S9–S11, pp. 25–28](../references/ExpEvaFCHD_Supplementary.pdf#page=25) | Separate workflow and statement-level evaluation |
| Physician interpretation and reporting time | [Supplementary Table S15, p. 40](../references/ExpEvaFCHD_Supplementary.pdf#page=40) | Paired physician and time evaluation |
| Matched-evidence template comparison | [Supplementary Table S16, p. 41](../references/ExpEvaFCHD_Supplementary.pdf#page=41) | Experiment catalog and interpretation boundaries |
| Prevalence scenarios | [Manuscript pp. 33–34](../references/ExpEvaFCHD_Manuscript.pdf#page=33), [Supplementary Table S18, pp. 42–44](../references/ExpEvaFCHD_Supplementary.pdf#page=42) | Prevalence transformation outline |
| Clinical data availability | [Manuscript p. 34](../references/ExpEvaFCHD_Manuscript.pdf#page=34) | `CODE_AVAILABILITY.md` |

## Reported facts and interface choices

Study counts, model names, experiment labels, evaluation units and the stated retrieval defaults are transcribed from the current scientific sources. A reported numerical result remains a manuscript result; it is not presented as an output produced by the included viewer.

Public JSON keys, operation names, synthetic identifiers, schema organization and example narratives are authored interface choices. They illustrate how components relate and are not asserted to be the original internal field names or clinical records. The spreadsheet organizes the public data contract and must not be treated as a dump of FetalCardioDB.

The seven-family taxonomy is distinct from unique-case counting and from entity-level validation. The supplied disease classification is retained in [Detailed_Classification_January_2026.pdf](../references/Detailed_Classification_January_2026.pdf) as a historical broad taxonomy reference. It does not provide a definitive machine-readable mapping for all 73 entities. Family memberships overlap; the complete entity-to-family mapping remains an author-supplied resource.

## Unreported research details

The supplied sources do not provide a complete executable specification of GA normalization, clinical feature weights, SAWS thresholds, calibration coefficients, complete concept resources, prompts or backend versions. Those dependencies remain abstract. There is no substitute clinical rule or fitted object presented as the study implementation.

The manuscript refers to Supplementary Checklist 1, but no separately identifiable checklist is included in the supplied 50-page supplementary PDF. This package does not manufacture or claim to include that checklist.

## Scope of this update

The repository has been revised for pseudocode-based communication of the method and examples. The full research implementation, data permissions and any additional reproducibility assets remain matters for the corresponding authors. The original MIT license is preserved; the supplied scientific source files remain unchanged.
