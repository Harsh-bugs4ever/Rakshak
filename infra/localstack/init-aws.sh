#!/bin/bash
# Runs inside the LocalStack container once the services are ready.
#
# Creates the four tables so `docker compose up` alone gives you a working
# stack. Seeding still happens from the host via `python scripts/bootstrap.py`,
# which validates the content before writing it.

set -euo pipefail

echo "[rakshak] creating DynamoDB tables..."

create_table() {
  local name="$1"
  shift
  if awslocal dynamodb describe-table --table-name "$name" >/dev/null 2>&1; then
    echo "[rakshak]   = $name already exists"
    return 0
  fi
  awslocal dynamodb create-table --table-name "$name" --billing-mode PAY_PER_REQUEST "$@" >/dev/null
  echo "[rakshak]   + $name"
}

create_table EmergencyProtocols \
  --attribute-definitions AttributeName=scenario_id,AttributeType=S \
  --key-schema AttributeName=scenario_id,KeyType=HASH

create_table AftermathSteps \
  --attribute-definitions AttributeName=stage_id,AttributeType=S \
  --key-schema AttributeName=stage_id,KeyType=HASH

create_table FAQs \
  --attribute-definitions AttributeName=faq_id,AttributeType=S AttributeName=topic,AttributeType=S \
  --key-schema AttributeName=faq_id,KeyType=HASH \
  --global-secondary-indexes \
    'IndexName=topic-index,KeySchema=[{AttributeName=topic,KeyType=HASH}],Projection={ProjectionType=ALL}'

create_table Resources \
  --attribute-definitions AttributeName=resource_id,AttributeType=S \
  --key-schema AttributeName=resource_id,KeyType=HASH

echo "[rakshak] tables ready. Seed them with: python scripts/bootstrap.py"
