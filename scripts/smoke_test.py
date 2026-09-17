"""Hit every endpoint against a running API and print pass/fail.

    sam local start-api --port 3000
    python scripts/smoke_test.py

This is the pre-demo check: it catches the "tables exist but are empty" and
"Lambda cannot reach LocalStack from inside Docker" failures that unit tests
cannot see, because both stacks have to be up for it to pass.
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

# (label, path, query, expectation) - expectation takes the parsed `data`.
CHECKS = [
    ("health", "/health", {}, lambda d: d["healthy"] is True),
    ("emergency numbers", "/emergency/numbers", {}, lambda d: d["unified"] == "112"),
    ("good samaritan", "/emergency/good-samaritan", {}, lambda d: len(d["points"]) >= 4),
    ("protocol list", "/emergency/protocols", {}, lambda d: d["count"] == 4),
    ("protocol: not_breathing", "/emergency/protocols",
     {"scenario": "not_breathing"}, lambda d: len(d["steps"]) >= 3),
    ("aftermath stages", "/aftermath/steps", {}, lambda d: d["count"] == 4),
    ("aftermath: hospital", "/aftermath/steps",
     {"stage": "hospital"}, lambda d: "MLC" in " ".join(d["checklist"])),
    ("faq by topic", "/aftermath/faqs", {"topic": "fir"}, lambda d: d["count"] > 0),
    ("faq search", "/aftermath/faqs",
     {"q": "police refusing fir"}, lambda d: d["items"][0]["faq_id"] == "faq_fir_delay"),
    ("resources: all", "/resources", {}, lambda d: d["total"] == 10),
    ("resources: hospitals near Bengaluru", "/resources",
     {"type": "hospital", "lat": "12.9716", "lon": "77.5946"},
     lambda d: d["items"][0]["distance_km"] < 10),
    ("resources: nationwide survives state filter", "/resources",
     {"state": "Tripura"},
     lambda d: any(i["resource_id"] == "res_nalsa" for i in d["items"])),
]

# Endpoints expected to fail in a specific way.
NEGATIVE_CHECKS = [
    ("unknown scenario is 404", "/emergency/protocols", {"scenario": "nope_nope"}, 404),
    ("bad stage is 400", "/aftermath/steps", {"stage": "morgue"}, 400),
    ("half a coordinate is 400", "/resources", {"lat": "12.97"}, 400),
]


def fetch(base, path, query):
    url = base.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test a running Rakshak API.")
    parser.add_argument("--base", default="http://localhost:3000", help="API base URL")
    args = parser.parse_args(argv)

    print(f"\nSmoke testing {args.base}\n")
    failures = 0

    for label, path, query, expect in CHECKS:
        try:
            status, body = fetch(args.base, path, query)
            if status != 200:
                raise AssertionError(f"HTTP {status}: {body.get('error')}")
            if not body.get("ok"):
                raise AssertionError(f"ok=false: {body.get('error')}")
            if not expect(body["data"]):
                raise AssertionError("response did not match expectation")
            print(f"  ok   {label}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FAIL {label}: {type(exc).__name__}: {exc}")

    for label, path, query, expected_status in NEGATIVE_CHECKS:
        try:
            status, body = fetch(args.base, path, query)
            if status != expected_status:
                raise AssertionError(f"expected {expected_status}, got {status}")
            if body.get("ok") is not False:
                raise AssertionError("error responses must carry ok=false")
            print(f"  ok   {label}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  FAIL {label}: {type(exc).__name__}: {exc}")

    total = len(CHECKS) + len(NEGATIVE_CHECKS)
    if failures:
        print(f"\n{failures} of {total} checks failed.")
        print("Is the stack seeded?  python scripts/bootstrap.py")
        return 1

    print(f"\nAll {total} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
