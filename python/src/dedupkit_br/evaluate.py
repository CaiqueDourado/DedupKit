"""Measure a clustering against known answers."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Hashable, List, Mapping

from .engine import Result


@dataclass(frozen=True)
class Scores:
    """Pairwise scores: a pair of records is a positive when both are in the same cluster."""

    precision: float
    recall: float
    f1: float
    true_pairs: int
    predicted_pairs: int
    correct_pairs: int


def _pairs(n: int) -> int:
    return n * (n - 1) // 2


def pairwise(predicted: Mapping[str, Hashable], truth: Mapping[str, Hashable]) -> Scores:
    """Pairwise precision, recall and F1 of ``predicted`` (id → cluster) against ``truth``
    (id → true entity). Only ids present in both are counted."""
    ids = [i for i in predicted if i in truth]
    pred = Counter(predicted[i] for i in ids)
    true = Counter(truth[i] for i in ids)
    both = Counter((predicted[i], truth[i]) for i in ids)
    predicted_pairs = sum(_pairs(n) for n in pred.values())
    true_pairs = sum(_pairs(n) for n in true.values())
    correct = sum(_pairs(n) for n in both.values())
    p = correct / predicted_pairs if predicted_pairs else 1.0
    r = correct / true_pairs if true_pairs else 1.0
    f = 2 * p * r / (p + r) if p + r else 0.0
    return Scores(p, r, f, true_pairs, predicted_pairs, correct)


def link_precision(result: Result, truth: Mapping[str, Hashable]) -> Dict[str, Dict[str, float]]:
    """For each rule: how many links it made and the share that joined two records of the
    same true entity. Shows which keys can be trusted."""
    made: Dict[str, int] = defaultdict(int)
    right: Dict[str, int] = defaultdict(int)
    for link in result.links:
        if link.a in truth and link.b in truth:
            made[link.rule] += 1
            right[link.rule] += truth[link.a] == truth[link.b]
    return {rule: {"links": made[rule], "precision": right[rule] / made[rule]} for rule in made}


def refused_that_were_right(result: Result, truth: Mapping[str, Hashable]) -> List[Dict[str, str]]:
    """Refused barcode matches whose records are in fact the same entity (the guard's misses)."""
    return [vars(r) for r in result.rejected if r.a in truth and r.b in truth and truth[r.a] == truth[r.b]]
