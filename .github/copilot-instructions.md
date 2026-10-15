# Copilot code review instructions

This repository is a fictional sample deliverable: an AWS Well-Architected and DevOps assessment for the fictional
retailer Harbor Goods. When reviewing pull requests:

- Check that best-practice IDs in `data/synthetic/` match the AWS Well-Architected Framework or the AWS
  Well-Architected DevOps Guidance exactly; titles follow the AWS wording, with access titles phrased in plain
  access terms.
- Check that any change to `data/synthetic/` or `scripts/` comes with regenerated `evidence/` and report tables
  (`make evidence`), and that `make verify` would still pass.
- Flag any real AWS account ID, ARN, IP address, email address or organization name. The repository allows no 12-digit
  account IDs (data uses `YOUR_AWS_ACCOUNT_ID`) and only `example.com`.
- Flag suppressed lint rules; fix violations instead of suppressing them.
- Workflows: `permissions: {}` at the top, SHA-pinned actions, no `pull_request_target`, no cloud credentials.
- Shell scripts need a shebang, executable permission, and must pass shellcheck and shellharden.
- Flag job-marketplace profile links, service offers and sales badges; none are allowed.
