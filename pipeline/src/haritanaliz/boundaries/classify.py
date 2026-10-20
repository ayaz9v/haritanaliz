"""Decide what an OSM boundary polygon or place point is, from its tags and name.

Nothing here assumes fixed admin levels; the rules come from the national data review
documented in docs/reports/sinir_kalitesi.md and docs/decisions.md.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Literal

from haritanaliz.text import (
    BELDE_SUFFIXES,
    fold_ascii,
    name_type_word,
    split_type_suffix,
    tr_lower,
)

UnitType = Literal["mahalle", "koy", "ozel", "belirsiz"]
TypeSource = Literal["ad", "etiket", "etiket_noktasi", "ayni_adli_nokta", "buyuksehir", "yok"]

# Settlement parts below the village/neighbourhood level (hamlets, summer pastures, localities).
_SUB_SETTLEMENT = re.compile(r"\b(mezra|mezrasi|yayla|yaylasi|mevki|mevkii|kom|komu)\b")
# Municipal areas that contain neighbourhoods (towns, district/provincial centres).
_CONTAINER = re.compile(r"\b(beldesi|belediyesi|ilce merkezi|il merkezi|bucagi)\b")

SUB_SETTLEMENT_CLASSES = frozenset({"mezra", "yayla", "kom"})
PLACE_TO_TYPE: Mapping[str, UnitType] = {
    "village": "koy",
    "neighbourhood": "mahalle",
    "suburb": "mahalle",
    "quarter": "mahalle",
}


def match_key(name: str) -> str:
    """Lowercase ASCII form with punctuation as spaces, for pattern matching on names."""
    return re.sub(r"[^0-9a-z]+", " ", fold_ascii(tr_lower(name))).strip()


@dataclass(frozen=True)
class Classifier:
    special_patterns: tuple[re.Pattern[str], ...]
    metropolitan_provinces: frozenset[str]

    @classmethod
    def from_settings(cls, patterns: Iterable[str], metropolitan: Iterable[str]) -> Classifier:
        return cls(
            special_patterns=tuple(re.compile(pattern) for pattern in patterns),
            metropolitan_provinces=frozenset(metropolitan),
        )

    def is_special_zone(self, name: str | None) -> bool:
        """Organised industrial zones, free zones and similar (by name)."""
        key = match_key(name or "")
        return any(pattern.search(key) for pattern in self.special_patterns)

    def is_metropolitan(self, province_iso: str | None) -> bool:
        return province_iso in self.metropolitan_provinces

    def unit_type(
        self,
        name: str | None,
        tags: Mapping[str, str],
        hint_place: str | None = None,
        hint_source: TypeSource = "etiket_noktasi",
    ) -> tuple[UnitType, TypeSource]:
        """Unit type from (in order) special-zone name, name suffix, own tags, a hint place
        tag (label member or same-named point). Metropolitan rules are applied separately."""
        if self.is_special_zone(name):
            return "ozel", "ad"
        from_name = name_type_word(name or "")
        if from_name in ("mahalle", "koy"):
            return from_name, "ad"  # type: ignore[return-value]
        from_tags = _type_from_tags(tags)
        if from_tags:
            return from_tags, "etiket"
        if hint_place and hint_place in PLACE_TO_TYPE:
            return PLACE_TO_TYPE[hint_place], hint_source
        return "belirsiz", "yok"

    def apply_metropolitan(
        self, unit_type: UnitType, source: TypeSource, province_iso: str | None
    ) -> tuple[UnitType, TypeSource]:
        """Since Law 6360 (2014) metropolitan provinces have no villages: every village or
        undetermined unit there is a mahalle."""
        if self.is_metropolitan(province_iso) and unit_type in ("koy", "belirsiz"):
            return "mahalle", "buyuksehir"
        return unit_type, source


def is_sub_settlement(name: str | None, tags: Mapping[str, str]) -> bool:
    """Hamlet (mezra), summer pasture (yayla), locality (mevki) or similar: not an
    administrative unit."""
    if tags.get("turkey_class") in SUB_SETTLEMENT_CLASSES:
        return True
    return bool(_SUB_SETTLEMENT.search(match_key(name or "")))


def is_container(name: str | None, admin_level: str | None, tags: Mapping[str, str]) -> bool:
    """Municipal area that contains neighbourhoods: a town (belde), a district centre or a
    municipality. In Türkiye these are mapped with admin_level=7 or named accordingly."""
    if admin_level == "7" or tags.get("turkey_class") == "belde":
        return True
    _, suffix = split_type_suffix(name or "")
    if suffix in BELDE_SUFFIXES:
        return True
    return bool(_CONTAINER.search(match_key(name or "")))


def is_village_part(tags: Mapping[str, str]) -> bool:
    """A place point that is part of a village (is_in:village), not a unit of its own."""
    return "is_in:village" in tags


def _type_from_tags(tags: Mapping[str, str]) -> UnitType | None:
    if tags.get("turkey_class") == "mahalle":
        return "mahalle"
    place = tags.get("place")
    return PLACE_TO_TYPE.get(place) if place else None
