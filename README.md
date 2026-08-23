<!-- SPDX-License-Identifier: Apache-2.0 OR MIT>

<p align="center">
  <img src="https://cloudcdn.pro/clients/pacs008/v1/logos/pacs008.svg" alt="pacs008 logo" width="128" />
</p>

<h1 align="center">pacs008</h1>

<p align="center">
  A Python library for generating, validating, parsing and auditing
  ISO 20022 <code>pacs.008</code> FI-to-FI Customer Credit Transfer
  messages — with scheme-aware rules for CBPR+, HVPS+, Fedwire, CHAPS,
  T2 RTGS and SCT Inst.
</p>

<p align="center">
  <a href="https://github.com/sebastienrousseau/pacs008/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/sebastienrousseau/pacs008/ci.yml?branch=main&label=CI&style=for-the-badge" alt="CI" /></a>
  <a href="https://pypi.org/project/pacs008/"><img src="https://img.shields.io/pypi/v/pacs008?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI" /></a>
  <a href="https://pypi.org/project/pacs008/"><img src="https://img.shields.io/pypi/pyversions/pacs008.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python versions" /></a>
  <a href="https://pypi.org/project/pacs008/"><img src="https://img.shields.io/pypi/dm/pacs008.svg?style=for-the-badge" alt="PyPI Downloads" /></a>
  <a href="https://codecov.io/github/sebastienrousseau/pacs008?branch=main"><img src="https://img.shields.io/codecov/c/github/sebastienrousseau/pacs008?style=for-the-badge&logo=codecov" alt="Codecov" /></a>
  <a href="https://opensource.org/license/apache-2-0/"><img src="https://img.shields.io/pypi/l/pacs008?style=for-the-badge" alt="Licence" /></a>
  <a href="https://pacs008.com"><img src="https://img.shields.io/badge/Docs-pacs008.com-blue?style=for-the-badge" alt="Docs" /></a>
</p>

---

## Contents

**Getting started**

- [Install](#install) — pip, optional extras, from source
- [Quick Start](#quick-start) — generate a pacs.008 message in ten lines
- [Supported message types](#supported-message-types) — pacs/camt/head families
- [The pacs008 ecosystem](#the-pacs008-ecosystem) — library, CLI, REST API, scheme profiles, observability

**Usage**

- [Generate from a data source](#generate-from-a-data-source) — CSV / JSON / JSONL / SQLite / Parquet / Python objects
- [Apply a scheme profile](#apply-a-scheme-profile) — CBPR+, Fedwire, CHAPS, HVPS+, T2 RTGS, SCT Inst
- [Validate postal addresses (Nov 2026 cliff)](#validate-postal-addresses-nov-2026-cliff)
- [Validate LEI, IBAN and BIC](#validate-lei-iban-and-bic)
- [Check settlement dates against rail calendars](#check-settlement-dates-against-rail-calendars)
- [Cleanse text for the SWIFT character set](#cleanse-text-for-the-swift-character-set)
- [Wrap a message in a Business Application Header (BAH)](#wrap-a-message-in-a-business-application-header-bah)
- [Parse inbound messages by `MsgDefIdr`](#parse-inbound-messages-by-msgdefidr)
- [Stream large batches with constant memory](#stream-large-batches-with-constant-memory)
- [Split a batch to fit scheme cardinality](#split-a-batch-to-fit-scheme-cardinality)
- [Track Verification of Payee (VoP) results](#track-verification-of-payee-vop-results)
- [Detect duplicate submissions (idempotency)](#detect-duplicate-submissions-idempotency)
- [Sign a generation event for audit (DORA)](#sign-a-generation-event-for-audit-dora)
- [Emit OpenTelemetry spans](#emit-opentelemetry-spans)
- [Run the bundled examples](#run-the-bundled-examples) — `examples/`

**Interfaces**

- [Command-line interface](#command-line-interface) — flags, exit codes
- [REST API (FastAPI)](#rest-api-fastapi) — endpoints
- [Docker](#docker)

**Reference**

- [Input data format](#input-data-format) — required and optional columns
- [Architecture](#architecture) — package layout
- [Development](#development) — running the tests, quality gates
- [Security](#security)
- [Licence](#licence)

---

## Install

### From PyPI

```bash
pip install pacs008
```

The default install pulls in everything needed to generate and validate
pacs.008 messages from CSV / JSON / JSONL / SQLite / Parquet sources,
serve the FastAPI REST API, and run the CLI.

### Optional extras

| Extra | Activates | Install |
|---|---|---|
| `otel` | OpenTelemetry tracing spans around `process_files` | `pip install "pacs008[otel]"` |

### From source

```bash
git clone https://github.com/sebastienrousseau/pacs008.git
cd pacs008
poetry install --extras otel   # full dev environment
```

`pacs008` is tested on Python 3.10 — 3.12 across Ubuntu, macOS and Windows.

---

## Quick Start

Generate a pacs.008.001.08 message from a single Python dictionary:

```python
from pacs008 import generate_xml_string

payment = {
    "msg_id": "MSG-2026-001",
    "creation_date_time": "2026-06-13T10:30:00",
    "nb_of_txs": "1",
    "settlement_method": "CLRG",
    "interbank_settlement_date": "2026-06-15",
    "end_to_end_id": "E2E-INV-001",
    "tx_id": "TX-001",
    "uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "interbank_settlement_amount": "25000.00",
    "interbank_settlement_currency": "EUR",
    "charge_bearer": "SHAR",
    "debtor_name": "Acme Corp GmbH",
    "debtor_account_iban": "DE89370400440532013000",
    "debtor_agent_bic": "DEUTDEFF",
    "creditor_agent_bic": "BNPAFRPP",
    "creditor_name": "Widget Industries SA",
    "creditor_account_iban": "FR7630006000011234567890189",
    "remittance_information": "Invoice INV-2026-001",
}

xml = generate_xml_string(
    [payment],
    "pacs.008.001.08",
    "pacs008/templates/pacs.008.001.08/template.xml",
    "pacs008/templates/pacs.008.001.08/pacs.008.001.08.xsd",
)
# xml now contains an XSD-validated <Document>…</Document> ready to send.
```

Or from the command line:

```bash
pacs008 \
    -t pacs.008.001.08 \
    -m pacs008/templates/pacs.008.001.08/template.xml \
    -s pacs008/templates/pacs.008.001.08/pacs.008.001.08.xsd \
    -d payments.csv
```

Add `--dry-run` to validate without writing the output file (ideal for CI
pre-flight checks).

---

## Supported message types

Every shipped message family has a JSON Schema for input validation, a Jinja2
template for XML generation, and an XSD for output validation.

| Family | Versions shipped | Notes |
|---|---|---|
| `pacs.008` | `001.01` → `001.13` (13 versions) | FI-to-FI Customer Credit Transfer. `001.08+` adds UETR; `001.10+` adds mandate; `001.13` adds message expiry. |
| `pacs.002` | `001.12` | FI-to-FI Payment Status Report. |
| `pacs.003` | `001.09` | FI-to-FI Customer Direct Debit. |
| `pacs.004` | `001.11` | Payment Return. |
| `pacs.007` | `001.11` | FI-to-FI Payment Reversal. |
| `pacs.009` | `001.10` | Financial Institution Credit Transfer. |
| `pacs.010` | `001.05` | Financial Institution Direct Debit. |
| `pacs.028` | `001.05` | FI-to-FI Payment Status Request. |
| `head.001` | `001.02` | Business Application Header — used by [`pacs008.standards.bah`](#wrap-a-message-in-a-business-application-header-bah). |

---

## The pacs008 ecosystem

`pacs008` is a single Python package with a clear separation between
delivery surfaces and the typed business logic underneath. Every
sub-package can be used independently.

| Sub-package | Purpose |
|---|---|
| **`pacs008`** _(top-level)_ | `process_files`, `generate_xml_string` — the high-level generation entry points. |
| **`pacs008.cli`** | Click-based CLI (`pacs008 …`) — batch processing. |
| **`pacs008.api`** | FastAPI REST API with sync + async job endpoints. |
| **`pacs008.core`** | The generation pipeline plus the scheme-aware batch `splitter`. |
| **`pacs008.profiles`** | `SchemeProfile` ABC + 7 concrete profiles: `generic`, `cbpr_plus`, `fedwire`, `chaps`, `hvps_plus`, `t2_rtgs`, `sct_inst`. |
| **`pacs008.standards`** | Standards primitives — `PostalAddress` (Nov 2026 cliff), `wrap_in_bah` (head.001). |
| **`pacs008.validation`** | `IBAN`, `BIC`, `LEI` validators (ISO 13616 / 9362 / 17442); JSON Schema + XSD validators; rail holiday calendars. |
| **`pacs008.compliance`** | SWIFT-X / SWIFT-Z charset cleansing with `anyascii` fallback for non-Latin scripts. |
| **`pacs008.vop`** | EPC Verification of Payee result model (mandatory across SEPA since 9 Oct 2025). |
| **`pacs008.idempotency`** | Pluggable duplicate-detection (`MemoryStore`, `SQLiteStore`). |
| **`pacs008.observability`** | Structured JSON logging, request-id tracing, signed audit envelopes (Ed25519, DORA), optional OpenTelemetry. |
| **`pacs008.xml`** | Generation (`generate_xml`), constant-memory writer (`stream_writer`), inbound parser (`parser`). |
| **`pacs008.{csv,json,db,parquet}`** | Format-specific loaders + validators. |

---

## Usage

### Generate from a data source

`process_files` is the high-level entry point that loads, validates and
serialises a batch end-to-end.

```python
from pacs008 import process_files

process_files(
    xml_message_type="pacs.008.001.08",
    xml_template_file_path="pacs008/templates/pacs.008.001.08/template.xml",
    xsd_schema_file_path="pacs008/templates/pacs.008.001.08/pacs.008.001.08.xsd",
    data_file_path="payments.csv",
    # Optional: enforce a scheme rulebook (see below). Default: "generic".
    scheme="generic",
)
```

The `data_file_path` parameter accepts any of:

| Type | Extension or shape |
|---|---|
| CSV | `.csv` |
| JSON | `.json` (array of objects) |
| JSON Lines | `.jsonl` |
| SQLite | `.db` (table named `pacs008`) |
| Apache Parquet | `.parquet` |
| Python list | `list[dict[str, Any]]` |
| Python dict | single transaction as `dict[str, Any]` |

### Apply a scheme profile

A scheme profile encodes one rail's usage guideline: charge bearers,
UETR requirement, address policy, cardinality cap, version pinning,
character set and settlement calendar.

```python
from pacs008.profiles import get_profile

profile = get_profile("cbpr_plus")    # also: fedwire, chaps, hvps_plus, t2_rtgs, sct_inst, generic
print(profile.allowed_charge_bearers)  # frozenset({'CRED', 'DEBT', 'SHAR', 'SLEV'})
print(profile.max_transactions_per_msg)  # 10000
print(profile.pinned_versions()["pacs.008"])  # '001.08'  (MR2019 hold)
```

Apply it through `process_files` — `SchemeViolationError` carries every
finding in one batch so callers can surface them all at once.

```python
from pacs008 import process_files
from pacs008.profiles import SchemeViolationError

try:
    process_files(..., scheme="fedwire")
except SchemeViolationError as exc:
    for v in exc.violations:
        print(f"row {v.row}: {v.rule} — {v.message}")
```

### Validate postal addresses (Nov 2026 cliff)

On **14 November 2026** SWIFT CBPR+, HVPS+, T2 RTGS, CHAPS, Fedwire and Lynx
decommission fully unstructured postal addresses. `pacs008.standards.address`
classifies and remediates addresses ahead of the cliff.

```python
from datetime import date
from pacs008.standards.address import (
    AddressPolicy,
    PostalAddress,
    from_unstructured,
)

# Classify an address already in structured form.
addr = PostalAddress(
    strt_nm="High Street", bldg_nb="42",
    pst_cd="SW1A 1AA", twn_nm="London", ctry="GB",
)
addr.classify()       # AddressClassification.STRUCTURED
addr.is_structured()  # True

# Upgrade legacy unstructured lines to hybrid form (GB/US/DE/FR/JP heuristics).
hybrid = from_unstructured(
    ["42 High Street", "London SW1A 1AA"], country_hint="GB",
)
# hybrid.twn_nm == "London", hybrid.pst_cd == "SW1A 1AA", hybrid.ctry == "GB"

# Enforce a policy. After the cliff, HYBRID_OR_STRUCTURED rejects unstructured.
error = PostalAddress(adr_line=("42 High Street, London SW1A 1AA",)).validate(
    AddressPolicy.HYBRID_OR_STRUCTURED, today=date(2026, 11, 15),
)
# error contains a rejection reason citing the cliff date.
```

### Validate LEI, IBAN and BIC

ISO 17442 LEI (with ISO 7064 mod-97-10 checksum), ISO 13616 IBAN, ISO 9362 BIC:

```python
from pacs008.validation.lei_validator import validate_lei_safe
from pacs008.validation.iban_validator import validate_iban_safe
from pacs008.validation.bic_validator import validate_bic_safe

validate_lei_safe("HWUPKR0MPOU8FGXBT394")   # True   (Apple Inc.)
validate_iban_safe("DE89370400440532013000")  # True
validate_bic_safe("DEUTDEFF")                 # True
```

### Check settlement dates against rail calendars

Four calendars ship out of the box and compute holidays algorithmically — no
hard-coded date lists to keep up to date.

```python
from datetime import date
from pacs008.validation.calendar import (
    AlwaysOpenCalendar,  # FedNow, SCT Inst — 24/7
    CHAPSCalendar,       # Bank of England rules with weekend substitution
    FedwireCalendar,     # 11 US federal holidays incl. Juneteenth
    TARGETCalendar,      # ECB TARGET2 — 1 Jan, Good Friday, Easter Mon, 1 May, 25/26 Dec
)

cal = TARGETCalendar()
cal.is_open(date(2026, 12, 25))         # False (Christmas Day)
cal.next_business_day(date(2026, 12, 25))  # date(2026, 12, 28) — Mon
```

### Cleanse text for the SWIFT character set

Transliterates accented Latin and non-Latin scripts (Cyrillic, CJK, Arabic,
Greek, Hebrew, Devanagari) to the SWIFT-X or SWIFT-Z character set so SWIFT
gateways do not silently reject the message.

```python
from pacs008.compliance import cleanse_data_with_report

raw = [{"debtor_name": "Москва Müller", "msg_id": "X" * 50}]
clean, report = cleanse_data_with_report(raw)

# clean[0]["debtor_name"] == "Moskva Mueller"   (Cyrillic via anyascii; ü via map)
# len(clean[0]["msg_id"]) == 35                 (truncated to ISO 20022 max)
print(report.summary())
# "1 violations found across 1/1 rows. All auto-corrected."
```

Pass `policy="reject"` to raise `PaymentValidationError` instead of cleansing.

### Wrap a message in a Business Application Header (BAH)

CBPR+ and HVPS+ require every business message to be enveloped in a
`head.001.001.02` BAH.

```python
from pacs008 import generate_xml_string
from pacs008.standards.bah import wrap_in_bah

payload = generate_xml_string([payment], "pacs.008.001.08", template, xsd)

envelope = wrap_in_bah(
    payload,
    sender_bic="HSBCGB2L",
    receiver_bic="DEUTDEFF",
    biz_msg_idr="BIZMSG-2026-001",
    msg_def_idr="pacs.008.001.08",
    creation_dt="2026-06-13T10:30:00Z",
    priority="HIGH",       # optional: HIGH / NORM / URGT
)
# envelope is a BizMsgEnvlp/Hdr+Doc XML document ready to send.
```

### Parse inbound messages by `MsgDefIdr`

The inbound parser classifies any pacs/pain/camt/head/admi message — including
BAH-wrapped envelopes — by reading `AppHdr.MsgDefIdr` (or the root namespace
URI if no BAH is present).

```python
from pacs008.xml.parser import parse

msg = parse(open("inbound.xml", "rb").read())
msg.msg_family       # 'pacs.002'
msg.version          # '001.10'
msg.msg_def_idr      # 'pacs.002.001.10'
msg.envelope_wrapped # True
msg.bah.sender_bic   # 'DEUTDEFF'  (None if envelope_wrapped is False)
```

### Stream large batches with constant memory

For 100k-row batches the Jinja path would exhaust container memory; the
streaming writer keeps peak RSS bounded by one `<CdtTrfTxInf>` block.

```python
from pacs008.xml.stream_writer import write_stream

def rows():
    for i in range(100_000):
        yield {"msg_id": "BATCH001", "uetr": f"u{i}", ...}

with open("big.xml", "wb") as f:
    n = write_stream(rows(), output=f, msg_id="BATCH001")
# n == 100_000 — peak memory stays low because rows() is a generator.
```

### Split a batch to fit scheme cardinality

SCT Inst and Fedwire mandate exactly one transaction per file. Split a wide
batch lazily — `split_for_scheme` is a generator so a 1 M-row input does not
materialise all chunks at once.

```python
from pacs008.core.splitter import required_chunks, split_for_scheme

required_chunks(rows, "fedwire")     # math.ceil(len(rows) / 1)

for chunk in split_for_scheme(rows, "fedwire"):
    # Each chunk: list[dict] with a rewritten msg_id "BATCH001-0001", "-0002", …
    process_files(..., data_file_path=chunk, scheme="fedwire")
```

### Track Verification of Payee (VoP) results

EPC VoP is mandatory for eurozone PSPs since **9 October 2025**.

```python
from pacs008.vop import (
    VoPMatchResult,
    VoPResult,
    embed_in_row,
    validate_vop_results,
)

row = embed_in_row(
    {"msg_id": "M1"},
    VoPResult(
        result=VoPMatchResult.MATCH,
        name_compared="Alice Smith",
        iban="DE89370400440532013000",
    ),
)

# Audit a list of payment rows for VoP coverage and outcomes.
errors = validate_vop_results([row])  # [] — MATCH passes.
```

### Detect duplicate submissions (idempotency)

A pluggable store with in-memory (LRU + TTL) and persistent SQLite back-ends.
Default policy is `OnDuplicate.ERROR` — silent dedup is opt-in.

```python
from datetime import timedelta
from pacs008.idempotency import (
    IdempotencyViolation,
    MemoryStore,
    OnDuplicate,
    compute_payload_hash,
)

store = MemoryStore()
key = "MSG-2026-001"
payload_hash = compute_payload_hash({"msg_id": key, "amount": "25000.00"})

store.check(key, payload_hash, window=timedelta(hours=24))     # False — novel.

try:
    store.check(key, payload_hash, window=timedelta(hours=24))  # raises
except IdempotencyViolation as exc:
    print(f"Duplicate of {exc.previous.recorded_at.isoformat()}")
```

For persistence across process restarts:

```python
from pacs008.idempotency import SQLiteStore
store = SQLiteStore("/var/lib/pacs008/idempotency.db")
```

### Sign a generation event for audit (DORA)

A tamper-evident, Ed25519-signed summary suitable for DORA-aligned audit
trails — the validator decisions are stable strings that survive in your
SIEM long after the run.

```python
from pacs008.observability.audit import (
    Ed25519Signer,
    sign_envelope,
    verify_envelope,
)

signer = Ed25519Signer.generate()   # or .from_private_key_pem(pem_bytes)
record = sign_envelope(
    input_payload=open("payments.csv", "rb").read(),
    output_xml=xml.encode("utf-8"),
    validator_decisions=("swift_charset:cleansed", "scheme:cbpr_plus:ok"),
    scheme="cbpr_plus",
    signer=signer,
)

verify_envelope(record, public_key_bytes=signer.public_key_bytes())  # True
# record.to_dict() is JSON-serialisable and ready to ship to a SIEM.
```

### Emit OpenTelemetry spans

Install the optional extra (`pip install "pacs008[otel]"`); enable with the
`PACS008_OTEL_ENABLED` environment variable. When OTel is not installed the
helpers silently no-op so instrumentation can stay in production code.

```python
from pacs008.observability.otel import trace_span

with trace_span(
    "pacs008.generate",
    attributes={
        "pacs008.scheme": "cbpr_plus",
        "payment.uetr": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    },
):
    process_files(..., scheme="cbpr_plus")
```

### Run the bundled examples

Two ready-to-run scripts ship in the repository — useful as smoke tests after
install and as starting points for new integrations.

```bash
poetry run python examples/generate_xml.py       # generates output_pacs008.xml
poetry run python examples/swift_compliance.py   # demonstrates charset cleansing + report
```

Both scripts execute in CI on every push and are the canonical reference for
the "happy path" call sequence.

---

## Command-line interface

```bash
pacs008 \
    -t pacs.008.001.08 \
    -m pacs008/templates/pacs.008.001.08/template.xml \
    -s pacs008/templates/pacs.008.001.08/pacs.008.001.08.xsd \
    -d payments.csv \
    -o ./output \
    --verbose
```

| Flag | Description |
|---|---|
| `-t / --xml-message-type` | One of `pacs.008.001.01` … `pacs.008.001.13`. Required. |
| `-m / --template` | Path to the Jinja2 XML template. Required. |
| `-s / --schema` | Path to the XSD schema for output validation. Required. |
| `-d / --data` | Path to a CSV / JSON / JSONL / SQLite / Parquet file. Required. |
| `-o / --output-dir` | Output directory (default: current working directory). |
| `--dry-run` (alias `--validate-only`) | Validate inputs without writing XML. |
| `-v / --verbose` | Enable DEBUG-level logs. |
| `-h / --help` | Full help text. |

**Exit codes:** `0` success · `1` validation or processing error · `2` invalid
arguments.

---

## REST API (FastAPI)

```bash
uvicorn pacs008.api.app:app --host 0.0.0.0 --port 8000
# Interactive docs: http://localhost:8000/api/docs  (or /api/redoc)
```

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Liveness check + library version. |
| `POST` | `/api/validate` | Validate a data file against the schema. |
| `POST` | `/api/generate` | Synchronous XML generation. |
| `POST` | `/api/generate/async` | Submit an async generation job, returns `job_id`. |
| `GET` | `/api/status/{job_id}` | Poll an async job. |
| `DELETE` | `/api/jobs/{job_id}` | Cancel an async job. |
| `GET` | `/api/download/{job_id}` | Download the generated XML for a completed job. |

Example:

```bash
curl -X POST http://localhost:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "file_path": "/data/payments.csv",
    "data_source": "csv",
    "message_type": "pacs.008.001.08",
    "output_dir": "/data/out"
  }'
```

---

## Docker

```bash
docker build -t pacs008:local .
docker run --rm -p 8000:8000 pacs008:local
# The container starts uvicorn on :8000 with the API mounted at /api/*.
```

The image runs as a non-root `appuser`, ships a `/api/health` healthcheck, and
contains the production dependency set only (no dev tooling).

---

## Input data format

### Required columns

| Field | Description | Example |
|---|---|---|
| `msg_id` | Message identifier (max 35 chars) | `MSG-2026-001` |
| `creation_date_time` | ISO 8601 timestamp | `2026-06-13T10:30:00` |
| `nb_of_txs` | Number of transactions | `1` |
| `settlement_method` | `CLRG`, `INDA`, `COVE` or `INGA` | `CLRG` |
| `interbank_settlement_date` | Settlement date (ISO 8601) | `2026-06-15` |
| `end_to_end_id` | End-to-end identifier (max 35 chars) | `E2E-INV-001` |
| `tx_id` | Transaction identifier | `TX-001` |
| `interbank_settlement_amount` | Decimal amount | `25000.00` |
| `interbank_settlement_currency` | ISO 4217 code | `EUR` |
| `charge_bearer` | `DEBT`, `CRED`, `SHAR` or `SLEV` | `SHAR` |
| `debtor_name` | Debtor name (max 140 chars) | `Acme Corp GmbH` |
| `debtor_agent_bic` | Debtor bank BIC (8 or 11 chars) | `DEUTDEFF` |
| `creditor_agent_bic` | Creditor bank BIC (8 or 11 chars) | `BNPAFRPP` |
| `creditor_name` | Creditor name (max 140 chars) | `Widget Industries SA` |

> **Numeric fields accept both forms.** `nb_of_txs` and
> `interbank_settlement_amount` validate whether supplied as native JSON
> numbers (`1`, `25000.00`) or as numeric strings (`"1"`, `"25000.00"`) — the
> latter being what CSV rows and many JSON producers emit. Numeric bounds
> still apply (`nb_of_txs` ≥ 1; a positive decimal amount), and non-numeric
> values are still rejected.

### Version-specific columns

| Field | Available from | Description |
|---|---|---|
| `uetr` | `001.08+` | UUID v4 (36 chars) — UETR for SWIFT gpi tracking. |
| `mandate_id` | `001.10+` | Mandate identifier (max 35 chars). |
| `expiry_date_time` | `001.13` | ISO 8601 timestamp — message expiry. |

### Optional scheme-aware columns

| Prefix | Used by |
|---|---|
| `{party}_lei` | `validate_leis` and `CHAPSProfile` (FI fields required). `{party}` ∈ {`debtor`, `creditor`, `debtor_agent`, `creditor_agent`, `ultimate_debtor`, `ultimate_creditor`}. |
| `{party}_address_{field}` | `validate_addresses` — `{field}` ∈ {`strt_nm`, `bldg_nb`, `pst_cd`, `twn_nm`, `ctry`, …} or `adr_line_0` … `adr_line_6`. |
| `vop_result`, `vop_iban`, `vop_name_compared`, `vop_reason_code`, `vop_performed_at` | `pacs008.vop` — EPC Verification of Payee. |

---

## Architecture

```
pacs008/
├── api/              # FastAPI REST app, async job manager
├── cli/              # Click CLI
├── compliance/       # SWIFT X / Z charset cleansing (anyascii fallback)
├── core/             # process_files pipeline + scheme-aware batch splitter
├── csv/  json/  db/  parquet/   # Format-specific loaders + validators
├── data/             # Universal data loader
├── idempotency/      # IdempotencyStore ABC + MemoryStore + SQLiteStore
├── observability/    # Structured JSON logs, request-id tracing,
│                       Ed25519 audit envelope, optional OpenTelemetry
├── profiles/         # SchemeProfile ABC + Generic, CBPR+, Fedwire,
│                       CHAPS, HVPS+, T2 RTGS, SCT Inst profiles
├── schemas/          # 20 JSON schemas for input validation
├── security/         # Path traversal prevention
├── standards/        # PostalAddress (Nov 2026 cliff), wrap_in_bah (head.001)
├── templates/        # 20 Jinja2 templates + XSD schemas
├── validation/       # IBAN, BIC, LEI, JSON Schema, XSD, holiday calendars
├── vop/              # EPC Verification of Payee result model
└── xml/              # generate_xml, stream_writer, inbound parser
```

### Generation pipeline

```mermaid
flowchart LR
    A["CSV / JSON / JSONL /
       SQLite / Parquet"] --> B[Data Loader]
    B --> C[Schema Validation]
    C --> D["Scheme Profile
             (optional)"]
    D --> E[SWIFT Charset Cleansing]
    E --> F[Jinja2 Template]
    F --> G[XSD Validation]
    G --> H[pacs.008 XML]
```

---

## Development

```bash
git clone https://github.com/sebastienrousseau/pacs008.git
cd pacs008
poetry install --extras otel
poetry shell

make check       # ruff + black + mypy + bandit + pytest + example scripts
make test        # pytest with coverage
make test-fast   # pytest without coverage
make lint        # ruff + black --check
make type-check  # mypy --strict
```

Quality gates (CI-enforced):

| Gate | Tool |
|---|---|
| Lint | `ruff check pacs008/` |
| Format | `black --check pacs008/ tests/` |
| Types | `mypy pacs008/` (strict mode) |
| Tests | `pytest --cov=pacs008` (90% branch-coverage floor) |
| Security | `bandit -r pacs008/` |
| Smoke | `pytest -m smoke` |
| Cross-platform matrix | Python 3.10 — 3.12 × Ubuntu / macOS / Windows |

---

## Security

Security issues should be reported **privately** via GitHub's [Security
Advisories](https://github.com/sebastienrousseau/pacs008/security/advisories/new)
or by email to `contact@sebastienrousseau.com`. See [`SECURITY.md`](./SECURITY.md)
for the full disclosure policy, SLA targets, and hardening guidance for
production deployments.

Highlights:

- XXE protection via `defusedxml` on every parse path.
- Path-traversal protection in `pacs008.security.path_validator`.
- Automatic PII redaction (IBAN / BIC / name / account) in structured logs.
- Tamper-evident Ed25519-signed audit records for every generation event.

---

## Licence

Licensed under the [Apache Licence, Version 2.0](https://opensource.org/license/apache-2-0/).
See [`LICENSE`](./LICENSE) for the full text. Unless you explicitly state
otherwise, any contribution intentionally submitted for inclusion in the work
shall be licensed as above, without any additional terms or conditions.

---

## Contributing

Contributions are welcome — please read [`CONTRIBUTING.md`](./CONTRIBUTING.md)
first. All contributors agree to abide by the project's code of conduct, and
all pull requests must pass the full CI matrix (`make check`).

Thanks to all our [contributors](https://github.com/sebastienrousseau/pacs008/graphs/contributors).
