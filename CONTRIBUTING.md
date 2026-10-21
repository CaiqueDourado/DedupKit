# Contributing

Issues and pull requests are welcome in English or Portuguese.

```bash
python -m pip install ./python[test] && python -m pytest python/tests
cd dotnet && dotnet test
```

## Rules that keep both languages identical

- Change the rule in [spec/ALGORITHMS.md](spec/ALGORITHMS.md) first, then in **both** implementations.
- ASCII character classes only (`[0-9]`, `"a" <= ch <= "z"`), no culture-dependent case mapping,
  no Unicode normalization at run time. Accents go through the generated table (`python tools/make_fold_table.py`).
- Regenerate the test vectors with `python tools/make_testdata.py` and commit `testdata/`. Both test
  suites must pass with the new `golden.json`.
- When a change moves the benchmark, run `python evaluation/evaluate.py` and `python evaluation/figures.py`
  and commit the new results with the change.

## Useful contributions

- Pairs that DedupKit merges wrongly or misses, with the names (no personal data).
- Units, colours or abbreviations that Brazilian stores use and the attribute check does not know.
- Benchmarks on other real catalogs.
