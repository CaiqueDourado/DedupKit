# Why these keys

Gold: 715 pairs labelled one by one (164 same product, 551 different), from product-matching-pairs-portuguese. They were chosen hard: most share a barcode, a photo or almost the whole name. Blocks: 9,971 distinct names of the catalog's public sample.

| Key | In DedupKit | Same-product pairs joined | Different-product pairs joined | Precision | Blocks | Largest block |
|---|:---:|---:|---:|---:|---:|---:|
| `normalize` | yes | 11 (7%) | 0 | 100% | 8,855 | 7 |
| `fingerprint` | yes | 16 (10%) | 1 | 94% | 8,448 | 20 |
| `token_key` | yes | 16 (10%) | 1 | 94% | 8,319 | 22 |
| `phonetic_key` | yes | 12 (7%) | 2 | 86% | 8,776 | 10 |
| `ngram_fingerprint` | yes | 13 (8%) | 0 | 100% | 8,759 | 8 |
| `fingerprint_2019` | no | 19 (12%) | 31 | 38% | 7,766 | 23 |
| `phonetic_no_digits` | no | 22 (13%) | 219 | 9% | 7,522 | 22 |
| `skeleton` | no | 36 (22%) | 254 | 12% | 6,726 | 36 |
| `skeleton_2019` | no | 23 (14%) | 219 | 10% | 7,474 | 21 |
| `omission` | no | 45 (27%) | 268 | 14% | 6,337 | 43 |

## Counterexamples found in the sample (same key, no word in common)

- `omission` `KVBMGPDCLNTSRAEOI`: *Acabamento para Registro Gaveta 1 1/2" LK Cromado - 4900.C17.GD - Deca - Deca* × *Bandagem Vollke Elastica Preta 5 Metros*
- `omission` `KVBMGPDCLNTSRAEOI`: *Acabamento para Registro Gaveta 1 1/2" LK Cromado - 4900.C17.GD - Deca - Deca* × *Bandagem Vollke Elástica 5 Metros Preta*
- `phonetic_no_digits` `ADV3 O K E`: *Adivinha o que e* × *Adivinhe o que e*
- `documented_2019` `skeleton_2019: D/VCNTR/VCNTR / D/VCNTR/VCNTR`: *DVD Canta Rio 98* × *Dvd - Centurião*
- `documented_2019` `phonetic_key: B2K VMTJ AMBRGR / B2K VMTJ AMBRJR`: *Barraca Vintage Hambúrguer* × *Barraca Vintage Hamburger*
