# Security Policy

## Supported Versions

This project is currently in active beta development.

Security fixes are prioritized for:

| Version / Branch                  | Supported        |
| --------------------------------- | ---------------- |
| `main`                            | Yes              |
| latest deployed Streamlit version | Yes              |
| older local test copies           | Best effort only |

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for security vulnerabilities.

Use one of these safe reporting paths:

1. GitHub private vulnerability reporting, if enabled.
2. GitHub Security Advisory reporting.
3. A private message to the repository owner if GitHub private reporting is unavailable.

When reporting, include:

* A clear description of the issue.
* Steps to reproduce.
* Affected file or feature.
* Screenshots or logs if safe.
* Whether the issue exposes secrets, local files, user paths, credentials, or system data.
* Whether the issue affects the Streamlit app, local storage audit, OCR feature, profile export, cleanup/trash system, or dependency setup.

## Scope

In scope:

* The Apex Optimizer Dashboard source code.
* Streamlit app behavior.
* Profile import/export logic.
* Storage audit logic.
* Safe cleanup/trash behavior.
* OCR screen-capture workflow.
* PresentMon/FPS import handling.
* Dependency and requirements configuration.
* GitHub Actions workflows.
* Secret handling and accidental key exposure.
* File path safety.
* Local-only privacy protections.

Out of scope:

* Attacks against EA, Respawn, Apex Legends, Steam, GitHub, Streamlit Cloud, NVIDIA, Microsoft, or third-party services.
* Social engineering.
* Physical attacks.
* Denial-of-service testing.
* Spam.
* Automated scraping.
* Credential stuffing.
* Attempts to bypass Apex anti-cheat.
* Cheat development, recoil scripts, macros, memory reading, injection, or gameplay exploitation.
* Accessing another person’s machine, account, files, tokens, or private data.

## Safe Testing Rules

Good-faith testing is welcome if it follows these limits:

* Do not access, copy, delete, or modify data that is not yours.
* Do not exfiltrate secrets, tokens, keys, cookies, session data, or private files.
* Do not test against live users.
* Do not run destructive payloads.
* Do not bypass game anti-cheat systems.
* Do not test against third-party services without permission.
* Stop immediately if you discover private data exposure and report it privately.

## Response Expectations

This is a small independent project, so response times are best effort.

Expected response targets:

* Initial acknowledgement: within 7 days.
* Triage/update: within 14 days.
* Critical secret exposure: prioritized as soon as possible.
* Fix timeline: depends on severity, reproducibility, and project workload.

## Severity Guide

Critical:

* Remote code execution.
* Exposed API keys, tokens, or credentials.
* Arbitrary file read/write/delete outside approved folders.
* Secret leakage through logs, exports, or UI.
* Unsafe cleanup that can delete user files outside the app scope.

High:

* Path traversal.
* Broken file-scope protections.
* Private local path exposure in public exports.
* Unsafe dependency or workflow configuration.
* Vulnerabilities that expose system or user data.

Medium:

* Crash bugs that expose traces or local paths.
* Unsafe defaults.
* Missing validation around imports, exports, or scan paths.

Low:

* UI-only issues.
* Documentation gaps.
* Non-sensitive debug messages.

## Project Security Principles

This project should remain:

* Local-first.
* Public-safe.
* No-cheat.
* No anti-cheat bypass.
* No secret exposure.
* No destructive cleanup outside approved folders.
* No frontend API keys.
* No credential logging.
* No hidden data collection.

## Disclosure

Please give the maintainer time to investigate and fix the issue before public disclosure.

Do not publicly disclose a vulnerability until a fix is available or the maintainer has agreed to disclosure.
