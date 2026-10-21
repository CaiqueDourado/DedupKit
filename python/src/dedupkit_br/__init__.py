"""Find records that are the same product (or person, or company) in Brazilian Portuguese data.

>>> from dedupkit_br import Record, match
>>> result = match([Record("1", "Fone de Ouvido sem Fio JBL"), Record("2", "FONES DE OUVIDO JBL SEM FIO")])
>>> result.clusters
[['1', '2']]
"""

from .attributes import attributes, conflict
from .codes import clean_code, code_class, is_placeholder, is_valid_gtin
from .engine import (DEFAULT_RULES, LEGACY_RULES, Link, Record, Rejected, Result, Rule, code_blacklist, match,
                     rules_by_name)
from .evaluate import Scores, link_precision, pairwise, refused_that_were_right
from .text import (STOPWORDS, fingerprint, legacy_fingerprint, ngram_fingerprint, normalize, normalize_url,
                   phonetic_key, phonetic_word, shares_word, singular, token_key, tokens)

__version__ = "0.1.1"

__all__ = [
    "DEFAULT_RULES", "LEGACY_RULES", "attributes", "conflict", "Link", "Record", "Rejected", "Result", "Rule", "STOPWORDS", "Scores",
    "clean_code", "code_blacklist", "code_class", "fingerprint", "is_placeholder", "is_valid_gtin",
    "legacy_fingerprint", "link_precision", "match", "ngram_fingerprint", "normalize", "normalize_url",
    "pairwise", "phonetic_key", "phonetic_word", "refused_that_were_right", "rules_by_name", "shares_word",
    "singular", "token_key", "tokens",
]
