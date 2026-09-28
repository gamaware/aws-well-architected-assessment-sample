# Copilot code review instructions

This repository is a fictional sample deliverable: an AWS Well-Architected and DevOps assessment for the fictional
retailer Harbor Goods. When reviewing pull requests:

- Check that best-practice IDs and titles in `data/synthetic/` match the AWS Well-Architected Framework or the AWS
  Well-Architected DevOps Guidance exactly.
- Check that any change to `data/synthetic/` or `scripts/` comes with regenerated `evidence/` and report tables
  (`make evidence`), and that `make verify` would still pass.
- Flag any real AWS account ID, ARN, IP address, email address or organization name. The repository allows only AWS
  documentation example IDs and `example.com`.
- Flag suppressed lint rules; fix violations instead of suppressing them.
- Workflows: `permissions: {}` at the top, SHA-pinned actions, no `pull_request_target`, no cloud credentials.
- Shell scripts need a shebang, executable permission, and must pass shellcheck and shellharden.
