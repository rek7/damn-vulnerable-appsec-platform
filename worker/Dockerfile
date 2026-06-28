# DVAP worker image.
#
# Build context MUST be the repo ROOT (it COPYs worker/, evil-repos/, seeds/):
#     docker build -f worker/Dockerfile -t dvap-worker .
#
# This scan worker runs submitted repository contents through real analyzer
# toolchains (checkov, ruby + rubocop, node + npm + eslint, python build
# tooling) so validation scenarios reflect genuine tool behavior. It runs as a
# NON-ROOT user and relies on containment controls such as synthetic watermarked
# seeds, no external egress, and link-local blocking.

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    NODE_MAJOR=20

# --- system toolchains -------------------------------------------------------
# git: git-source clones. ruby + ruby-dev + build tools: gemspec eval + rubocop.
# nodejs + npm: eslint + npm lifecycle. ca-certificates/curl: node apt setup.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
        curl \
        ca-certificates \
        gnupg \
        ruby \
        ruby-dev \
        build-essential \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
        | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
        > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# --- ruby analyzer toolchain (rubocop) --------------------------------------
RUN gem install --no-document rubocop

# --- node analyzer toolchain (eslint, global so it's on PATH) ---------------
RUN npm install -g eslint@8

# --- python deps (app + checkov + build tooling) ----------------------------
WORKDIR /app
COPY worker/requirements.txt /app/worker/requirements.txt
RUN pip install --no-cache-dir -r /app/worker/requirements.txt \
    && pip install --no-cache-dir setuptools wheel

# --- application + bundled payloads + synthetic seeds ------------------------
COPY worker/ /app/worker
COPY evil-repos/ /app/evil-repos
COPY seeds/ /app/seeds

# --- non-root user + writable k8s SA token dir -------------------------------
# Create the serviceaccount dir up-front and chown it so the non-root user can
# write the (synthetic) token file per scan (§7).
RUN useradd --create-home --uid 10001 dvap \
    && mkdir -p /var/run/secrets/kubernetes.io/serviceaccount \
    && chown -R dvap:dvap /var/run/secrets/kubernetes.io/serviceaccount /app

USER dvap

ENV DVAP_SEEDS_FILE=/app/seeds/synthetic.env \
    DVAP_K8S_TOKEN_SRC=/app/seeds/k8s-sa-token \
    DVAP_EVIL_REPOS_DIR=/app/evil-repos

EXPOSE 8100

# Run from /app/worker so `app` (the package) is importable as `app`.
WORKDIR /app/worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
