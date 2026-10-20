const FOLD: Record<string, string> = {
  ç: "c",
  ğ: "g",
  ı: "i",
  ö: "o",
  ş: "s",
  ü: "u",
  â: "a",
  î: "i",
  û: "u",
};

/**
 * Normalizes text for case- and accent-insensitive Turkish search: Turkish lowercasing
 * (I → ı, İ → i), then folding Turkish letters to ASCII. "İSTANBUL", "Istanbul" and
 * "istanbul" all become "istanbul"; "Şanlıurfa" becomes "sanliurfa".
 */
export function normalizeTr(text: string): string {
  return text
    .toLocaleLowerCase("tr-TR")
    .replace(/[çğıöşüâîû]/g, (char) => FOLD[char] ?? char)
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/\s+/g, " ")
    .trim();
}

/** Turkish alphabetical order (ç after c, ı before i, ...). */
export const trCollator = new Intl.Collator("tr-TR", { sensitivity: "base" });

/**
 * Returns the items whose name matches the query, best matches first:
 * exact, then prefix, then word prefix, then substring; ties in Turkish alphabetical order.
 */
export function searchByName<T extends { name: string }>(
  items: readonly T[],
  query: string,
  limit = 8,
): T[] {
  const needle = normalizeTr(query);
  if (!needle) return [];

  const matches: { item: T; rank: number }[] = [];
  for (const item of items) {
    const name = normalizeTr(item.name);
    let rank: number;
    if (name === needle) rank = 0;
    else if (name.startsWith(needle)) rank = 1;
    else if (name.split(/[\s/-]+/).some((word) => word.startsWith(needle))) rank = 2;
    else if (name.includes(needle)) rank = 3;
    else continue;
    matches.push({ item, rank });
  }

  matches.sort((a, b) => a.rank - b.rank || trCollator.compare(a.item.name, b.item.name));
  return matches.slice(0, limit).map((match) => match.item);
}
