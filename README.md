# DedupKit

[Português](README.pt-BR.md)

[![Python](https://github.com/CaiqueDourado/DedupKit/actions/workflows/python.yml/badge.svg)](https://github.com/CaiqueDourado/DedupKit/actions/workflows/python.yml)
[![.NET](https://github.com/CaiqueDourado/DedupKit/actions/workflows/dotnet.yml/badge.svg)](https://github.com/CaiqueDourado/DedupKit/actions/workflows/dotnet.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

Find listings that are the same product in Brazilian Portuguese data, and refuse the ones
that only look the same.

```text
Fone de Ouvido sem Fio JBL Tune 510BT Preto     ┐
FONES DE OUVIDO JBL TUNE 510BT S/ FIO PRETO     ├─ same product
Fone Ouvido JBL Tune 510BT Bluetooth Preto      ┘

Chuveiro Elétrico Lorenzetti Acqua Duo 220V 7800W  ┐ same barcode, refused:
Chuveiro Eletrico Lorenzetti Acqua Duo 127V 5500W  ┘ power_w: 7800 vs 5500
```

DedupKit is the matching logic of a 2019–2022 price-comparison catalog, rewritten as a
library, tested, and measured. It runs in **Python and .NET with identical results**: both
implementations are checked against the same 448 texts and 8 matching configurations in
[`testdata/golden.json`](testdata/golden.json). No dependencies in either language.

- **Text keys for Portuguese:** accent folding, OpenRefine-style fingerprints and character
  n-grams, plural reduction (`fogões` → `fogao`, `jardins` → `jardim`), a phonetic key
  (`xuveiro` = `chuveiro`, `caçarola` = `cassarola`), and URLs without tracking parameters.
- **Codes as stores fill them in:** GTIN check digit, placeholders (`SEM GTIN`, `0`, `7.89E+12`),
  long and short codes, and a blacklist of codes a store reuses for everything.
- **Attribute check:** two listings are never merged when their names state different sizes,
  weights, volumes, voltages, power, memory, colours or gender (`400g` vs `500g`, `110V` vs `220V`).
- **Audit trail:** every link records the rule and value that made it, and every refused pair says why.

## Install

```bash
pip install "dedupkit-br @ git+https://github.com/CaiqueDourado/DedupKit#subdirectory=python"
```

```bash
dotnet add package DedupKit   # once published; meanwhile reference dotnet/src/DedupKit
```

## Use

Python:

```python
from dedupkit_br import Record, match

records = [
    Record("1", "Fone de Ouvido sem Fio JBL Tune 510BT Preto", brand="JBL", codes=("6925281979309",)),
    Record("2", "FONES DE OUVIDO JBL TUNE 510BT S/ FIO PRETO", brand="JBL"),
    Record("5", "Chuveiro Elétrico Lorenzetti Acqua Duo 220V 7800W", codes=("7891129220911",)),
    Record("6", "Chuveiro Eletrico Lorenzetti Acqua Duo 127V 5500W", codes=("7891129220911",)),
]
result = match(records)
result.clusters      # [['1', '2']]
result.via["2"]      # ('name_tokens', '510bt fio fone jbl ouvido preto tune')
result.rejected[0]   # Rejected(a='5', b='6', rule='code', value='7891129220911', reason='power_w: 7800 vs 5500')
```

C#:

```csharp
using DedupKit;

var result = Matcher.Match(records);                       // same clusters, links and refusals
var strict = Matcher.Match(records, new MatchOptions { Rules = Rules.ByName("code", "name", "name_tokens", "url", "short_code_brand") });
```

Command line, on a CSV with a header row:

```bash
dedupkit-br match examples/listings.csv --brand brand --code code --url url --source source --rejected refused.csv > clusters.csv
```

The .NET sample does the same: `dotnet run --project dotnet/samples/MatchListings -- examples/listings.csv`.

The building blocks are public too:

| Python | C# | Example |
|---|---|---|
| `normalize` | `TextKeys.Normalize` | `"Pendente TLF-28, Preto!"` → `"pendente tlf 28 preto"` |
| `fingerprint` | `TextKeys.Fingerprint` | `"Preto Pendente preto"` → `"pendente preto"` |
| `token_key` | `TextKeys.TokenKey` | `"Fones de Ouvido s/ Fio"` → `"fio fone ouvido"` |
| `phonetic_key` | `TextKeys.PhoneticKey` | `"Xuveiro"` and `"Chuveiro"` → `"XVR"` |
| `normalize_url` | `TextKeys.NormalizeUrl` | `"https://www.Loja.com.br/p/12/?utm_source=x&id=3"` → `"loja.com.br/p/12?id=3"` |
| `attributes` | `ProductAttributes.Extract` | `"Ração 2,5kg"` → `{weight_kg: {2.5}}` |
| `conflict` | `ProductAttributes.Conflict` | `"110V"`, `"220V"` → `"voltage_v: 110 vs 220"` |
| `is_valid_gtin`, `code_class` | `Codes.IsValidGtin`, `Codes.Classify` | `"7891234567895"` → valid, `long` |

## How it works

```mermaid
flowchart TD
    A[Listings: name, brand, codes, URL, image] --> B[Keys per rule<br/>barcode, name, fingerprint, phonetic,<br/>n-grams, words, URL, short code + brand, image]
    B --> C{Same key value?}
    C -- block larger than 100 --> S[Skipped and reported]
    C -- yes --> D{Barcode match and<br/>no word in common?}
    D -- yes --> R[Refused, with the reason]
    D -- no --> E{Different size, voltage,<br/>colour, memory...?}
    E -- yes --> R
    E -- no --> L[Link: rule + value]
    L --> F[Clusters: connected components<br/>or the 2019 two-hop mode]
```

The exact rules, for both languages, are in [spec/ALGORITHMS.md](spec/ALGORITHMS.md).

## What each safeguard buys

Measured on 4,073 synthetic listings of 1,138 product variants with known answers
([`tools/synth_listings.py`](tools/synth_listings.py)). They imitate what made the real catalog hard:
stores writing names in their own style, sizes and colours of one product sharing a barcode or a photo,
reused SKUs, a "no photo" placeholder, the same page scraped twice.

![Precision and recall of each configuration](docs/img/safeguards.png)

| Configuration | Precision | Recall |
|---|---:|---:|
| The 2019 catalog: every key, two hops, fingerprint bug | 23.4% | 91.2% |
| Fingerprint fixed, barcode without the word check | 25.9% | 91.2% |
| + word check on barcodes | 44.4% | 91.2% |
| + attribute check (default) | 81.5% | 90.2% |
| + brand check | 87.6% | 90.2% |
| Recommended keys + attribute check | 89.9% | 85.1% |

Of 1,274 refused pairs, 6 were in fact the same product. Speed: about 41,000 listings in 13 seconds in Python.
Per-rule numbers are in [evaluation/results.md](evaluation/results.md); `python evaluation/evaluate.py` reproduces them.

Synthetic data gives exact answers but flatters any method built for it. So the defaults were also
checked on a real sample (next section), and one safeguard that looked good here, the brand check,
is off by default because real data broke it.

## On real data

[`evaluation/real_sample.py`](evaluation/real_sample.py) runs the attribute check on the 28,569 offers
of the [catalog's public sample](https://github.com/CaiqueDourado/catalogo-produtos-ecommerce-brasil),
grouped in 2019 into 4,030 groups. Without changing any parameter, **762 of those groups would be
split**. Pairs refused, by reason: colour 806, length 325, volume 113, voltage 93, memory 31,
weight 25, power 9, and 41 barcode matches whose names share no word.

| Rule | Listing A | Listing B | Why refused |
|---|---|---|---|
| code | Mass Way 2500 Baunilha 400g | Mass Way 2500 (500g) - Baunilha | weight 0.4 vs 0.5 kg |
| code | Squeeze Alumínio 500ml - Preto - Acte Sports | Squeeze Alumínio 750Ml - Preto - Acte Sports | volume 0.5 vs 0.75 l |
| code | Sutiã de Amamentação Preto Medela | Sutiã de Amamentação Branco Medela | colour |
| image | Toalheiro Elétrico A20 220v Emmeti | Toalheiro Elétrico A10 127v Emmeti | voltage 220 vs 127 |
| image | Pen Drive 32gb de Couro Branco com Argola ... | Pen Drive 4gb Personalizado de Couro Branco ... | memory 32 vs 4 GB |

Every one of these was a single product page in the old catalog. The full catalog (114.6 million offers, 18.3 million groups) is on [Kaggle](https://www.kaggle.com/datasets/caiquedourado/catalogo-produtos-ecommerce-brasil), if you want to run DedupKit at scale. The brand check, on the other
hand, refused 6,729 pairs in the same sample, mostly correct ones, because marketplaces fill the
brand field with the seller's name. Turn it on (`check_brands=True`) only when your brand field is clean.

## The story

The catalog matched offers from dozens of stores with a SQL Server routine (2020–2022) over twelve
keys. It is published, read-only, in the catalog repository:
[legacy/agrupa_insere_grupos_produtos_similares.sql](https://github.com/CaiqueDourado/catalogo-produtos-ecommerce-brasil/tree/main/legacy).
Rewriting it showed what the numbers above measure:

- the name fingerprint was computed by a keyer that **kept every other word**, so different products
  could share a key (`legacy_fingerprint` reproduces it);
- barcode matches were checked for a shared word only for long EANs, and nothing compared sizes or voltages,
  so sellers that reuse one barcode for a whole product line merged it into one page;
- the two-hop grouping depended on the order in which offers arrived (`mode="two_hop"` reproduces it;
  the default `connected` mode does not depend on order).

Image keys come from the 16×16 signature of the same catalog, now
[SimilarImageFinder](https://github.com/CaiqueDourado/SimilarImageFinder). Pass any image hash in `image`.

## Limits

- Written for Brazilian Portuguese product names. The text keys work on other Latin-alphabet text, but the
  stopwords, plurals, phonetic rules, colours and units are Portuguese.
- Rule-based and explainable, not learned. It will not know that "Galaxy S23" and "SM-S911B" are the same phone.
- All pairs inside a block are compared, so a block is capped at 100 records (`max_block`) and reported when skipped.
- The attribute check only sees what the name says. A listing that omits the size will match both sizes.

## Repository

| Path | Contents |
|---|---|
| `python/` | the `dedupkit-br` package (`import dedupkit_br`) and its tests |
| `dotnet/` | the `DedupKit` library, tests and a sample |
| `spec/ALGORITHMS.md` | the rules both implementations follow |
| `testdata/golden.json` | expected outputs, generated by `tools/make_testdata.py` |
| `tools/` | fold-table generator, synthetic listings, test-data generator |
| `evaluation/` | synthetic benchmark, real-sample check, figure |
| `examples/listings.csv` | the example above |

Credits for the ideas used are in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).
Contributions: [CONTRIBUTING.md](CONTRIBUTING.md). MIT License.
