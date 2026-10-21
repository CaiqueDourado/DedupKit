"""Command line: ``dedupkit-br match listings.csv > clusters.csv``."""

from __future__ import annotations

import argparse
import csv
import sys
from typing import List, Optional

from .engine import DEFAULT_RULES, Record, match, rules_by_name


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="dedupkit-br", description="Group listings that are the same product.")
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("match", help="read a CSV of listings, write id,cluster,rule,value")
    m.add_argument("csv", help="input CSV (UTF-8, header row)")
    m.add_argument("--id", default="id", help="id column (default: id)")
    m.add_argument("--name", default="name", help="name column (default: name)")
    m.add_argument("--brand", default=None)
    m.add_argument("--code", default=None, help="barcode/SKU column; several codes may be separated by commas")
    m.add_argument("--url", default=None)
    m.add_argument("--image", default=None, help="image signature column (for example a SimilarImageFinder hash)")
    m.add_argument("--source", default=None, help="store or source column (used by the code blacklist)")
    m.add_argument("--rules", default=None, help="comma-separated rule names (default: all): " + ",".join(r.name for r in DEFAULT_RULES))
    m.add_argument("--mode", choices=["connected", "two_hop"], default="connected")
    m.add_argument("--no-attribute-check", action="store_true", help="do not refuse pairs with different sizes, voltages, colours...")
    m.add_argument("--brand-check", action="store_true", help="also refuse pairs with different brands")
    m.add_argument("--rejected", default=None, help="write refused pairs to this CSV")
    args = parser.parse_args(argv)

    def col(row, name):
        return (row.get(name) or "") if name else ""

    records = []
    with open(args.csv, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            codes = tuple(c.strip() for c in col(row, args.code).split(",") if c.strip())
            records.append(Record(col(row, args.id), col(row, args.name), col(row, args.brand), codes,
                                  col(row, args.url), col(row, args.image), col(row, args.source)))
    rules = rules_by_name(*args.rules.split(",")) if args.rules else DEFAULT_RULES
    result = match(records, rules=rules, mode=args.mode, check_attributes=not args.no_attribute_check,
                   check_brands=args.brand_check)

    out = csv.writer(sys.stdout, lineterminator="\n")
    out.writerow(["id", "cluster", "rule", "value"])
    for r in records:
        rule, value = result.via.get(r.id, ("", ""))
        out.writerow([r.id, result.cluster_of[r.id], rule, value])
    if args.rejected:
        with open(args.rejected, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["a", "b", "rule", "value", "reason"])
            for x in result.rejected:
                w.writerow([x.a, x.b, x.rule, x.value, x.reason])
    print(f"{len(records)} listings, {len(result.clusters)} clusters with 2 or more, {len(result.rejected)} pairs refused",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
