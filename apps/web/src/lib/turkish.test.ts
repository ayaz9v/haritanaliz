import { describe, expect, it } from "vitest";
import { normalizeTr, searchByName } from "./turkish";

describe("normalizeTr", () => {
  it("applies Turkish case rules for dotted and dotless i", () => {
    expect(normalizeTr("İSTANBUL")).toBe("istanbul");
    expect(normalizeTr("Istanbul")).toBe("istanbul");
    expect(normalizeTr("IĞDIR")).toBe("igdir");
  });

  it("folds Turkish letters and collapses whitespace", () => {
    expect(normalizeTr("  Şanlıurfa   Merkez ")).toBe("sanliurfa merkez");
    expect(normalizeTr("Çankırı")).toBe("cankiri");
    expect(normalizeTr("Gümüşhane")).toBe("gumushane");
    expect(normalizeTr("Hâkimiyet")).toBe("hakimiyet");
  });
});

describe("searchByName", () => {
  const places = [
    { name: "Ankara" },
    { name: "Antalya" },
    { name: "Afyonkarahisar" },
    { name: "Karaman" },
    { name: "Kahramanmaraş" },
    { name: "İzmir" },
    { name: "Yeni Mahalle" },
  ];
  const names = (query: string, limit?: number) =>
    searchByName(places, query, limit).map((place) => place.name);

  it("ranks exact, prefix, word prefix and substring matches in that order", () => {
    expect(names("karaman")).toEqual(["Karaman"]);
    expect(names("kara")).toEqual(["Karaman", "Afyonkarahisar", "Ankara"]);
    expect(names("mah")).toEqual(["Yeni Mahalle"]);
    expect(names("maras")).toEqual(["Kahramanmaraş"]);
  });

  it("ignores case and Turkish letters in the query", () => {
    expect(names("IZMIR")).toEqual(["İzmir"]);
    expect(names("kahramanmaraş")).toEqual(["Kahramanmaraş"]);
  });

  it("sorts ties alphabetically and respects the limit", () => {
    // Ankara/Antalya are prefix matches; the rest are substring matches in Turkish order.
    expect(names("an")).toEqual(["Ankara", "Antalya", "Kahramanmaraş", "Karaman"]);
    expect(names("an", 2)).toEqual(["Ankara", "Antalya"]);
  });

  it("returns nothing for an empty query", () => {
    expect(names("   ")).toEqual([]);
  });
});
