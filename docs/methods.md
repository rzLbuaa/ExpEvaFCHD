# ExpEvaFCHD method outline

This document maps the supplied manuscript to the public pseudocode. It records reported operations and separates them from interfaces whose complete clinical implementation is available from the corresponding authors. The primary method source is the [manuscript, pp. 30–32](../references/ExpEvaFCHD_Manuscript.pdf#page=30).

## Inputs and outputs

An examination supplies structured fetal echocardiographic measurements acquired by an ultrasound device or recorded in a worksheet. The method does not consume raw images or video. The historical expert database contains aligned measurements, a binary screening label, expert lesion labels and an expert narrative for each case.

The full workflow produces a screening conclusion, candidate lesion set, structured narrative and attribution object. The attribution object links abnormality-related statements to measurement fields or retrieved-case evidence. Report status and evidence sufficiency remain distinct from the positive/negative classification: an unavailable or insufficient-evidence result must not silently become a negative diagnosis.

The public schemas formalize a demonstration interface, not a recovered private database schema. The main file injects research-specific operations through `ops` so their absence is explicit. See [Data contract](data_contract.md).

## 1. Deterministic structured alignment

Alignment resolves field aliases, canonical measurement units, field ordering, missing values and formatting irregularities. Clearly irrelevant narrative fragments are removed before downstream use. The canonical aligned vector is the only structured signal permitted to drive numerical retrieval and consistency checking; unaligned raw text cannot determine the screening conclusion.

A useful alignment record identifies the source field, canonical field, source unit, conversion operation and missingness or rejection status. Those provenance fields are public interface choices. The supplied main manuscript does not enumerate the complete alias registry or clinical normalization rules.

Gestational-age normalization is an explicit component in the manuscript's ablation design. Its exact transformation and reference curves are not specified in the supplied documents. The pseudocode therefore delegates it to an abstract operation instead of supplying invented clinical equations. Source: [manuscript, pp. 31–32](../references/ExpEvaFCHD_Manuscript.pdf#page=31).

## 2. Similar-case retrieval

Let `J(x)` denote the numerical fields available in the aligned query. Measurements are standardized using local-cohort statistics:

$$
z_j(x)=\frac{x_j-\mu_j}{\sigma_j}.
$$

With nonnegative field weights, the weighted distance and radial-basis similarity are:

$$
d_w(x,q)=\sqrt{\sum_{j\in J(x)}w_j\left[z_j(x)-z_j(q)\right]^2},
\qquad
s(x,q)=\exp\left[-\gamma d_w(x,q)^2\right].
$$

The manuscript specifies top-10 retrieval above a minimum similarity of 0.22. Gamma is initialized by a median-distance heuristic and may be adjusted for a deployment; its exact estimator is not specified. The public configuration records the stated defaults without inventing feature weights or a fitted gamma. Source: [manuscript, p. 31](../references/ExpEvaFCHD_Manuscript.pdf#page=31).

Optional source balancing groups candidate references by hospital and selects them in round-robin order. If no case survives similarity filtering, the highest-similarity reference is returned with a low-similarity fallback status. This retrieval fallback remains subject to evidence validation and does not by itself establish an abnormal finding.

The supplied specification does not fully resolve missing fields in a candidate reference, zero-variance features, similarity ties, or the complete source-balancing policy. These remain explicit dependencies. Retrieval statistics, reference cases and calibration assets need a provenance distinct from held-out validation cases; the manuscript reports temporal separation and patient-level isolation of the cohorts. Source: [manuscript, pp. 29–30](../references/ExpEvaFCHD_Manuscript.pdf#page=29).

## 3. Polarity-controlled evidence aggregation

Evidence aggregation extracts disease concepts and aliases from reference narratives while retaining negation. A phrase such as “not observed” cannot be converted into positive disease support merely because it contains a disease term.

The retrieved set contributes a similarity-weighted positive-evidence proportion, `r_pos`. The evidence package also contains ranked abnormality cues, concise descriptions of positive or suspicious similar cases, and directly traceable excerpts. Supporting evidence refers to the query measurements or the retained references, not to an unconstrained model assertion. Source: [manuscript, pp. 30–31](../references/ExpEvaFCHD_Manuscript.pdf#page=30).

The full concept dictionary, negation rules, evidence aggregation details and screening/lesion decision rules are research assets. In particular, the manuscript names a “No SAWS threshold” ablation without specifying a complete SAWS formula and numerical threshold. The public outline retains that named component and its removal condition without assigning a substitute threshold.

## 4. Constrained generation and validation

The generation backend receives canonical measurements and the evidence package. Model parameters remain unchanged. Generation is constrained to preserve measurement values and support abnormality-related statements with measurements or retrieved evidence.

Validation uses deterministic concept matching, numerical consistency checks and negation recognition. Attribution failures lead to rejection or a fallback route. If structured-output parsing fails, the method falls back to section-level parsing and then, if necessary, to a single recommendation text block; evidence validation is still required. With no usable numerical evidence, the workflow returns an insufficient-evidence report. Source: [manuscript, pp. 31–32](../references/ExpEvaFCHD_Manuscript.pdf#page=31).

The public files express these branches without inventing their clinical acceptance thresholds. Example outputs and traces are authored illustrations of the information structure. They are not generated by a research backend and do not establish clinical correctness.

Acceptance explicitly requires both statement attribution and the author-supplied evidence-control verdict. This gate is applied to the initial report and to every replacement report before label extraction. A citation to a retrieved case cannot bypass insufficient support, including support derived only from a low-similarity fallback.

## Generation backends and report roles

| Backend | Access reported by the study |
|---|---|
| Kimi-K2 | Locally deployed model accessed through the Beihang Hangzhou computing platform |
| DeepSeek-V3.2 | Locally deployed model accessed through the same platform |
| GLM-4.5 | Locally deployed model accessed through the same platform |
| Llama-3.1-70B | Locally deployed model accessed through the same platform |
| Qwen3-Max | Research-team test API |
| GPT-5 | Research-team test API |

Source: [Supplementary Table S17, p. 42](../references/ExpEvaFCHD_Supplementary.pdf#page=42). The table does not specify exact weight revisions, quantization, decoding parameters, endpoint strings or dated API snapshots. The configuration catalog preserves those gaps rather than filling them with current provider defaults.

The evidence-processing workflow is organized independently of the generation services. In the manuscript's matched-evidence experiment, template reports and the full Qwen3-Max system have identical binary confusion matrices, while language quality differs. This identifies an experimental comparison, not an assertion that all backends always yield identical screening decisions. Sources: [manuscript, pp. 12–14](../references/ExpEvaFCHD_Manuscript.pdf#page=12), [Supplementary Table S6](../references/ExpEvaFCHD_Supplementary.pdf#page=20) and [S16](../references/ExpEvaFCHD_Supplementary.pdf#page=41).

Physician-facing outputs emphasize findings and evidence. Patient-facing outputs express the same evidence in accessible language. The study retains physician review and final clinical judgment; it does not directly measure improved patient comprehension. Source: [manuscript, pp. 25–28](../references/ExpEvaFCHD_Manuscript.pdf#page=25).

## Risk calibration

The shared retrieval-risk layer is evaluated separately from the narrative layer. The study compares raw support scores with fixed-mapping probabilities using Brier score, ECE, calibration-in-the-large, intercept, slope and decile reliability. The fitted mapping, coefficients and complete fitting procedure are not provided in the supplied material. The public pseudocode accepts a fixed calibration object through an abstract interface; it does not fit a mapping to the evaluation cohorts. Sources: [manuscript, pp. 20 and 33](../references/ExpEvaFCHD_Manuscript.pdf#page=33) and [Supplementary Tables S7–S8](../references/ExpEvaFCHD_Supplementary.pdf#page=22).

## Abstract dependencies

| Dependency | What the sources establish | Public representation |
|---|---|---|
| Alignment resources | Deterministic alias, unit and missingness handling | Data contract and operation interface |
| GA normalization | Named component and ablation | Abstract transformation |
| Numerical retrieval | Standardized weighted distance, RBF similarity, top-10, 0.22 | Equations and reported defaults |
| Candidate missingness and gamma fitting | Incomplete implementation detail | Explicitly unresolved policy |
| Concept and polarity resources | Concept extraction and negation handling | Abstract resource interface |
| SAWS and decision thresholds | Named threshold ablation | Abstract decision operation |
| Prompts and validation | Evidence-constrained reports and deterministic checks | Workflow contracts |
| Fixed probability mapping | Calibration results for raw and mapped risk | Supplied fitted-object interface |
| Model execution | Six names and access arrangements | Metadata without credentials or invented revisions |
| Evaluation implementation | Metrics and statistical procedures | [Evaluation pseudocode and documentation](evaluation.md) |

The complete implementation can be requested from the corresponding authors listed in [CODE_AVAILABILITY.md](../CODE_AVAILABILITY.md).
