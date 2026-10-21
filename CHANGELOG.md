# Changelog

## 0.2.0 (2026-10-21)

Attribute check, after 780 real pairs labelled by hand:

- New attributes: clothing and shoe `size` (`- 38 -`, `Tamanho 40`, `(M)`), pack `quantity` (`Kit 3 Pares`,
  `c/ 50`, `2 Un`) and `dimensions` lists (`20x30`, `160x80 cm`, `1,50 x 2,00 m`, compared in cm when a unit is given).
- 110, 115, 120 and 127 V are the same network: no longer a conflict.
- `inox`, `prata` and `cromado` are one colour; `cobre` is not read as a colour in "cobre leito" (bedspread).
- Inch marks (`55"`) are read as `pol`, so screen and tool sizes are compared.

The synthetic benchmark does not change (its names have no sizes or packs); on the catalog sample,
795 of the 4,030 groups of 2019 would be split (was 762).

## 0.1.1 (2026-10-21)

- Attributes: numbers inside dimension lists and packs (`10,6x8,5cm`, `1,50 x 2,00 m`, `2 x 500ml`) are no longer read as a measure. Before, `10,6x8,5cm` gave a length of 5 cm and refused a correct pair. Found while building the product-matching pairs dataset.

## 0.1.0 (2026-10-21)

First release, Python (`dedupkit-br`) and .NET (`DedupKit`) with identical results.

- Text keys: normalization, fingerprint, legacy fingerprint, character n-grams, plural reduction,
  token key, Brazilian Portuguese phonetic key, URL normalization, shared-word check.
- Codes: cleaning, GTIN check digit, placeholders, long/short classes, code blacklist.
- Attributes: weight, volume, voltage, power, memory, battery, length, screen, BTU, colour, gender; conflicts.
- Matching: ten rules, blocking with a size cap, word and attribute checks, optional brand check,
  `connected` and `two_hop` modes, audit trail (links, via, refused pairs, skipped blocks).
- Evaluation helpers (pairwise precision/recall, precision per rule), synthetic benchmark, real-sample check.
- Command line `dedupkit-br match` and the .NET sample `MatchListings`.
