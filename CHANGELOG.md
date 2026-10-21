# Changelog

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
