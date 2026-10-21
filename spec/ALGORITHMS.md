# DedupKit algorithms

This file is the reference for both implementations (Python `dedupkit_br`, .NET `DedupKit`).
A change goes here first, then into both languages, then `python tools/make_testdata.py`
regenerates `testdata/golden.json`, and both test suites must pass with it.

Everything is deterministic. Character classes are ASCII only (`[a-z]`, `[0-9]`): no
`str.isdigit()`, `char.IsLetter()` or culture-dependent case mapping, because they differ between
runtimes. Accent folding uses a generated table (`tools/make_fold_table.py`), not Unicode
normalization at run time.

## 1. Text

### 1.1 Character folding

Each character is mapped on its own:

| Input | Output |
|---|---|
| a character in the fold table (284 Latin letters U+00C0–U+024F, ª, º) | its ASCII letters in lower case (`Ç`→`c`, `ß`→`ss`, `Œ`→`oe`, `Ł`→`l`) |
| `A`–`Z` | lower case |
| `a`–`z`, `0`–`9` | unchanged |
| combining marks U+0300–U+036F (decomposed input) | removed |
| anything else (punctuation, symbols, other scripts, emoji) | a space |

In phonetic mode only, `ç`/`Ç` become `ss` (so that `caçarola` and `cassarola` meet).

### 1.2 `normalize(text)`

Fold every character, split on spaces, drop empty pieces, join with one space.
`"Pendente TLF-28, Preto!"` → `"pendente tlf 28 preto"`. `tokens(text)` is that string split on spaces.

### 1.3 Fingerprints

- `fingerprint(text)`: unique tokens, sorted by ordinal comparison, joined with a space
  (OpenRefine's fingerprint keyer, without its Unicode step).
- `legacy_fingerprint(text)`: the 2019 pipeline's version, bug included. After sorting it kept
  the words at even positions only (0, 2, 4...), separated by a space, so `"a b c d"` became
  `"a c"`. Kept only to reproduce old results.
- `ngram_fingerprint(text, n=2)`: `normalize(text)` without spaces, cut into all character n-grams,
  unique, sorted, concatenated with no separator. A string shorter than `n` is returned as is.
  `n < 1` is an error.

### 1.4 Stopwords

`a o as os um uma uns umas de da do das dos em na no nas nos e ou com sem para pra pro por pelo
pela pelos pelas ao aos que se c p s`. The last three are what remains of the abbreviations
`c/` (com), `p/` (para) and `s/` (sem) after folding.

### 1.5 `singular(word)` (plural reduction)

Input is one normalized word. Rules adapted from the plural step of RSLP (Orengo and Huyck 2001)
for text without accents. The first rule that applies wins:

1. shorter than 4 letters, not ending in `s`, or in the invariable list
   (`mais menos pires lapis cais tenis onibus virus bonus campus atlas gas atras apos ambas ambos
   depois pois dois tres seis simples oculos jeans gratis pais mas oasis iris chassis vies ferias
   parabens alias lotus lens bis status`) → unchanged;
2. irregular list: `maes→mae reis→rei leis→lei bois→boi herois→heroi biquinis→biquini
   bikinis→bikini taxis→taxi jacuzzis→jacuzzi`;
3. `-ns` → `-m` (`jardins` → `jardim`);
4. `-oes`, `-aes` → `-ao` (`fogoes`, `paes`);
5. `-ais` → `-al`; `-eis` → `-el`; `-ois` → `-ol`;
6. `-is` with at least 5 letters and `n`, `r`, `z` or `f` before it → `-il` (`funis`, `barris`, `fuzis`, `perfis`);
7. `-res` or `-zes` after a vowel → drop `es` (`flores`, `luzes`);
8. ending `-ss`, `-us` or `-is` → unchanged;
9. otherwise drop the final `s`.

### 1.6 `token_key(text)`

Tokens that are not stopwords, each reduced with `singular`, unique, sorted, joined with a space.
`"Fones de Ouvido s/ Fio"` and `"fone ouvido fio"` share a key.

### 1.7 Phonetic key

`phonetic_key(text)`: normalize in phonetic mode, then `phonetic_word` for each word, keep the
non-empty results, join with a space (word order is kept).

`phonetic_word(word)`: a word made of digits only is returned unchanged. Otherwise these regular
expression replacements are applied in this order, each to the whole word:

| # | Pattern | Replacement | Why |
|---:|---|---|---|
| 1 | `^h` | (empty) | silent initial h |
| 2 | `ch`, `sh` | `x` | same sound as x |
| 3 | `ph` → `f`, `th` → `t` | | foreign spellings |
| 4 | `lh` → `1`, `nh` → `3` | | digraphs kept apart from l and n |
| 5 | `h` | (empty) | |
| 6 | `rr`, `^r`, `r` after `n`/`l`/`s` | `2` | strong r |
| 7 | `s` between vowels | `z` | `casa` |
| 8 | `ss` | `s` | runs after 7, so `cassarola` keeps an s |
| 9 | `sc`, `xc` before `e`/`i`/`y` | `s` | `nascer`, `exceto` |
| 10 | `g` before `e`/`i`/`y` | `j` | runs before 11, so `guitarra` keeps its g |
| 11 | `qu` before `e`/`i`/`y` → `k`; `gu` before `e`/`i`/`y` → `g`; `q` → `k` | | |
| 12 | `c` before `e`/`i`/`y` → `s`; other `c` → `k` | | |
| 13 | `y` → `i`, `w` → `v` | | |
| 14 | `^ex` before a vowel | `ez` | `exame` |
| 15 | `z$` | `s` | final z sounds like s |
| 16 | `n` before a consonant (`bcdfgjklmpqstvxz2`) or at the end | `m` | nasal |
| 17 | `l` before a consonant (`bcdfgjkmnpqstvxz23`) or at the end | `u` | `sal`, `alto` |

Then keep the first character and every later character that is not a vowel (`aeiou`), collapse
runs of the same letter `a`–`z` (digits are never collapsed, so `220v` stays `220V`), and upper-case.
`chuveiro` and `xuveiro` → `XVR`; `caçarola` and `cassarola` → `KSRL`.

These are DedupKit's own rules for Brazilian Portuguese, not a port of Metaphone-PT.

### 1.8 `normalize_url(url)`

1. strip spaces, tabs and line breaks at the ends; lower-case ASCII letters;
2. remove a scheme (`^[a-z][a-z0-9+.-]*://`), then a leading `www.`;
3. cut at the first `#`;
4. split path and query at the first `?`; remove trailing `/` from the path;
5. drop query parameters whose name starts with `utm_` or is one of
   `gclid fbclid msclkid dclid ref ref_ source origem origin campaign cmp partner parceiro afiliado
   affiliate awc zanpid lmdsid chave opn epar franq s_kwcid tag srsltid _ga mc_cid mc_eid`;
6. sort the remaining `name=value` parts as strings and append them after `?` (no `?` if none).

Other parameters stay because some stores put the product id in them (`produto.aspx?id=123`).

### 1.9 `shares_word(a, b)`

Tokens longer than one character that are not stopwords. True when the two sets intersect, or a
token of 3+ letters of one side contains a token of 3+ letters of the other.

## 2. Codes

- `clean_code`: remove space, tab, CR, LF, `-` and `.`; upper-case ASCII letters.
- `is_valid_gtin`: cleaned code of 8, 12, 13 or 14 ASCII digits with a correct GS1 check digit.
- `is_placeholder`: empty; one of `SEMGTIN SEMEAN NULL NONE NA N/A #N/A --- - 0 1000000000000`;
  all zeros; or contains `+` (spreadsheet notation such as `7.89E+12`).
- `code_class`: `placeholder` as above; for all digits, `long` when 7+ digits with 6+ left after
  removing leading zeros, `short` when 7+ digits otherwise or 4–6 digits, else `invalid`; for codes
  with letters, `long` from 5 characters, `short` for 3–4, else `invalid`.

The check digit is not required for a code to be `long`: many stores publish internal codes of
GTIN length, and those still identify the product inside the catalog.

## 3. Attributes

The name is folded as in 1.1 but keeping `.` and `,`, and spaces are collapsed.

Measures: `(?<![a-z0-9])([0-9]+(?:[.,][0-9]+)?) ?(unit)(?![a-z0-9])`, units tried longest first:

| Dimension | Units (factor to the base unit) |
|---|---|
| `weight_kg` | kg, kgs (1); g, gr (0.001); mg (0.000001) |
| `volume_l` | l, lt, litro, litros (1); ml (0.001) |
| `voltage_v` | v (1) |
| `power_w` | w (1); kw (1000) |
| `memory_gb` | gb (1); tb (1000); mb (0.001) |
| `battery_mah` | mah (1) |
| `length_cm` | mm (0.1); cm (1); m (100) |
| `screen_in` | pol, polegada, polegadas (1) |
| `cooling_btu` | btu, btus (1) |

Number: a `.` followed by exactly three digits is a thousands separator (`12.000`, `7.500`) and is
removed; then `,` becomes `.`. The value is multiplied by the factor in exact decimal arithmetic and
written without trailing zeros (`500g` and `0,5 kg` both give `0.5`).

Words (the folded name with `.` and `,` turned into spaces):

- colours, with feminine and plural-free variants mapped to one value: preto, branco, azul, vermelho,
  verde, amarelo, rosa, cinza, grafite, inox, prata (prateado/a), dourado, cobre, bege, marrom, roxo,
  laranja, chumbo, transparente, nude, lilas, vinho;
- gender: masculino, feminino, infantil, unissex;
- `bivolt` removes `voltage_v` (the product works on both).

`conflict(a, b)`: for each dimension present in **both** names, in alphabetical order of the
dimension, the first one whose value sets do not intersect is reported as
`"<dimension>: <a values joined by /> vs <b values joined by />"`. `110V` against `110V 220V` is not a
conflict. A dimension present in only one name is not a conflict.

## 4. Matching

### 4.1 Records and rules

A record has `id` (unique), `name`, and optional `brand`, `codes` (list), `url`, `image` and
`source`. A rule maps a record to zero or more key values. Default rules, in this order:

| Rule | Key | Emitted when |
|---|---|---|
| `code` | each `long` cleaned code (word check on) | |
| `name` | `normalize(name)` | 2+ tokens |
| `name_fingerprint` | `fingerprint(name)` | 3+ distinct tokens |
| `name_phonetic` | `phonetic_key(name)` | longer than 3 characters and has a space |
| `name_ngram` | `ngram_fingerprint(name, 2)` | normalized name without spaces has 10+ characters |
| `name_tokens` | `token_key(name)` | has a space |
| `url` | `normalize_url(url)` | not empty |
| `short_code_brand` | `code + "|" + fingerprint(brand)` for each `short` code | usable brand |
| `short_code_brand_ngram` | `code + "|" + ngram_fingerprint(brand)` for each `short` code | usable brand |
| `image` | `image` trimmed | not empty |

A usable brand has 3+ characters after normalization and is not generic (`generico`, `sem marca`,
`importado`, `diversos`, `outros`, ...: see `GENERIC_BRANDS`). Image values are opaque: use a
perceptual hash from [SimilarImageFinder](https://github.com/CaiqueDourado/SimilarImageFinder) or a file hash.

`LEGACY_RULES` is the same list with `legacy_fingerprint` in `name_fingerprint`.
The recommended subset for precision is `code, name, name_tokens, url, short_code_brand`.

### 4.2 Code blacklist

Unless a blacklist is given, codes are ignored by the three code rules when, after cleaning, the
same code appears in more than 5 listings of the same `source`, or a letters-only code appears in
more than one listing.

### 4.3 Candidate pairs

For each rule in order: build blocks of record indexes per key value (input order). Visit blocks
in ordinal order of the value. Blocks of one record are ignored; blocks larger than `max_block`
(default 100) are skipped and reported. For every pair `(i, j)` in a block, `i` before `j` in input
order:

1. if the pair is already linked by an earlier rule, skip it;
2. if the rule needs a shared word and `shares_word(name_i, name_j)` is false, refuse:
   `"names share no word"`;
3. with the attribute check (default on), refuse when `conflict` reports a dimension;
4. with the brand check (default off), refuse when both brands are usable, differ, and neither
   brand's words are all present in the other listing's name tokens: `"brand: x vs y"`;
5. otherwise link the pair with this rule and value.

Refused pairs are reported in visit order and may be refused again by a later rule.

The brand check is off by default because marketplaces put the seller in the brand field: on the
real catalog sample it refused thousands of correct pairs.

### 4.4 Clustering

- `connected` (default): union-find over the links in the order they were made; the smaller root
  wins. Each link that joins two clusters is kept in the audit trail, and each record's `via` is
  the first such link that touched it. Result does not depend on input order except for numbering.
- `two_hop`: the 2019 algorithm. For each record without a group, in input order: hop 1 is its
  linked neighbours (sorted by index), hop 2 the neighbours of those not yet reached. All of them
  join the smallest group number already held by any of them, or a new group. Records that already
  have a group keep it. This reproduces how the old catalog could chain or miss records.

Clusters are numbered 1, 2, 3... in order of their first record.

## 5. Evaluation

`pairwise(predicted, truth)`: precision, recall and F1 over the pairs of records placed in the
same cluster (records missing from `truth` are ignored). `link_precision`: for each rule, how many
links it made and the share that joined records of the same true entity.
