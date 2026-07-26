# Phase 4 Gate 1 verification

All Gate 1 acceptance checks passed:

- `one_document_record_per_parsed_document`: **True**
- `source_to_output_level_counts_exact`: **True**
- `output_keys_unique`: **True**
- `all_source_statuses_allowed`: **True**
- `valid_rows_use_only_canonical_codes`: **True**
- `nonvalid_rows_have_null_canonical`: **True**
- `word_rows_are_explicit_attributes`: **True**
- `effective_rows_are_word_rows`: **True**
- `unresolved_effective_rows_have_null_canonical`: **True**
- `resolved_effective_rows_have_canonical_language`: **True**
- `protected_test_payloads_read_zero`: **True**
- `frozen_artifact_hashes_unchanged`: **True**
- `two_builds_and_persisted_table_logically_identical`: **True**
- `evidence_policy_manifest_completed`: **True**
- `parse_errors_fully_accounted`: **True**
- `non_primary_language_attributes_quarantined`: **True**
- `gate0_word_language_census_reconciled`: **True**

Gate 2 implementation may now join this span artifact to the frozen decomposed token keys. Protected-test access, training-dataset export, and GPU training remain unauthorized.