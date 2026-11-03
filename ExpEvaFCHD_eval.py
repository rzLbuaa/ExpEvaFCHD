from collections import Counter


REPORT_METRICS = ("Cosine", "CosineTI", "Relevance", "Informativeness", "Validity")
HANDLING_CATEGORIES = ("accepted_unchanged", "minor_revision", "major_revision_or_rejection")
WORKFLOW_EVENTS = ("low_evidence", "draft_validation_failure", "fallback", "review_or_escalation")
ERROR_CATEGORIES = ("other_or_unlocalized", "venous_family", "multiple_families", "substantial_missingness")


def prepare_rows(records, ops, policy):
    rows = list(records)
    ids = [row["case_id"] for row in rows]
    if any(not isinstance(case_id, str) or not case_id for case_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Evaluation requires unique, nonempty case identifiers.")
    ops.require_declared_missing_and_abstention_policy(policy)
    resolved = list(ops.resolve_evaluation_labels(rows, policy))
    if Counter(row["case_id"] for row in resolved) != Counter(ids):
        raise ValueError("Evaluation must preserve case identifiers and denominators.")
    if any(row[key] not in (0, 1) for row in resolved for key in ("reference_label", "predicted_label")):
        raise ValueError("Unresolved screening labels require the author-supplied analysis policy.")
    return resolved


def pair_by_case_id(first, second):
    left = {row["case_id"]: row for row in first}
    right = {row["case_id"]: row for row in second}
    if len(left) != len(first) or len(right) != len(second) or left.keys() != right.keys():
        raise ValueError("Paired analysis requires identical, unique case identifiers.")
    pairs = [(left[case_id], right[case_id]) for case_id in sorted(left)]
    if any(a["reference_label"] != b["reference_label"] for a, b in pairs):
        raise ValueError("Paired reference labels must agree.")
    return pairs


def confusion_counts(rows):
    return {
        "tp": sum(row["reference_label"] == 1 and row["predicted_label"] == 1 for row in rows),
        "fp": sum(row["reference_label"] == 0 and row["predicted_label"] == 1 for row in rows),
        "tn": sum(row["reference_label"] == 0 and row["predicted_label"] == 0 for row in rows),
        "fn": sum(row["reference_label"] == 1 and row["predicted_label"] == 0 for row in rows),
    }


def binary_metrics(rows, ops, policy):
    counts = confusion_counts(rows)
    tp, fp, tn, fn = (counts[key] for key in ("tp", "fp", "tn", "fn"))
    fractions = {"sensitivity": (tp, tp + fn), "specificity": (tn, tn + fp),
                 "ppv": (tp, tp + fp), "npv": (tn, tn + fn), "accuracy": (tp + tn, len(rows))}
    result = {name: ops.proportion_with_wilson(numerator, denominator, confidence=0.95, undefined=None)
              for name, (numerator, denominator) in fractions.items()}
    result.update({"n": len(rows), "counts": counts})
    result["likelihood_ratios"] = ops.likelihood_ratios_log_delta(
        counts, confidence=0.95, zero_cell_policy=policy["zero_cell_likelihood_ratio"])
    return result


def family_recognition(rows, families, ops, policy):
    if len(families) != 7 or len(set(families)) != 7:
        raise ValueError("The evaluation taxonomy requires seven distinct disease families.")
    ops.validate_family_sets(rows, families)
    results = {}
    for family in families:
        binary = [{"reference_label": int(family in row["reference_families"]),
                   "predicted_label": int(family in row["predicted_families"])} for row in rows]
        result = binary_metrics(binary, ops, policy)
        results[family] = {"n": len(rows), "counts": result["counts"], "recall": result["sensitivity"],
                           "specificity": result["specificity"], "precision": result["ppv"]}
    return results


def family_set_agreement(rows, ops, policy):
    positive = [row for row in rows if row["reference_label"] == 1]
    ops.require_complete_reference_family_sets(positive)
    strata = {"all_positive": positive,
              "single_family": [row for row in positive if len(set(row["reference_families"])) == 1],
              "multiple_families": [row for row in positive if len(set(row["reference_families"])) > 1]}
    results = {}
    for name, cases in strata.items():
        sets = [(set(row["reference_families"]), set(row["predicted_families"])) for row in cases]
        reference = sum(len(truth) for truth, prediction in sets)
        predicted = sum(len(prediction) for truth, prediction in sets)
        correct = sum(len(truth & prediction) for truth, prediction in sets)
        estimates = {"micro_recall": ops.divide_or_null(correct, reference),
                     "micro_precision": ops.divide_or_null(correct, predicted),
                     "micro_f1": ops.divide_or_null(2 * correct, reference + predicted),
                     "mean_jaccard": ops.mean_or_null([len(a & b) / len(a | b) for a, b in sets]),
                     "exact_match": ops.divide_or_null(sum(a == b for a, b in sets), len(cases))}
        results[name] = {"n": len(cases), "reference_labels": reference, "predicted_labels": predicted,
                         "correct_labels": correct, "estimates": estimates,
                         "ci95": ops.family_set_intervals(cases, estimates, policy["family_set_intervals"])}
    return results


def paired_correctness_comparison(pairs, outcome, ops):
    if any(type(value) is not bool for pair in pairs for value in pair):
        raise ValueError("Paired correctness requires explicit boolean adjudications.")
    outcomes = Counter(pairs)
    a, b, c, d = (outcomes[key] for key in ((True, True), (True, False), (False, True), (False, False)))
    result = {"outcome": outcome, "n": len(pairs), "a": a, "b": b, "c": c, "d": d,
              "difference": ops.divide_or_null(c - b, len(pairs)), "ci95": None, "p_exact": None}
    if pairs:
        improvement = ops.clopper_pearson_interval(c, len(pairs), confidence=0.975)
        deterioration = ops.clopper_pearson_interval(b, len(pairs), confidence=0.975)
        result["ci95"] = [improvement[0] - deterioration[1], improvement[1] - deterioration[0]]
        result["p_exact"] = 1.0 if b + c == 0 else ops.exact_mcnemar(b, c, alternative="two-sided")
    return result


def paired_binary_comparison(first, second, outcome, ops):
    pairs = pair_by_case_id(first, second)
    if outcome not in ("sensitivity", "specificity", "accuracy"):
        raise ValueError("Unsupported paired screening outcome.")
    if outcome != "accuracy":
        target = int(outcome == "sensitivity")
        pairs = [(a, b) for a, b in pairs if a["reference_label"] == target]
    correctness = [(a["predicted_label"] == a["reference_label"],
                    b["predicted_label"] == b["reference_label"]) for a, b in pairs]
    return paired_correctness_comparison(correctness, outcome, ops)


def adjust_screening_family(results, expected_count, ops):
    if len(results) != expected_count or any(result["p_exact"] is None for result in results):
        raise ValueError("A complete, declared comparison family is required for Holm adjustment.")
    adjusted = ops.holm_adjust([result["p_exact"] for result in results])
    return [dict(result, p_holm=p) for result, p in zip(results, adjusted)]


def base_full_comparisons(by_model, ops, policy):
    if len(by_model) != 6:
        raise ValueError("The study comparison family contains six models.")
    results = []
    for model, conditions in by_model.items():
        base = prepare_rows(conditions["base"], ops, policy)
        full = prepare_rows(conditions["full"], ops, policy)
        results.extend(dict(paired_binary_comparison(base, full, outcome, ops), model=model)
                       for outcome in ("sensitivity", "specificity", "accuracy"))
    return adjust_screening_family(results, 18, ops)


def comparator_comparisons(full_qwen, comparators, ops, policy):
    full = prepare_rows(full_qwen, ops, policy)
    results = [dict(paired_binary_comparison(prepare_rows(rows, ops, policy), full, "accuracy", ops),
                    comparator=name) for name, rows in comparators.items()]
    return adjust_screening_family(results, 12, ops)


def report_quality(first, second, metric_assets, ops, policy):
    pairs = pair_by_case_id(first, second)
    scored = ops.offline_report_metric_pairs(pairs, metric_assets, metrics=REPORT_METRICS)
    return ops.summarize_paired_report_metrics(
        scored, strata=("reference_negative", "reference_positive"), confidence=0.95,
        mean_interval="student_t", paired_test="two_sided_wilcoxon_signed_rank",
        multiplicity_plan=policy["report_quality_multiplicity"], preserve_metric_directions=True)


def matched_evidence_report_ratings(template, generated, ops, policy):
    pairs = pair_by_case_id(template, generated)
    ops.require_identical_evidence_and_decisions(pairs)
    return ops.paired_report_ratings(
        pairs, dimensions=("readability_and_clarity", "clinical_content_completeness"),
        confidence=0.95, paired_test="two_sided_wilcoxon_signed_rank",
        multiplicity_plan=policy["matched_evidence_rating_multiplicity"])


def shared_risk_calibration(rows, frozen_mapping, ops, policy):
    ops.require_frozen_mapping_provenance(frozen_mapping)
    results = {}
    for key in ("raw_support_score", "fixed_mapping_probability"):
        values = ops.validated_risk_values(rows, key, frozen_mapping)
        results[key] = ops.calibration_analysis(
            values, outcomes=[row["reference_label"] for row in rows],
            metrics=("brier", "ece", "citl", "intercept", "slope"),
            deciles=10, observed_interval="wilson", confidence=0.95, analysis_plan=policy["calibration"])
    return results


def statement_audit(rows, ops):
    ops.require_physician_statement_support_annotations(rows)
    statements = [statement for row in rows for statement in row["abnormality_statements"]]
    supported = sum(statement["evidence_supported"] is True for statement in statements)
    unsupported = sum(statement["evidence_supported"] is False for statement in statements)
    if supported + unsupported != len(statements):
        raise ValueError("Incomplete statement audit labels require resolution.")
    covered = sum(bool(row["abnormality_statements"]) for row in rows)
    return {"reports": len(rows), "statements": len(statements), "reports_with_statements": covered,
            "supported": supported, "unsupported": unsupported,
            "sfcr": ops.proportion_with_wilson(supported, len(statements), confidence=0.95, undefined=None),
            "uasr": ops.proportion_with_wilson(unsupported, len(statements), confidence=0.95, undefined=None),
            "report_coverage": ops.proportion_with_wilson(covered, len(rows), confidence=0.95, undefined=None)}


def workflow_events(rows, ops):
    if any(row["report_handling"] not in HANDLING_CATEGORIES for row in rows):
        raise ValueError("Each report requires one mutually exclusive handling category.")
    ops.require_boolean_workflow_flags(rows, WORKFLOW_EVENTS)
    counts = Counter({category: 0 for category in HANDLING_CATEGORIES})
    counts.update(row["report_handling"] for row in rows)
    counts["accepted_unchanged_or_minor_revision"] = counts["accepted_unchanged"] + counts["minor_revision"]
    counts.update({event: sum(row["workflow_flags"][event] for row in rows) for event in WORKFLOW_EVENTS})
    counts["false_negative_without_escalation_flags"] = sum(
        row["reference_label"] == 1 and row["predicted_label"] == 0 and
        not ops.has_escalation_flag(row) for row in rows)
    return {name: ops.proportion_with_wilson(count, len(rows), confidence=0.95, undefined=None)
            for name, count in counts.items()}


def error_attribution(rows, ops):
    results = {}
    for name, reference, prediction in (("fn", 1, 0), ("fp", 0, 1)):
        errors = [row for row in rows if row["reference_label"] == reference and row["predicted_label"] == prediction]
        if any(row["error_category"] not in ERROR_CATEGORIES for row in errors):
            raise ValueError("Each error requires one adjudicated attribution category.")
        results[name] = {category: ops.proportion_with_wilson(
            sum(row["error_category"] == category for row in errors), len(errors), confidence=0.95, undefined=None)
            for category in ERROR_CATEGORIES}
    return results


def physician_assistance(unaided, assisted, ops, policy):
    first, second = (prepare_rows(rows, ops, policy) for rows in (unaided, assisted))
    pairs = pair_by_case_id(first, second)
    correctness = [(a.get("interpretation_correct"), b.get("interpretation_correct")) for a, b in pairs]
    interpretation = paired_correctness_comparison(correctness, "interpretation_accuracy", ops)
    return {"unaided_binary_screening": binary_metrics(first, ops, policy),
            "assisted_binary_screening": binary_metrics(second, ops, policy),
            "paired_interpretation_accuracy": interpretation,
            "time_savings": ops.paired_time_analysis(pairs, confidence=0.95, analysis_plan=policy["physician_time"])}


def standardized_predictive_values(screening, prevalences, ops):
    sensitivity = screening["sensitivity"]["estimate"]
    specificity = screening["specificity"]["estimate"]
    if sensitivity is None or specificity is None:
        raise ValueError("Prevalence standardization requires defined sensitivity and specificity.")
    results = []
    for prevalence in prevalences:
        if not 0 < prevalence < 1:
            raise ValueError("Assumed prevalence must be strictly between zero and one.")
        ppv = ops.divide_or_null(prevalence * sensitivity,
                                prevalence * sensitivity + (1 - prevalence) * (1 - specificity))
        npv = ops.divide_or_null((1 - prevalence) * specificity,
                                (1 - prevalence) * specificity + prevalence * (1 - sensitivity))
        intervals = ops.transform_likelihood_ratio_intervals(
            screening["likelihood_ratios"], prevalence, ppv_increases_with_lr_positive=True,
            npv_decreases_with_lr_negative=True)
        results.append({"assumed_prevalence": prevalence, "ppv": ppv, "npv": npv, "ci95": intervals})
    return results


if __name__ == "__main__":
    print("Illustrative evaluation pseudocode. Contact the corresponding authors for the complete implementation.")
