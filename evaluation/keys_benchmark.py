"""Why these keys: the text keys of the 2019 catalog, measured on real names.

    python evaluation/keys_benchmark.py

Two real sources, downloaded into evaluation/.cache/ on the first run:
- the 780 pairs labelled one by one of product-matching-pairs-portuguese (gold_pairs.csv): for each key, how many
  same-product pairs it joins (recall) and how many different-product pairs it wrongly joins;
- the 9,971 distinct names of the catalog's public sample (produtos.csv): how many blocks each key makes and how
  big the largest one is (a key that puts thousands of names in one block is useless for matching).

Keys measured: the ones DedupKit ships, and the 2019 experiments it did not keep (omission, skeleton, the fingerprint
with the every-other-word bug, phonetic key without numbers). Writes evaluation/keys_benchmark.json and .md.
"""

from __future__ import annotations

import csv
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))

import dedupkit_br as dk  # noqa: E402
from dedupkit_br.text import legacy_fingerprint, ngram_fingerprint  # noqa: E402

CACHE = ROOT / "evaluation" / ".cache"
SOURCES = {
    "gold_pairs.csv": "https://raw.githubusercontent.com/CaiqueDourado/product-matching-pairs-portuguese/main/gold/gold_pairs.csv",
    "produtos.csv": "https://raw.githubusercontent.com/CaiqueDourado/catalogo-produtos-ecommerce-brasil/main/sample/produtos.csv",
}
CONSONANTS = "JKQXZVWYBFMGPDHCLNTSR"


def fetch(name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        urllib.request.urlretrieve(SOURCES[name], path)
    return path


def letters(text: str) -> str:
    """Upper case, no accents, letters only, no spaces: the input of omission and skeleton (the 2019 code dropped
    digits too)."""
    return re.sub(r"[^a-z]", "", dk.normalize(text)).upper()


def omission(text: str) -> str:
    """Pollock and Zamora's omission key (via Talisman), as ported in 2019: the consonants present, in a fixed order
    (rarest first), then the vowels in order of appearance, each once."""
    s = letters(text)
    key = "".join(c for c in CONSONANTS if c in s)
    seen = []
    for c in s:
        if c not in CONSONANTS and c not in seen:
            seen.append(c)
    return key + "".join(seen)


def skeleton_2019(text: str) -> str:
    """The 2019 skeleton port, bugs included: the vowel part repeats the consonants, nothing is deduplicated."""
    s = letters(text)
    if not s:
        return ""
    first = s[0]
    cons = "".join(c for c in s[1:] if c != first and c not in "AEIOU")
    return f"{first}/{cons}/{cons}"


def skeleton(text: str) -> str:
    """Pollock and Zamora's skeleton key, as Talisman defines it: first letter, then the other consonants and then the
    vowels, each once, in order of appearance."""
    s = letters(text)
    if not s:
        return ""
    first, cons, vows = s[0], [], []
    for c in s[1:]:
        if c == first:
            continue
        bucket = vows if c in "AEIOU" else cons
        if c not in bucket:
            bucket.append(c)
    return first + "".join(cons) + "".join(vows)


KEYS = {  # name -> (function, in DedupKit?, what it is)
    "normalize": (dk.normalize, True, "lower case, no accents, punctuation as spaces (the 2019 'soft')"),
    "fingerprint": (dk.fingerprint, True, "unique words, sorted (OpenRefine)"),
    "token_key": (dk.token_key, True, "fingerprint without stopwords, plurals to singular"),
    "phonetic_key": (dk.phonetic_key, True, "Portuguese phonetic key per word, in order"),
    "ngram_fingerprint": (ngram_fingerprint, True, "character bigrams, unique, sorted (OpenRefine)"),
    "fingerprint_2019": (legacy_fingerprint, False, "fingerprint with the 2019 every-other-word bug"),
    "phonetic_no_digits": (lambda t: dk.phonetic_key(re.sub(r"\d+", " ", t)), False, "phonetic key with numbers removed"),
    "skeleton": (skeleton, False, "first letter, consonants, vowels (Pollock and Zamora)"),
    "skeleton_2019": (skeleton_2019, False, "the 2019 skeleton port, with its bugs"),
    "omission": (omission, False, "consonants in a fixed order, then vowels (Pollock and Zamora)"),
}


def gold_scores() -> dict:
    with open(fetch("gold_pairs.csv"), encoding="utf-8", newline="") as f:
        pairs = [(r["name_a"], r["name_b"], int(r["label"])) for r in csv.DictReader(f) if r["label"] in ("0", "1")]
    pos = sum(1 for *_, y in pairs if y == 1)
    out = {}
    for name, (fn, _, _) in KEYS.items():
        tp = sum(1 for a, b, y in pairs if y == 1 and fn(a) and fn(a) == fn(b))
        fp = sum(1 for a, b, y in pairs if y == 0 and fn(a) and fn(a) == fn(b))
        out[name] = {"joined_same": tp, "joined_different": fp, "recall": tp / pos,
                     "precision": tp / (tp + fp) if tp + fp else None}
    return {"pairs": len(pairs), "same_product": pos, "different": len(pairs) - pos, "keys": out}


def block_scores() -> dict:
    with open(fetch("produtos.csv"), encoding="utf-8", newline="") as f:
        names = sorted({r["name"] for r in csv.DictReader(f) if r["name"]})
    out = {}
    for name, (fn, _, _) in KEYS.items():
        blocks = Counter(k for k in map(fn, names) if k)
        big_key, big = blocks.most_common(1)[0]
        joined = sum(n for n in blocks.values() if n > 1)
        out[name] = {"blocks": len(blocks), "names_sharing_a_key": joined, "largest_block": big,
                     "largest_block_key": big_key[:60]}
    return {"distinct_names": len(names), "keys": out}


def collisions(fn, names, limit=3):
    """Pairs of names with the same key and no word in common: the counterexamples."""
    by_key = {}
    found = []
    for n in names:
        k = fn(n)
        if not k or len(n) < 12:
            continue
        for other in by_key.get(k, []):
            if not dk.shares_word(n, other):
                found.append((other, n, k))
                break
        by_key.setdefault(k, []).append(n)
        if len(found) >= limit:
            break
    return found


def main() -> None:
    gold, blocks = gold_scores(), block_scores()
    with open(fetch("produtos.csv"), encoding="utf-8", newline="") as f:
        names = sorted({r["name"] for r in csv.DictReader(f) if r["name"]})
    examples = {k: collisions(KEYS[k][0], names) for k in ("omission", "skeleton", "fingerprint_2019", "phonetic_no_digits")}
    documented = [("skeleton_2019", "DVD Canta Rio 98", "Dvd - Centurião"), ("phonetic_key", "Barraca Vintage Hambúrguer", "Barraca Vintage Hamburger")]
    examples["documented_2019"] = [(a, b, f"{k}: {KEYS[k][0](a)} / {KEYS[k][0](b)}") for k, a, b in documented]
    res = {"gold": gold, "blocks": blocks, "counterexamples": examples}
    (ROOT / "evaluation" / "keys_benchmark.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")

    lines = ["# Why these keys", "",
             f"Gold: {gold['pairs']} pairs labelled one by one ({gold['same_product']} same product, {gold['different']} different), "
             "from product-matching-pairs-portuguese. They were chosen hard: most share a barcode, a photo or almost the whole name. "
             f"Blocks: {blocks['distinct_names']:,} distinct names of the catalog's public sample.", "",
             "| Key | In DedupKit | Same-product pairs joined | Different-product pairs joined | Precision | Blocks | Largest block |",
             "|---|:---:|---:|---:|---:|---:|---:|"]
    for name, (_, ships, _) in KEYS.items():
        g, b = gold["keys"][name], blocks["keys"][name]
        prec = "–" if g["precision"] is None else f"{g['precision']:.0%}"
        lines.append(f"| `{name}` | {'yes' if ships else 'no'} | {g['joined_same']} ({g['recall']:.0%}) | {g['joined_different']} | "
                     f"{prec} | {b['blocks']:,} | {b['largest_block']:,} |")
    lines += ["", "## Counterexamples found in the sample (same key, no word in common)", ""]
    for k, ex in examples.items():
        for a, b, key in ex[:2]:
            lines.append(f"- `{k}` `{key[:60]}`: *{a}* × *{b}*")
    (ROOT / "evaluation" / "keys_benchmark.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
