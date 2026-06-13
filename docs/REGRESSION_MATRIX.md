# Regression coverage matrix

Generated from AST inspection of `pacs008/` and grep against
`tests/test_*.py`. Each row maps a public top-level symbol
(class, function, or coroutine) to test files that reference
it **either** by identifier **or** by importing the module
that defines it. The second condition catches FastAPI route
handlers tested via `TestClient` calls and pydantic models
used only as response types — where the symbol name does not
appear in test source.

**Regeneration command:**

```bash
poetry run python scripts/regression_matrix.py > docs/REGRESSION_MATRIX.md
```

## `pacs008/__main__.py`

| Symbol | Line | Test files |
|---|---|---|
| `main` | 15 | `test_bic_validator.py`, `test_cli_full.py`, `test_cli_integration.py`, `test_iban_validator.py`, `test_main_entry.py`, `test_perf_baseline.py` |

## `pacs008/api/app.py`

| Symbol | Line | Test files |
|---|---|---|
| `cancel_job` | 442 | `test_api.py`, `test_api_extended.py`, `test_api_full.py`, `test_job_manager.py` |
| `download_xml` | 474 | `test_api.py`, `test_api_extended.py`, `test_api_full.py` |
| `generate_xml_async` | 359 | `test_api.py`, `test_api_extended.py`, `test_api_full.py` |
| `generate_xml_sync` | 263 | `test_api.py`, `test_api_extended.py`, `test_api_full.py` |
| `get_job_status` | 399 | `test_api.py`, `test_api_extended.py`, `test_api_full.py` |
| `health` | 182 | `test_api.py`, `test_api_extended.py`, `test_api_full.py` |
| `validate_data` | 201 | `test_api.py`, `test_api_extended.py`, `test_api_full.py`, `test_validation.py` |

## `pacs008/api/job_manager.py`

| Symbol | Line | Test files |
|---|---|---|
| `JobManager` | 73 | `test_api_extended.py`, `test_api_full.py`, `test_job_manager.py` |
| `JobResult` | 34 | `test_api_extended.py`, `test_api_full.py`, `test_job_manager.py` |
| `JobStatus` | 24 | `test_api_extended.py`, `test_api_full.py`, `test_job_manager.py` |

## `pacs008/api/models.py`

| Symbol | Line | Test files |
|---|---|---|
| `DataSourceType` | 26 | `test_api_extended.py`, `test_api_full.py`, `test_api_models.py` |
| `GenerateXMLRequest` | 83 | `test_api_extended.py`, `test_api_full.py`, `test_api_models.py` |
| `GenerateXMLResponse` | 153 | `test_api_extended.py`, `test_api_full.py`, `test_api_models.py` |
| `HealthResponse` | 188 | `test_api_extended.py`, `test_api_full.py`, `test_api_models.py` |
| `JobStatusResponse` | 165 | `test_api_extended.py`, `test_api_full.py`, `test_api_models.py` |
| `MessageType` | 36 | `test_api_extended.py`, `test_api_full.py`, `test_api_models.py` |
| `ValidationError` | 111 | `test_api_extended.py`, `test_api_full.py`, `test_api_models.py`, `test_coverage_fillers.py` |
| `ValidationRequest` | 61 | `test_api_extended.py`, `test_api_full.py`, `test_api_models.py` |
| `ValidationResponse` | 119 | `test_api_extended.py`, `test_api_full.py`, `test_api_models.py` |

## `pacs008/cli/cli.py`

| Symbol | Line | Test files |
|---|---|---|
| `main` | 359 | `test_bic_validator.py`, `test_cli_full.py`, `test_cli_integration.py`, `test_iban_validator.py`, `test_main_entry.py`, `test_perf_baseline.py` |

## `pacs008/compliance/swift_charset.py`

| Symbol | Line | Test files |
|---|---|---|
| `ComplianceReport` | 229 | `test_compliance.py`, `test_gold_master.py`, `test_swift_charset_extended.py` |
| `ComplianceViolation` | 204 | `test_compliance.py`, `test_gold_master.py`, `test_swift_charset_extended.py` |
| `cleanse_data` | 430 | `test_compliance.py`, `test_enterprise_xsd.py`, `test_gold_master.py`, `test_perf_baseline.py`, `test_swift_charset_extended.py` |
| `cleanse_data_with_report` | 483 | `test_compliance.py`, `test_gold_master.py`, `test_swift_charset_extended.py` |
| `cleanse_string` | 329 | `test_compliance.py`, `test_gold_master.py`, `test_swift_charset_extended.py` |
| `enforce_field_lengths` | 375 | `test_compliance.py`, `test_gold_master.py`, `test_swift_charset_extended.py` |
| `validate_swift_charset` | 311 | `test_compliance.py`, `test_gold_master.py`, `test_swift_charset_extended.py` |

## `pacs008/context/context.py`

| Symbol | Line | Test files |
|---|---|---|
| `Context` | 20 | `test_cli_full.py`, `test_context.py` |

## `pacs008/core/core.py`

| Symbol | Line | Test files |
|---|---|---|
| `process_files` | 316 | `test_calendar.py`, `test_core_process.py`, `test_core_scheme.py`, `test_profiles_extended.py` |

## `pacs008/core/splitter.py`

| Symbol | Line | Test files |
|---|---|---|
| `required_chunks` | 63 | `test_perf_baseline.py`, `test_splitter.py` |
| `split_for_scheme` | 92 | `test_perf_baseline.py`, `test_splitter.py` |

## `pacs008/csv/load_csv_data.py`

| Symbol | Line | Test files |
|---|---|---|
| `load_csv_data` | 28 | `test_csv_loader.py`, `test_gold_master.py` |
| `load_csv_data_streaming` | 98 | `test_csv_loader.py`, `test_gold_master.py` |

## `pacs008/csv/validate_csv_data.py`

| Symbol | Line | Test files |
|---|---|---|
| `validate_csv_data` | 156 | `test_csv_validate.py` |

## `pacs008/data/loader.py`

| Symbol | Line | Test files |
|---|---|---|
| `load_payment_data` | 82 | `test_data_loader.py`, `test_data_loader_extended.py` |
| `load_payment_data_streaming` | 236 | `test_data_loader.py`, `test_data_loader_extended.py` |

## `pacs008/db/load_db_data.py`

| Symbol | Line | Test files |
|---|---|---|
| `load_db_data` | 59 | `test_db_loader.py` |
| `sanitize_table_name` | 29 | `test_db_loader.py` |

## `pacs008/db/load_db_data_streaming.py`

| Symbol | Line | Test files |
|---|---|---|
| `load_db_data_streaming` | 27 | `test_db_loader.py` |

## `pacs008/db/validate_db_data.py`

| Symbol | Line | Test files |
|---|---|---|
| `validate_db_data` | 24 | `test_db_loader.py` |

## `pacs008/exceptions.py`

| Symbol | Line | Test files |
|---|---|---|
| `ConfigurationError` | 119 | `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py`, `test_db_loader.py` _(+6 more)_ |
| `DataSourceError` | 139 | `test_api_full.py`, `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py` _(+7 more)_ |
| `InvalidBICError` | 229 | `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py`, `test_db_loader.py` _(+6 more)_ |
| `InvalidIBANError` | 191 | `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py`, `test_db_loader.py` _(+6 more)_ |
| `InvalidLEIError` | 267 | `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py`, `test_db_loader.py` _(+6 more)_ |
| `MissingRequiredFieldError` | 314 | `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py`, `test_db_loader.py` _(+6 more)_ |
| `Pacs008Error` | 54 | `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py`, `test_db_loader.py` _(+6 more)_ |
| `PaymentValidationError` | 70 | `test_api_full.py`, `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py` _(+7 more)_ |
| `SchemaValidationError` | 158 | `test_api_full.py`, `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py` _(+7 more)_ |
| `XMLGenerationError` | 99 | `test_bic_validator.py`, `test_core_process.py`, `test_csv_loader.py`, `test_data_loader.py`, `test_data_loader_extended.py`, `test_db_loader.py` _(+6 more)_ |

## `pacs008/idempotency/base.py`

| Symbol | Line | Test files |
|---|---|---|
| `IdempotencyEntry` | 62 | `test_idempotency.py` |
| `IdempotencyStore` | 70 | `test_idempotency.py` |
| `IdempotencyViolation` | 44 | `test_idempotency.py` |
| `OnDuplicate` | 31 | `test_idempotency.py` |
| `compute_payload_hash` | 142 | `test_idempotency.py` |

## `pacs008/idempotency/memory.py`

| Symbol | Line | Test files |
|---|---|---|
| `MemoryStore` | 27 | `test_idempotency.py` |

## `pacs008/idempotency/sqlite.py`

| Symbol | Line | Test files |
|---|---|---|
| `SQLiteStore` | 28 | `test_idempotency.py` |

## `pacs008/json/load_json_data.py`

| Symbol | Line | Test files |
|---|---|---|
| `load_json_data` | 31 | `test_json_loader.py` |
| `load_json_data_streaming` | 106 | `test_json_loader.py` |
| `load_jsonl_data` | 138 | `test_json_loader.py` |
| `load_jsonl_data_streaming` | 207 | `test_json_loader.py` |

## `pacs008/observability/audit.py`

| Symbol | Line | Test files |
|---|---|---|
| `AuditRecord` | 141 | `test_audit.py` |
| `Ed25519Signer` | 86 | `test_audit.py` |
| `Signer` | 65 | `test_audit.py` |
| `sign_envelope` | 182 | `test_audit.py` |
| `verify_envelope` | 233 | `test_audit.py` |

## `pacs008/observability/events.py`

| Symbol | Line | Test files |
|---|---|---|
| `Events` | 35 | `test_logging_schema.py` |
| `log_data_load_event` | 229 | `test_logging_schema.py` |
| `log_event` | 72 | `test_logging_schema.py` |
| `log_process_error` | 168 | `test_logging_schema.py` |
| `log_process_start` | 111 | `test_logging_schema.py` |
| `log_process_success` | 140 | `test_logging_schema.py` |
| `log_validation_event` | 193 | `test_logging_schema.py` |
| `log_xml_generation_event` | 267 | `test_logging_schema.py` |

## `pacs008/observability/fields.py`

| Symbol | Line | Test files |
|---|---|---|
| `ExecutionStatus` | 34 | `test_logging_schema.py` |
| `Fields` | 43 | `test_logging_schema.py` |
| `LogLevel` | 24 | `test_logging_schema.py` |

## `pacs008/observability/formatters.py`

| Symbol | Line | Test files |
|---|---|---|
| `JSONFormatter` | 31 | `test_coverage_fillers.py`, `test_logging_schema.py` |
| `configure_json_logging` | 71 | `test_coverage_fillers.py`, `test_logging_schema.py` |

## `pacs008/observability/metrics.py`

| Symbol | Line | Test files |
|---|---|---|
| `ExecutionMetrics` | 202 | `test_logging_schema.py` |
| `ExecutionSummaryTracker` | 36 | `test_logging_schema.py` |

## `pacs008/observability/otel.py`

| Symbol | Line | Test files |
|---|---|---|
| `add_attribute` | 114 | `test_otel.py` |
| `is_enabled` | 66 | `test_otel.py` |
| `trace_span` | 81 | `test_otel.py` |

## `pacs008/observability/redaction.py`

| Symbol | Line | Test files |
|---|---|---|
| `mask_sensitive_data` | 27 | `test_logging_schema.py` |

## `pacs008/observability/tracing.py`

| Symbol | Line | Test files |
|---|---|---|
| `generate_request_id` | 40 | `test_logging_schema.py` |
| `get_request_id` | 54 | `test_logging_schema.py` |
| `set_request_id` | 71 | `test_logging_schema.py` |

## `pacs008/parquet/load_parquet_data.py`

| Symbol | Line | Test files |
|---|---|---|
| `load_parquet_data` | 50 | `test_parquet_loader.py` |
| `load_parquet_data_streaming` | 110 | `test_parquet_loader.py` |

## `pacs008/profiles/base.py`

| Symbol | Line | Test files |
|---|---|---|
| `BusinessRuleViolation` | 45 | `test_profiles.py` |
| `SchemeProfile` | 93 | `test_profiles.py` |
| `SchemeViolationError` | 69 | `test_calendar.py`, `test_core_scheme.py`, `test_profiles.py`, `test_profiles_extended.py` |
| `get_profile` | 309 | `test_profiles.py`, `test_profiles_extended.py` |
| `list_profiles` | 326 | `test_profiles.py`, `test_profiles_extended.py` |
| `register_profile` | 300 | `test_profiles.py` |

## `pacs008/profiles/cbpr_plus.py`

| Symbol | Line | Test files |
|---|---|---|
| `CBPRPlusProfile` | 51 | `test_calendar.py`, `test_profiles.py`, `test_swift_charset_extended.py` |

## `pacs008/profiles/chaps.py`

| Symbol | Line | Test files |
|---|---|---|
| `CHAPSProfile` | 44 | `test_profiles_extended.py` |

## `pacs008/profiles/fedwire.py`

| Symbol | Line | Test files |
|---|---|---|
| `FedwireProfile` | 53 | `test_calendar.py`, `test_profiles.py`, `test_splitter.py`, `test_swift_charset_extended.py` |

## `pacs008/profiles/generic.py`

| Symbol | Line | Test files |
|---|---|---|
| `GenericProfile` | 32 | `test_calendar.py`, `test_profiles.py`, `test_swift_charset_extended.py` |

## `pacs008/profiles/hvps_plus.py`

| Symbol | Line | Test files |
|---|---|---|
| `HVPSPlusProfile` | 47 | `test_profiles_extended.py` |

## `pacs008/profiles/sct_inst.py`

| Symbol | Line | Test files |
|---|---|---|
| `SCTInstProfile` | 46 | `test_profiles_extended.py` |

## `pacs008/profiles/t2_rtgs.py`

| Symbol | Line | Test files |
|---|---|---|
| `T2RTGSProfile` | 36 | `test_profiles_extended.py` |

## `pacs008/security/path_validator.py`

| Symbol | Line | Test files |
|---|---|---|
| `PathValidationError` | 11 | `test_path_validator.py` |
| `SecurityError` | 15 | `test_path_validator.py` |
| `sanitize_for_log` | 106 | `test_path_validator.py` |
| `validate_path` | 88 | `test_path_validator.py` |

## `pacs008/standards/address.py`

| Symbol | Line | Test files |
|---|---|---|
| `AddressClassification` | 72 | `test_address.py`, `test_profiles.py`, `test_profiles_extended.py` |
| `AddressPolicy` | 80 | `test_address.py`, `test_profiles.py`, `test_profiles_extended.py` |
| `AddressValidationError` | 641 | `test_address.py`, `test_profiles.py`, `test_profiles_extended.py` |
| `PostalAddress` | 155 | `test_address.py`, `test_profiles.py`, `test_profiles_extended.py` |
| `Severity` | 101 | `test_address.py`, `test_profiles.py`, `test_profiles_extended.py` |
| `from_unstructured` | 382 | `test_address.py`, `test_profiles.py`, `test_profiles_extended.py` |
| `validate_addresses` | 660 | `test_address.py`, `test_profiles.py`, `test_profiles_extended.py` |

## `pacs008/standards/bah.py`

| Symbol | Line | Test files |
|---|---|---|
| `BusinessApplicationHeader` | 70 | `test_bah.py`, `test_parser.py` |
| `extract_bah_fields` | 207 | `test_bah.py`, `test_parser.py` |
| `wrap_in_bah` | 135 | `test_bah.py`, `test_parser.py` |

## `pacs008/validation/bic_validator.py`

| Symbol | Line | Test files |
|---|---|---|
| `validate_bic` | 221 | `test_bic_validator.py` |
| `validate_bic_format` | 143 | `test_bic_validator.py` |
| `validate_bic_safe` | 266 | `test_bic_validator.py` |

## `pacs008/validation/calendar.py`

| Symbol | Line | Test files |
|---|---|---|
| `AlwaysOpenCalendar` | 182 | `test_calendar.py`, `test_profiles_extended.py` |
| `CHAPSCalendar` | 301 | `test_calendar.py`, `test_profiles_extended.py` |
| `Calendar` | 139 | `test_calendar.py`, `test_profiles_extended.py` |
| `FedwireCalendar` | 229 | `test_calendar.py`, `test_profiles_extended.py` |
| `SettlementDateError` | 418 | `test_calendar.py`, `test_profiles_extended.py` |
| `TARGETCalendar` | 192 | `test_calendar.py`, `test_profiles_extended.py` |
| `compute_easter` | 82 | `test_calendar.py`, `test_profiles_extended.py` |
| `get_calendar` | 387 | `test_calendar.py`, `test_profiles_extended.py` |
| `list_calendars` | 401 | `test_calendar.py`, `test_profiles_extended.py` |
| `register_calendar` | 382 | `test_calendar.py`, `test_profiles_extended.py` |
| `validate_settlement_dates` | 465 | `test_calendar.py`, `test_profiles_extended.py` |

## `pacs008/validation/iban_validator.py`

| Symbol | Line | Test files |
|---|---|---|
| `validate_iban` | 243 | `test_iban_validator.py` |
| `validate_iban_checksum` | 192 | `test_iban_validator.py` |
| `validate_iban_format` | 121 | `test_iban_validator.py` |
| `validate_iban_safe` | 300 | `test_iban_validator.py` |

## `pacs008/validation/lei_validator.py`

| Symbol | Line | Test files |
|---|---|---|
| `LEIValidationError` | 243 | `test_lei_validator.py`, `test_perf_baseline.py` |
| `validate_lei` | 152 | `test_lei_validator.py`, `test_perf_baseline.py` |
| `validate_lei_checksum` | 121 | `test_lei_validator.py`, `test_perf_baseline.py` |
| `validate_lei_format` | 81 | `test_lei_validator.py`, `test_perf_baseline.py` |
| `validate_lei_safe` | 211 | `test_lei_validator.py`, `test_perf_baseline.py` |
| `validate_leis` | 284 | `test_lei_validator.py`, `test_perf_baseline.py` |

## `pacs008/validation/schema_validator.py`

| Symbol | Line | Test files |
|---|---|---|
| `SchemaValidator` | 78 | `test_api_full.py`, `test_coverage_fillers.py`, `test_validation.py` |
| `ValidationError` | 46 | `test_api_full.py`, `test_coverage_fillers.py`, `test_validation.py` |

## `pacs008/validation/service.py`

| Symbol | Line | Test files |
|---|---|---|
| `ValidationConfig` | 72 | `test_validation.py`, `test_validation_service.py` |
| `ValidationReport` | 91 | `test_validation.py`, `test_validation_service.py` |
| `ValidationResult` | 55 | `test_validation.py`, `test_validation_service.py` |
| `ValidationService` | 105 | `test_validation.py`, `test_validation_service.py` |

## `pacs008/vop/match.py`

| Symbol | Line | Test files |
|---|---|---|
| `VoPMatchResult` | 26 | `test_vop.py` |
| `VoPResult` | 58 | `test_vop.py` |
| `VoPValidationError` | 168 | `test_vop.py` |
| `embed_in_row` | 110 | `test_vop.py` |
| `extract_from_row` | 138 | `test_vop.py` |
| `validate_vop_results` | 181 | `test_vop.py` |

## `pacs008/xml/generate_updated_xml_file_path.py`

| Symbol | Line | Test files |
|---|---|---|
| `generate_updated_xml_file_path` | 23 | `test_coverage_fillers.py` |

## `pacs008/xml/generate_xml.py`

| Symbol | Line | Test files |
|---|---|---|
| `generate_xml` | 453 | `test_compliance.py`, `test_enterprise_xsd.py`, `test_generate_xml.py`, `test_gold_master.py`, `test_new_message_types.py`, `test_version_matrix.py` _(+1 more)_ |
| `generate_xml_string` | 379 | `test_compliance.py`, `test_enterprise_xsd.py`, `test_generate_xml.py`, `test_gold_master.py`, `test_new_message_types.py`, `test_perf_baseline.py` _(+2 more)_ |

## `pacs008/xml/parser.py`

| Symbol | Line | Test files |
|---|---|---|
| `ParseError` | 75 | `test_parser.py` |
| `ParsedMessage` | 80 | `test_parser.py` |
| `parse` | 106 | `test_parser.py`, `test_vop.py` |

## `pacs008/xml/register_namespaces.py`

| Symbol | Line | Test files |
|---|---|---|
| `register_namespaces` | 23 | `test_coverage_fillers.py` |

## `pacs008/xml/stream_writer.py`

| Symbol | Line | Test files |
|---|---|---|
| `write_stream` | 73 | `test_stream_writer.py` |

## `pacs008/xml/validate_via_xsd.py`

| Symbol | Line | Test files |
|---|---|---|
| `validate_via_xsd` | 31 | `test_cli_full.py`, `test_xsd_validation.py` |
| `validate_xml_string_via_xsd` | 66 | `test_xsd_validation.py` |

## `pacs008/xml/write_xml_to_file.py`

| Symbol | Line | Test files |
|---|---|---|
| `indent_xml` | 25 | `test_write_xml.py` |
| `write_xml_to_file` | 53 | `test_write_xml.py` |

## `pacs008/xml/xml_to_string.py`

| Symbol | Line | Test files |
|---|---|---|
| `xml_to_string` | 26 | `test_write_xml.py` |


## Summary

- **Public top-level symbols inspected:** 167
- **Referenced by ≥1 test file:** 167 (100%)
- **Without test reference:** 0

✅ Every public top-level symbol is referenced by ≥1 test file.
