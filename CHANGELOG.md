# Changelog

## 2026-11-03 — manuscript-aligned illustrative release

The date identifies this repository update, not publication of the associated manuscript.

### Public release scope

- Replaced the earlier implementation-oriented presentation with comment-free Python-style pseudocode and explicit operation interfaces.
- Added an English README, a Chinese README, a public availability statement and manuscript citation metadata.
- Made full-implementation access through the corresponding authors explicit.
- Added authored synthetic input/output examples and a standard-library JSON viewer; these examples are not model predictions or study observations.
- Removed installation and execution claims that would imply the public package reproduces the complete research system.

### Alignment with the supplied scientific documents

- Documented all four stages, including polarity handling, evidence validation, parsing fallback, low-similarity retrieval fallback and insufficient numerical evidence.
- Updated the three cohort sizes and six model backends to the supplied manuscript and supplementary information.
- Distinguished unique cases, overlapping disease-family memberships and abnormality statements.
- Added evaluation and experiment outlines covering case-level screening, family sets, report quality, statement support, calibration, prevalence scenarios, physician comparisons and component ablations.
- Kept unreported clinical rules, model revisions and fitted calibration objects as explicit abstract dependencies.
- Added source-to-module references and retained the supplied manuscript, supplement and original January 2026 taxonomy reference.
- Updated the structured data template and documented schema conventions.

### Preserved material

- Retained the original MIT license without modification.
- Retained the original main Python entry filenames as pseudocode entry points.
- Retained the two original requirements filenames as empty files for this dependency-free illustrative release.
