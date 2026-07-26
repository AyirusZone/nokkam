# Security Policy

## Supported Versions

cad-tui is a single-user, local-only terminal application with no network
listeners and no server component. Security fixes are released against the
latest minor version on PyPI; there is no long-term support branch.

| Version | Supported          |
| ------- | ------------------- |
| Latest  | :white_check_mark:  |
| Older   | :x:                  |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it privately rather
than opening a public issue:

- Open a [GitHub Security Advisory](https://github.com/AyirusZone/cad_tui/security/advisories/new)
  for this repository, or
- Email suriyarajan12@gmail.com with a description of the issue and steps to
  reproduce.

Please do not disclose the issue publicly until a fix has been released.

You can expect an initial response within 5 business days. If the report is
confirmed, a fix will be prioritized and a new release published; you'll be
credited in the release notes unless you'd prefer otherwise.

## Scope

Given cad-tui's local-only nature, reports of interest include (but aren't
limited to):

- Arbitrary code execution via crafted import/export files
- SQL injection in the local SQLite layer
- Path traversal via configuration or CLI arguments

Reports about the CI/CD pipeline (e.g. workflow permissions, supply-chain
concerns in dependencies) are also welcome.
