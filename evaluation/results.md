# Evaluation results

4,073 synthetic listings of 1,138 product variants (tools/synth_listings.py).

## Each rule alone

| Rule | Precision | Recall | Precision with attribute check | Recall with attribute check |
|---|---:|---:|---:|---:|
| barcode (long code) + shared word (`code`) | 88.0% | 52.1% | 97.5% | 52.0% |
| exact name (`name`) | 100.0% | 13.3% | 100.0% | 13.3% |
| name fingerprint (`name_fingerprint`) | 100.0% | 36.3% | 100.0% | 36.3% |
| phonetic key (`name_phonetic`) | 100.0% | 14.2% | 100.0% | 14.2% |
| character bigrams (`name_ngram`) | 99.8% | 21.7% | 99.8% | 21.7% |
| words, singular, no stopwords (`name_tokens`) | 100.0% | 45.3% | 100.0% | 45.3% |
| URL without parameters (`url`) | 100.0% | 0.6% | 100.0% | 0.6% |
| short code + brand (`short_code_brand`) | 15.9% | 0.1% | 46.7% | 0.1% |
| short code + brand bigrams (`short_code_brand_ngram`) | 15.9% | 0.1% | 46.7% | 0.1% |
| same image file (`image`) | 50.6% | 8.0% | 87.3% | 8.0% |

## Configurations

| Configuration | Precision | Recall | F1 |
|---|---:|---:|---:|
| 2019: all keys, two hops, fingerprint bug, no attribute check | 23.4% | 91.2% | 0.372 |
| all keys, two hops, no attribute check | 45.8% | 91.0% | 0.609 |
| all keys, barcode without the word check, no attribute check | 25.9% | 91.2% | 0.403 |
| all keys, connected, no attribute check | 44.4% | 91.2% | 0.598 |
| all keys, connected, attribute check | 81.5% | 90.2% | 0.856 |
| all keys, two hops, attribute check | 81.8% | 90.2% | 0.858 |
| all keys, connected, attribute and brand check | 87.6% | 90.2% | 0.889 |
| recommended keys, connected, attribute check | 89.9% | 85.1% | 0.874 |

Pairs refused (no shared word or conflicting attributes): 1,274, of which 6 were in fact the same product.
