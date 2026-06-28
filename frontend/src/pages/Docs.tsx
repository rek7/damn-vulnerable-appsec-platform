// Platform documentation for setup, operating model, and repository coverage.
import { Link, Navigate, useParams } from 'react-router-dom';

interface DocSection {
  title: string;
  paragraphs: string[];
  bullets?: string[];
}

interface ReferenceDoc {
  slug: string;
  category: string;
  title: string;
  summary: string;
  sections: DocSection[];
  related: string[];
}

const DOCS: ReferenceDoc[] = [
  {
    slug: 'quickstart',
    category: 'Start here',
    title: 'Quickstart',
    summary:
      'Create a workspace, add an application, and run the first repository assessment with a standard policy profile.',
    sections: [
      {
        title: 'Before you start',
        paragraphs: [
          'A workspace groups applications, owners, policy defaults, and evidence retention rules. Most teams start with one workspace per business unit or delivery organization.',
          'Each application record should have a repository URL, technical owner, business owner, service tier, and the assessment programs that apply to the project. You can add those details up front or let repository intake populate the first draft.',
        ],
      },
      {
        title: 'Run the first assessment',
        paragraphs: [
          'Open an application, choose a program, and start a repository assessment from a managed template, archive, or approved source URL. The platform records the analyzer summary, generated findings, and linked evidence activity under the same assessment record.',
          'For a clean review workflow, assign the findings to the owning team before changing policy thresholds. That keeps the initial evidence separate from later triage decisions.',
        ],
        bullets: [
          'Use a standard profile for the first run.',
          'Confirm that owners and service tier are correct.',
          'Review generated findings before adding exceptions.',
        ],
      },
      {
        title: 'Where to go next',
        paragraphs: [
          'After the first assessment completes, configure release gates, notification routing, and recurring scans. Teams that use pull request annotations usually configure branch review before scheduled assessment cadence.',
        ],
      },
    ],
    related: ['application-onboarding', 'repository-intake', 'release-gates'],
  },
  {
    slug: 'application-onboarding',
    category: 'Start here',
    title: 'Application onboarding',
    summary:
      'Register applications with ownership, repository metadata, service tier, and the security programs that apply.',
    sections: [
      {
        title: 'Application records',
        paragraphs: [
          'An application record is the durable unit used for policy, findings, reporting, and evidence. It can represent a service, library, worker, infrastructure repository, or deployable component.',
          'Keep the record close to how teams ship software. If a monorepo owns several services, create separate application records when ownership, policy, or release gates differ.',
        ],
      },
      {
        title: 'Required fields',
        paragraphs: [
          'Repository URL, default branch, owner team, service tier, and data classification are the minimum fields needed for useful routing. Release cadence and deployment environment improve prioritization but can be added later.',
        ],
        bullets: [
          'Repository name and approved source URL.',
          'Technical owner, business owner, and escalation group.',
          'Service tier, runtime, deployment environment, and data classification.',
        ],
      },
      {
        title: 'Assessment scope',
        paragraphs: [
          'Scope tells the platform which evidence to collect for an application. A web service may require code analysis, dependency review, image review, infrastructure policy, and secrets review, while a documentation repository may only need repository metadata and content indexing.',
        ],
      },
    ],
    related: ['repository-intake', 'asset-inventory', 'workspace-configuration'],
  },
  {
    slug: 'repository-intake',
    category: 'Start here',
    title: 'Repository intake',
    summary:
      'Define how repositories enter the platform, how ownership is assigned, and how assessment scope is recorded.',
    sections: [
      {
        title: 'Intake flow',
        paragraphs: [
          'Repository intake normalizes source metadata before any assessment runs. The intake job reads branch defaults, repository topics, language mix, ownership files, and release metadata to create the first application profile.',
          'Teams can accept the discovered profile as-is or override fields before the repository becomes eligible for scheduled scans and release gates.',
        ],
      },
      {
        title: 'Repository signals',
        paragraphs: [
          'The intake job looks for common project files and configuration conventions. Examples include `package.json`, `requirements.txt`, `pyproject.toml`, `Gemfile`, `*.gemspec`, `go.mod`, `pom.xml`, `build.gradle`, `Dockerfile`, `Chart.yaml`, and workflow definitions under `.github/workflows/`.',
          'These files do not decide policy on their own. They help the platform choose the right assessment program and route findings to the people who can act on them.',
        ],
      },
      {
        title: 'Ownership mapping',
        paragraphs: [
          'Repository ownership files, repository teams, topics, and service catalog references are merged into an ownership suggestion. Workspace administrators can require manual approval when ownership is missing or ambiguous.',
        ],
      },
    ],
    related: ['application-onboarding', 'project-discovery', 'asset-inventory'],
  },
  {
    slug: 'project-discovery',
    category: 'Start here',
    title: 'Project discovery',
    summary:
      'Use repository structure, manifests, lockfiles, and service metadata to infer which assessment programs apply.',
    sections: [
      {
        title: 'Detection model',
        paragraphs: [
          'Project discovery is intentionally conservative. The platform prefers durable repository evidence over naming conventions, so it looks for manifests, build descriptors, policy directories, container build context, API schemas, and documentation roots.',
          'When multiple ecosystems are present, discovery records all candidates and lets policy decide whether each program is required, optional, or informational.',
        ],
      },
      {
        title: 'Signals that imply coverage',
        paragraphs: [
          'A repository does not need to name every tool it uses for the platform to build an assessment profile. Files such as `package.json`, `pnpm-lock.yaml`, `pyproject.toml`, `Pipfile`, `Gemfile`, `*.gemspec`, `go.mod`, `pom.xml`, `build.gradle`, `Cargo.toml`, and `composer.json` are enough to infer package inventory requirements.',
          'Infrastructure and delivery signals work the same way. `Dockerfile`, `docker-compose.yml`, `Chart.yaml`, `kustomization.yaml`, `main.tf`, `template.yaml`, `buildspec.yml`, `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, and `.circleci/config.yml` tell the platform which review programs are likely relevant before a team configures named integrations.',
        ],
      },
      {
        title: 'Ambiguous repositories',
        paragraphs: [
          'A repository can be both an application and an infrastructure module. For example, a service may include dependency manifests, container files, deployment overlays, and policy bundles. In that case, the assessment profile should keep each program separate so evidence remains easy to review.',
        ],
      },
      {
        title: 'Manual overrides',
        paragraphs: [
          'Workspace owners can add or remove programs when discovery does not have enough context. The override is recorded with a reason, reviewer, and expiration date so future imports can be compared against the decision.',
        ],
      },
    ],
    related: ['repository-intake', 'policy-management', 'integration-health'],
  },
  {
    slug: 'repository-management',
    category: 'Start here',
    title: 'Repository management',
    summary:
      'Maintain source metadata, ownership files, branch rules, and recurring assessment schedules.',
    sections: [
      {
        title: 'Repository records',
        paragraphs: [
          'Repository management keeps the source record aligned with the application inventory. It stores the approved URL, default branch, repository topics, owner hints, branch metadata, and whether the repository is eligible for scheduled assessments.',
          'The source record can exist before an application is fully onboarded. This lets teams import a repository set, clean up ownership, and decide which services need application records later.',
        ],
      },
      {
        title: 'Source metadata',
        paragraphs: [
          'Common metadata includes ownership files, `.gitmodules`, `.lfsconfig`, branch protection status, repository topics, workflow paths, and links to service catalog entries. Metadata should be refreshed regularly because ownership and branch rules often change outside the platform.',
        ],
      },
      {
        title: 'Schedules',
        paragraphs: [
          'Recurring schedules should be based on application tier and repository activity. High-priority services usually need more frequent assessment than archived libraries or migration projects.',
        ],
      },
    ],
    related: ['repository-intake', 'application-onboarding', 'integration-health'],
  },
  {
    slug: 'supported-integrations',
    category: 'Programs',
    title: 'Integration catalog',
    summary:
      'Review supported scanners, package managers, build systems, infrastructure formats, and delivery integrations.',
    sections: [
      {
        title: 'Code and scanner integrations',
        paragraphs: [
          'Code review and scanner coverage includes Semgrep, CodeQL, SonarQube, Bandit, Brakeman, ESLint, RuboCop, Checkov, tfsec, KICS, OPA, Conftest, Trivy, Grype, Hadolint, Gitleaks, TruffleHog, detect-secrets, Safety, Syft, and SPDX SBOM inputs.',
          'Integrations can be configured directly or discovered from repository configuration. The assessment record keeps the original tool name, normalized finding category, evidence path, owner, severity, and review state together.',
        ],
      },
      {
        title: 'Package and build ecosystems',
        paragraphs: [
          'Dependency and build coverage includes npm, pnpm, Yarn, pip, Poetry, Pipenv, Bundler, RubyGems, Composer, Cargo, Go modules, Maven, Gradle, Make, CMake, Bazel, webpack, and Docker build context.',
          'The platform uses manifests and lockfiles to decide which inventory jobs should run, then links each finding back to the source file that introduced the package or build behavior.',
        ],
      },
      {
        title: 'Delivery and infrastructure systems',
        paragraphs: [
          'Delivery and infrastructure coverage includes Kubernetes, Terraform, Helm, Kustomize, CloudFormation, Ansible, Packer, GitHub Actions, GitLab CI, Jenkins, CircleCI, Travis CI, Azure Pipelines, Bitbucket Pipelines, AWS CodeBuild, and Google Cloud Build.',
          'These integrations are treated as evidence sources, not separate application records. Their findings remain attached to the owning application so release gates, exceptions, and reporting stay consistent.',
        ],
      },
      {
        title: 'Reporting expectations',
        paragraphs: [
          'Program coverage reports answer whether required evidence exists, whether findings are open, and whether exceptions have valid owners and expiration dates. They should not be treated as a replacement for application ownership review.',
        ],
      },
    ],
    related: ['code-analysis', 'dependency-intelligence', 'infrastructure-policy'],
  },
  {
    slug: 'code-analysis',
    category: 'Programs',
    title: 'Code analysis',
    summary:
      'Review language-aware analyzer output, project-level rule configuration, and developer handoff notes.',
    sections: [
      {
        title: 'How code analysis works',
        paragraphs: [
          'Code analysis collects source findings from analyzer output and project-level rule configuration. The platform keeps raw evidence attached to the assessment while presenting a normalized view for triage.',
          'Configuration files such as `.semgrep.yaml`, `codeql-config.yml`, `qlpack.yml`, `sonar-project.properties`, `.bandit`, `.brakeman.yml`, `.eslintrc.js`, and `.rubocop.yml` are treated as repository signals. They help identify custom rules, disabled checks, and project-specific review behavior.',
        ],
      },
      {
        title: 'Rule packs and exceptions',
        paragraphs: [
          'Rule packs should be owned by a platform or security team, while project exceptions should be owned by the application team. The finding lifecycle records who accepted each exception, why it was accepted, and when it must be reviewed again.',
        ],
      },
      {
        title: 'Developer handoff',
        paragraphs: [
          'Findings should include affected file context, rule name, severity, and remediation notes. Keep long-form guidance in documentation pages and link to it from the finding rather than copying large policy text into every result.',
        ],
      },
    ],
    related: ['finding-lifecycle', 'developer-workflows', 'policy-management'],
  },
  {
    slug: 'dependency-intelligence',
    category: 'Programs',
    title: 'Dependency intelligence',
    summary:
      'Build an inventory from manifests, lockfiles, package metadata, and advisory correlation.',
    sections: [
      {
        title: 'Inventory sources',
        paragraphs: [
          'Dependency intelligence begins with manifests and lockfiles. Common repository details include `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`, `poetry.lock`, `Gemfile`, `Gemfile.lock`, `*.gemspec`, `composer.json`, `Cargo.toml`, `go.mod`, `pom.xml`, and `build.gradle`.',
          'The platform records the package graph, source file, owning application, and the assessment that produced the inventory. That makes later advisory updates traceable back to the original repository evidence.',
        ],
      },
      {
        title: 'Prioritization',
        paragraphs: [
          'Prioritization combines advisory metadata, application tier, exposure, dependency type, and owner policy. A low-severity package in a critical service may still require faster review than a higher-severity package in an internal prototype.',
        ],
      },
      {
        title: 'Upgrade workflow',
        paragraphs: [
          'Upgrade guidance should include the affected package, current version, target version, source manifest, and any available context from the owning team. Exceptions must include an expiration date so inventory does not drift indefinitely.',
        ],
      },
    ],
    related: ['developer-workflows', 'asset-inventory', 'reporting-analytics'],
  },
  {
    slug: 'infrastructure-policy',
    category: 'Programs',
    title: 'Infrastructure policy',
    summary:
      'Evaluate cloud templates, deployment overlays, modules, and policy bundles before release.',
    sections: [
      {
        title: 'Policy inputs',
        paragraphs: [
          'Infrastructure policy reviews repository files that describe deployment state. Typical inputs include Terraform modules, OpenTofu projects, provider metadata, Helm charts, Kustomize overlays, CloudFormation templates, Ansible inventories, Packer templates, and policy directories that contain Rego bundles.',
          'Project configuration such as `.checkov.yml`, `.tfsec.yml`, `kics.config`, and custom policy directories helps the platform explain which policy packs were loaded for a run.',
        ],
      },
      {
        title: 'Deployment readiness',
        paragraphs: [
          'A failed policy check should block promotion only when the application tier and release policy require it. Informational findings can still be routed to infrastructure owners without interrupting delivery.',
        ],
      },
      {
        title: 'Exception handling',
        paragraphs: [
          'Infrastructure exceptions should include the affected resource, environment, control mapping, compensating control, and expiration date. Reviewers should be able to see whether the same exception appears across related modules.',
        ],
      },
    ],
    related: ['release-gates', 'policy-management', 'asset-inventory'],
  },
  {
    slug: 'secrets-governance',
    category: 'Programs',
    title: 'Secrets governance',
    summary:
      'Track credential-like findings, owner routing, remediation evidence, and recurring patterns.',
    sections: [
      {
        title: 'Review scope',
        paragraphs: [
          'Secrets governance focuses on detection coverage, ownership, and remediation evidence for credential-like material. The platform does not decide rotation policy by itself; it records evidence so owners can decide whether rotation, revocation, or dismissal is appropriate.',
          'Repository details such as `.gitleaks.toml`, `.trufflehog.yaml`, `.secrets.baseline`, `.gitignore`, allowlist configuration, generated files, archive contents, and environment templates help explain how a finding was produced.',
        ],
      },
      {
        title: 'Remediation evidence',
        paragraphs: [
          'Evidence should include the affected location, credential family, owner response, and the remediation action taken. If the value is not confirmed, record the review note and keep sensitive-looking content masked in the operator view.',
        ],
      },
      {
        title: 'Trend analysis',
        paragraphs: [
          'Recurring patterns are often more useful than one-off findings. Use reporting to identify teams, file paths, templates, or workflows that repeatedly produce credential-like material.',
        ],
      },
    ],
    related: ['data-handling', 'finding-lifecycle', 'reporting-analytics'],
  },
  {
    slug: 'container-review',
    category: 'Programs',
    title: 'Container and image review',
    summary:
      'Connect Dockerfiles, image metadata, generated inventories, and registry context to application findings.',
    sections: [
      {
        title: 'Repository inputs',
        paragraphs: [
          'Container review uses repository build context and generated image metadata. Common inputs include `Dockerfile`, `docker-compose.yml`, `.dockerignore`, image labels, registry configuration, build arguments, package databases, and SBOM exports such as SPDX documents.',
          'Files like `.syft.yaml`, `trivy.yaml`, `.grype.yaml`, and `.hadolint.yaml` may appear when teams customize image inventory, package review, or Dockerfile policy behavior.',
        ],
      },
      {
        title: 'Promotion gates',
        paragraphs: [
          'Image policy should be evaluated before promotion to protected environments. The finding record should include the image digest, base image status, affected package or Dockerfile location, and any exception attached to the release.',
        ],
      },
      {
        title: 'Inventory updates',
        paragraphs: [
          'Image inventories can change even when source code does not. Schedule recurring review for long-lived services and rebuild images when base image or operating system package metadata changes.',
        ],
      },
    ],
    related: ['dependency-intelligence', 'release-gates', 'asset-inventory'],
  },
  {
    slug: 'documentation-ingestion',
    category: 'Programs',
    title: 'Documentation ingestion',
    summary:
      'Index service docs, runbooks, API references, and remediation guidance alongside application findings.',
    sections: [
      {
        title: 'Supported content',
        paragraphs: [
          'Documentation ingestion collects service metadata, remediation guides, runbooks, API references, and ownership notes from the repository. Common inputs include `README.md`, `docs/**/*.md`, `mkdocs.yml`, `conf.py`, `mint.json`, `docs.json`, API reference schemas, diagrams, frontmatter, and embedded image references.',
          'The goal is to make findings easier to act on. The platform links a finding to relevant service docs rather than forcing reviewers to leave the application record and search manually.',
        ],
      },
      {
        title: 'Staleness checks',
        paragraphs: [
          'Documentation inventory includes last modified time, repository path, owner, and whether the page maps to an active application. Stale guidance should remain visible so teams can fix it as part of normal remediation work.',
        ],
      },
      {
        title: 'API references',
        paragraphs: [
          'API schemas and generated references are useful for ownership and data classification. Treat them as application metadata unless a policy specifically requires deeper review.',
        ],
      },
    ],
    related: ['developer-workflows', 'api-reference', 'data-handling'],
  },
  {
    slug: 'ci-cd-integrations',
    category: 'Automation',
    title: 'CI/CD integrations',
    summary:
      'Connect assessments to build workflows, branch rules, artifact promotion, and developer feedback loops.',
    sections: [
      {
        title: 'Workflow discovery',
        paragraphs: [
          'Automation discovery looks for workflow files and build metadata such as `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml`, `.travis.yml`, `azure-pipelines.yml`, `bitbucket-pipelines.yml`, `buildspec.yml`, and `cloudbuild.yaml`.',
          'These files tell the platform where assessments can run and where results should be posted. They do not automatically enforce policy until a release gate or branch rule is configured.',
        ],
      },
      {
        title: 'Build annotations',
        paragraphs: [
          'Build annotations should stay concise. Include status, affected application, finding count, and a link to the full assessment record. Long policy explanations belong in documentation or finding details.',
        ],
      },
      {
        title: 'Failure behavior',
        paragraphs: [
          'Use blocking failures for protected branches and high-confidence policy requirements. Use advisory results for new programs, exploratory repositories, and teams that are still tuning ownership or severity thresholds.',
        ],
      },
    ],
    related: ['branch-and-pr-review', 'release-gates', 'notifications'],
  },
  {
    slug: 'branch-and-pr-review',
    category: 'Automation',
    title: 'Branch and pull request review',
    summary:
      'Send concise assessment status into pull requests while preserving detailed evidence in the platform.',
    sections: [
      {
        title: 'Pull request status',
        paragraphs: [
          'Pull request review should show whether required programs ran, whether blocking findings exist, and whether any exceptions were applied. Developers should be able to open the assessment detail page for evidence and remediation context.',
        ],
      },
      {
        title: 'Diff-aware routing',
        paragraphs: [
          'When file ownership is available, route findings to the team that owns the affected path. When ownership is ambiguous, route to the application owner and record the ambiguity so the repository metadata can be improved.',
        ],
      },
      {
        title: 'Retry behavior',
        paragraphs: [
          'Retries should create a new assessment record but remain linked to the same pull request. This keeps evidence immutable while still making it easy to compare before and after states.',
        ],
      },
    ],
    related: ['ci-cd-integrations', 'developer-workflows', 'finding-lifecycle'],
  },
  {
    slug: 'release-gates',
    category: 'Automation',
    title: 'Release gates',
    summary:
      'Apply policy decisions before promotion while keeping exceptions and evidence reviewable.',
    sections: [
      {
        title: 'Gate inputs',
        paragraphs: [
          'A release gate combines application tier, target environment, required programs, finding state, exception state, and assessment freshness. Teams should configure gates per environment rather than using one global rule for every release.',
        ],
      },
      {
        title: 'Blocking criteria',
        paragraphs: [
          'Blocking criteria should be narrow enough for engineers to understand. A common pattern is to block when required assessments are missing, critical findings are open, or approved exceptions have expired.',
        ],
      },
      {
        title: 'Evidence retention',
        paragraphs: [
          'The gate decision stores the assessment IDs, policy version, reviewer, and timestamp used at the moment of release. This makes later audit review independent from current application state.',
        ],
      },
    ],
    related: ['policy-management', 'infrastructure-policy', 'audit-log'],
  },
  {
    slug: 'api-reference',
    category: 'Automation',
    title: 'API reference',
    summary:
      'Use the platform API to create scans, fetch findings, inspect evidence, and manage workspace configuration.',
    sections: [
      {
        title: 'Authentication',
        paragraphs: [
          'API clients should use workspace-scoped service accounts with the smallest role needed for the job. Store tokens in the approved secret store for the automation environment and rotate them on a fixed cadence.',
        ],
      },
      {
        title: 'Common resources',
        paragraphs: [
          'The primary resources are applications, assessments, findings, evidence, exceptions, policies, users, teams, and webhooks. Most automation reads assessment status and posts links back into a workflow or ticket.',
        ],
      },
      {
        title: 'Idempotency',
        paragraphs: [
          'Create requests that may be retried should include an idempotency key. Use the repository URL, commit SHA, workflow run ID, and program name when building a repeatable key for automation.',
        ],
      },
    ],
    related: ['webhooks', 'ci-cd-integrations', 'data-export'],
  },
  {
    slug: 'webhooks',
    category: 'Automation',
    title: 'Webhooks',
    summary:
      'Subscribe external systems to assessment, finding, exception, and integration-health events.',
    sections: [
      {
        title: 'Event delivery',
        paragraphs: [
          'Webhook events are delivered with a stable event ID, workspace ID, event type, resource ID, timestamp, and signature. Consumers should treat delivery as at-least-once and deduplicate by event ID.',
        ],
      },
      {
        title: 'Retry policy',
        paragraphs: [
          'Failed deliveries are retried with backoff. Disable endpoints that repeatedly fail so they do not hide integration-health issues for other subscribers.',
        ],
      },
      {
        title: 'Payload design',
        paragraphs: [
          'Webhook bodies include enough metadata to fetch the full resource from the API. They should not include sensitive evidence blobs or masked values that belong in the platform UI.',
        ],
      },
    ],
    related: ['api-reference', 'notifications', 'integration-health'],
  },
  {
    slug: 'policy-management',
    category: 'Operations',
    title: 'Policy management',
    summary: 'Centralize requirements, exception rules, escalation paths, and approval evidence.',
    sections: [
      {
        title: 'Policy structure',
        paragraphs: [
          'A policy defines which programs are required for an application tier, which findings block release, who can approve exceptions, and how long evidence is retained.',
          'Keep policy names human-readable and versioned. Reviewers should be able to tell which policy produced a decision without reading implementation details.',
        ],
      },
      {
        title: 'Exception rules',
        paragraphs: [
          'Exceptions should require an owner, reason, scope, expiration date, and approval trail. Scope can be an application, finding, file path, package, image digest, or infrastructure resource depending on the program.',
        ],
      },
      {
        title: 'Change management',
        paragraphs: [
          'Policy changes should be staged before enforcement. Use advisory mode to measure impact, notify owners, and clean up stale metadata before blocking releases.',
        ],
      },
    ],
    related: ['exceptions-and-risk', 'release-gates', 'audit-log'],
  },
  {
    slug: 'finding-lifecycle',
    category: 'Operations',
    title: 'Finding lifecycle',
    summary:
      'Move issues from detection to triage, ownership, remediation, exception, and closure.',
    sections: [
      {
        title: 'State model',
        paragraphs: [
          'Findings move through open, assigned, in progress, exception requested, exception approved, resolved, and closed states. Each transition records the actor, timestamp, and reason.',
        ],
      },
      {
        title: 'Deduplication',
        paragraphs: [
          'Deduplication groups recurring results by application, program, affected location, and stable rule or package identity. The original evidence remains attached to each assessment even when the finding is grouped.',
        ],
      },
      {
        title: 'Closure',
        paragraphs: [
          'Closure requires evidence that the issue no longer appears or that the exception is approved. A closed finding can reopen if a later assessment reports the same issue after the closure timestamp.',
        ],
      },
    ],
    related: ['triage-operations', 'developer-workflows', 'policy-management'],
  },
  {
    slug: 'developer-workflows',
    category: 'Operations',
    title: 'Developer workflows',
    summary:
      'Make findings actionable inside pull requests, tickets, documentation, and team dashboards.',
    sections: [
      {
        title: 'Developer view',
        paragraphs: [
          'Developers need concise context: what changed, why it matters, where to look, and what action is expected. Keep policy language short and link to the deeper documentation page when needed.',
        ],
      },
      {
        title: 'Ticket handoff',
        paragraphs: [
          'A ticket should include the finding title, affected location, owner, severity, due date, remediation summary, and a link back to the platform evidence. Avoid duplicating sensitive data in external systems.',
        ],
      },
      {
        title: 'Recurring patterns',
        paragraphs: [
          'When the same issue appears across several repositories, use trend reports to create shared guidance or a platform fix instead of opening separate tickets with the same instructions.',
        ],
      },
    ],
    related: ['branch-and-pr-review', 'documentation-ingestion', 'finding-lifecycle'],
  },
  {
    slug: 'exceptions-and-risk',
    category: 'Operations',
    title: 'Exceptions and risk acceptance',
    summary: 'Record temporary risk decisions with ownership, scope, expiration, and evidence.',
    sections: [
      {
        title: 'When to request an exception',
        paragraphs: [
          'Use an exception when a finding is understood but cannot be remediated before a required milestone. Do not use exceptions to hide findings that need ownership cleanup or duplicate review.',
        ],
      },
      {
        title: 'Required evidence',
        paragraphs: [
          'A useful request includes affected resource, business justification, compensating control, owner, expiration date, and the policy or release gate that would otherwise block the work.',
        ],
      },
      {
        title: 'Expiration',
        paragraphs: [
          'Expired exceptions should return the finding to an actionable state. Notify the owner before expiration so teams can either remediate, renew with updated evidence, or accept enforcement.',
        ],
      },
    ],
    related: ['policy-management', 'finding-lifecycle', 'notifications'],
  },
  {
    slug: 'triage-operations',
    category: 'Operations',
    title: 'Triage operations',
    summary: 'Review new findings, assign owners, resolve duplicates, and document decisions.',
    sections: [
      {
        title: 'Daily queue',
        paragraphs: [
          'The triage queue should be reviewed by severity, application tier, and service ownership. New critical findings should be assigned before lower-priority cleanup work.',
        ],
      },
      {
        title: 'Decision notes',
        paragraphs: [
          'Decision notes should be short and specific. Record what was reviewed, why the state changed, and what evidence supports the decision.',
        ],
      },
      {
        title: 'Escalation',
        paragraphs: [
          'Escalate findings when ownership is missing, due dates are missed, or a release gate is blocked without a clear reviewer. Escalation rules should be visible in the application record.',
        ],
      },
    ],
    related: ['finding-lifecycle', 'exceptions-and-risk', 'reporting-analytics'],
  },
  {
    slug: 'asset-inventory',
    category: 'Administration',
    title: 'Asset inventory',
    summary:
      'Join repositories, services, owners, deployment metadata, and assessment coverage in one application view.',
    sections: [
      {
        title: 'Inventory records',
        paragraphs: [
          'Inventory records connect repository metadata to service ownership and runtime context. They are used for reporting, prioritization, policy selection, and integration-health checks.',
        ],
      },
      {
        title: 'Metadata sources',
        paragraphs: [
          'The platform can combine repository topics, service catalog data, cloud account mappings, deployment environment, container image references, and owner groups. Manual fields remain available when source systems are incomplete.',
        ],
      },
      {
        title: 'Coverage gaps',
        paragraphs: [
          'A coverage gap means the platform expected evidence but did not receive it. Gaps can come from missing metadata, disabled workflow steps, stale credentials, or policy that no longer matches how the application is built.',
        ],
      },
    ],
    related: ['application-onboarding', 'reporting-analytics', 'integration-health'],
  },
  {
    slug: 'data-handling',
    category: 'Administration',
    title: 'Data handling',
    summary:
      'Define how assessment evidence, repository metadata, audit events, and exports are retained.',
    sections: [
      {
        title: 'Evidence boundaries',
        paragraphs: [
          'Assessment evidence may include file paths, analyzer summaries, masked data markers, package names, image metadata, and policy decisions. Sensitive-looking values should stay masked in the operator view and should not be copied into tickets or webhook bodies.',
        ],
      },
      {
        title: 'Retention',
        paragraphs: [
          'Retention policy should match audit requirements and storage cost. Keep release-gate evidence long enough to explain production decisions, and purge stale operational artifacts when they no longer support review.',
        ],
      },
      {
        title: 'Exports',
        paragraphs: [
          'Exports should include the workspace, application, time range, filters, and requester. Review exports before sharing them outside the owning team.',
        ],
      },
    ],
    related: ['access-governance', 'audit-log', 'data-export'],
  },
  {
    slug: 'access-governance',
    category: 'Administration',
    title: 'Access governance',
    summary:
      'Manage workspace roles, approval groups, evidence visibility, and periodic access reviews.',
    sections: [
      {
        title: 'Role model',
        paragraphs: [
          'Workspace roles control who can create applications, run assessments, approve exceptions, export evidence, and configure integrations. Use groups rather than individual assignments wherever possible.',
        ],
      },
      {
        title: 'Approval groups',
        paragraphs: [
          'Approval groups should match the policy they own. A team that owns infrastructure exceptions may not be the right approver for application dependency exceptions.',
        ],
      },
      {
        title: 'Review cadence',
        paragraphs: [
          'Review privileged roles, service accounts, and integration tokens on a fixed cadence. Escalate stale access when the owner or business unit is no longer valid.',
        ],
      },
    ],
    related: ['workspace-configuration', 'data-handling', 'audit-log'],
  },
  {
    slug: 'reporting-analytics',
    category: 'Administration',
    title: 'Reporting and analytics',
    summary:
      'Compare coverage, trends, SLA performance, and remediation outcomes across applications.',
    sections: [
      {
        title: 'Program scorecards',
        paragraphs: [
          'Scorecards summarize required coverage, open findings, exception state, and assessment freshness by application tier or owner group. They should help teams decide where to spend time, not replace detailed triage.',
        ],
      },
      {
        title: 'Trend reporting',
        paragraphs: [
          'Trend reports are most useful when grouped by owner, application tier, finding family, and source program. Use them to identify systemic issues and to measure whether guidance is working.',
        ],
      },
      {
        title: 'Executive summaries',
        paragraphs: [
          'Executive summaries should emphasize risk movement, overdue work, coverage gaps, and release impact. Keep implementation details in drill-down views for program owners.',
        ],
      },
    ],
    related: ['asset-inventory', 'policy-management', 'triage-operations'],
  },
  {
    slug: 'workspace-configuration',
    category: 'Administration',
    title: 'Workspace configuration',
    summary:
      'Set defaults for applications, teams, integrations, policy scope, and notification routing.',
    sections: [
      {
        title: 'Defaults',
        paragraphs: [
          'Workspace defaults reduce onboarding friction. Set default policy profile, owner mapping rules, notification channels, retention policy, and required metadata before importing a large repository set.',
        ],
      },
      {
        title: 'Environment tiers',
        paragraphs: [
          'Environment tiers let teams apply different release gates to development, staging, and production. A finding can be informational in one tier and blocking in another.',
        ],
      },
      {
        title: 'Change review',
        paragraphs: [
          'Changes to workspace defaults should be visible in the audit log. When a default changes enforcement behavior, notify application owners before the next scheduled assessment.',
        ],
      },
    ],
    related: ['access-governance', 'notifications', 'integration-health'],
  },
  {
    slug: 'integration-health',
    category: 'Administration',
    title: 'Integration health',
    summary:
      'Track scan freshness, connector status, ingestion errors, stale credentials, and queue latency.',
    sections: [
      {
        title: 'Health signals',
        paragraphs: [
          'Health status includes last successful run, connector state, rate-limit status, queue latency, credential age, repository count, and recent error messages. A healthy connector should still be reviewed when coverage drops unexpectedly.',
        ],
      },
      {
        title: 'Failure triage',
        paragraphs: [
          'Start with credential age, rate limits, network reachability, and API permissions. If one application fails while others succeed, inspect repository metadata and workflow configuration before changing workspace credentials.',
        ],
      },
      {
        title: 'Freshness policy',
        paragraphs: [
          'Freshness requirements should match application tier. Production services usually need more recent evidence than archived libraries or internal tools.',
        ],
      },
    ],
    related: ['workspace-configuration', 'ci-cd-integrations', 'notifications'],
  },
  {
    slug: 'audit-log',
    category: 'Administration',
    title: 'Audit log',
    summary:
      'Review administrative changes, policy decisions, exception approvals, exports, and integration events.',
    sections: [
      {
        title: 'Recorded events',
        paragraphs: [
          'The audit log records workspace changes, application updates, policy edits, exception decisions, evidence exports, role changes, integration updates, and release-gate decisions.',
        ],
      },
      {
        title: 'Search and filters',
        paragraphs: [
          'Filter by actor, workspace, application, event type, resource, and time range. Use resource IDs for precise review when investigating a specific assessment or exception.',
        ],
      },
      {
        title: 'Retention',
        paragraphs: [
          'Audit retention should be longer than routine assessment evidence when release or compliance decisions depend on historical review.',
        ],
      },
    ],
    related: ['data-handling', 'access-governance', 'release-gates'],
  },
  {
    slug: 'notifications',
    category: 'Administration',
    title: 'Notifications',
    summary:
      'Route assessment results, overdue work, exception events, and integration-health changes to the right teams.',
    sections: [
      {
        title: 'Routing rules',
        paragraphs: [
          'Notification routing combines application owner, severity, program, environment tier, and event type. Keep routing close to ownership so alerts do not become a shared queue nobody owns.',
        ],
      },
      {
        title: 'Noise control',
        paragraphs: [
          'Batch low-priority events and send immediate notifications for release blockers, expired exceptions, and failed integrations. Suppression should be time-bound and visible in the audit log.',
        ],
      },
      {
        title: 'Delivery targets',
        paragraphs: [
          'Common delivery targets include team chat, ticket queues, build summaries, email, and webhook consumers. Do not send sensitive evidence to systems that are not approved for it.',
        ],
      },
    ],
    related: ['webhooks', 'workspace-configuration', 'exceptions-and-risk'],
  },
  {
    slug: 'data-export',
    category: 'Administration',
    title: 'Data export',
    summary:
      'Export findings, evidence summaries, application inventory, and reporting datasets for review.',
    sections: [
      {
        title: 'Export scope',
        paragraphs: [
          'Exports should be scoped by workspace, application, owner, program, status, and time range. Use narrow filters for remediation workflows and broader filters for reporting datasets.',
        ],
      },
      {
        title: 'File handling',
        paragraphs: [
          'Exported files should include generation time, requester, filters, and schema version. Store exports in an approved location and delete temporary copies after review.',
        ],
      },
      {
        title: 'Schema stability',
        paragraphs: [
          'Automation should rely on documented field names and schema versions. When a field changes meaning, publish the new version before removing the old one.',
        ],
      },
    ],
    related: ['api-reference', 'data-handling', 'reporting-analytics'],
  },
  {
    slug: 'troubleshooting',
    category: 'Administration',
    title: 'Troubleshooting',
    summary:
      'Diagnose missing findings, stale evidence, integration errors, and unexpected policy decisions.',
    sections: [
      {
        title: 'Missing assessments',
        paragraphs: [
          'Check whether the application has an owner, required programs, valid repository URL, and an active schedule. If automation should start the assessment, inspect the workflow run and API response first.',
        ],
      },
      {
        title: 'Unexpected findings',
        paragraphs: [
          'Open the assessment detail page and compare repository inputs, analyzer summary, policy version, and correlated evidence. If the repository changed between runs, compare the commit SHA and source archive.',
        ],
      },
      {
        title: 'Integration errors',
        paragraphs: [
          'Review connector status, credential age, rate limits, queue latency, and recent audit events. Most integration problems can be isolated before changing application policy.',
        ],
      },
    ],
    related: ['integration-health', 'audit-log', 'api-reference'],
  },
];

const DOC_MAP: Record<string, ReferenceDoc> = Object.fromEntries(
  DOCS.map((doc) => [doc.slug, doc]),
) as Record<string, ReferenceDoc>;

const DOC_GROUPS = [
  {
    title: 'Start here',
    description: 'Set up the workspace, register applications, and discover repository shape.',
    slugs: [
      'quickstart',
      'application-onboarding',
      'repository-intake',
      'project-discovery',
      'repository-management',
    ],
  },
  {
    title: 'Programs',
    description: 'Understand the assessment programs and the evidence they collect.',
    slugs: [
      'supported-integrations',
      'code-analysis',
      'dependency-intelligence',
      'infrastructure-policy',
      'secrets-governance',
      'container-review',
      'documentation-ingestion',
    ],
  },
  {
    title: 'Automation',
    description: 'Connect assessment results to build workflows, release gates, and APIs.',
    slugs: [
      'ci-cd-integrations',
      'branch-and-pr-review',
      'release-gates',
      'api-reference',
      'webhooks',
    ],
  },
  {
    title: 'Operations',
    description: 'Manage findings, exceptions, triage, and developer handoff.',
    slugs: [
      'policy-management',
      'finding-lifecycle',
      'developer-workflows',
      'exceptions-and-risk',
      'triage-operations',
    ],
  },
  {
    title: 'Administration',
    description: 'Configure inventory, access, reporting, notifications, and audit workflows.',
    slugs: [
      'asset-inventory',
      'data-handling',
      'access-governance',
      'reporting-analytics',
      'workspace-configuration',
      'integration-health',
      'audit-log',
      'notifications',
      'data-export',
      'troubleshooting',
    ],
  },
];

const FEATURED_SLUGS = [
  'project-discovery',
  'supported-integrations',
  'dependency-intelligence',
  'ci-cd-integrations',
];

function sectionId(title: string) {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

function InlineText({ text }: { text: string }) {
  const parts = text.split(/(`[^`]+`)/g);
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith('`') && part.endsWith('`')) {
          return (
            <code
              key={`${part}-${index}`}
              className="rounded bg-bg px-1.5 py-0.5 font-mono text-xs text-cyan"
            >
              {part.slice(1, -1)}
            </code>
          );
        }
        return <span key={`${part}-${index}`}>{part}</span>;
      })}
    </>
  );
}

function DocsIndex() {
  const featured = FEATURED_SLUGS.map((slug) => DOC_MAP[slug]).filter(Boolean);

  return (
    <div className="space-y-6">
      <section className="border-b border-edge pb-6">
        <p className="text-xs font-semibold uppercase tracking-wide text-cyan">Documentation</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-ink">DVAP platform docs</h1>
        <p className="mt-3 max-w-4xl text-sm leading-relaxed text-dim">
          Guides and reference material for onboarding applications, running repository assessments,
          reviewing findings, and operating an application security program.
        </p>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {featured.map((doc) => (
          <Link
            key={doc.slug}
            to={`/docs/${doc.slug}`}
            className="rounded-md border border-edge bg-panel p-4 transition-colors hover:border-cyan"
          >
            <p className="text-xs font-semibold uppercase tracking-wide text-cyan">
              {doc.category}
            </p>
            <h2 className="mt-2 text-sm font-bold text-ink">{doc.title}</h2>
            <p className="mt-2 text-xs leading-relaxed text-dim">{doc.summary}</p>
          </Link>
        ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-[16rem_1fr]">
        <aside className="panel h-max p-4 lg:sticky lg:top-20">
          <h2 className="text-xs font-bold uppercase tracking-widest text-dim">Browse by area</h2>
          <nav className="mt-3 space-y-1">
            {DOC_GROUPS.map((group) => (
              <a
                key={group.title}
                href={`#${sectionId(group.title)}`}
                className="block rounded px-2 py-1.5 text-sm text-dim hover:bg-panel2 hover:text-ink"
              >
                {group.title}
              </a>
            ))}
          </nav>
        </aside>

        <div className="space-y-8">
          {DOC_GROUPS.map((group) => (
            <section key={group.title} id={sectionId(group.title)} className="scroll-mt-24">
              <div className="mb-3">
                <h2 className="text-xl font-black tracking-tight text-ink">{group.title}</h2>
                <p className="mt-1 text-sm leading-relaxed text-dim">{group.description}</p>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {group.slugs.map((slug) => {
                  const doc = DOC_MAP[slug];
                  if (!doc) return null;
                  return (
                    <Link
                      key={slug}
                      to={`/docs/${slug}`}
                      className="rounded-md border border-edge bg-panel p-4 transition-colors hover:border-cyan"
                    >
                      <p className="text-xs font-semibold uppercase tracking-wide text-dim">
                        {doc.category}
                      </p>
                      <h3 className="mt-2 text-sm font-bold text-ink">{doc.title}</h3>
                      <p className="mt-2 text-xs leading-relaxed text-dim">{doc.summary}</p>
                    </Link>
                  );
                })}
              </div>
            </section>
          ))}

        </div>
      </div>
    </div>
  );
}

function DocsArticle({ doc }: { doc: ReferenceDoc }) {
  return (
    <div className="grid gap-6 lg:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="space-y-4 lg:sticky lg:top-20 lg:h-max">
        <Link to="/docs" className="btn w-full justify-start">
          &lt;- Back to docs
        </Link>
        <div className="panel p-4">
          <h2 className="text-xs font-bold uppercase tracking-widest text-dim">On this page</h2>
          <nav className="mt-3 space-y-1">
            {doc.sections.map((section) => (
              <a
                key={section.title}
                href={`#${sectionId(section.title)}`}
                className="block rounded px-2 py-1.5 text-sm text-dim hover:bg-panel2 hover:text-ink"
              >
                {section.title}
              </a>
            ))}
          </nav>
        </div>
      </aside>

      <article className="min-w-0">
        <header className="border-b border-edge pb-6">
          <nav
            className="flex flex-wrap items-center gap-2 text-xs text-dim"
            aria-label="Breadcrumb"
          >
            <Link to="/docs" className="font-semibold text-cyan hover:underline">
              Docs
            </Link>
            <span>/</span>
            <span>{doc.category}</span>
          </nav>
          <h1 className="mt-3 text-3xl font-black tracking-tight text-ink">{doc.title}</h1>
          <p className="mt-3 max-w-3xl text-base leading-relaxed text-dim">{doc.summary}</p>
        </header>

        <div className="space-y-8 py-6">
          {doc.sections.map((section) => (
            <section key={section.title} id={sectionId(section.title)} className="scroll-mt-24">
              <h2 className="text-xl font-black tracking-tight text-ink">{section.title}</h2>
              <div className="mt-3 space-y-3 text-sm leading-7 text-dim">
                {section.paragraphs.map((paragraph) => (
                  <p key={paragraph}>
                    <InlineText text={paragraph} />
                  </p>
                ))}
              </div>
              {section.bullets && (
                <ul className="mt-4 list-disc space-y-2 pl-5 text-sm leading-6 text-dim">
                  {section.bullets.map((item) => (
                    <li key={item}>
                      <InlineText text={item} />
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>

        <footer className="border-t border-edge pt-5">
          <h2 className="text-sm font-bold uppercase tracking-widest text-dim">Related pages</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            {doc.related.map((slug) => {
              const related = DOC_MAP[slug];
              if (!related) return null;
              return (
                <Link
                  key={slug}
                  to={`/docs/${slug}`}
                  className="rounded-md border border-edge bg-panel p-3 text-sm transition-colors hover:border-cyan"
                >
                  <span className="block text-xs font-semibold uppercase tracking-wide text-cyan">
                    {related.category}
                  </span>
                  <span className="mt-1 block font-semibold text-ink">{related.title}</span>
                </Link>
              );
            })}
          </div>
        </footer>
      </article>
    </div>
  );
}

export function Docs() {
  const { docId } = useParams();

  if (!docId) return <DocsIndex />;

  const doc = DOC_MAP[docId];
  if (!doc) return <Navigate to="/docs" replace />;

  return <DocsArticle doc={doc} />;
}
