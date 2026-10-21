"""Write testdata/golden.json from the Python implementation; the .NET tests must reproduce it.

Run from the repository root:  python tools/make_testdata.py
Uses tools/synth_listings.py and, when available, real names from the catalog sample
(evaluation/.cache/produtos.csv, downloaded by evaluation/real_sample.py).
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python" / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import dedupkit_br as dk  # noqa: E402
from synth_listings import generate  # noqa: E402

TRICKY = [
    "", " ", "Pendente TLF-28, Preto!", "  AÇÚCAR   Refinado  ", "Straße Œuvre Æsir ŁÓDŹ", "café́ com leite",
    "Fone de Ouvido sem Fio JBL", "FONES DE OUVIDO JBL S/ FIO", "Caçarola Antiaderente 24cm", "cassarola antiaderente",
    "Chuveiro Elétrico 220v 7500W", "Xuveiro eletrico 220 v 7.500 w", "Ração Royal Canin 15kg", "Racao Royal Canin 2,5 kg",
    "Geladeira Brastemp Frost Free 375L Inox 110V", "Jeladeira Brastemp 375 L Branca 220 V", "Guitarra Strinberg STS100",
    "Liquidificador Bivolt 1000W Preto", "Smartphone 128GB Azul 6,1 polegadas", "Tênis Masculino Preto/Branco 42",
    "Panela de Pressão 4,5L", "Kit 3 Pães de Queijo 500g", "TV 50\" 4K", "Livro - O Pequeno Príncipe (Edição de Bolso)",
    "Lençóis Casal 4 Peças", "LENCOL CASAL 4 PECAS", "Toalha de Mesa 1,50m", "Ar-Condicionado 12.000 BTUs", "Bateria 5000mAh",
    "Porta Escova 10,6x8,5cm Verde", "Toalha 1,50 x 2,00 m", "Kit 2 x 500ml", "Bota Ramarim Tachas - 40 - PRETO", "Camiseta M/L Basica - G", "Pulseira Galileo (M)", "Sapatênis R480 - Tamanho 38 - Marinho", "Meia Kit 3 Pares", "Lâmpada H4 Kit c/50", "Roldana 2 Un", "Kit 4 em 1", "Forno 110V", "Concha Inox Cromada", "TV 55\" Samsung", "Monitor 24” LED", "Quadro 20x30", "Tampo 160x80 Cm", "Colchão 193x203x22cm", "ZAPATILLAS Talle 31", "Kit 007 Peças", "Kit Cobre Leito Queen Marinho", "Pendente Cobre E27", "日本語 テキスト", "emoji 😀 teste", "x" * 300, "1 2 3 4 5", "Água Mineral 1,5 litros", "Óculos de Sol",
]
WORDS = ["flores", "motores", "torres", "cofres", "animais", "papeis", "lencois", "fogoes", "paes", "maes", "tenis",
         "funis", "biquinis", "kits", "dvds", "luzes", "jardins", "cadeiras", "meses", "oculos", "lapis", "onibus",
         "bons", "reis", "herois", "barris", "fuzis", "perfis", "ingleses", "mares", "pires", "gas", "res", "as"]
CODES = ["7891234567895", "7891234567890", " 789-123-456-7895 ", "4521", "000000012345", "SEM GTIN", "7.89E+12",
         "BB799-6-100-38", "abc", "0000000", "12345678", "96385074", "036000291452", "10012345678902", "", "N/A", "12"]
URLS = ["https://www.Loja.com.br/Produto/X/?utm_source=a&id=3&gclid=1#top", "http://loja.com.br/p/12?idsku=152557&utm_source=Google_Shopping",
        "https://americanas.com.br/produto/123/", "LOJA.COM.BR/A?b=2&a=1", "", "ftp://x.org/a?ref=9"]


def text_case(t: str, other: str) -> dict:
    return {
        "text": t,
        "normalize": dk.normalize(t),
        "fingerprint": dk.fingerprint(t),
        "legacy_fingerprint": dk.legacy_fingerprint(t),
        "ngram2": dk.ngram_fingerprint(t),
        "ngram3": dk.ngram_fingerprint(t, 3),
        "token_key": dk.token_key(t),
        "phonetic": dk.phonetic_key(t),
        "attributes": {k: sorted(v) for k, v in sorted(dk.attributes(t).items())},
        "other": other,
        "shares_word": dk.shares_word(t, other),
        "conflict": dk.conflict(t, other),
    }


def result_dict(result: dk.Result) -> dict:
    return {
        "cluster_of": result.cluster_of,
        "via": {k: list(v) for k, v in sorted(result.via.items())},
        "links": [[l.a, l.b, l.rule, l.value] for l in result.links],
        "rejected": [[r.a, r.b, r.rule, r.value, r.reason] for r in result.rejected],
        "skipped": [list(s) for s in result.skipped],
    }


def main() -> None:
    texts = list(TRICKY)
    sample = ROOT / "evaluation" / ".cache" / "produtos.csv"
    if sample.exists():
        with open(sample, encoding="utf-8", newline="") as f:
            names = [row["name"] for row in csv.DictReader(f) if row["name"]]
        texts += names[::97][:300]
    listings = generate(seed=5, products_per_kind=12)
    texts += [l.name for l in listings[::7][:150]]
    golden = {
        "generator": "tools/make_testdata.py",
        "texts": [text_case(t, texts[(i + 1) % len(texts)]) for i, t in enumerate(texts)],
        "singular": {w: dk.singular(w) for w in WORDS},
        "codes": [{"code": c, "clean": dk.clean_code(c), "valid_gtin": dk.is_valid_gtin(c), "placeholder": dk.is_placeholder(c),
                   "class": dk.code_class(c)} for c in CODES],
        "urls": {u: dk.normalize_url(u) for u in URLS},
        "listings": [{"id": l.id, "name": l.name, "brand": l.brand, "codes": list(l.codes), "url": l.url, "image": l.image,
                      "source": l.source, "entity": l.entity} for l in listings],
        "results": {},
    }
    records = [dk.Record(l.id, l.name, l.brand, l.codes, l.url, l.image, l.source) for l in listings]
    for mode in ("connected", "two_hop"):
        for check in (True, False):
            golden["results"][f"{mode}|attributes={check}"] = result_dict(dk.match(records, mode=mode, check_attributes=check))
    golden["results"]["connected|brands"] = result_dict(dk.match(records, check_brands=True))
    golden["results"]["two_hop|legacy"] = result_dict(dk.match(records, rules=dk.LEGACY_RULES, mode="two_hop", check_attributes=False))
    golden["results"]["connected|max_block=3"] = result_dict(dk.match(records, max_block=3))
    out = ROOT / "testdata" / "golden.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(golden, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(golden['texts'])} texts, {len(listings)} listings -> {out}")


if __name__ == "__main__":
    main()
