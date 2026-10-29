"""One match decision with its audit trail, as JSON (docs/example-decision.json).

    python scripts/make_json.py

Runs ``match()`` with the default options on examples/listings.csv and writes what the library
returns about one pair: listings 5 and 6, two showers with the same barcode, one 220 V / 7800 W and
the other 127 V / 5500 W. Every value comes from a library call:

- ``records``: the two ``Record`` objects as read from the CSV (like the command line reads them);
- ``shared_keys``: rules whose ``Rule.keys()`` give both records the same value (they share a block);
- ``attributes``: ``attributes(name)`` for each record, and ``conflict``: ``conflict(name_a, name_b)``;
- ``links``, ``rejected``: the ``Result.links`` and ``Result.rejected`` entries for this pair;
- ``cluster_of``, ``via``: ``Result.cluster_of`` and ``Result.via`` for both ids;
- ``same_cluster``: whether ``Result.cluster_of`` puts them together.

Needs only the package itself (no network); run from the repository root.
"""

from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))

from dedupkit_br import DEFAULT_RULES, Record, attributes, conflict, match  # noqa: E402

PAIR = ("5", "6")
OUT = ROOT / "docs" / "example-decision.json"


def read_listings(path: Path) -> list[Record]:
    """Records from the example CSV, read the same way as ``dedupkit-br match`` reads them."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [Record(row["id"], row["name"], row["brand"], tuple(c.strip() for c in row["code"].split(",") if c.strip()),
                       row["url"], row["image"], row["source"]) for row in csv.DictReader(f)]


def decision(records: list[Record], a: str, b: str) -> dict:
    result = match(records)
    by_id = {r.id: r for r in records}
    ra, rb = by_id[a], by_id[b]
    pair = {a, b}
    shared = []
    for rule in DEFAULT_RULES:
        common = sorted(set(k for k in rule.keys(ra) if k) & set(k for k in rule.keys(rb) if k))
        shared += [{"rule": rule.name, "value": v} for v in common]
    return {
        "input": "examples/listings.csv",
        "call": "match(records)",
        "records": [{**asdict(r), "codes": list(r.codes)} for r in (ra, rb)],
        "shared_keys": shared,
        "attributes": {r.id: {k: sorted(v) for k, v in sorted(attributes(r.name).items())} for r in (ra, rb)},
        "conflict": conflict(ra.name, rb.name),
        "links": [asdict(x) for x in result.links if {x.a, x.b} == pair],
        "rejected": [asdict(x) for x in result.rejected if {x.a, x.b} == pair],
        "cluster_of": {i: result.cluster_of[i] for i in (a, b)},
        "via": {i: list(result.via[i]) if i in result.via else None for i in (a, b)},
        "same_cluster": result.cluster_of[a] == result.cluster_of[b],
    }


def main() -> None:
    records = read_listings(ROOT / "examples" / "listings.csv")
    OUT.write_text(json.dumps(decision(records, *PAIR), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
