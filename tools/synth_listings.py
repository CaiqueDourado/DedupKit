"""Synthetic store listings with known answers, for tests and the benchmark.

Each *variant* (a product in one size, colour or voltage) is a true entity with its own valid
GTIN. Each variant is sold by several stores, and every store writes the name its own way:
different word order, upper case, abbreviations, plurals, marketing words, typos and unit
formats. The hard cases are deliberate:

- sibling variants differ by a single attribute ("Ração ... 2,5kg" and "Ração ... 15kg");
- some listings carry the GTIN of another product (marketplace errors) or of a sibling;
- short internal SKUs ("4521") are reused by unrelated products;
- sister stores share the same image file; sizes of one product often share one photo;
- a "no photo" placeholder is used by many listings.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

CATALOG = [
    ("Fone de Ouvido", ["JBL", "Sony", "Philips", "Xiaomi", "Edifier"], ["Tune 510BT", "WH-CH520", "TAH1205", "Redmi Buds 4", "W820NB"],
     [("cor", ["Preto", "Branco", "Azul"]), ("tipo", ["Bluetooth", "Sem Fio"])]),
    ("Ração para Cães", ["Royal Canin", "Pedigree", "Golden", "Premier", "Purina"], ["Club Performance Junior", "Adulto Raças Pequenas", "Fórmula Filhotes", "Ambientes Internos", "Dog Chow Extra Life"],
     [("peso", ["2,5kg", "10,1kg", "15kg", "1kg"])]),
    ("Pendente", ["Taschibra", "Startec", "Bronzearte", "Avant"], ["TLF 28", "Cone 25", "Bell", "Industrial Retrô"],
     [("cor", ["Preto", "Branco", "Cobre"]), ("soquete", ["E27"])]),
    ("Geladeira", ["Brastemp", "Consul", "Electrolux", "Panasonic"], ["Frost Free 375L", "Duplex 340L", "Inverse 454L", "Cycle Defrost 261L"],
     [("tensao", ["110V", "220V"]), ("cor", ["Branca", "Inox"])]),
    ("Tênis", ["Nike", "Adidas", "Olympikus", "Mizuno", "Fila"], ["Revolution 6", "Runfalcon 3.0", "Corre 3", "Wave Prophecy", "Racer"],
     [("cor", ["Preto", "Branco", "Cinza"]), ("genero", ["Masculino", "Feminino"])]),
    ("Smartphone", ["Samsung", "Motorola", "Xiaomi", "Apple"], ["Galaxy A54", "Moto G84", "Redmi Note 13", "iPhone 13"],
     [("memoria", ["128GB", "256GB"]), ("cor", ["Preto", "Azul", "Grafite"])]),
    ("Panela de Pressão", ["Tramontina", "Rochedo", "Clock", "Panelux"], ["Vancouver", "Turbo", "Life Smart", "Brilliance"],
     [("capacidade", ["4,5L", "7L", "3L"])]),
    ("Cadeira de Escritório", ["Pethiflex", "Flexform", "Cavaletti", "Frisokar"], ["PP-04GTBP Presidente", "Ergonômica Mesh", "Diretor Giratória", "Secretária Fixa"],
     [("cor", ["Preta", "Vermelha", "Cinza"])]),
    ("Chuveiro Elétrico", ["Lorenzetti", "Fame", "Hydra", "Zagonel"], ["Duo Shower", "Advanced Turbo", "Fit", "Optma"],
     [("tensao", ["127V", "220V"]), ("potencia", ["5500W", "7500W"])]),
    ("Liquidificador", ["Oster", "Philco", "Mondial", "Arno", "Britânia"], ["Turbo Power", "PLQ1400", "L-99", "Power Max", "Diamante"],
     [("tensao", ["110V", "220V"]), ("cor", ["Preto", "Vermelho"])]),
]

STORES = [
    # (name, naming style, image group: stores of the same group share image files)
    ("Americanas", "b2w", "b2w"), ("Submarino", "b2w", "b2w"), ("Shoptime", "b2w", "b2w"),
    ("Magazine Luiza", "magalu", "magalu"), ("Casas Bahia", "via", "via"), ("Extra", "via", "via"),
    ("Pontofrio", "via", "via"), ("Amazon", "feed", "amazon"), ("Carrefour", "feed", "carrefour"),
    ("Loja do Zé", "upper", "ze"), ("Mega Ofertas", "upper", "mega"), ("Shop Vitrine", "feed", "vitrine"),
]
MARKETING = ["Original", "Lançamento", "Envio Imediato", "Promoção", "Novo", "Garantia"]
PLURALS = {"Fone de Ouvido": "Fones de Ouvido", "Pendente": "Pendentes", "Tênis": "Tênis",
           "Panela de Pressão": "Panelas de Pressão", "Cadeira de Escritório": "Cadeiras de Escritório"}


@dataclass
class Listing:
    id: str
    name: str
    brand: str
    codes: Tuple[str, ...]
    url: str
    image: str
    source: str
    entity: str  # the answer: variant id


def gtin13(rng: random.Random) -> str:
    body = "789" + "".join(str(rng.randrange(10)) for _ in range(9))
    total = sum(int(d) * (3 if i % 2 else 1) for i, d in enumerate(body))
    return body + str((10 - total % 10) % 10)


def _unit(value: str, rng: random.Random) -> str:
    """Write a unit the way different stores do: '2,5kg', '2.5 Kg', '2,5 KG'."""
    for unit in ("kg", "GB", "V", "W", "L"):
        if value.endswith(unit) and value[:-len(unit)].replace(",", "").isdigit():
            number = value[:-len(unit)]
            choice = rng.randrange(4)
            if choice == 1:
                return number + " " + unit
            if choice == 2:
                return number.replace(",", ".") + unit.lower()
            if choice == 3:
                return number + " " + unit.upper()
    return value


def _typo(word: str, rng: random.Random) -> str:
    if len(word) < 5:
        return word
    i = rng.randrange(1, len(word) - 2)
    kind = rng.randrange(3)
    if kind == 0:
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if kind == 1:
        return word[:i] + word[i + 1:]
    return word[:i] + word[i] + word[i:]


def _strip_accents(s: str) -> str:
    table = str.maketrans("áàâãéêíóôõúçÁÀÂÃÉÊÍÓÔÕÚÇ", "aaaaeeiooouc" "AAAAEEIOOOUC")
    return s.translate(table)


def name_for(kind: str, brand: str, model: str, attrs: List[str], style: str, rng: random.Random) -> str:
    attrs = [_unit(a, rng) for a in attrs]
    if rng.random() < 0.25 and kind in PLURALS:
        kind = PLURALS[kind]
    if style == "b2w":
        name = f"{kind} {model} {' '.join(attrs)} - {brand}"
    elif style == "magalu":
        name = f"{kind} {brand} {model} {' '.join(attrs)}"
    elif style == "via":
        name = f"{kind} {brand} {model} - {' - '.join(attrs)}"
    elif style == "upper":
        name = _strip_accents(f"{kind} {brand} {model} {' '.join(attrs)}").upper().replace(" COM ", " C/ ").replace(" PARA ", " P/ ")
    else:
        parts = [brand, kind, model] + attrs
        if rng.random() < 0.5:
            parts.append(rng.choice(MARKETING))
        name = " ".join(parts)
    if rng.random() < 0.1:
        words = name.split(" ")
        j = rng.randrange(len(words))
        words[j] = _typo(words[j], rng)
        name = " ".join(words)
    return name


def generate(seed: int = 7, products_per_kind: int = 60) -> List[Listing]:
    rng = random.Random(seed)
    listings: List[Listing] = []
    variants: List[Dict] = []
    used = set()
    for kind, brands, models, attr_defs in CATALOG:
        for p in range(products_per_kind):
            while True:
                brand = rng.choice(brands)
                model = rng.choice(models)
                if rng.random() < 0.6:
                    model = f"{model} {rng.randrange(100, 999)}"
                if (kind, brand, model) not in used:
                    used.add((kind, brand, model))
                    break
            combos = [[]]
            for _, values in attr_defs:
                pick = rng.sample(values, k=rng.randint(1, min(2, len(values))))
                combos = [c + [v] for c in combos for v in pick]
            photo = f"{kind}-{p}"
            for attrs in combos:
                # sizes and voltages of one product often share one photo; colours do not
                colour = next((a for a in attrs if a in {"Preto", "Branco", "Azul", "Cobre", "Branca", "Inox", "Cinza", "Grafite", "Preta", "Vermelha", "Vermelho"}), "")
                variants.append({"id": f"v{len(variants)}", "kind": kind, "brand": brand, "model": model, "attrs": attrs,
                                 "gtin": gtin13(rng), "photo": photo + "-" + colour, "sku": str(rng.randrange(1000, 9999))})
    sku_pool = [str(rng.randrange(1000, 9999)) for _ in range(40)]
    for v in variants:
        stores = rng.sample(STORES, k=rng.randint(1, 6))
        siblings = [w for w in variants if w["kind"] == v["kind"] and w["model"] == v["model"] and w["id"] != v["id"]]
        for store, style, image_group in stores:
            n = len(listings)
            roll = rng.random()
            if roll < 0.72:
                codes = (v["gtin"],)
            elif roll < 0.80:
                codes = ()
            elif roll < 0.85:
                codes = (rng.choice(variants)["gtin"],)          # marketplace error: another product's code
            elif roll < 0.90 and siblings:
                codes = (rng.choice(siblings)["gtin"],)          # seller reused the sibling's code
            else:
                codes = (rng.choice(sku_pool),)                   # short internal SKU, reused everywhere
            b = rng.random()
            brand = v["brand"] if b < 0.7 else (v["brand"].upper() if b < 0.8 else ("Importado" if b < 0.85 else ""))
            if rng.random() < 0.04:
                image = "no-photo"
            elif image_group in ("b2w", "via"):
                image = f"{v['photo']}@{image_group}"           # sister stores serve the same file
            else:
                image = f"{v['photo']}@{store}#{rng.randrange(10**6)}"  # each store re-encodes its copy
            listings.append(Listing(
                id=f"L{n:05d}",
                name=name_for(v["kind"], v["brand"], v["model"], v["attrs"], style, rng),
                brand=brand,
                codes=codes,
                url=f"https://www.{store.lower().replace(' ', '')}.com.br/p/{n}",
                image=image,
                source=store,
                entity=v["id"],
            ))
    # a few listings scraped twice (same URL, slightly different name)
    for k in range(0, len(listings), 97):
        src = listings[k]
        listings.append(Listing(f"L{len(listings):05d}", src.name + " " + rng.choice(MARKETING), src.brand, src.codes,
                                src.url + "?utm_source=feed", src.image, src.source, src.entity))
    return listings
