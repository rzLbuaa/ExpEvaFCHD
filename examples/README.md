# Synthetic examples

Every record in this directory is fabricated for method illustration. Measurements are arbitrary. Labels, retrieved-reference IDs, text and attribution links are manually authored. No example is a patient record, an output of a model, a clinical decision rule, or a reproduction of the study results.

## Contents

| File | Purpose |
| --- | --- |
| `synthetic_casebase.json` | Three reference records with separate measurements, expert narratives, binary labels and multilabel family sets |
| `demonstration.json` | One preset single-family output showing the four stages and attribution fields |
| `multifamily.json` | One preset positive case with two family memberships and two entity names |
| `insufficient.json` | An input with no numerical evidence, a null screening label and empty diagnosis sets |
| `paired_screening.example.json` | Four matched synthetic cases illustrating the input grain for paired screening comparisons |
| `show_example.py` | Standard-library JSON viewer |

The corresponding illustrative record and report schemas are in [schemas](../schemas/). The complete clinical schema, disease mapping and inference implementation are author-provided resources.

## Display an example

Run these commands from the repository root with Python 3.10 or later:

```bash
python examples/show_example.py
python examples/show_example.py --case multifamily --section output
python examples/show_example.py --case insufficient --section trace
```

The viewer prints stored JSON. It does not compute retrieval similarities, risk scores, clinical labels, report-quality scores or experimental metrics. It makes no network requests and needs no API key or third-party package.

## Counting and missingness

`multifamily.json` represents one positive case and two distinct family memberships. A second disease entity in the same family would still contribute only one membership to that family's case-level set. The two entity names in this example are illustrative assignments, not a complete 73-entity mapping.

All `raw_support` and `mapped_probability` values are null because no retrieval scoring or author-supplied probability mapping is executed. Null is not zero risk. The insufficient-evidence example also retains a null screening label; an unprocessed or rejected record is not silently counted as a negative result.

Query records have `reference: null`. Expert labels and reference narratives belong only to casebase records; the query's ground truth is reserved for evaluation outside the inference input. Synthetic reference and query patient keys are disjoint.

Attribution in the examples illustrates the location of evidence links. A link to a positive reference case does not establish that the query has the same disease, and the sample attribution status explicitly preserves that distinction.

## Paired evaluation input

`paired_screening.example.json` keeps reference, base and full labels together under a stable `case_id`. It illustrates improvement, deterioration, correctness in both conditions and errors in both conditions. The data are a teaching fixture and are not included in any reported manuscript statistic. The evaluation pseudocode requires matching by case identity; it never reconstructs paired outcomes from marginal confusion matrices.

See [evaluation](../docs/evaluation.md) for cohort denominators, missing-output handling, family-set evaluation and paired-test definitions, and [code availability](../CODE_AVAILABILITY.md) for the complete implementation.
