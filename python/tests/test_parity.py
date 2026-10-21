"""Golden values shared with the .NET tests (testdata/golden.json)."""

import json
from pathlib import Path

import pytest

import dedupkit_br as dk

GOLDEN = json.loads((Path(__file__).resolve().parents[2] / "testdata" / "golden.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", GOLDEN["texts"], ids=lambda c: c["text"][:30])
def test_text_keys(case):
    t = case["text"]
    assert dk.normalize(t) == case["normalize"]
    assert dk.fingerprint(t) == case["fingerprint"]
    assert dk.legacy_fingerprint(t) == case["legacy_fingerprint"]
    assert dk.ngram_fingerprint(t) == case["ngram2"]
    assert dk.ngram_fingerprint(t, 3) == case["ngram3"]
    assert dk.token_key(t) == case["token_key"]
    assert dk.phonetic_key(t) == case["phonetic"]
    assert {k: sorted(v) for k, v in sorted(dk.attributes(t).items())} == case["attributes"]
    assert dk.shares_word(t, case["other"]) == case["shares_word"]
    assert dk.conflict(t, case["other"]) == case["conflict"]


def test_singular_codes_urls():
    for w, s in GOLDEN["singular"].items():
        assert dk.singular(w) == s
    for c in GOLDEN["codes"]:
        assert (dk.clean_code(c["code"]), dk.is_valid_gtin(c["code"]), dk.is_placeholder(c["code"]), dk.code_class(c["code"])) == \
            (c["clean"], c["valid_gtin"], c["placeholder"], c["class"])
    for u, n in GOLDEN["urls"].items():
        assert dk.normalize_url(u) == n


@pytest.mark.parametrize("key", sorted(GOLDEN["results"]))
def test_match_results(key):
    records = [dk.Record(l["id"], l["name"], l["brand"], tuple(l["codes"]), l["url"], l["image"], l["source"])
               for l in GOLDEN["listings"]]
    mode, option = key.split("|")
    kwargs = {"mode": mode}
    if option.startswith("attributes="):
        kwargs["check_attributes"] = option == "attributes=True"
    elif option == "brands":
        kwargs["check_brands"] = True
    elif option == "legacy":
        kwargs.update(rules=dk.LEGACY_RULES, check_attributes=False)
    elif option.startswith("max_block="):
        kwargs["max_block"] = int(option.split("=")[1])
    r = dk.match(records, **kwargs)
    expected = GOLDEN["results"][key]
    assert r.cluster_of == expected["cluster_of"]
    assert {k: list(v) for k, v in r.via.items()} == expected["via"]
    assert [[l.a, l.b, l.rule, l.value] for l in r.links] == expected["links"]
    assert [[x.a, x.b, x.rule, x.value, x.reason] for x in r.rejected] == expected["rejected"]
    assert [list(s) for s in r.skipped] == expected["skipped"]
