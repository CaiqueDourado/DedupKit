# dedupkit-br

Find listings that are the same product in Brazilian Portuguese data, and refuse the ones that only look
the same (different size, voltage, colour...). Fingerprints, a Portuguese phonetic key, plural reduction,
barcode rules and an audit trail of every link. No dependencies. Same results as the .NET package `DedupKit`.

```python
from dedupkit_br import Record, match

result = match([
    Record("1", "Fone de Ouvido sem Fio JBL Tune 510BT Preto", codes=("6925281979309",)),
    Record("2", "FONES DE OUVIDO JBL TUNE 510BT S/ FIO PRETO"),
    Record("3", "Chuveiro Elétrico Lorenzetti 220V 7800W", codes=("7891129220911",)),
    Record("4", "Chuveiro Elétrico Lorenzetti 127V 5500W", codes=("7891129220911",)),
])
result.clusters   # [['1', '2']]
result.rejected   # [Rejected(a='3', b='4', rule='code', value='7891129220911', reason='power_w: 7800 vs 5500')]
```

Command line: `dedupkit-br match listings.csv --brand brand --code code > clusters.csv`.

Documentation, benchmark and the rules: https://github.com/CaiqueDourado/DedupKit
