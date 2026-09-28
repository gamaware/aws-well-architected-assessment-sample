#!/usr/bin/env bash
# Manual live test (never in CI): record the Harbor Goods answers in the AWS Well-Architected Tool, compare the
# Tool's risk counts with the report, then delete the workload. Runs only against the maintainer's dev profile.
set -euo pipefail

PROFILE="dev"
REGION="${LIVE_REGION:-us-east-1}"
PREFIX="harbor-goods-portfolio-test"
NAME="$PREFIX-$(date +%s)"
TAG_KEY="purpose"
TAG_VALUE="portfolio-test"

cd "$(dirname "$0")/../.."

echo "Account for profile $PROFILE:"
aws sts get-caller-identity --profile "$PROFILE" --output table
read -r -p "Create and delete a Well-Architected Tool workload in this account? [y/N] " answer
[[ "$answer" == "y" || "$answer" == "Y" ]] || { echo "Stopped."; exit 1; }

list_ids() {
  aws wellarchitected list-workloads --profile "$PROFILE" --region "$REGION" \
    --workload-name-prefix "$NAME" --query 'WorkloadSummaries[].WorkloadId' --output text
}

cleanup() {
  local status=$?
  local listing failed=0
  # Only this run's workload: NAME ends in a unique timestamp, so parallel or older runs are never touched.
  if ! listing="$(list_ids)"; then
    echo "ERROR: could not list workloads; check for $NAME by hand" >&2
    exit 1
  fi
  local ids=()
  read -r -a ids <<<"$listing"
  for id in "${ids[@]}"; do
    [[ "$id" == "None" ]] && continue
    echo "Deleting workload $id"
    aws wellarchitected delete-workload --profile "$PROFILE" --region "$REGION" --workload-id "$id" || failed=1
  done
  listing="$(list_ids)" || failed=1
  if [[ "$failed" != 0 || ( -n "$listing" && "$listing" != "None" ) ]]; then
    echo "ERROR: workload $NAME may remain; delete it by hand" >&2
    exit 1
  fi
  # Second check across the account by tag (the tagging index can lag a few minutes behind).
  local left
  left="$(aws resourcegroupstaggingapi get-resources --profile "$PROFILE" --region "$REGION" \
    --tag-filters "Key=$TAG_KEY,Values=$TAG_VALUE" --resource-type-filters wellarchitected \
    --query 'length(ResourceTagMappingList)' --output text)"
  if [[ "$left" != "0" ]]; then
    echo "WARNING: $left resource(s) tagged $TAG_KEY=$TAG_VALUE still listed; re-check in a few minutes" >&2
    exit 1
  fi
  echo "Cleanup verified: $NAME is gone and nothing tagged $TAG_KEY=$TAG_VALUE remains."
  exit "$status"
}
trap cleanup EXIT

PYTHONPATH=scripts uv run --locked --group live python scripts/live/wa_tool_roundtrip.py \
  --profile "$PROFILE" --region "$REGION" --name "$NAME" --tag "$TAG_KEY=$TAG_VALUE" --output live-output
