# Security Policy

## Scope

This policy applies to the `yenk/Dali` public repository: benchmark schemas,
corpus data, reference implementations, and evaluation tooling.

It does **not** cover private infrastructure, hosted services, or enterprise
deployments. Those have separate disclosure channels.

## Reporting a vulnerability

If you discover a security vulnerability in this repository, please **do not
open a public GitHub issue**.

Report privately by emailing the maintainer at **yen.kha@gammalex.com** with the subject prefix `[SECURITY]`.

Include:
- A description of the vulnerability and its potential impact
- Steps to reproduce (minimal example if possible)
- Which files or components are affected

You will receive acknowledgment within **72 hours** and a resolution timeline
within **7 days**.

## What qualifies

Report privately:
- Corpus data that inadvertently exposes personally identifiable information
- Schema or parser behavior that could cause consuming systems to silently
  accept malformed or adversarially crafted citation data
- Dependency vulnerabilities with a credible exploit path in the benchmark runner

Do not report as security issues:
- Benchmark accuracy limitations (open a regular issue)
- LLM output quality problems (out of scope for this repo)
- Theoretical attacks with no practical exploit path

## Disclosure policy

We follow **coordinated disclosure**: fixes are prepared privately, then the
vulnerability is disclosed publicly after the fix is released. We will credit
reporters by name unless they prefer anonymity.

## Supported versions

Only the current `main` branch is actively maintained. Older tagged releases
do not receive security patches.
