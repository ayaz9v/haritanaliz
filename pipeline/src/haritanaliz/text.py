"""Turkish-aware text handling for place names.

Python's ``str.lower()`` is not Turkish-aware: it turns "I" into "i" (should be "ı") and "İ"
into "i" plus a combining dot. All functions here apply Turkish casing first.
"""

from __future__ import annotations

import re
import unicodedata

_FOLD = str.maketrans(
    {"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u", "â": "a", "î": "i", "û": "u"}
)

# Unit-type suffixes, matched on the Turkish-lowercased name. Order matters: longer first.
_SUFFIX = re.compile(
    r"(?:\s+|^)(mahallesi|mahalesi|mah\.?|mh\.?|köyü|beldesi)\s*$",
)

MAHALLE_SUFFIXES = frozenset({"mahallesi", "mahalesi", "mah", "mah.", "mh", "mh."})
KOY_SUFFIXES = frozenset({"köyü"})
BELDE_SUFFIXES = frozenset({"beldesi"})


def tr_lower(text: str) -> str:
    """Lowercase with Turkish rules (I → ı, İ → i)."""
    return text.replace("I", "ı").replace("İ", "i").lower()


def tr_upper(text: str) -> str:
    """Uppercase with Turkish rules (i → İ, ı → I)."""
    return text.replace("i", "İ").replace("ı", "I").upper()


def fold_ascii(text: str) -> str:
    """Fold Turkish letters to ASCII and drop any remaining diacritics."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_FOLD))
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def split_type_suffix(name: str) -> tuple[str, str | None]:
    """Split a trailing unit-type word ("Mahallesi", "Mah.", "Köyü", ...) from a name.

    Returns the base name with its original casing and the suffix in Turkish lowercase,
    or ``None`` when there is no suffix. A name that is only a suffix is left unchanged.
    """
    stripped = name.strip()
    lowered = tr_lower(stripped)
    match = _SUFFIX.search(lowered)
    if not match or match.start() == 0:
        return stripped, None
    # tr_lower keeps the length of Turkish text, so the index applies to the original.
    return stripped[: match.start()].rstrip(" ,-"), match.group(1)


def name_type_word(name: str) -> str | None:
    """Unit type stated in the name: "mahalle", "koy" or "belde", else None.

    Besides the suffixes, a trailing standalone "Mahalle" also marks a neighbourhood
    ("Yeni Mahalle" is the neighbourhood "Yeni"); "Yenimahalle" in one word does not.
    """
    base, suffix = split_type_suffix(name)
    if suffix in MAHALLE_SUFFIXES:
        return "mahalle"
    if suffix in KOY_SUFFIXES:
        return "koy"
    if suffix in BELDE_SUFFIXES:
        return "belde"
    words = tr_lower(base).split()
    if len(words) >= 2 and words[-1] == "mahalle":
        return "mahalle"
    return None


def normalize_name(name: str) -> str:
    """Matching key for a place name: no type word, Turkish-lowercased, ASCII-folded,
    punctuation turned into spaces. "Kızılay Mahallesi", "KIZILAY MAH." → "kizilay";
    "Yeni Mahalle" → "yeni".
    """
    base, _ = split_type_suffix(name)
    folded = fold_ascii(tr_lower(base))
    folded = folded.replace("'", "").replace("’", "")
    words = re.sub(r"[^0-9a-z]+", " ", folded).split()
    if len(words) >= 2 and words[-1] == "mahalle":
        words = words[:-1]
    return " ".join(words)


def display_name(name: str) -> str:
    """Name without the type suffix, for breadcrumbs and lists ("Alsancak Mahallesi" →
    "Alsancak"). All-uppercase names are converted to Turkish title case."""
    base, _ = split_type_suffix(name)
    if base.isupper():
        base = " ".join(_tr_capitalize(word) for word in base.split())
    return base


_TR_ALPHABET = "abcçdefgğhıijklmnoöprsştuüvyz"
_TR_ORDER = {char: f"{position:02d}" for position, char in enumerate(_TR_ALPHABET)}


def tr_sort_key(text: str) -> str:
    """Sort key in Turkish alphabetical order (c < ç < d, ı < i, o < ö, s < ş, u < ü)."""
    return "".join(_TR_ORDER.get(char, f"9{char}") for char in tr_lower(text))


def _tr_capitalize(word: str) -> str:
    lowered = tr_lower(word)
    return tr_upper(lowered[:1]) + lowered[1:]
