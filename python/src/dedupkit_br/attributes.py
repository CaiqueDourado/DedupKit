"""Attributes written in product names (size, voltage, memory, colour) and conflicts between them.

Two listings with the same barcode or the same photo are not the same product when one says
2,5kg and the other 15kg, or 110V and 220V. Sellers reuse codes and photos across sizes and
colours, so this check catches the most common wrong merge in Brazilian catalogs.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Dict, FrozenSet, Optional, Tuple

from ._fold import FOLD

# unit -> (dimension, multiplier to the base unit)
UNITS: Dict[str, Tuple[str, Decimal]] = {
    "kg": ("weight_kg", Decimal(1)), "kgs": ("weight_kg", Decimal(1)), "g": ("weight_kg", Decimal("0.001")),
    "gr": ("weight_kg", Decimal("0.001")), "mg": ("weight_kg", Decimal("0.000001")),
    "l": ("volume_l", Decimal(1)), "lt": ("volume_l", Decimal(1)), "litro": ("volume_l", Decimal(1)),
    "litros": ("volume_l", Decimal(1)), "ml": ("volume_l", Decimal("0.001")),
    "v": ("voltage_v", Decimal(1)), "w": ("power_w", Decimal(1)), "kw": ("power_w", Decimal(1000)),
    "gb": ("memory_gb", Decimal(1)), "tb": ("memory_gb", Decimal(1000)), "mb": ("memory_gb", Decimal("0.001")),
    "mah": ("battery_mah", Decimal(1)),
    "mm": ("length_cm", Decimal("0.1")), "cm": ("length_cm", Decimal(1)), "m": ("length_cm", Decimal(100)),
    "pol": ("screen_in", Decimal(1)), "polegadas": ("screen_in", Decimal(1)), "polegada": ("screen_in", Decimal(1)),
    "btu": ("cooling_btu", Decimal(1)), "btus": ("cooling_btu", Decimal(1)),
}
COLOURS = {
    "preto": "preto", "preta": "preto", "branco": "branco", "branca": "branco", "azul": "azul",
    "vermelho": "vermelho", "vermelha": "vermelho", "verde": "verde", "amarelo": "amarelo", "amarela": "amarelo",
    "rosa": "rosa", "cinza": "cinza", "grafite": "grafite", "inox": "prata", "prata": "prata", "prateado": "prata",
    "prateada": "prata", "cromado": "prata", "cromada": "prata", "dourado": "dourado", "dourada": "dourado", "cobre": "cobre", "bege": "bege",
    "marrom": "marrom", "roxo": "roxo", "roxa": "roxo", "laranja": "laranja", "chumbo": "chumbo",
    "transparente": "transparente", "nude": "nude", "lilas": "lilas", "vinho": "vinho",
}
GENDERS = {"masculino": "masculino", "masculina": "masculino", "feminino": "feminino", "feminina": "feminino",
           "infantil": "infantil", "unissex": "unissex"}

# Clothing and shoe sizes, as stores write them: "Bota X - 38 - PRETO", "Camiseta - G", "Tamanho 40", "(M)"
_SIZES = r"(pp|p|m|g|gg|xg|xgg|eg|egg|xs|s|l|xl|xxl|[1-9]|[1-5][0-9])"
_SIZE = re.compile(r"(?:(?<= )- " + _SIZES + r"(?= -|$)|\b(?:tamanho|tam|talle|tamano) " + _SIZES + r"\b|\(" + _SIZES + r"\))")
# Pack quantity: "Kit 3 Pares", "Kit c/ 50", "com 12 unidades", "2 Un"
_QUANTITY = re.compile(r"\bkit (?:com |c )?([0-9]+)\b(?! em 1\b)|\b(?:c|com|cx c) ([0-9]+) (?:un|und|unid|unidade|unidades|peca|pecas|par|pares|pcs)\b"
                       r"|\b([0-9]+) (?:un|und|unid|unidades|pares|pcs)\b|\bpack (?:com |c )?([0-9]+)\b")
# Dimension lists: "20x30", "160x80 cm", "1,50 x 2,00 m", "100x26,5cm" (values in cm when a unit is given)
_DIMENSIONS = re.compile(r"(?<![a-z0-9.,])([0-9]+(?:[.,][0-9]+)?(?: ?x ?[0-9]+(?:[.,][0-9]+)?)+) ?(mm|cm|m)?(?![a-z0-9])")
_DIM_FACTOR = {"mm": Decimal("0.1"), "cm": Decimal(1), "m": Decimal(100)}
_INCH = re.compile(r"([0-9]) ?(?:\"|\u201d|\u2033|'')")
VOLTAGE_127 = frozenset({"110", "115", "120", "127"})  # in Brazil "110V" products run on the 127 V network

_MEASURE = re.compile(r"(?<![a-z0-9])(?<![0-9][.,])(?<![0-9]x )(?<![0-9] x )([0-9]+(?:[.,][0-9]+)?) ?(" + "|".join(sorted(UNITS, key=len, reverse=True)) + r")(?![a-z0-9])")


def _fold(text: str) -> str:
    out = []
    for ch in text or "":
        m = FOLD.get(ch)
        if m is not None:
            out.append(m)
        elif "A" <= ch <= "Z":
            out.append(chr(ord(ch) + 32))
        elif "a" <= ch <= "z" or "0" <= ch <= "9" or ch in ".,":
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def _fold_keep(text: str) -> str:
    """Like _fold, but keeps "-", "(" and ")" so that size markers survive."""
    out = []
    for ch in text or "":
        m = FOLD.get(ch)
        if m is not None:
            out.append(m)
        elif "A" <= ch <= "Z":
            out.append(chr(ord(ch) + 32))
        elif "a" <= ch <= "z" or "0" <= ch <= "9" or ch in "-()":
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def _canonical(number: str, factor: Decimal) -> str:
    # "12.000 BTUs" and "7.500W": a dot followed by exactly three digits separates thousands
    if "." in number and len(number.split(".", 1)[1]) == 3:
        number = number.replace(".", "")
    value = Decimal(number.replace(",", ".")) * factor
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def attributes(text: str) -> Dict[str, FrozenSet[str]]:
    """Measures, colours, gender, clothing size and pack quantity found in a name.
    ``"Ração 2,5kg"`` → ``{"weight_kg": {"2.5"}}``; ``"500g"`` and ``"0,5 kg"`` give the same value.
    "Bivolt" makes the voltage unknown, and 110, 115, 120 and 127 V are the same network (127)."""
    text = _INCH.sub(r"\1pol ", text or "")
    folded = _fold(text)
    found: Dict[str, set] = {}
    for number, unit in _MEASURE.findall(folded):
        dim, factor = UNITS[unit]
        found.setdefault(dim, set()).add(_canonical(number, factor))
    if "voltage_v" in found:
        found["voltage_v"] = {"127" if v in VOLTAGE_127 else v for v in found["voltage_v"]}
    words = set(folded.replace(".", " ").replace(",", " ").split())
    if "bivolt" in words:
        found.pop("voltage_v", None)
    sizes = {next(g for g in m if g) for m in _SIZE.findall(_fold_keep(text))}
    if sizes:
        found["size"] = sizes
    dims = set()
    for numbers, unit in _DIMENSIONS.findall(folded):
        parts = [p.strip() for p in numbers.split("x")]
        if unit:
            dims.add("cm:" + "x".join(_canonical(p, _DIM_FACTOR[unit]) for p in parts))
        else:
            dims.add("x".join(_canonical(p, Decimal(1)) for p in parts))
    if dims:
        found["dimensions"] = dims
    plain = folded.replace(".", " ").replace(",", " ")
    quantities = {next(g for g in m if g).lstrip("0") or "0" for m in _QUANTITY.findall(plain)}
    if quantities:
        found["quantity"] = quantities
    colours = {COLOURS[w] for w in words if w in COLOURS and not (w == "cobre" and "leito" in words)}
    if colours:
        found["colour"] = colours
    genders = {GENDERS[w] for w in words if w in GENDERS}
    if genders:
        found["gender"] = genders
    return {k: frozenset(v) for k, v in found.items()}


def conflict(a: str, b: str) -> Optional[str]:
    """The first attribute on which two names disagree, or None. Both names must state the
    attribute and share no value: "110V" vs "110V/220V" is not a conflict."""
    return conflict_between(attributes(a), attributes(b))


def conflict_between(ta: Dict[str, FrozenSet[str]], tb: Dict[str, FrozenSet[str]]) -> Optional[str]:
    """:func:`conflict` on attributes already extracted."""
    for dim in sorted(set(ta) & set(tb)):
        if dim == "dimensions":
            if not _dimensions_agree(ta[dim], tb[dim]):
                return f"{dim}: {'/'.join(sorted(ta[dim]))} vs {'/'.join(sorted(tb[dim]))}"
        elif not (ta[dim] & tb[dim]):
            return f"{dim}: {'/'.join(sorted(ta[dim]))} vs {'/'.join(sorted(tb[dim]))}"
    return None


def _dimensions_agree(a: FrozenSet[str], b: FrozenSet[str]) -> bool:
    """Two sets of dimension lists agree when some pair is comparable (both with a unit, or both
    without) and one list starts with the other ("10.6x8.5x10.6" and "10.6x8.5"). Pairs that
    cannot be compared do not count as a conflict."""
    compared = False
    for x in a:
        for y in b:
            if x.startswith("cm:") != y.startswith("cm:"):
                continue
            compared = True
            px, py = x.split("x"), y.split("x")
            n = min(len(px), len(py))
            if px[:n] == py[:n]:
                return True
    return not compared
