CREATE TABLE IF NOT EXISTS integration_credentials (
    id text PRIMARY KEY,
    service text NOT NULL,
    credential_type text NOT NULL,
    owner text NOT NULL,
    value text NOT NULL,
    notes text NOT NULL DEFAULT ''
);

INSERT INTO integration_credentials
    (id, service, credential_type, owner, value, notes)
VALUES
    (
        'aws-deploy-access-key',
        'aws-production-deploy',
        'aws_access_key_id',
        'platform-security',
        'AKIAFAKECANARY000001',
        'Synthetic canary credential for lateral-movement validation.'
    ),
    (
        'aws-deploy-secret-key',
        'aws-production-deploy',
        'aws_secret_access_key',
        'platform-security',
        'FAKEAwsCanarySecretKeyForDVAPDoNotUse000000000FAKE',
        'Synthetic canary credential for lateral-movement validation.'
    ),
    (
        'aws-session-token',
        'aws-production-deploy',
        'aws_session_token',
        'platform-security',
        'FQoGZXIvYXdzEFAKEdvapCanarySessionTokenDoNotUseFAKE',
        'Synthetic session token with no cloud privileges.'
    ),
    (
        'ci-github-token',
        'repository-automation',
        'github_token',
        'appsec-automation',
        'ghp_FAKEdvapCanaryGithubToken000000000000',
        'Synthetic source-control token for scanner validation.'
    ),
    (
        'npm-publish-token',
        'package-publishing',
        'npm_token',
        'release-engineering',
        'npm_FAKEdvapCanaryPublishToken000000000000',
        'Synthetic package-publishing token for scanner validation.'
    ),
    (
        'db-reader-dsn',
        'application-postgres',
        'postgres_url',
        'application-platform',
        'postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/dvap',
        'Intentionally overexposed internal database DSN for local assessment scenarios.'
    )
ON CONFLICT (id) DO UPDATE
SET service = EXCLUDED.service,
    credential_type = EXCLUDED.credential_type,
    owner = EXCLUDED.owner,
    value = EXCLUDED.value,
    notes = EXCLUDED.notes;
