# DVAP Integration Contracts

This document describes the product-level contracts between DVAP services. It is written for maintainers who need to understand how the local AppSec platform fits together without relying on implementation-specific UI copy.

## Services

| Service | Responsibility |
|---|---|
| `api` | Owns scan records, workspace configuration, finding inputs, and activity updates |
| `worker` | Fetches repositories, runs analyzer integrations, and returns assessment results |
| `listener` | Receives local assessment activity and forwards it to the API |
| `frontend` | Presents the dashboard, findings, assessments, security activity, and documentation |

## Scan Lifecycle

1. The frontend submits an assessment request.
2. The API creates an assessment record with the current workspace profile.
3. The worker prepares a temporary work directory for the selected source.
4. Analyzer integrations run and return structured status, summary, and step-log entries.
5. The API stores the completed scan and publishes assessment updates to application views.
6. Related security signals are linked to the assessment record for review.

## Source Types

| Source | Use |
|---|---|
| Built-in template | Repeatable local assessment examples |
| Upload | Archive-based repository review |
| Git URL | Public repository intake from approved source-control hosts |

Archive uploads should enforce size, file-type, and path-boundary checks. Git URL intake should allow only approved public source-control hosts and reject local, private, or link-local targets.

## Data Shapes

### Scan

- `id`
- `scan_token`
- `module`
- `source`
- `status`
- `workspace_profile`
- `result`
- `analyzers`
- `steps`
- `signal_count`
- `created_at`
- `updated_at`

### Analyzer Result

- `name`
- `assessment`
- `status`
- `has_evidence`
- `summary`
- `duration_ms`

### Signal

- `id`
- `scan_id`
- `scan_token`
- `assessment`
- `decoded`
- `received_at`
- `method`
- `path`
- `remote`

Sensitive-looking values should be redacted in the UI.

## Frontend Contracts

- The dashboard links to all assessment programs and docs.
- Program pages provide built-in templates plus git and upload intake.
- Assessment detail renders analyzer status, step logs, findings, and correlated evidence.
- Finding cards use product-facing assessment labels rather than backend identifiers.
- Documentation routes are available at `/docs` and `/docs/:docId`.
- Documentation includes repository discovery guidance and an integration catalog for scanner, build, package, infrastructure, and delivery systems.

## Test Expectations

The project should keep unit, lint, typecheck, build, and end-to-end checks green. Internal identifiers may remain stable for API compatibility, but rendered UI and docs should use product-facing language.
