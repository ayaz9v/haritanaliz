from __future__ import annotations

import pytest

from haritanaliz.text import (
    display_name,
    fold_ascii,
    normalize_name,
    split_type_suffix,
    tr_lower,
    tr_upper,
)


def test_turkish_casing_handles_dotted_and_dotless_i() -> None:
    assert tr_lower("IĞDIR") == "ığdır"
    assert tr_lower("İSTANBUL") == "istanbul"
    assert tr_lower("Istanbul") == "ıstanbul"
    assert tr_upper("istanbul") == "İSTANBUL"
    assert tr_upper("ılıca") == "ILICA"
    # Python's own lower() turns "İ" into "i" + combining dot; ours must not.
    assert len(tr_lower("İzmir")) == len("İzmir")


def test_fold_ascii() -> None:
    assert fold_ascii("çğıöşü ÇĞÖŞÜ") == "cgiosu CGOSU"
    assert fold_ascii("Hâkimiyet") == "Hakimiyet"


@pytest.mark.parametrize(
    ("name", "base", "suffix"),
    [
        ("Alsancak Mahallesi", "Alsancak", "mahallesi"),
        ("KIZILAY MAHALLESİ", "KIZILAY", "mahallesi"),
        ("Cumhuriyet Mah.", "Cumhuriyet", "mah."),
        ("Cumhuriyet Mh", "Cumhuriyet", "mh"),
        ("Bağlıca Köyü", "Bağlıca", "köyü"),
        ("Gölbaşı Beldesi", "Gölbaşı", "beldesi"),
        ("Yeni Mahalle", "Yeni Mahalle", None),  # "Mahalle" alone is part of the name
        ("Yeniköy", "Yeniköy", None),
        ("Mahallesi", "Mahallesi", None),
        ("Çankaya", "Çankaya", None),
    ],
)
def test_split_type_suffix(name: str, base: str, suffix: str | None) -> None:
    assert split_type_suffix(name) == (base, suffix)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Kızılay Mahallesi", "kizilay"),
        ("KIZILAY MAH.", "kizilay"),
        ("İnönü Mahallesi", "inonu"),
        ("INÖNÜ", "inonu"),
        ("Çankaya", "cankaya"),
        ("Hacı Bayram-ı Veli Mahallesi", "haci bayram i veli"),
        ("Şehit Er Ali'nin Köyü", "sehit er alinin"),
        ("  Gazi   Osman  Paşa ", "gazi osman pasa"),
    ],
)
def test_normalize_name(name: str, expected: str) -> None:
    assert normalize_name(name) == expected


def test_display_name_strips_suffix_and_fixes_all_caps() -> None:
    assert display_name("Alsancak Mahallesi") == "Alsancak"
    assert display_name("KIZILAY MAHALLESİ") == "Kızılay"
    assert display_name("İSKELE MAH.") == "İskele"
    assert display_name("Bağlıca Köyü") == "Bağlıca"
    assert display_name("Konak") == "Konak"
