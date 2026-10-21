"""Which keys can be trusted? Precision and recall of each rule on synthetic listings.

Run from the repository root:  python evaluation/evaluate.py
Writes evaluation/results.json and evaluation/results.md.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import dedupkit_br as dk  # noqa: E402
from synth_listings import generate  # noqa: E402

RULE_LABELS = {
    "code": "barcode (long code) + shared word",
    "name": "exact name",
    "name_fingerprint": "name fingerprint",
    "name_phonetic": "phonetic key",
    "name_ngram": "character bigrams",
    "name_tokens": "words, singular, no stopwords",
    "url": "URL without parameters",
    "short_code_brand": "short code + brand",
    "short_code_brand_ngram": "short code + brand bigrams",
    "image": "same image file",
}


def run(records, truth, rules, mode="connected", check_attributes=True, check_brands=False):
    t = time.time()
    result = dk.match(records, rules=rules, mode=mode, check_attributes=check_attributes, check_brands=check_brands)
    s = dk.pairwise(result.cluster_of, truth)
    return result, {"precision": s.precision, "recall": s.recall, "f1": s.f1, "seconds": time.time() - t}


def main() -> None:
    listings = generate()
    records = [dk.Record(l.id, l.name, l.brand, l.codes, l.url, l.image, l.source) for l in listings]
    truth = {l.id: l.entity for l in listings}
    out = {"listings": len(listings), "entities": len(set(truth.values())), "single_rules": {}, "configurations": {}}

    for rule in dk.DEFAULT_RULES:
        _, scores = run(records, truth, (rule,), check_attributes=False)
        _, checked = run(records, truth, (rule,))
        scores["checked"] = checked
        out["single_rules"][rule.name] = scores

    unguarded_code = dk.Rule("code", dk.DEFAULT_RULES[0].keys, needs_shared_word=False)
    recommended = dk.rules_by_name("code", "name", "name_tokens", "url", "short_code_brand")
    configs = {
        "2019: all keys, two hops, fingerprint bug, no attribute check": (dk.LEGACY_RULES, "two_hop", False),
        "all keys, two hops, no attribute check": (dk.DEFAULT_RULES, "two_hop", False),
        "all keys, barcode without the word check, no attribute check": ((unguarded_code,) + dk.DEFAULT_RULES[1:], "connected", False),
        "all keys, connected, no attribute check": (dk.DEFAULT_RULES, "connected", False),
        "all keys, connected, attribute check": (dk.DEFAULT_RULES, "connected", True),
        "all keys, two hops, attribute check": (dk.DEFAULT_RULES, "two_hop", True),
        "all keys, connected, attribute and brand check": (dk.DEFAULT_RULES, "connected", "brands"),
        "recommended keys, connected, attribute check": (recommended, "connected", True),
    }
    for label, (rules, mode, check) in configs.items():
        result, scores = run(records, truth, rules, mode, bool(check), check == "brands")
        scores["link_precision"] = dk.link_precision(result, truth)
        scores["refused"] = len(result.rejected)
        scores["refused_but_same"] = len(dk.refused_that_were_right(result, truth))
        out["configurations"][label] = scores

    (ROOT / "evaluation" / "results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    lines = ["# Evaluation results", "",
             f"{out['listings']:,} synthetic listings of {out['entities']:,} product variants (tools/synth_listings.py).", "",
             "## Each rule alone", "", "| Rule | Precision | Recall | Precision with attribute check | Recall with attribute check |", "|---|---:|---:|---:|---:|"]
    for name, s in out["single_rules"].items():
        c = s["checked"]
        lines.append(f"| {RULE_LABELS[name]} (`{name}`) | {s['precision']:.1%} | {s['recall']:.1%} | {c['precision']:.1%} | {c['recall']:.1%} |")
    lines += ["", "## Configurations", "", "| Configuration | Precision | Recall | F1 |", "|---|---:|---:|---:|"]
    for name, s in out["configurations"].items():
        lines.append(f"| {name} | {s['precision']:.1%} | {s['recall']:.1%} | {s['f1']:.3f} |")
    c = out["configurations"]["all keys, connected, attribute check"]
    lines += ["", f"Pairs refused (no shared word or conflicting attributes): {c['refused']:,}, of which {c['refused_but_same']:,} were in fact the same product."]
    (ROOT / "evaluation" / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
