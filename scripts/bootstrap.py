"""Create the DynamoDB tables and load data/*.json into them.

Idempotent: run it as often as you like. Existing tables are reused unless you
pass --drop, and records are overwritten by primary key.

    python scripts/bootstrap.py                  # create + seed against LocalStack
    python scripts/bootstrap.py --drop           # recreate tables from scratch
    python scripts/bootstrap.py --validate-only  # check data/*.json, touch nothing
    python scripts/bootstrap.py --endpoint http://localhost:4566
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common import config, store  # noqa: E402
from src.common.schema import TABLE_SPECS, validate_records  # noqa: E402

DATA_DIR = ROOT / "data"

# Table definitions mirror template.yaml. Kept here too so the local stack can
# be brought up without CloudFormation.
TABLE_DEFINITIONS = {
    "emergency_protocols": {
        "AttributeDefinitions": [{"AttributeName": "scenario_id", "AttributeType": "S"}],
        "KeySchema": [{"AttributeName": "scenario_id", "KeyType": "HASH"}],
    },
    "aftermath_steps": {
        "AttributeDefinitions": [{"AttributeName": "stage_id", "AttributeType": "S"}],
        "KeySchema": [{"AttributeName": "stage_id", "KeyType": "HASH"}],
    },
    "faqs": {
        "AttributeDefinitions": [
            {"AttributeName": "faq_id", "AttributeType": "S"},
            {"AttributeName": "topic", "AttributeType": "S"},
        ],
        "KeySchema": [{"AttributeName": "faq_id", "KeyType": "HASH"}],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "topic-index",
                "KeySchema": [{"AttributeName": "topic", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    },
    "resources": {
        "AttributeDefinitions": [{"AttributeName": "resource_id", "AttributeType": "S"}],
        "KeySchema": [{"AttributeName": "resource_id", "KeyType": "HASH"}],
    },
}


def load_records(logical: str):
    path = DATA_DIR / TABLE_SPECS[logical]["file"]
    if not path.exists():
        raise SystemExit(f"Missing seed file: {path}")
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path.name} is not valid JSON: {exc}") from exc


def validate_all() -> int:
    problems = []
    for logical in TABLE_SPECS:
        problems.extend(validate_records(logical, load_records(logical)))

    if problems:
        print(f"\n{len(problems)} problem(s) found in seed data:\n")
        for problem in problems:
            print(f"  x {problem}")
        return 1

    total = sum(len(load_records(logical)) for logical in TABLE_SPECS)
    print(f"  ok  seed data valid ({total} records across {len(TABLE_SPECS)} tables)")
    return 0


def client():
    return store.resource().meta.client


def table_exists(name: str) -> bool:
    try:
        client().describe_table(TableName=name)
        return True
    except client().exceptions.ResourceNotFoundException:
        return False


def drop_table(name: str):
    if not table_exists(name):
        return
    client().delete_table(TableName=name)
    waiter = client().get_waiter("table_not_exists")
    waiter.wait(TableName=name, WaiterConfig={"Delay": 1, "MaxAttempts": 30})
    print(f"  -   dropped {name}")


def create_table(logical: str) -> bool:
    """Create the table if absent. Returns True if it was created."""
    name = config.table_name(logical)
    if table_exists(name):
        print(f"  =   {name} already exists")
        return False

    client().create_table(
        TableName=name,
        BillingMode="PAY_PER_REQUEST",
        **TABLE_DEFINITIONS[logical],
    )
    waiter = client().get_waiter("table_exists")
    waiter.wait(TableName=name, WaiterConfig={"Delay": 1, "MaxAttempts": 30})
    print(f"  +   created {name}")
    return True


def seed_table(logical: str) -> int:
    records = load_records(logical)
    problems = validate_records(logical, records)
    if problems:
        for problem in problems:
            print(f"  x {problem}")
        raise SystemExit(f"Refusing to seed {logical}: fix the data first.")

    written = store.batch_put(logical, records)
    print(f"  >   seeded {config.table_name(logical)} with {written} records")
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Bootstrap the Rakshak local stack.")
    parser.add_argument("--endpoint", help="DynamoDB endpoint (default: $AWS_ENDPOINT_URL or LocalStack)")
    parser.add_argument("--region", help="AWS region (default: $AWS_REGION or ap-south-1)")
    parser.add_argument("--drop", action="store_true", help="delete and recreate the tables")
    parser.add_argument("--validate-only", action="store_true", help="validate data/*.json and exit")
    parser.add_argument("--skip-seed", action="store_true", help="create tables but do not load data")
    args = parser.parse_args(argv)

    if args.validate_only:
        return validate_all()

    os.environ.setdefault("AWS_ENDPOINT_URL", args.endpoint or "http://localhost:4566")
    if args.endpoint:
        os.environ["AWS_ENDPOINT_URL"] = args.endpoint
    if args.region:
        os.environ["AWS_REGION"] = args.region
    # LocalStack accepts anything, but boto3 refuses to sign without credentials.
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    store.reset_clients()

    endpoint = config.dynamodb_endpoint() or "aws"
    print(f"\nRakshak bootstrap -> {endpoint} ({config.region()})\n")

    started = time.perf_counter()
    try:
        if args.drop:
            for logical in TABLE_SPECS:
                drop_table(config.table_name(logical))

        for logical in TABLE_SPECS:
            create_table(logical)

        if not args.skip_seed:
            total = sum(seed_table(logical) for logical in TABLE_SPECS)
            print(f"\nDone. {total} records loaded in {time.perf_counter() - started:.1f}s.")
        else:
            print("\nTables ready (seeding skipped).")
    except Exception as exc:  # noqa: BLE001
        print(f"\nBootstrap failed: {type(exc).__name__}: {exc}")
        print("Is LocalStack running?  docker run -d -p 4566:4566 localstack/localstack")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
