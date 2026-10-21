"""Record linkage by blocking keys: which records are the same product, and why."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .attributes import attributes, conflict_between
from .codes import clean_code, code_class
from .text import (fingerprint, legacy_fingerprint, ngram_fingerprint, normalize, normalize_url, phonetic_key,
                   shares_word, token_key, tokens)

GENERIC_BRANDS = frozenset({
    "brand", "marca", "importado", "produto importado", "original", "nao informado", "indisponivel",
    "n a", "n d", "na", "nd", "generico", "generica", "sem marca", "outros", "outras", "diversos", "varios",
})


@dataclass(frozen=True)
class Record:
    """One listing. Only ``id`` and ``name`` are required."""

    id: str
    name: str
    brand: str = ""
    codes: Tuple[str, ...] = ()
    url: str = ""
    image: str = ""
    source: str = ""


@dataclass(frozen=True)
class Rule:
    """A blocking key. Records with the same non-empty value are candidates.

    ``keys`` returns the values of one record (a record may have several codes). When
    ``needs_shared_word`` is set, a candidate pair is accepted only if the two names share a word.
    """

    name: str
    keys: Callable[[Record], Sequence[str]]
    needs_shared_word: bool = False


@dataclass(frozen=True)
class Link:
    a: str
    b: str
    rule: str
    value: str


@dataclass(frozen=True)
class Rejected:
    a: str
    b: str
    rule: str
    value: str
    reason: str


@dataclass
class Result:
    """``cluster_of`` maps every id to a cluster number (1, 2, ... in input order).
    ``via`` says which rule brought each record into its cluster."""

    cluster_of: Dict[str, int]
    via: Dict[str, Tuple[str, str]]
    links: List[Link]
    rejected: List[Rejected]
    skipped: List[Tuple[str, str, int]]

    @property
    def clusters(self) -> List[List[str]]:
        """Clusters with two or more records, in order of their first record."""
        groups: Dict[int, List[str]] = defaultdict(list)
        for rid, c in self.cluster_of.items():
            groups[c].append(rid)
        return [ids for _, ids in sorted(groups.items()) if len(ids) > 1]


# ---- default rules (the 2019 catalog's keys, with the corrections) ----

def _brand_ok(brand: str) -> Optional[str]:
    b = normalize(brand)
    if len(b) < 3 or b in GENERIC_BRANDS:
        return None
    return b


def _long_codes(r: Record) -> List[str]:
    return sorted({clean_code(c) for c in r.codes if code_class(c) == "long"})


def _short_codes_with(brand_key: Callable[[str], str]) -> Callable[[Record], List[str]]:
    def keys(r: Record) -> List[str]:
        b = _brand_ok(r.brand)
        if b is None:
            return []
        k = brand_key(b)
        return sorted({clean_code(c) + "|" + k for c in r.codes if code_class(c) == "short"})
    return keys


def _name_exact(r: Record) -> List[str]:
    n = normalize(r.name)
    return [n] if len(tokens(n)) >= 2 else []


def _name_fingerprint(r: Record) -> List[str]:
    t = tokens(r.name)
    return [fingerprint(r.name)] if len(set(t)) >= 3 else []


def _name_phonetic(r: Record) -> List[str]:
    k = phonetic_key(r.name)
    return [k] if len(k) > 3 and " " in k else []


def _name_ngram(r: Record) -> List[str]:
    n = normalize(r.name).replace(" ", "")
    return [ngram_fingerprint(r.name)] if len(n) >= 10 else []


def _name_tokens(r: Record) -> List[str]:
    k = token_key(r.name)
    return [k] if " " in k else []


def _url(r: Record) -> List[str]:
    u = normalize_url(r.url)
    return [u] if u else []


def _image(r: Record) -> List[str]:
    image = (r.image or "").strip(" \t\r\n")
    return [image] if image else []


def _legacy_name_fingerprint(r: Record) -> List[str]:
    t = tokens(r.name)
    return [legacy_fingerprint(r.name)] if len(set(t)) >= 3 else []


DEFAULT_RULES: Tuple[Rule, ...] = (
    Rule("code", _long_codes, needs_shared_word=True),
    Rule("name", _name_exact),
    Rule("name_fingerprint", _name_fingerprint),
    Rule("name_phonetic", _name_phonetic),
    Rule("name_ngram", _name_ngram),
    Rule("name_tokens", _name_tokens),
    Rule("url", _url),
    Rule("short_code_brand", _short_codes_with(fingerprint)),
    Rule("short_code_brand_ngram", _short_codes_with(ngram_fingerprint)),
    Rule("image", _image),
)
"""The keys of the 2019 catalog, in its order, with the fingerprint bug fixed."""

LEGACY_RULES: Tuple[Rule, ...] = tuple(
    Rule("name_fingerprint", _legacy_name_fingerprint) if r.name == "name_fingerprint" else r for r in DEFAULT_RULES
)
"""Same as DEFAULT_RULES but with the 2019 fingerprint (keeps every other word), to measure its effect."""


def rules_by_name(*names: str) -> Tuple[Rule, ...]:
    """Pick default rules by name, in the given order."""
    table = {r.name: r for r in DEFAULT_RULES}
    return tuple(table[n] for n in names)


# ---- matching ----

def code_blacklist(records: Sequence[Record], max_per_source: int = 5) -> set:
    """Codes that cannot identify a product: used by more than ``max_per_source`` listings of
    the same store, or letters-only codes used by more than one listing."""
    per_source: Dict[Tuple[str, str], int] = defaultdict(int)
    letters_only: Dict[str, int] = defaultdict(int)
    for r in records:
        for c in {clean_code(x) for x in r.codes}:
            if not c:
                continue
            per_source[(r.source, c)] += 1
            if all("A" <= ch <= "Z" for ch in c):
                letters_only[c] += 1
    bad = {c for (_, c), n in per_source.items() if n > max_per_source}
    bad |= {c for c, n in letters_only.items() if n > 1}
    return bad


def _brand_conflict(i: int, j: int, brands, name_words) -> Optional[str]:
    """Different brands, and neither brand is written in the other listing's name."""
    a, b = brands[i], brands[j]
    if a is None or b is None or a == b:
        return None
    if set(a.split(" ")) <= name_words[j] or set(b.split(" ")) <= name_words[i]:
        return None
    return f"brand: {a} vs {b}"


def match(
    records: Iterable[Record],
    rules: Sequence[Rule] = DEFAULT_RULES,
    mode: str = "connected",
    max_block: int = 100,
    blacklist: Optional[set] = None,
    check_attributes: bool = True,
    check_brands: bool = False,
) -> Result:
    """Group records that are the same product.

    - ``mode="connected"``: records linked by any rule, directly or through others, form one
      cluster. Independent of input order.
    - ``mode="two_hop"``: the 2019 algorithm. For each record not yet grouped, take its
      neighbours and their neighbours; they join the oldest existing cluster among them, or
      a new one. Depends on input order; chains stop after two hops.

    A key value shared by more than ``max_block`` records (a generic image, a placeholder
    name) is skipped and reported in ``Result.skipped``. Codes in ``blacklist`` (by default
    :func:`code_blacklist`) are ignored. With ``check_attributes`` (default), a pair whose
    names state different sizes, voltages, memories, colours or genders is refused whatever
    the rule (see :mod:`dedupkit_br.attributes`). ``check_brands`` also refuses pairs whose
    brand fields differ (and neither brand appears in the other name); it is off by default
    because marketplaces often put the seller's name in the brand field.
    """
    if mode not in ("connected", "two_hop"):
        raise ValueError("mode must be 'connected' or 'two_hop'")
    recs = list(records)
    ids = [r.id for r in recs]
    if len(set(ids)) != len(ids):
        raise ValueError("record ids must be unique")
    bad_codes = code_blacklist(recs) if blacklist is None else set(blacklist)
    code_rules = {"code", "short_code_brand", "short_code_brand_ngram"}
    attrs = [attributes(r.name) for r in recs] if check_attributes else None
    brands = [_brand_ok(r.brand) for r in recs] if check_brands else None
    name_words = [set(tokens(r.name)) for r in recs] if check_brands else None

    rejected: List[Rejected] = []
    skipped: List[Tuple[str, str, int]] = []
    # neighbours[i][j] = (rule, value) of the first rule that linked i and j
    neighbours: List[Dict[int, Tuple[str, str]]] = [dict() for _ in recs]
    edges: List[Tuple[int, int, str, str]] = []  # in deterministic order, for the audit trail

    for rule in rules:
        blocks: Dict[str, List[int]] = defaultdict(list)
        for i, r in enumerate(recs):
            for v in rule.keys(r):
                if not v:
                    continue
                if rule.name in code_rules and v.split("|", 1)[0] in bad_codes:
                    continue
                blocks[v].append(i)
        for value in sorted(blocks):
            members = blocks[value]
            if len(members) < 2:
                continue
            if len(members) > max_block:
                skipped.append((rule.name, value, len(members)))
                continue
            for x in range(len(members)):
                for y in range(x + 1, len(members)):
                    i, j = members[x], members[y]
                    if j in neighbours[i]:
                        continue
                    if rule.needs_shared_word and not shares_word(recs[i].name, recs[j].name):
                        rejected.append(Rejected(ids[i], ids[j], rule.name, value, "names share no word"))
                        continue
                    if attrs is not None or brands is not None:
                        why = (conflict_between(attrs[i], attrs[j]) if attrs is not None else None) or (
                            _brand_conflict(i, j, brands, name_words) if brands is not None else None)
                        if why:
                            rejected.append(Rejected(ids[i], ids[j], rule.name, value, why))
                            continue
                    neighbours[i][j] = (rule.name, value)
                    neighbours[j][i] = (rule.name, value)
                    edges.append((i, j, rule.name, value))

    if mode == "connected":
        return _connected(recs, ids, edges, rejected, skipped)
    return _two_hop(recs, ids, neighbours, rejected, skipped)


def _connected(recs, ids, edges, rejected, skipped) -> Result:
    parent = list(range(len(recs)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    links: List[Link] = []
    via: Dict[str, Tuple[str, str]] = {}
    for i, j, rule, value in edges:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)
            links.append(Link(ids[i], ids[j], rule, value))
            via.setdefault(ids[j], (rule, value))
            via.setdefault(ids[i], (rule, value))
    number: Dict[int, int] = {}
    cluster_of: Dict[str, int] = {}
    for i in range(len(recs)):
        root = find(i)
        if root not in number:
            number[root] = len(number) + 1
        cluster_of[ids[i]] = number[root]
    return Result(cluster_of, via, links, rejected, skipped)


def _two_hop(recs, ids, neighbours, rejected, skipped) -> Result:
    group: List[Optional[int]] = [None] * len(recs)
    via: Dict[str, Tuple[str, str]] = {}
    links: List[Link] = []
    next_group = 1
    for seed in range(len(recs)):
        if group[seed] is not None:
            continue
        hop1 = sorted(neighbours[seed])
        reached: Dict[int, Tuple[int, str, str]] = {}
        for h in hop1:
            rule, value = neighbours[seed][h]
            reached[h] = (seed, rule, value)
        for h in hop1:
            for m in sorted(neighbours[h]):
                if m != seed and m not in reached:
                    rule, value = neighbours[h][m]
                    reached[m] = (h, rule, value)
        members = [seed] + sorted(reached)
        existing = [group[m] for m in members if group[m] is not None]
        if existing:
            target = min(existing)
        else:
            target = next_group
            next_group += 1
        for m in members:
            if group[m] is None:
                group[m] = target
                if m in reached:
                    frm, rule, value = reached[m]
                    via[ids[m]] = (rule, value)
                    links.append(Link(ids[frm], ids[m], rule, value))
    # renumber clusters by first record
    number: Dict[int, int] = {}
    cluster_of: Dict[str, int] = {}
    for i, g in enumerate(group):
        if g not in number:
            number[g] = len(number) + 1
        cluster_of[ids[i]] = number[g]
    return Result(cluster_of, via, links, rejected, skipped)
