# Security Policy

## Supported versions

Security fixes are applied to the latest released version on PyPI and the
`main` branch. The table below tracks which series receive fixes.

| Version | Supported |
|---------|-----------|
| `0.0.7` | Latest released `0.0.x` only |
| < `0.0.7` | No |

A longer-term support window will be announced here once `1.0.0` ships.

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues privately by either:

1. **Preferred:** GitHub's private vulnerability reporting — open a draft
   advisory at <https://github.com/sebastienrousseau/pacs008/security/advisories/new>.
2. **Email:** `contact@sebastienrousseau.com` with the subject line
   `[pacs008 security]`.

Include, where possible:

- A description of the issue and its impact (confidentiality, integrity,
  availability).
- Steps to reproduce, ideally with a minimal proof of concept.
- The affected version(s) and platform(s).
- Any suggested mitigation or fix.

## What to expect

| Stage | Target |
|-------|--------|
| Acknowledgement | Within 3 business days |
| Initial assessment | Within 10 business days |
| Fix or mitigation plan | Within 30 days for high/critical severity |
| Public disclosure | Coordinated with reporter after a fix is available |

For low-severity issues, the timeline may be longer. We will keep you updated
on progress.

## Scope

In scope:

- Code under `pacs008/` shipped to PyPI.
- The Dockerfile and example scripts under `examples/`.
- Default configuration of the FastAPI app.

Out of scope:

- Third-party dependencies (please report upstream — we will track the
  advisory and update our pinned ranges).
- Vulnerabilities that require local code execution on the host already
  running `pacs008`.
- Denial-of-service via deliberately crafted input that exceeds documented
  size limits (open a feature request to add a guard instead).

## Hardening guidance for operators

If you deploy `pacs008` (CLI, library, or REST API) in production:

- Run the FastAPI app behind a reverse proxy that enforces TLS, rate
  limiting, and authentication.
- Validate paths passed to `process_files` come from a trusted source.
  `pacs008.security.path_validator` is a defence in depth, not a
  substitute for input validation.
- Keep `pacs008`, its runtime dependencies, and the Python interpreter
  patched.
- Treat generated XML as potentially containing PII subject to
  GDPR/PCI-DSS — encrypt at rest and in transit.

## Credits

We will credit reporters who follow this policy in release notes and the
GitHub advisory, unless they request anonymity.
