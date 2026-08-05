# camt.110.001.01 — Investigation Request

**Status: schema only. This message type is not yet supported by the library.**

`camt.110.001.01` is deliberately absent from `valid_xml_types` in
`pacs008/constants.py`. The schema being present is not the same as the message
being supported, and listing it before it works would claim a capability the
package does not have.

## Why this schema is here

From **November 2026**, all Swift users must be able to receive and consume
`camt.110` investigation requests. From **November 2027**, `camt.110` and
`camt.111` both become mandatory, replacing the retiring free-format MT
Exceptions & Investigations messages.

Inflow translation from `camt.110` to MT199 exists as a transition aid, but
because `camt.110` is highly structured and MT199 is free format, the result is
technically valid and operationally poor. It is a bridge, not a destination.

Tracked in [#12](https://github.com/sebastienrousseau/pacs008/issues/12).

## What is still needed

Compare against any supported family, for example
`pacs008/templates/pacs.008.001.13/`, which contains three files:

| File | Status | Notes |
|---|---|---|
| `camt.110.001.01.xsd` | **Present** | Official schema, self-contained, no imports |
| `camt.110.001.01.xml` | Missing | A realistic sample message |
| `template.xml` | Missing | The same structure with `{{placeholder}}` fields |

Then:

1. Add `"camt.110.001.01"` to `valid_xml_types` in `pacs008/constants.py`.
2. Decide the direction of support. The November 2026 obligation is to
   **receive and consume**, so parsing and validation matter more than
   generation. That is the opposite of the pacs.008 path, where generation came
   first, and the template may not be the most useful artefact to build first.
3. Add tests, including a sample that fails validation, so the checks are known
   to fire.

The sample and template are not included here on purpose. They require
judgement about which investigation types and reason codes are representative,
and inventing that content would produce something that looks authoritative and
is not.

## Provenance

Schema obtained from the ISO 20022 Registration Authority. See the `NOTICE`
file at the repository root for attribution and terms.
