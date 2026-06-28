# Benign cover: a trivial Terraform resource so Checkov has IaC to scan and the
# repo looks like an ordinary infrastructure project. The actual payload lives in
# checkov_checks/extra_check.py, which Checkov imports because of .checkov.yml.
resource "aws_s3_bucket" "example" {
  bucket = "dvap-example-bucket"
}
