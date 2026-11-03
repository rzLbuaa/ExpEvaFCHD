PUBLIC_RELEASE = "Illustrative pseudocode. Complete implementation: heyihuaecho@hotmail.com; haogangzhu@buaa.edu.cn."


def prepare_reference_assets(reference_records, split_manifest, settings, ops):
    ops.require_patient_and_temporal_separation(reference_records, split_manifest)
    ops.require_reference_records_without_validation_patients(reference_records)
    resources = ops.load_author_supplied_resources(settings)
    aligned_records = ops.align_reference_measurements(reference_records, resources)
    statistics = ops.obtain_reference_only_normalization_statistics(aligned_records, resources)
    ops.verify_statistics_and_mapping_provenance(statistics, resources, split_manifest)
    gamma = ops.obtain_median_distance_gamma(aligned_records, statistics, resources)
    return {
        "records": aligned_records,
        "statistics": statistics,
        "gamma": gamma,
        "resources": resources,
        "split_manifest": split_manifest,
    }


def align_query(raw_record, assets, ops):
    fields = ops.select_measurements_without_identifiers_or_reference_labels(raw_record)
    aligned = ops.canonicalize_aliases_units_order_and_missingness(fields, assets["resources"])
    ops.reject_ambiguous_units_and_conflicting_field_values(aligned)
    ops.require_deterministic_alignment(aligned)
    return aligned


def retrieve_similar_cases(aligned, assets, settings, ops):
    fields = ops.available_numerical_fields(aligned)
    if not fields:
        return {"cases": [], "status": "no_usable_numerical_evidence", "low_similarity_fallback": False}
    candidates = ops.prepare_candidate_comparisons(
        aligned,
        assets["records"],
        fields,
        assets["statistics"],
        assets["resources"],
    )
    ops.require_author_missingness_zero_variance_and_weight_policies(candidates, assets["resources"])
    scored = []
    for candidate in candidates:
        distance = ops.weighted_standardized_distance(aligned, candidate, fields, assets)
        similarity = ops.radial_basis_similarity(distance, assets["gamma"])
        scored.append(ops.attach_similarity(candidate, similarity))
    ranked = ops.rank_by_similarity_with_author_tie_policy(scored, assets["resources"])
    if not ranked:
        return {"cases": [], "status": "no_comparable_reference_case", "low_similarity_fallback": False}
    eligible = ops.filter_minimum_similarity(ranked, settings["retrieval"]["minimum_similarity"])
    if not eligible:
        return {"cases": ranked[:1], "status": "low_similarity_fallback", "low_similarity_fallback": True}
    if ops.source_balancing_enabled(settings, assets["resources"]):
        eligible = ops.round_robin_by_hospital(eligible, assets["resources"])
    return {
        "cases": eligible[:settings["retrieval"]["top_k"]],
        "status": "retrieved",
        "low_similarity_fallback": False,
    }


def aggregate_evidence(aligned, retrieval, assets, ops):
    concepts = ops.extract_concepts_aliases_and_negation(retrieval["cases"], assets["resources"])
    positive_evidence = ops.exclude_negated_concepts_from_positive_support(concepts)
    raw_support = ops.similarity_weighted_positive_evidence(retrieval["cases"], positive_evidence)
    cues = ops.rank_supported_abnormality_cues(positive_evidence, retrieval["cases"])
    excerpts = ops.select_representative_excerpts_with_case_ids(retrieval["cases"], positive_evidence)
    evidence = {
        "aligned_measurements": aligned,
        "retrieved_cases": retrieval["cases"],
        "abnormality_cues": cues,
        "representative_excerpts": excerpts,
        "raw_support": raw_support,
        "low_similarity_fallback": retrieval["low_similarity_fallback"],
    }
    evidence["controls"] = ops.apply_author_saws_and_evidence_sufficiency_rules(evidence, assets["resources"])
    return evidence


def shared_risk_record(evidence, assets, ops):
    mapping = ops.get_frozen_probability_mapping(assets["resources"])
    if mapping is None:
        return {
            "raw_support": evidence["raw_support"],
            "mapped_probability": None,
            "mapping_status": "author_mapping_not_supplied",
        }
    ops.require_mapping_fitted_without_validation_outcomes(mapping, assets["split_manifest"])
    return {
        "raw_support": evidence["raw_support"],
        "mapped_probability": ops.apply_frozen_mapping(evidence["raw_support"], mapping),
        "mapping_status": "fixed_author_mapping",
    }


def parse_with_fallbacks(draft, resources, ops):
    parsed = ops.try_parse_structured_output(draft, resources)
    if parsed is not None:
        return parsed, "structured"
    parsed = ops.try_parse_sections(draft, resources)
    if parsed is not None:
        return parsed, "section_fallback"
    return ops.wrap_single_recommendation_block(draft, resources), "recommendation_fallback"


def validate_report(parsed, aligned, evidence, assets, ops):
    return ops.validate_concepts_numbers_negation_and_statement_attribution(
        parsed,
        aligned,
        evidence,
        assets["resources"],
    )


def report_is_acceptable(parsed, evidence, audit, ops):
    return (
        ops.attribution_requirements_satisfied(audit)
        and ops.author_evidence_controls_allow_output(parsed, evidence["controls"], audit)
    )


def generate_and_validate(aligned, evidence, assets, settings, ops):
    draft = ops.try_generate_with_fixed_backend(aligned, evidence, settings, assets["resources"])
    events = []
    if draft is None:
        draft = ops.evidence_preserving_generation_fallback(aligned, evidence, assets["resources"])
        events.append("generation_fallback")
    if draft is None:
        return {"status": "rejected", "report": None, "audit": None, "events": events + ["generation_failure"]}
    parsed, parse_mode = parse_with_fallbacks(draft, assets["resources"], ops)
    if parse_mode != "structured":
        events.append(parse_mode)
    audit = validate_report(parsed, aligned, evidence, assets, ops)
    if not report_is_acceptable(parsed, evidence, audit, ops):
        events.append("draft_validation_failure")
        fallback = ops.evidence_preserving_validation_fallback(aligned, evidence, assets["resources"])
        if fallback is None:
            return {"status": "rejected", "report": None, "audit": audit, "events": events}
        parsed, parse_mode = parse_with_fallbacks(fallback, assets["resources"], ops)
        events.append("validation_fallback")
        if parse_mode != "structured":
            events.append(parse_mode)
        audit = validate_report(parsed, aligned, evidence, assets, ops)
        if not report_is_acceptable(parsed, evidence, audit, ops):
            return {"status": "rejected", "report": None, "audit": audit, "events": events}
    return {"status": "validated_draft", "report": parsed, "audit": audit, "events": events}


def exp_eva_fchd(raw_record, assets, settings, ops):
    aligned = align_query(raw_record, assets, ops)
    retrieval = retrieve_similar_cases(aligned, assets, settings, ops)
    if not retrieval["cases"]:
        return ops.insufficient_evidence_output(
            raw_record,
            aligned,
            retrieval,
            screening_label=None,
            disease_families=[],
            disease_entities=[],
        )
    evidence = aggregate_evidence(aligned, retrieval, assets, ops)
    risk = shared_risk_record(evidence, assets, ops)
    generated = generate_and_validate(aligned, evidence, assets, settings, ops)
    if generated["status"] == "rejected":
        return ops.rejected_output_with_audit(
            raw_record,
            retrieval,
            risk,
            generated,
            screening_label=None,
            disease_families=[],
            disease_entities=[],
        )
    labels = ops.extract_validated_labels_with_shared_concept_and_negation_rules(
        generated["report"],
        evidence,
        assets["resources"],
    )
    return ops.build_output_with_statement_attribution_and_physician_review(
        raw_record,
        aligned,
        retrieval,
        evidence,
        risk,
        labels,
        generated,
    )


if __name__ == "__main__":
    print(PUBLIC_RELEASE)
