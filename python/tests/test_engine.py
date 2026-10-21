import sys
from pathlib import Path

import pytest

import dedupkit_br as dk

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from synth_listings import generate  # noqa: E402


def recs():
    return [
        dk.Record("a", "Guitarra Strinberg Preta", codes=("7891234567895",)),
        dk.Record("b", "Reservatório de água Gol", codes=("7891234567895",)),
        dk.Record("c", "Guitarra Strinberg STS100 preta", codes=("7891234567895",)),
        dk.Record("d", "Guitarra Strinberg STS100 Preto"),
        dk.Record("e", "Ração Golden 15kg", codes=("7894904567891",)),
        dk.Record("f", "Ração Golden 2,5kg", codes=("7894904567891",)),
    ]


@pytest.mark.parametrize("mode", ["connected", "two_hop"])
def test_barcode_needs_a_shared_word_and_same_size(mode):
    r = dk.match(recs(), mode=mode)
    assert r.clusters == [["a", "c", "d"]]
    reasons = {(x.a, x.b): x.reason for x in r.rejected}
    assert reasons[("a", "b")] == "names share no word"
    assert reasons[("e", "f")].startswith("weight_kg")
    assert r.via["c"][0] == "code"


def test_without_checks_everything_with_the_code_joins():
    unguarded = (dk.Rule("code", dk.DEFAULT_RULES[0].keys, needs_shared_word=False),)
    r = dk.match(recs(), rules=unguarded, check_attributes=False)
    assert ["a", "b", "c"] in r.clusters and ["e", "f"] in r.clusters


def test_big_blocks_are_skipped():
    many = [dk.Record(str(i), f"Produto {i} qualquer", image="no-photo") for i in range(150)]
    r = dk.match(many, rules=dk.rules_by_name("image"))
    assert r.clusters == [] and r.skipped == [("image", "no-photo", 150)]


def test_blacklist_codes_repeated_in_one_store():
    many = [dk.Record(str(i), f"Camiseta Básica {i}", codes=("7891234567895",), source="loja") for i in range(8)]
    assert "7891234567895" in dk.code_blacklist(many)
    assert dk.match(many, rules=dk.rules_by_name("code")).clusters == []


def test_ids_must_be_unique():
    with pytest.raises(ValueError):
        dk.match([dk.Record("1", "a"), dk.Record("1", "b")])


def test_connected_is_order_independent():
    listings = generate(seed=3, products_per_kind=8)
    records = [dk.Record(l.id, l.name, l.brand, l.codes, l.url, l.image, l.source) for l in listings]
    a = dk.match(records).clusters
    b = dk.match(list(reversed(records))).clusters
    assert sorted(sorted(c) for c in a) == sorted(sorted(c) for c in b)


def test_scores_on_synthetic_listings():
    listings = generate(seed=3, products_per_kind=8)
    records = [dk.Record(l.id, l.name, l.brand, l.codes, l.url, l.image, l.source) for l in listings]
    truth = {l.id: l.entity for l in listings}
    checked = dk.pairwise(dk.match(records).cluster_of, truth)
    unchecked = dk.pairwise(dk.match(records, check_attributes=False).cluster_of, truth)
    assert checked.precision > unchecked.precision
    assert checked.recall > 0.8


def test_pairwise():
    s = dk.pairwise({"1": 1, "2": 1, "3": 2}, {"1": "x", "2": "x", "3": "x"})
    assert (s.precision, s.correct_pairs, s.true_pairs) == (1.0, 1, 3)
