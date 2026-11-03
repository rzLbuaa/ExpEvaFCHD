# Code and data availability

## Public repository statement

The public ExpEvaFCHD repository provides illustrative pseudocode, documented data contracts, study and experiment metadata, a structured data template, and explicitly synthetic examples to explain the framework and its evaluation design. The complete, detailed implementation is available from the corresponding authors upon reasonable request. The public examples do not reproduce the clinical experiments reported in the manuscript.

This paragraph describes the scope of this repository release. It does not modify the Code availability statement in the supplied manuscript.

## Corresponding authors

| Corresponding author | Email |
|---|---|
| Yihua He | [heyihuaecho@hotmail.com](mailto:heyihuaecho@hotmail.com) |
| Haogang Zhu | [haogangzhu@buaa.edu.cn](mailto:haogangzhu@buaa.edu.cn) |

The names and addresses follow the [manuscript title page](references/ExpEvaFCHD_Manuscript.pdf#page=1).

## Distributed materials

The two principal Python files express the inference and evaluation workflows through abstract operations. Explanations are in the accompanying Markdown documents rather than code comments or docstrings. The example viewer uses the Python standard library to display fixed, authored JSON. The configurations distinguish manuscript-reported settings from illustrative interface choices and unreported research assets.

The template and schemas explain data organization; they do not contain the FetalCardioDB clinical database. Synthetic examples are teaching material, not anonymized patient records, empirical results, or a validated clinical model.

## Full implementation and research assets

The complete implementation includes the operational components needed to instantiate the abstract interfaces. These can include the complete alignment and concept resources, clinical feature and gestational-age rules, threshold logic, prompt and validation resources, backend integration, fitted calibration objects, and experimental analysis routines. Their exact content and release arrangements are determined by the corresponding authors.

The public package does not invent missing numerical settings, model checkpoints, clinical decision thresholds or calibration coefficients. The supplied scientific documents do not fully specify these materials; [Methods](docs/methods.md) records the resulting boundaries.

## Clinical data

As stated in the [manuscript, p. 34](references/ExpEvaFCHD_Manuscript.pdf#page=34), data are available from the corresponding authors upon reasonable request, subject to applicable regulatory and ethical requirements and the necessary approvals for use. Case-level data, patient identifiers, expert retrieval records, experiment pairing files and private service credentials are not distributed in this package.

## License and external assets

The original [MIT license](LICENSE) is retained unchanged. Its presence does not grant access to restricted clinical data, third-party model weights, external resources, service accounts or implementation materials that are not included in this release. Supplied reference documents retain their original content and authorship.
