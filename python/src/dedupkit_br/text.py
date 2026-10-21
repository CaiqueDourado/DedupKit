"""Text keys for matching: normalization, fingerprints, n-grams, plural reduction and a
Portuguese phonetic key. Every function is deterministic and identical in the .NET version
(see spec/ALGORITHMS.md)."""

from __future__ import annotations

import re
from typing import List

from ._fold import FOLD

STOPWORDS = frozenset(
    "a o as os um uma uns umas de da do das dos em na no nas nos e ou com sem para pra pro "
    "por pelo pela pelos pelas ao aos que se c p s".split()
)

# Plural reduction (after accents are removed). Words that do not change, or change irregularly.
PLURAL_SAME = frozenset(
    "mais menos pires lapis cais tenis onibus virus bonus campus atlas gas atras apos ambas ambos "
    "depois pois dois tres seis simples oculos jeans gratis pais mas oasis iris chassis vies ferias "
    "parabens alias lotus lens bis status".split()
)
PLURAL_IRREGULAR = {
    "maes": "mae", "reis": "rei", "leis": "lei", "bois": "boi", "herois": "heroi",
    "biquinis": "biquini", "bikinis": "bikini", "taxis": "taxi", "jacuzzis": "jacuzzi",
}
_VOWELS = "aeiou"


def _fold_char(ch: str, phonetic: bool) -> str:
    if phonetic and ch in ("ç", "Ç"):
        return "ss"
    mapped = FOLD.get(ch)
    if mapped is not None:
        return mapped
    if "A" <= ch <= "Z":
        return chr(ord(ch) + 32)
    if "a" <= ch <= "z" or "0" <= ch <= "9":
        return ch
    if "̀" <= ch <= "ͯ":  # combining accents (decomposed input)
        return ""
    return " "


def _normalize(text: str, phonetic: bool) -> str:
    if not text:
        return ""
    out = "".join(_fold_char(ch, phonetic) for ch in text)
    return " ".join(t for t in out.split(" ") if t)


def normalize(text: str) -> str:
    """Lower case, accents removed (ç → c), anything that is not a letter or digit becomes a
    space, spaces collapsed. ``"Pendente TLF-28, Preto!"`` → ``"pendente tlf 28 preto"``."""
    return _normalize(text, False)


def tokens(text: str) -> List[str]:
    """Words of the normalized text, in order."""
    n = normalize(text)
    return n.split(" ") if n else []


def fingerprint(text: str) -> str:
    """OpenRefine-style fingerprint: unique words, sorted. Word order and repetitions stop
    mattering: ``"Preto Pendente preto"`` → ``"pendente preto"``."""
    return " ".join(sorted(set(tokens(text))))


def legacy_fingerprint(text: str) -> str:
    """The 2019 pipeline's fingerprint, bug included: after sorting it kept only every other
    word, so different names could share a key. Only for reproducing old results."""
    words = sorted(set(tokens(text)))
    out = []
    for i in range(0, len(words), 2):
        out.append(words[i])
        if i + 1 < len(words):
            out.append(" ")
    return "".join(out)


def ngram_fingerprint(text: str, n: int = 2) -> str:
    """OpenRefine-style n-gram fingerprint: the normalized text without spaces, cut into
    character n-grams, unique and sorted, concatenated. Tolerant to spacing and small typos,
    and to word order; very permissive on short texts."""
    if n < 1:
        raise ValueError("n must be positive")
    s = normalize(text).replace(" ", "")
    if len(s) < n:
        return s
    return "".join(sorted({s[i:i + n] for i in range(len(s) - n + 1)}))


def singular(word: str) -> str:
    """Reduce a normalized Portuguese plural to the singular (rules adapted from the RSLP
    plural step, Orengo and Huyck 2001, for text without accents)."""
    w = word
    if len(w) < 4 or not w.endswith("s") or w in PLURAL_SAME:
        return w
    if w in PLURAL_IRREGULAR:
        return PLURAL_IRREGULAR[w]
    if w.endswith("ns"):
        return w[:-2] + "m"
    if w.endswith("oes") or w.endswith("aes"):
        return w[:-3] + "ao"
    if w.endswith("ais"):
        return w[:-3] + "al"
    if w.endswith("eis"):
        return w[:-3] + "el"
    if w.endswith("ois"):
        return w[:-3] + "ol"
    if w.endswith("is") and len(w) >= 5 and w[-3] in "nrzf":
        return w[:-2] + "il"
    if w.endswith("res") and w[-4] in _VOWELS:
        return w[:-2]
    if w.endswith("zes") and w[-4] in _VOWELS:
        return w[:-2]
    if w.endswith("ss") or w.endswith("us") or w.endswith("is"):
        return w
    return w[:-1]


def token_key(text: str) -> str:
    """Words without stopwords, reduced to the singular, unique and sorted:
    ``"Fones de Ouvido sem Fio"`` and ``"fone ouvido fio"`` share a key."""
    return " ".join(sorted({singular(t) for t in tokens(text) if t not in STOPWORDS}))


_PHONETIC_RULES = [
    (r"^h", ""),
    (r"ch", "x"), (r"sh", "x"), (r"ph", "f"), (r"th", "t"),
    (r"lh", "1"), (r"nh", "3"),
    (r"h", ""),
    (r"rr", "2"), (r"^r", "2"), (r"(?<=[nls])r", "2"),
    (r"(?<=[aeiou])s(?=[aeiou])", "z"),
    (r"ss", "s"),
    (r"sc(?=[eiy])", "s"), (r"xc(?=[eiy])", "s"),
    (r"g(?=[eiy])", "j"),
    (r"qu(?=[eiy])", "k"), (r"gu(?=[eiy])", "g"), (r"q", "k"),
    (r"c(?=[eiy])", "s"), (r"c", "k"),
    (r"y", "i"), (r"w", "v"),
    (r"^ex(?=[aeiou])", "ez"),
    (r"z$", "s"),
    (r"n(?=[bcdfgjklmpqstvxz2])", "m"), (r"n$", "m"),
    (r"l(?=[bcdfgjkmnpqstvxz23]|$)", "u"),
]
_PHONETIC = [(re.compile(p), r) for p, r in _PHONETIC_RULES]
_REPEAT = re.compile(r"([a-z])\1+")


def phonetic_word(word: str) -> str:
    """Phonetic key of one normalized word, written for Brazilian Portuguese: sounds that are
    spelled in several ways collapse (ç/ss/sc/c+e → s, ch/x → x, lh, nh, strong r, nasal m/n,
    final l → u) and vowels after the first letter are dropped. ``"cassarola"`` and
    ``"caçarola"`` → ``"KSRL"``; ``"chuveiro"`` and ``"xuveiro"`` → ``"XVR"``."""
    if not word:
        return ""
    if all("0" <= ch <= "9" for ch in word):
        return word
    w = word
    for pattern, repl in _PHONETIC:
        w = pattern.sub(repl, w)
    if not w:
        return ""
    w = w[0] + "".join(c for c in w[1:] if c not in _VOWELS)
    return _REPEAT.sub(r"\1", w).upper()


def phonetic_key(text: str) -> str:
    """Phonetic key of each word, in the original order."""
    words = [t for t in _normalize(text, True).split(" ") if t]  # ç is read as ss here
    return " ".join(k for k in (phonetic_word(t) for t in words) if k)


TRACKING_PARAMS = frozenset({
    "gclid", "fbclid", "msclkid", "dclid", "ref", "ref_", "source", "origem", "origin", "campaign", "cmp",
    "partner", "parceiro", "afiliado", "affiliate", "awc", "zanpid", "lmdsid", "chave", "opn", "epar", "franq",
    "s_kwcid", "tag", "srsltid", "_ga", "mc_cid", "mc_eid",
})


def normalize_url(url: str) -> str:
    """Lower case (ASCII letters), without scheme, ``www.``, fragment, trailing slash and tracking parameters
    (``utm_*``, ``gclid``, affiliate ids...). Other parameters stay, sorted, because some stores
    put the product id there (``produto.aspx?id=123``)."""
    u = "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in (url or "").strip(" \t\r\n"))
    u = re.sub(r"^[a-z][a-z0-9+.-]*://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("#", 1)[0]
    path, _, query = u.partition("?")
    path = path.rstrip("/")
    kept = []
    for part in query.split("&"):
        if not part:
            continue
        key = part.split("=", 1)[0]
        if key.startswith("utm_") or key in TRACKING_PARAMS:
            continue
        kept.append(part)
    return path + ("?" + "&".join(sorted(kept)) if kept else "")


def shares_word(a: str, b: str) -> bool:
    """True when the two texts share a word (or one word contains the other, from 3 letters
    on), ignoring stopwords and one-letter words. Used to refuse a barcode match between two
    products whose names have nothing in common."""
    ta = {t for t in tokens(a) if len(t) > 1 and t not in STOPWORDS}
    tb = {t for t in tokens(b) if len(t) > 1 and t not in STOPWORDS}
    if ta & tb:
        return True
    for x in ta:
        for y in tb:
            if len(x) >= 3 and len(y) >= 3 and (x in y or y in x):
                return True
    return False
