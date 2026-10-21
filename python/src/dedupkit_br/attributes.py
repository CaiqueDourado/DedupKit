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
    "rosa": "rosa", "cinza": "cinza", "grafite": "grafite", "inox": "inox", "prata": "prata", "prateado": "prata",
    "prateada": "prata", "dourado": "dourado", "dourada": "dourado", "cobre": "cobre", "bege": "bege",
    "marrom": "marrom", "roxo": "roxo", "roxa": "roxo", "laranja": "laranja", "chumbo": "chumbo",
    "transparente": "transparente", "nude": "nude", "lilas": "lilas", "vinho": "vinho",
}
GENDERS = {"masculino": "masculino", "masculina": "masculino", "feminino": "feminino", "feminina": "feminino",
           "infantil": "infantil", "unissex": "unissex"}

_MEASURE = re.compile(r"(?<![a-z0-9])([0-9]+(?:[.,][0-9]+)?) ?(" + "|".join(sorted(UNITS, key=len, reverse=True)) + r")(?![a-z0-9])")


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
    """Measures, colours and gender found in a name. ``"Ração 2,5kg"`` → ``{"weight_kg": {"2.5"}}``;
    ``"500g"`` and ``"0,5 kg"`` give the same value. "Bivolt" makes the voltage unknown."""
    folded = _fold(text)
    found: Dict[str, set] = {}
    for number, unit in _MEASURE.findall(folded):
        dim, factor = UNITS[unit]
        found.setdefault(dim, set()).add(_canonical(number, factor))
    words = set(folded.replace(".", " ").replace(",", " ").split())
    if "bivolt" in words:
        found.pop("voltage_v", None)
    colours = {COLOURS[w] for w in words if w in COLOURS}
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
        if not (ta[dim] & tb[dim]):
            return f"{dim}: {'/'.join(sorted(ta[dim]))} vs {'/'.join(sorted(tb[dim]))}"
    return None
