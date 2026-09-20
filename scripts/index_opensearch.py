"""Create OpenSearch indexes and bulk-upsert DynamoDB reference content."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common import search  # noqa: E402
from src.common.geo import extract_point  # noqa: E402
from src.common.store import scan_all  # noqa: E402

MAPPINGS = ROOT / "infra" / "opensearch"

INDEXES = {
    search.RESOURCES_INDEX: {
        "mapping": "resources.mapping.json",
        "logical": "resources",
        "id_field": "resource_id",
    },
    search.TOPICS_INDEX: {
        "mapping": "aftermath_topics.mapping.json",
        "logical": "faqs",
        "id_field": "faq_id",
    },
}


def load_mapping(filename: str) -> dict:
    with (MAPPINGS / filename).open(encoding="utf-8") as fh:
        return json.load(fh)


def to_document(record: dict, index: str) -> dict:
    """Shape a DynamoDB item for OpenSearch.

    Two conversions matter: Decimal is not JSON-serialisable, and `geo` must be
    a plain {lat, lon} pair for the geo_point mapping to accept it.
    """
    from src.common.store import from_dynamo

    document = from_dynamo(dict(record))

    if index == search.RESOURCES_INDEX:
        point = extract_point(record)
        if point:
            document["geo"] = {"lat": point[0], "lon": point[1]}
        else:
            # An unmapped geo field is better than a malformed one: the
            # geo_distance sort is configured to ignore it.
            document.pop("geo", None)

    return document


def build_documents(index: str) -> list:
    spec = INDEXES[index]
    return [
        {"_id": record.get(spec["id_field"]), "_source": to_document(record, index)}
        for record in scan_all(spec["logical"])
    ]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Index Rakshak content into OpenSearch.")
    parser.add_argument("--recreate", action="store_true", help="delete and rebuild the indexes")
    parser.add_argument("--dry-run", action="store_true", help="build documents, write nothing")
    args = parser.parse_args(argv)

    for index, spec in INDEXES.items():
        documents = build_documents(index)
        print(f"  {index}: {len(documents)} documents, mapping {spec['mapping']}")
        if args.dry_run:
            continue
        try:
            from opensearchpy.helpers import bulk

            connection = search.client()
            if args.recreate and connection.indices.exists(index=index):
                connection.indices.delete(index=index)
            if not connection.indices.exists(index=index):
                connection.indices.create(index=index, body=load_mapping(spec["mapping"]))
            actions = [{"_index": index, **document} for document in documents]
            if actions:
                bulk(connection, actions, raise_on_error=True, refresh=True)
        except Exception as exc:
            print(f"\n  Indexing failed ({type(exc).__name__}). Check the search endpoint and mappings.")
            return 1

    if args.dry_run:
        print("\nDry run complete - nothing was written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
