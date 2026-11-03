# Illustrative data contract

The public release uses small synthetic JSON records to explain how structured measurements, expert evidence, diagnostic labels and report attribution are separated. The JSON schemas and corrected spreadsheet are illustrative interfaces. They do not disclose the complete validated research schema, clinical terminology mapping or implementation.

The method and evaluation definitions are drawn from [the manuscript](../references/ExpEvaFCHD_Manuscript.pdf), Methods and Tables 1-2, and [the supplementary material](../references/ExpEvaFCHD_Supplementary.pdf). The historical spreadsheet supplied in the original repository provides the bilingual header inventory. The source hierarchy and limitations below preserve that distinction.

## Record roles

| Field | Meaning | Use |
| --- | --- | --- |
| `schema_version` | `illustrative-1` | Public example format, independent of the full research schema |
| `record_type` | `query` or `reference` | Separates a held-out query from eligible reference evidence |
| `synthetic` | Always `true` in this public contract | Identifies authored demonstration data |
| `case_id` | Synthetic examination key | Linking outputs and evidence within the demonstration |
| `patient_key` | Synthetic patient or pregnancy linkage key | Exclusion of the same patient/pregnancy across retrieval and evaluation |
| `site_id` | Synthetic site key | Site isolation and audit metadata |
| `examination_date` | ISO date or `null` | Temporal eligibility, when the date is known |
| `measurements` | Numeric, Boolean or null fields | Aligned query or reference measurements |
| `reference` | Null for queries; expert annotation object for reference records | Expert evidence and evaluation labels |

Identity and audit fields are never measurement-similarity features or diagnostic prompt evidence. Real identifiers are not part of the public examples. The schemas describe object structure; they do not implement deduplication, temporal eligibility or access controls.

A query record has `reference: null`. The held-out query's screening label, diagnostic entity labels, family labels and expert narrative remain outside inference. A reference record has `reference.screening_label`, `reference.disease_entities`, `reference.disease_families` and `reference.expert_narrative`. The expert casebase and an evaluation cohort have different roles even when both originate from the same tabular export.

## Measurements and missingness

Illustrative named fields include `gestational_age_weeks`, `cardiac_axis_deg`, `left_ventricle_mm`, `right_ventricle_mm`, `aortic_isthmus_mm`, `heart_rate_bpm` and `rhythm_regular`. Additional measurement names may hold numbers, Booleans or `null`; this flexibility does not establish those names as validated research features.

Missing measurements remain null or absent. Zero is a measured value and is never used as a replacement for missingness. Units are resolved before numerical alignment. Renaming a column does not establish a unit conversion. The alias example deliberately distinguishes aortic diameter, aortic isthmus and aortic flow velocity, and distinguishes pulmonary arterial diameter from flow velocity. Ambiguous headings require explicit source resolution.

No clinical normal ranges or diagnostic thresholds are supplied by this contract. Any normalization statistics, weights, diagnostic rules and complete terminology mappings belong to the full implementation available from the corresponding authors.

## Disease labels

`disease_entities` and `disease_families` are sets serialized as arrays without duplicate members. A case may contain multiple entities and multiple families. A repeated entity within the same family does not create a second family membership. Normal/negative is a case-level label, not an eighth disease family.

| Family ID | Manuscript label |
| --- | --- |
| `septal_defects` | Septal defects |
| `great_vessels_aortic_arch` | Great vessels/aortic arch |
| `venous_return_systemic_veins` | Venous return/systemic veins |
| `valves_outflow_tracts` | Valves/outflow tracts |
| `physiological_shunt_abnormalities` | Physiological shunt abnormalities |
| `other_structural_abnormalities` | Other structural abnormalities |
| `cardiac_position_abnormalities` | Cardiac position abnormalities |

The machine-readable IDs are public-release naming conventions; the English labels follow the manuscript. The manuscript reports 73 disease entities and evaluates set prediction at the seven-family level. This release does not construct or claim a complete 73-entity mapping. Entity labels in synthetic examples illustrate the field only.

The unchanged [January 2026 taxonomy PDF](../references/Detailed_Classification_January_2026.pdf) remains a historical reference. Its seven broad headings correspond to the manuscript families, with wording changes including “great vessels/arch configuration” and “malposition.” It contains subtype ranges, overlapping terminology and provisional inclusions rather than an enumerated, versioned 73-item mapping. These prose descriptions are not a validated parser or an authoritative machine-readable entity map.

Count independent cases separately from family memberships. A case can contribute once to each of several families, so the sum of family counts can exceed the number of distinct positive cases. Missing or unresolved family mapping is not a negative label and is not repaired by assigning the nearest-sounding family. An evaluation run must state its policy for unresolved labels and report the affected denominator.

## Report structure

`report.schema.json` defines authored synthetic outputs with an explicit `provenance.kind: authored_example` and `computed_by_research_system: false`. They demonstrate the intended output structure without claiming that inference or calibration has run.

| Object | Purpose |
| --- | --- |
| `status` | `illustrative`, `insufficient_evidence` or `rejected` |
| `screening_label` | Positive/negative illustration, or null when no conclusion is issued |
| `disease_entities`, `disease_families` | Nonexclusive diagnostic label sets |
| `retrieval` | Referenced case IDs, retrieval status and whether low-similarity fallback was used |
| `risk` | Raw support, mapped probability and explicit mapping status |
| `report` | Findings, interpretation and recommendation text |
| `attribution` | Statement identifiers, polarity, source measurements and reference-case links |
| `workflow` | Physician-review requirement and workflow events |
| `provenance` | Authored-example status and description |

`risk.raw_support` and `risk.mapped_probability` are separate fields. Either may be null. A raw evidence-support proportion does not establish a calibrated probability. The public example does not supply a fitted mapping.

For `insufficient_evidence` or `rejected`, the screening label is null and the diagnostic arrays are empty. This prevents a failure to produce a conclusion from being encoded as a negative case. Negative illustrations also have empty diagnostic arrays. Each attributed statement records its support and polarity explicitly; the schema validates structure, not the clinical truth of the statement or the existence of a referenced case.

## Corrected bilingual spreadsheet

[`Structured_Data_Standard_Template.xlsx`](../templates/Structured_Data_Standard_Template.xlsx) retains the original 52-field inventory in aligned `Chinese` and `English` header sheets. Both remain blank below the headers. A `Field dictionary` sheet states roles, units, illustrative names and handling rules. It contains documentation rows only.

The Chinese sheet's extra empty column and the unused empty sheet were removed. Cardiac axis is labelled as an angle in degrees. “Spindle” is replaced with “Cardiac axis,” “Pulmonary Artery Duct” with “Ductus arteriosus,” and “venous catheter” variants with “Ductus venosus.” The cardiothoracic measure is labelled as an area ratio to preserve the Chinese field's meaning. Diagnostic fields are distinguished from ultrasound findings.

Historical identifier columns are retained for compatibility and marked as local linkage fields. They are never retrieval features or prompt content. Query reference-diagnosis columns remain hidden from inference. The 52 columns include identity, metadata, narrative, diagnosis and measurement fields; they must not be described as 52 independent physiological measurements.

The legacy pulmonary-vein and ductus-venosus S/D/A columns do not state velocity units. The dictionary preserves that uncertainty instead of inventing units. Numeric data are not included, so correcting the headings does not claim that historical values have been converted or clinically verified.

## Availability

The complete field specification, validated entity mapping, normalization, retrieval, polarity rules, prompts, inference code and evaluation implementation are available by contacting the corresponding authors, as described in [Code availability](../CODE_AVAILABILITY.md).
