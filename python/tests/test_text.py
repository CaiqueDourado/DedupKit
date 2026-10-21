import pytest

import dedupkit_br as dk


@pytest.mark.parametrize("text, expected", [
    ("Pendente TLF-28, Preto!", "pendente tlf 28 preto"),
    ("  AÇÚCAR   Refinado  ", "acucar refinado"),
    ("Straße Œuvre", "strasse oeuvre"),
    ("café́", "cafe"),
    ("", ""),
])
def test_normalize(text, expected):
    assert dk.normalize(text) == expected


def test_fingerprint_ignores_order_case_and_repeats():
    assert dk.fingerprint("Preto Pendente preto") == dk.fingerprint("PENDENTE preto") == "pendente preto"


def test_legacy_fingerprint_keeps_every_other_word():
    assert dk.legacy_fingerprint("a b c d") == "a c "
    assert dk.legacy_fingerprint("a b c") == "a c"
    # the bug: different names, same key
    assert dk.legacy_fingerprint("Geladeira Brastemp 220V Inox") == dk.legacy_fingerprint("Geladeira Cinza 220V Preta")


def test_ngram_fingerprint():
    assert dk.ngram_fingerprint("Paris") == "arispari"
    assert dk.ngram_fingerprint("a") == "a"


@pytest.mark.parametrize("word, single", [
    ("flores", "flor"), ("motores", "motor"), ("torres", "torre"), ("animais", "animal"), ("papeis", "papel"),
    ("lencois", "lencol"), ("fogoes", "fogao"), ("maes", "mae"), ("tenis", "tenis"), ("funis", "funil"),
    ("kits", "kit"), ("luzes", "luz"), ("jardins", "jardim"), ("cadeiras", "cadeira"), ("oculos", "oculos"),
    ("lapis", "lapis"), ("onibus", "onibus"),
])
def test_singular(word, single):
    assert dk.singular(word) == single


def test_token_key():
    assert dk.token_key("Fones de Ouvido sem Fio") == dk.token_key("fone ouvido fio") == "fio fone ouvido"


@pytest.mark.parametrize("a, b", [
    ("Caçarola", "cassarola"), ("Chuveiro", "xuveiro"), ("Geladeira", "Jeladeira"), ("Pêssego", "pessego"),
    ("Assento", "acento"), ("Quilo", "Kilo"),
])
def test_phonetic_equal(a, b):
    assert dk.phonetic_key(a) == dk.phonetic_key(b)


def test_phonetic_keeps_digits_and_order():
    assert dk.phonetic_key("Chuveiro 220v") == "XVR 220V"
    assert dk.phonetic_key("Guitarra") == "GT2"


def test_normalize_url():
    assert dk.normalize_url("https://www.Loja.com.br/Produto/X/?utm_source=a&id=3&gclid=1#top") == "loja.com.br/produto/x?id=3"


def test_shares_word():
    assert dk.shares_word("Guitarra Strinberg Preta", "Guitarra STS100")
    assert not dk.shares_word("Guitarra Strinberg", "Reservatório de Água Gol")
    assert dk.shares_word("Smartphone Samsung", "Samsungs Galaxy")  # containment from 3 letters


def test_codes():
    assert dk.is_valid_gtin("7891234567895")
    assert not dk.is_valid_gtin("7891234567890")
    assert dk.code_class("7891234567895") == "long"
    assert dk.code_class("4521") == "short"
    assert dk.code_class("000000012345") == "short"
    assert dk.code_class("SEM GTIN") == "placeholder"
    assert dk.code_class("7.89E+12") == "placeholder"
    assert dk.code_class("BB799-6") == "long"


def test_attributes_and_conflicts():
    assert dk.attributes("Ração 2,5kg")["weight_kg"] == {"2.5"}
    assert dk.attributes("Ração 500g")["weight_kg"] == dk.attributes("Ração 0,5 kg")["weight_kg"]
    assert dk.conflict("Ração Golden 2,5kg", "Ração Golden 15kg") == "weight_kg: 2.5 vs 15"
    assert dk.conflict("Liquidificador 110V/220V", "Liquidificador 220 V") is None
    assert dk.conflict("Liquidificador Bivolt", "Liquidificador 220V") is None
    assert dk.conflict("Geladeira Branca", "Geladeira Inox") == "colour: branco vs prata"
    assert dk.conflict("Concha Inox", "Concha Prata") is None
    assert dk.conflict("Forno 110V", "Forno 127V") is None
    assert dk.conflict("Bota - 38 - Preto", "Bota - 40 - Preto") == "size: 38 vs 40"
    assert dk.conflict("Meia Kit 3 Pares", "Meia Kit 6 Pares") == "quantity: 3 vs 6"
    assert dk.conflict("Quadro 20x30", "Quadro 30x40") == "dimensions: 20x30 vs 30x40"
    assert dk.conflict("Porta Escova 10,6 X 8,5 X 10,6 Cm", "Porta Escova 10,6x8,5cm") is None
    assert dk.conflict("Toalha 1,50 x 2,00 m", "Toalha 150x200cm") is None
    assert dk.conflict('TV 55" Samsung', 'TV 40" Samsung') == "screen_in: 55 vs 40"
    assert dk.conflict("Tênis Masculino", "Tênis Feminino") == "gender: masculino vs feminino"
