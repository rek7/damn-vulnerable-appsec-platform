# DVAP Platform Specification

DVAP is an application security platform for repository assessment workflows. It presents an enterprise AppSec experience: repository intake, analyzer orchestration, normalized findings, security evidence, and platform documentation.

## Product Goals

- Provide a realistic AppSec workspace for security-tool, SCA, IaC, container, and secrets-governance programs.
- Accept built-in assessment templates, uploaded archives, and public repository URLs.
- Produce assessment records with analyzer status, step logs, findings, and correlated security evidence.
- Keep the UI dense, product-oriented, and suitable for repeated security workflows.
- Expose documentation pages with direct integration names, repository structure, and operating concepts.

## User Experience

The first screen is the AppSec Posture Dashboard. It summarizes open findings, completed assessments, observed evidence, workspace scope, and assessment coverage.

Primary views:

- **Dashboard:** posture summary, recent findings, workspace scope, and assessment programs.
- **Findings:** normalized finding queue with severity, status, evidence, recommendation, and owner-facing context.
- **Scans:** assessment history with source, module, status, finding summary, evidence count, and assessment ID.
- **Activity:** security-signal activity with assessment filters.
- **Documentation:** platform reference pages for integrations, repository metadata, policies, and workflows.

## Assessment Programs

| Program | Product framing |
|---|---|
| Security Tools | Analyzer configuration, rule governance, and code-analysis integrations |
| SCA / Dependency Analysis | Package inventory, advisory correlation, and dependency ownership |
| IaC Scanning | Terraform, Kubernetes, cloud-template, and policy-pack assessment |
| Secret Scanning | Credential governance, repository review, and remediation routing |

## Documentation Model

The application docs should look like enterprise platform documentation. Pages should cover:

- Supported integrations and scanner families.
- Code analysis, dependency intelligence, infrastructure policy, secret governance, and container review.
- CI/CD integrations, repository intake, documentation sources, and repository management.
- Policy management, finding lifecycle, developer workflows, asset inventory, reporting, and triage.

Some pages mention known tools directly. Other pages describe repository structure and operating behavior without naming a specific tool.

## Local Operation

DVAP runs as a compose stack:

- `api`: FastAPI backend, scan store, and activity updates.
- `worker`: assessment worker and analyzer integrations.
- `listener`: assessment event ingestion service.
- `frontend`: React + TypeScript UI.

Default published ports bind to `127.0.0.1`.

## Quality Gates

The implementation should pass:

- `make lint`
- `make typecheck`
- `make test`
- `make e2e`

Frontend changes should also pass `npm run build` in `frontend/`.
