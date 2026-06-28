# DVAP Security Platform

DVAP is a local application security platform for repository assessment workflows across security tools, SCA, IaC scanning, container review, and secrets governance.

The platform provides a product-style operator experience: submit a repository, run assessment templates, review normalized findings, inspect assessment history, monitor correlated security evidence, and browse documentation pages that match an enterprise AppSec workspace.

## Quick start

```sh
docker compose up
```

| Service | URL |
|---|---|
| Operator UI | http://127.0.0.1:8080 |
| API | http://127.0.0.1:8000 |
| Assessment event ingestion | http://127.0.0.1:9000 |
| Postgres | 127.0.0.1:54329 |

The default workspace profile is ready for local assessment runs with no additional setup. API state is stored in Postgres, and the local compose profile shares a synthetic database DSN with app services so repository-assessment scenarios can include internal credential exposure and service-to-database reachability. Seeded credentials are watermarked fake values only.

To generate local AWS canary credentials from Canarytokens.org, provide an alert destination and run:

```sh
CANARYTOKENS_EMAIL=security@example.com make canarytokens
```

You can also set `CANARYTOKENS_WEBHOOK_URL` for webhook delivery. The generated seed overlay is written under `seeds/` as ignored local files and is loaded by the compose stack on the next start.

Movement-oriented integration records always use canary-specific credential fields. If a live Canarytokens.org overlay is not present, the stack uses the bundled synthetic canary defaults rather than generic cloud credentials.

## Platform areas

| Program | Coverage |
|---|---|
| Security Tools | Analyzer configuration, rule governance, and code-analysis integrations |
| SCA / Dependency Analysis | Package inventory, advisory correlation, ownership, and upgrade workflows |
| IaC Scanning | Terraform, Kubernetes, cloud-template, and policy-pack assessment |
| Secret Scanning | Credential governance, repository review, and remediation routing |
| Documentation | Product references for integrations, repository signals, policies, and triage workflows |

## Operator workflow

1. Open the operator UI.
2. Choose an assessment program from the dashboard.
3. Run a built-in assessment template, submit a public repository URL, or upload an archive.
4. Review findings, analyzer output, step logs, and correlated evidence.
5. Use the docs section for platform reference pages and operating guidance.

## Development

```sh
make lint
make typecheck
make test
make e2e
```

The stack is intentionally local-first. Published service ports bind to `127.0.0.1` in the default compose configuration.

## Repository layout

```text
./
├── api/               FastAPI backend for assessments, findings, and activity
├── worker/            Assessment worker and analyzer integrations
├── listener/          Assessment event ingestion service
├── db/                Postgres initialization and synthetic integration data
├── frontend/          React + TypeScript operator UI
├── e2e/               End-to-end checks
├── docs/              Project notes and API contracts
├── docker-compose.yml
└── Makefile
```

## License

See `LICENSE` for terms.
