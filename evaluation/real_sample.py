"""Run DedupKit on real listings: the sample of the Brazilian e-commerce catalog
(28,569 offers in 4,030 groups made by the 2019 pipeline).

There is no answer key for these offers, so this script does not score anything. It shows
what the attribute check refuses on real data, with examples, and how many 2019 groups it
would split. Run from the repository root:  python evaluation/real_sample.py
Downloads the sample CSVs (about 11 MB) into evaluation/.cache/ on the first run.
"""

from __future__ import annotations

import csv
import json
import sys
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))

import dedupkit_br as dk  # noqa: E402

BASE = "https://raw.githubusercontent.com/CaiqueDourado/catalogo-produtos-ecommerce-brasil/main/sample/"
CACHE = ROOT / "evaluation" / ".cache"


def fetch(name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        urllib.request.urlretrieve(BASE + name, path)
    return path


def load():
    codes = defaultdict(list)
    with open(fetch("eans.csv"), encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["code"]:
                codes[row["product_id"]].append(row["code"])
    records, legacy = [], {}
    with open(fetch("produtos.csv"), encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            records.append(dk.Record(row["id"], row["name"] or "", row["brand"] or "", tuple(codes[row["id"]]),
                                     row["url"] or "", row["image_hash"] or "", row["store_id"]))
            if row["group_id"]:
                legacy[row["id"]] = row["group_id"]
    return records, legacy


def main() -> None:
    records, legacy = load()
    names = {r.id: r.name for r in records}
    result = dk.match(records)  # default: all keys, connected, attribute check
    reasons = Counter(r.reason.split(":")[0] for r in result.rejected)
    by_group = defaultdict(set)
    for rid, g in legacy.items():
        by_group[g].add(result.cluster_of[rid])
    split = sum(1 for clusters in by_group.values() if len(clusters) > 1)
    examples = {}
    for r in result.rejected:
        dim = r.reason.split(":")[0]
        if dim in ("weight_kg", "volume_l", "voltage_v", "memory_gb", "length_cm", "colour") and dim not in examples:
            examples[dim] = {"rule": r.rule, "a": names[r.a], "b": names[r.b], "reason": r.reason}
    with_brands = dk.match(records, check_brands=True)
    brand_refusals = sum(1 for r in with_brands.rejected if r.reason.startswith("brand:"))
    out = {"offers": len(records), "groups_2019": len(by_group), "groups_2019_split": split,
           "refused_by_reason": dict(reasons.most_common()), "brand_check_refusals": brand_refusals,
           "examples": examples}
    (ROOT / "evaluation" / "real_sample.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
