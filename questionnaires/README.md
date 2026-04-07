# Deployment Questionnaires

This directory contains the pre-deployment decision guides that help you determine which solutions to deploy and how to configure them, based on your specific industrial AI context and ISO/IEC 42001 compliance requirements.

## Recommended Order

Work through the questionnaires in this order:

1. **[01 — Deployment Scope](./01-deployment-scope.md)**: Determine which tiers and architectural components you need. Start here.
2. **[02 — Edge Requirements](./02-edge-requirements.md)**: Configuration decisions for the Edge tier.
3. **[03 — Platform Requirements](./03-platform-requirements.md)**: Configuration decisions for the Platform tier.
4. **[04 — Enterprise Requirements](./04-enterprise-requirements.md)**: Configuration decisions for the Enterprise tier.
5. **[05 — ISO/IEC 42001 Compliance](./05-iso42001-compliance.md)**: Map your architectural decisions to ISO/IEC 42001 clauses for audit readiness.

## Quick Selection Guide

| Scenario | Recommended Path |
|----------|-----------------|
| Greenfield deployment, all tiers | Complete all 5 questionnaires in order |
| Edge-only MVP (SME budget-constrained) | Q01 → Q02 → Q05 |
| Platform extension to existing edge | Q01 → Q03 → Q05 |
| Compliance audit preparation only | Q05 |
| Adding AI helpdesk to existing system | Q04 → individual solution questionnaire |
