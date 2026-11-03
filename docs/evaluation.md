# Evaluation design

`ExpEvaFCHD_eval.py` is illustrative Python-style pseudocode. Its `ops` argument supplies abstract statistical, parsing, calibration and auditing operations. It is not the full study evaluation engine. The complete implementation, analysis assets and permitted data access are available by contacting the corresponding authors listed in the main README.

The study protocol and reported endpoints are described in [the manuscript, pp. 32–34](../references/ExpEvaFCHD_Manuscript.pdf#page=32). [The supplementary tables](../references/ExpEvaFCHD_Supplementary.pdf#page=1) provide aggregate results. Illustrative records in this repository demonstrate interfaces and do not reproduce those clinical results.

## Evaluation records and dependencies

Evaluation functions operate on records containing `case_id`, `reference_label` and `predicted_label`. Both screening labels must be resolved to 0 or 1 under the author-supplied analysis policy. Depending on the endpoint, records also contain reference and predicted disease-family sets, report text, reference text, risk scores, physician statement audits, workflow flags, error attribution or report times. These are evaluation records assembled from the study outputs; they are distinct from the raw input fields in [the record schema](../schemas/record.schema.json) and the demonstration report structure in [the report schema](../schemas/report.schema.json).

Each physician interpretation record additionally requires an explicit author-adjudicated boolean `interpretation_correct`. Missing flags and nonboolean values are rejected. This endpoint cannot be inferred from agreement between the binary screening labels.

`prepare_rows` requires unique, nonempty case identifiers and an explicitly supplied policy for missing outputs and abstentions. Label resolution must preserve the complete identifier set. Unresolved outputs cause an error rather than silently disappearing from the denominator. Evaluation must also retain the original output and its disposition in the implementation's audit record.

Endpoint functions expect these prepared records. The base-versus-full, comparator and physician wrappers call `prepare_rows` explicitly; direct calls to other endpoints must use the same preparation step.

Paired analyses match records by exact case identifier and require the same reference labels on both sides. Their inputs must belong to the same evaluation cohort and predeclared analysis population. Marginal TP, FP, TN and FN totals cannot reconstruct discordant case pairs. The preprocessing interfaces must also use the same disease-concept extraction and negation rules as evidence aggregation, as stated in [the manuscript, p. 33](../references/ExpEvaFCHD_Manuscript.pdf#page=33).

The injected operations are intentionally unresolved. Required author-supplied dependencies include the prediction-failure policy, clinical concept mappings, zero-cell likelihood-ratio handling, disease-family interval procedure, report-metric resources, multiplicity plan, calibration mapping and provenance, timing analysis plan and adjudicated audit records. The public files do not infer these from rounded tables.

## Endpoint and denominator map

| Endpoint | Analysis population or denominator | Repository function | Source |
|---|---|---|---|
| Binary screening | Sensitivity: reference positives; specificity: reference negatives; PPV: predicted positives; NPV: predicted negatives; accuracy: all cases | `binary_metrics` | [S12, p. 29](../references/ExpEvaFCHD_Supplementary.pdf#page=29) |
| Disease-family recognition | One-versus-rest classification across all cases in each cohort | `family_recognition` | [S3, p. 9](../references/ExpEvaFCHD_Supplementary.pdf#page=9) |
| Disease-family set prediction | Reference-positive cases, with all-positive, single-family and multiple-family strata | `family_set_agreement` | [S4, pp. 15–18](../references/ExpEvaFCHD_Supplementary.pdf#page=15) |
| Paired screening changes | Exactly matched case identifiers; outcome-specific reference stratum | `paired_binary_comparison` | [S5, p. 19](../references/ExpEvaFCHD_Supplementary.pdf#page=19) |
| Automated report quality | Positive and negative reference-case strata evaluated separately | `report_quality` | [S1, p. 1](../references/ExpEvaFCHD_Supplementary.pdf#page=1), [S2, p. 5](../references/ExpEvaFCHD_Supplementary.pdf#page=5) |
| Matched-evidence report ratings | Paired template and LLM reports with identical evidence and decisions | `matched_evidence_report_ratings` | [S16, p. 41](../references/ExpEvaFCHD_Supplementary.pdf#page=41) |
| Shared retrieval risk calibration | Case-level risk values and reference outcomes, independent of narrative wording | `shared_risk_calibration` | [S7–S8, pp. 22–24](../references/ExpEvaFCHD_Supplementary.pdf#page=22) |
| Supported and unsupported abnormality statements | All physician-audited abnormality statements | `statement_audit` | [S11, pp. 26–28](../references/ExpEvaFCHD_Supplementary.pdf#page=26) |
| Report coverage | All reports | `statement_audit` | [S11, p. 26](../references/ExpEvaFCHD_Supplementary.pdf#page=26) |
| Clinical workflow event rates | All cases in the cohort | `workflow_events` | [S9, p. 25](../references/ExpEvaFCHD_Supplementary.pdf#page=25) |
| Error attribution | All false negatives or all false positives, separately | `error_attribution` | [S10, p. 26](../references/ExpEvaFCHD_Supplementary.pdf#page=26) |
| Physician assistance | Binary screening reported separately; paired interpretation accuracy uses adjudicated `interpretation_correct` flags | `physician_assistance` | [S15, pp. 40–41](../references/ExpEvaFCHD_Supplementary.pdf#page=40) |
| Prevalence-standardized predictive values | Assumed prevalence with source-cohort sensitivity and specificity held constant | `standardized_predictive_values` | [S18, pp. 42–44](../references/ExpEvaFCHD_Supplementary.pdf#page=42) |

The proportion operation returns the numerator, denominator, estimate and 95% interval. A zero denominator produces `null` for the estimate and interval. The likelihood-ratio operation returns positive and negative ratio estimates and intervals together with the declared handling of zero cells. No continuity correction is selected by this illustrative release.

## Binary screening and paired inference

Sensitivity, specificity, PPV, NPV and accuracy use 95% Wilson intervals. Positive and negative likelihood ratios use the log delta method. The full numerical routines remain abstract. These methods are stated in [the manuscript, p. 33](../references/ExpEvaFCHD_Manuscript.pdf#page=33).

For paired screening conditions, `a` counts cases correct under both conditions, `b` counts first-correct/second-incorrect cases, `c` counts first-incorrect/second-correct cases and `d` counts cases incorrect under both. The difference is `(c - b) / n`, where the second condition is Full. Sensitivity comparisons retain reference positives; specificity comparisons retain reference negatives; binary accuracy comparisons retain all matched cases.

The two-sided exact McNemar test uses the two discordant counts. For each of `b / n` and `c / n`, a 97.5% Clopper–Pearson interval is calculated. The conservative 95% difference interval is:

`[lower(c / n) - upper(b / n), upper(c / n) - lower(b / n)]`.

The denominator of these proportions is the entire relevant paired stratum, not the number of discordant pairs. With no discordance and a nonempty stratum, the exact test returns 1; the conservative difference interval can still have nonzero width. Empty strata retain undefined results. See [S5, p. 19](../references/ExpEvaFCHD_Supplementary.pdf#page=19).

[The experiment configuration](../configs/experiments.json) declares separate Holm families:

- S5: six backends × sensitivity, specificity and accuracy = 18 tests within each validation cohort.
- S6: 12 comparators against Full Qwen3-Max for case-level accuracy within each validation cohort.
- Physician comparisons: exact-test P values reported separately.

The evaluator requires a complete declared screening comparison family before adjustment. It does not pool tests across cohorts or reconstruct pairing from summary tables. Report-quality multiplicity and any other interval methods not fully specified in the supplied materials remain dependencies of the author-supplied analysis plan. See [S6, pp. 20–21](../references/ExpEvaFCHD_Supplementary.pdf#page=20).

## Disease-family sets

The seven families are defined in [the taxonomy file](../schemas/disease_families.json). A case may contribute to several families, while duplicate mentions of the same family within a case count once. Family-membership totals therefore differ from the number of positive cases. S3 includes all cohort cases in each family-specific confusion matrix; S4 restricts family-set evaluation to reference-positive cases.

Micro recall uses total correct family memberships divided by total reference family memberships. Micro precision uses total correct memberships divided by total predicted memberships. Micro F1 is `2 × correct / (reference + predicted)`. Jaccard similarity uses the intersection and union of each case's two family sets before averaging across cases. Exact match compares whole sets, not a selected primary family.

The single-family and multiple-family strata are defined by the number of distinct reference families. They are not defined by the number of generated labels or by a mutually exclusive primary diagnosis. The published aggregate totals are 495 memberships across 340 prospective positives and 430 memberships across 316 multicenter positives. The prospective cardiac-position family has zero reference-positive cases, making recall undefined. See [S3–S4, pp. 9–18](../references/ExpEvaFCHD_Supplementary.pdf#page=9).

The exact CI procedure for every family-set metric is not fully specified in the supplied method text. `ops.family_set_intervals` therefore receives an author-supplied interval plan. It must retain the case-level dependence between labels. This pseudocode does not declare a bootstrap design or invent an independent-label sampling scheme.

## Report quality and shared risk calibration

The automated report metrics are Cosine, CosineTI, Relevance, Informativeness and Validity. Means receive Student's t intervals with `n - 1` degrees of freedom; paired continuous or ordinal comparisons use two-sided Wilcoxon signed-rank tests and the declared Holm adjustment. The manuscript describes an offline evaluation workflow based on GPT-2 and Vipu Baike resources for Relevance, Informativeness and Validity. The necessary evaluator assets and scoring definitions are not downloaded or approximated by this release. See [the manuscript, pp. 32–33](../references/ExpEvaFCHD_Manuscript.pdf#page=32).

The code preserves each metric's stated interpretation. In particular, Informativeness decreases in the supplied Full-system tables; it is not automatically treated as a metric whose increase proves clinical improvement. Matched-evidence template comparisons additionally assess readability and clarity and clinical content completeness. Those ratings are distinct from the automated five-metric suite and require the corresponding rating records and analysis plan. See [S16, p. 41](../references/ExpEvaFCHD_Supplementary.pdf#page=41).

Calibration is evaluated for both the raw retrieval support score and the fixed-mapping probability. These values must remain separate from final report-extracted screening labels. The interface requires the frozen mapping and its provenance, and reports Brier score, ECE, calibration-in-the-large, intercept, slope and decile reliability. Observed proportions in reliability bins use Wilson intervals. Calibration coefficients, tie handling for deciles, endpoint handling and interval algorithms come from the author-supplied artifacts; the rounded S7–S8 results are not sufficient to recover them.

Although the risk layer is shared, the supplementary Full-system screening outputs differ by generation backend. The matched-evidence template matches Full Qwen3-Max's screening predictions specifically; this is not a claim that every backend must yield identical parsed report labels. See [S7, p. 22](../references/ExpEvaFCHD_Supplementary.pdf#page=22), [S12, p. 29](../references/ExpEvaFCHD_Supplementary.pdf#page=29) and [S13, p. 33](../references/ExpEvaFCHD_Supplementary.pdf#page=33).

## Audits, workflow and physician interpretation

SFCR and UASR use physician-adjudicated support labels for abnormality statements. Reports with no abnormality statements contribute to the report denominator but provide no statement denominator. Report coverage is computed separately. Missing support labels must be resolved; they are not silently classified as unsupported or excluded.

Report handling requires one of three categories: accepted unchanged, accepted after minor revision, or major revision/rejection. The first two can be summed to calculate acceptance with at most minor revision. Low-evidence alerts, draft-validation failures, fallback and review/escalation flags may overlap and are reported separately. The study's exact escalation rule is supplied through `ops.has_escalation_flag`; the pseudocode does not invent a threshold or equate absent individual flags with a known review decision. See [S9, p. 25](../references/ExpEvaFCHD_Supplementary.pdf#page=25).

FN and FP attribution use one adjudicated category per error: other/unlocalized, venous-family-related, multiple-family combinations or substantial field missingness. Their denominators are the corresponding error totals. No numerical missingness threshold is inferred from S10.

Physician assistance compares the same cases under unaided and assisted conditions, preserving unique identifiers and consistent reference labels. It returns `unaided_binary_screening` and `assisted_binary_screening` from the binary labels. Separately, `paired_interpretation_accuracy` uses the explicit author-adjudicated `interpretation_correct` flags, which account for an incorrect primary diagnosis or a diagnostic omission. A physician can correctly identify a positive screening case while still making an interpretation error. Equal positive binary labels therefore do not imply concordant interpretation correctness. See [the manuscript, p. 32](../references/ExpEvaFCHD_Manuscript.pdf#page=32).

The interpretation endpoint compares those correctness flags through `paired_correctness_comparison`, using the same two-sided exact McNemar test and the conservative difference interval assembled from two 97.5% Clopper–Pearson intervals. The direction is assisted minus unaided, and the denominator is all paired interpretation records. Report drafting/review time savings use paired differences and their author-supplied interval method. The repository does not infer case-level savings or interpretation transitions by subtracting independently rounded table means. See [S15, pp. 40–41](../references/ExpEvaFCHD_Supplementary.pdf#page=40).

## Standardized predictive values

At assumed prevalence `p`, sensitivity `Se` and specificity `Sp` remain fixed at the source-cohort estimates:

`PPV(p) = p × Se / [p × Se + (1 - p) × (1 - Sp)]`

`NPV(p) = (1 - p) × Sp / [(1 - p) × Sp + p × (1 - Se)]`.

Intervals follow monotonic transformation of the likelihood-ratio intervals: PPV increases with LR+, whereas NPV decreases with LR−. The supplied tables use prevalence scenarios 0.5%, 1% and 2%; the figure range is 0.1%–25%. These calculations do not account for uncertainty in target prevalence or transfer to another population and do not represent an additional validation cohort. See [the manuscript, p. 34](../references/ExpEvaFCHD_Manuscript.pdf#page=34) and [S18, p. 42](../references/ExpEvaFCHD_Supplementary.pdf#page=42).
