"""Boundary quality report (docs/reports/sinir_kalitesi.md) and per province/district CSVs."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from haritanaliz.boundaries.build import BoundaryBuild
from haritanaliz.config import BoundarySettings
from haritanaliz.osm.download import OsmExtract
from haritanaliz.text import normalize_name, tr_sort_key

TYPE_LABELS = {"mahalle": "Mahalle", "koy": "Köy", "ozel": "Özel bölge", "belirsiz": "Belirsiz"}
EXCLUDED_LABELS = {
    "alt_yerlesim": "Mezra, yayla, mevki (idari birim değil)",
    "birim_ici_alt_birim": "Köy/mahalle içindeki daha derin seviyeli parçalar",
    "adsiz": "Adı olmayan sınırlar",
    "ilce_seviyesinde_way": "İlçe seviyesi etiketli kapalı way'ler (çoğu ada)",
    "seviyesiz_birim_disi": "admin_level eksik/hatalı ve adı birim olmayan (fabrika, yerleşim sınırı vb.)",
    "yinelenen_birim": "Aynı birimin ikinci çizimi",
    "ada_ilce_degil": "İlçe seviyesi etiketli ada (başka ilçenin içinde)",
    "ilce_disinda": "Hiçbir ilçeyle kesişmeyen birim",
}
ISSUE_LABELS = {
    "admin_level_eksik_hatali": "admin_level eksik veya hatalı, adından birim olduğu anlaşılıyor",
    "birlesmeyen_iliski": "İlişki poligona birleşmiyor (halkalar kapanmıyor)",
    "birden_fazla_ilceye_tasma": "Birim birden fazla ilçeye taşıyor",
    "ilce_il_tasmasi": "İlçe ilinin dışına taşıyor",
    "geometri_onarildi": "Geçersiz geometri onarıldı",
    "yinelenen_kimlik": "Aynı OSM nesnesi iki birim olarak çıktı",
}


def load_reference(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_districts(build: BoundaryBuild, reference: dict[str, Any]) -> pd.DataFrame:
    """Compare districts per province with the official list (count and names)."""
    provinces = build.provinces.set_index("code")
    rows = []
    for code, entry in sorted(reference["provinces"].items()):
        province = provinces.loc[code]
        osm = build.districts[build.districts["province_id"] == province["id"]]
        osm_names = dict(zip(osm["name_norm"], osm["name"], strict=True))
        unmatched = set(osm_names)
        missing = []
        for official in entry["districts"]:
            key = normalize_name(official)
            if key == "merkez":
                match = next(
                    (k for k in sorted(unmatched) if k == "merkez" or k.endswith(" merkez")), None
                )
            else:
                match = key if key in unmatched else None
            if match is None:
                missing.append(official)
            else:
                unmatched.discard(match)
        rows.append(
            {
                "kod": code,
                "il": province["name"],
                "resmi": len(entry["districts"]),
                "osm": len(osm),
                "resmi_eslesmeyen": ", ".join(missing),
                "osm_eslesmeyen": ", ".join(sorted(osm_names[k] for k in unmatched)),
            }
        )
    return pd.DataFrame(rows)


def province_table(build: BoundaryBuild) -> pd.DataFrame:
    units = build.units
    counts = (
        units.groupby(["province_id", "type", "approx"])
        .size()
        .unstack(["type", "approx"], fill_value=0)
    )

    def count(type_: str, approx: bool) -> pd.Series:
        key = (type_, approx)
        return counts[key] if key in counts.columns else pd.Series(0, index=counts.index)

    cov = build.coverage.groupby("province_id")[
        ["area_km2", "covered_km2", "approx_km2", "gap_km2", "overlap_km2"]
    ].sum()
    districts = build.districts.groupby("province_id").size()
    zones = build.special_zones.groupby("province_id").size()
    provinces = build.provinces.set_index("id")
    table = pd.DataFrame(
        {
            "kod": provinces["code"],
            "il": provinces["name"],
            "ilce": districts,
            "mahalle_osm": count("mahalle", False),
            "mahalle_yaklasik": count("mahalle", True),
            "koy_osm": count("koy", False),
            "koy_yaklasik": count("koy", True),
            "ozel_birim": count("ozel", False) + count("ozel", True),
            "belirsiz": count("belirsiz", False),
            "ozel_bolge_poligonu": zones,
            "kara_alani_km2": cov["area_km2"],
            "osm_kapsam": cov["covered_km2"] / cov["area_km2"],
            "yaklasikla_kapsam": (cov["covered_km2"] + cov["approx_km2"]) / cov["area_km2"],
            "bosluk_km2": cov["gap_km2"],
            "cakisma_km2": cov["overlap_km2"],
        }
    ).fillna(0)
    integer = [
        c
        for c in table.columns
        if c.endswith(("_osm", "_yaklasik"))
        or c in ("ilce", "ozel_birim", "belirsiz", "ozel_bolge_poligonu")
    ]
    table[integer] = table[integer].astype(int)
    table["yaklasik"] = table["mahalle_yaklasik"] + table["koy_yaklasik"]
    return table.sort_values("kod")


def district_table(build: BoundaryBuild) -> pd.DataFrame:
    districts = build.districts.set_index("id")
    provinces = build.provinces.set_index("id")
    cov = build.coverage.copy()
    cov.insert(0, "ilce", districts["name"])
    cov.insert(0, "il", cov["province_id"].map(provinces["name"]))
    cov["osm_kapsam"] = cov["covered_km2"] / cov["area_km2"]
    cov["yaklasikla_kapsam"] = (cov["covered_km2"] + cov["approx_km2"]) / cov["area_km2"]
    cov = cov.rename(
        columns={
            "units": "birim_osm",
            "approx_units": "birim_yaklasik",
            "area_km2": "alan_km2",
            "covered_km2": "osm_km2",
            "approx_km2": "yaklasik_km2",
            "overlap_km2": "cakisma_km2",
            "gap_km2": "bosluk_km2",
            "gap_before_km2": "bosluk_once_km2",
            "points_in_gap": "aday_nokta",
        }
    )
    order = cov["il"].map(tr_sort_key) + "|" + cov["ilce"].map(tr_sort_key)
    return cov.loc[order.sort_values().index].reset_index()


def write_tables(build: BoundaryBuild, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    il_path = out_dir / "sinir_kalitesi_il.csv"
    ilce_path = out_dir / "sinir_kalitesi_ilce.csv"
    province_table(build).round(4).to_csv(il_path, index=False, lineterminator="\n")
    district_table(build).round(4).to_csv(ilce_path, index=False, lineterminator="\n")
    return il_path, ilce_path


def render_report(
    build: BoundaryBuild,
    extract: OsmExtract,
    settings: BoundarySettings,
    reference: dict[str, Any],
    generated: date,
) -> str:
    official = settings.official_counts
    stats = build.stats
    units = build.units
    provinces = province_table(build)
    validation = validate_districts(build, reference)
    real = units[~units["approx"]]
    approx = units[units["approx"]]
    land = provinces["kara_alani_km2"].sum()
    covered = build.coverage["covered_km2"].sum()
    approx_area = build.coverage["approx_km2"].sum()
    gap = build.coverage["gap_km2"].sum()
    total_with_sea = build.provinces["area_total_km2"].sum()

    def n(value: float) -> str:
        return f"{value:,.0f}".replace(",", ".")

    def dec(value: float, digits: int = 1) -> str:
        return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")

    def pct(value: float) -> str:
        sign = "−" if value < -0.0005 else ""
        return f"{sign}%{dec(abs(value) * 100)}"

    def diff(value: int, target: int) -> str:
        delta = value - target
        if delta == 0:
            return "0"
        return f"{'+' if delta > 0 else '−'}{n(abs(delta))} ({pct(delta / target)})"

    count = lambda frame, type_: int((frame["type"] == type_).sum())  # noqa: E731
    lines: list[str] = []
    add = lines.append
    add("# Sınır kalitesi raporu")
    add("")
    add(
        f"> Bu dosya `uv run haritanaliz boundaries` komutuyla üretilir; elle düzenlenmez. "
        f"Üretim tarihi: {generated.isoformat()}."
    )
    add(
        f"> OSM verisi: Geofabrik Türkiye extract'ı, veri zaman damgası "
        f"{extract.timestamp:%Y-%m-%dT%H:%M:%SZ}, MD5 `{extract.md5}`."
    )
    add("> Resmî sayılar: e-İçişleri Türkiye Mülki İdare Bölümleri Envanteri (erişim 2026-10-20).")
    add("")
    add("## Özet")
    add("")
    add("| Birim | OSM sınırı olan | Yaklaşık sınır | Toplam | Resmî | Fark |")
    add("|---|---:|---:|---:|---:|---:|")
    add(
        f"| İl | {len(build.provinces)} | – | {len(build.provinces)} | {official.il} | {diff(len(build.provinces), official.il)} |"
    )
    add(
        f"| İlçe | {len(build.districts)} | – | {len(build.districts)} | {official.ilce} | {diff(len(build.districts), official.ilce)} |"
    )
    for type_, target in (("mahalle", official.mahalle), ("koy", official.koy)):
        total = count(units, type_)
        add(
            f"| {TYPE_LABELS[type_]} | {n(count(real, type_))} | {n(count(approx, type_))} | "
            f"{n(total)} | {n(target)} | {diff(total, target)} |"
        )
    add(
        f"| Özel bölge (birim) | {count(real, 'ozel')} | {count(approx, 'ozel')} | {count(units, 'ozel')} | – | – |"
    )
    add(
        f"| Türü belirsiz | {count(real, 'belirsiz')} | {count(approx, 'belirsiz')} | {count(units, 'belirsiz')} | – | – |"
    )
    add("")
    add(
        f"- **Kara alanı:** {n(land)} km². İl poligonları karasularını da içerdiği için toplamları {n(total_with_sea)} km²; alanlar ilçelerin birleşimiyle kırpılarak hesaplandı (Türkiye merkezli Albers eşit alan projeksiyonu)."
    )
    add(
        f"- **OSM sınırlarının kapladığı alan:** {pct(covered / land)}. Yaklaşık sınırlarla birlikte {pct((covered + approx_area) / land)}; boş kalan {n(gap)} km² ({pct(gap / land)})."
    )
    add(
        f"- **Özel bölge poligonları:** arazi kullanımı olarak çizilmiş {stats['special_zones']} OSB/serbest bölge alanı ayrı katmanda."
    )
    add(
        f"- **Kapsayıcı sınırlar:** {stats['containers_by_name_or_level'] + stats['containers_by_nesting']} belde/belediye/eski köy sınırı birim sayılmadı ({stats['containers_by_name_or_level']} ad veya seviyeden, {stats['containers_by_nesting']} iç içe çizimden)."
    )
    add(
        f"- **Geçersiz geometri:** {stats['invalid_geometries']} (libosmium'un ürettiği poligonlar geçerli; birleşmeyen ilişkiler aşağıda)."
    )
    add("")
    add("## admin_level karşılıkları (veriyle doğrulandı)")
    add("")
    add(
        "Seviyeler varsayılmadı; Türkiye içindeki bütün idari poligonlar seviye, ad ve etiketlerine göre incelendi."
    )
    add("")
    add("| admin_level | Poligon | Türkiye'deki anlamı |")
    add("|---|---:|---|")
    meaning = {
        "2": "Ülke",
        "3": "Coğrafi bölge (idari birim değil, kullanılmadı)",
        "4": "İl (81, hepsinde ISO3166-2 kodu var)",
        "6": "İlçe; ayrıca ilçe seviyesiyle etiketlenmiş adalar",
        "7": "Belediye sınırları: belde, ilçe merkezi, bucak (kapsayıcı)",
        "8": "Mahalle ve köy; bazı illerde eski köy/belde sınırları da bu seviyede",
        "9": "Çoğu köy içi mahalle, mezra, yayla; birkaç belde mahallesi",
        "10": "Mezra, yayla, mevki",
        "yok": "Seviyesi eksik; adı birim olanlar kullanıldı",
    }
    for level, label in meaning.items():
        add(f"| {level} | {n(stats['admin_levels'].get(level, 0))} | {label} |")
    add("")
    unit_levels = real["admin_level"].fillna("yok")
    other = (
        real[unit_levels != "8"].groupby(["province_id", unit_levels[unit_levels != "8"]]).size()
    )
    level_names = build.provinces.set_index("id")["name"]
    if other.empty:
        add("OSM sınırı olan mahalle/köylerin hepsi bütün illerde `admin_level=8`.")
    else:
        detail = "; ".join(
            f"{level_names[pid]}: "
            + ", ".join(f"{level} → {count}" for (_, level), count in group.items())
            for pid, group in other.groupby(level=0)
        )
        add(
            "OSM sınırı olan mahalle/köyler bütün illerde ağırlıkla `admin_level=8`. "
            f"8 dışındaki seviyelerde kalan birimler (seviye → adet): {detail}."
        )
    add("")
    add("## İlçe doğrulaması")
    add("")
    mismatched = validation[validation["resmi"] != validation["osm"]]
    named = validation[
        (validation["resmi_eslesmeyen"] != "") | (validation["osm_eslesmeyen"] != "")
    ]
    add(
        f"OSM'de {len(build.districts)} ilçe, resmî listede {validation['resmi'].sum()} ilçe var. Sayısı tutmayan il: {len(mismatched)}."
    )
    add("")
    islands = build.excluded[build.excluded["reason"] == "ada_ilce_degil"]["name"].dropna()
    if not islands.empty:
        add(
            "İlçe seviyesiyle etiketlenmiş ama başka bir ilçenin içinde kalan adalar ilçe sayılmadı: "
            + ", ".join(islands)
            + "."
        )
    if mismatched.empty:
        add("")
        add("Bütün illerde ilçe sayısı resmî listeyle aynı.")
    else:
        add("")
        add("| İl | Resmî | OSM |")
        add("|---|---:|---:|")
        for row in mismatched.itertuples():
            add(f"| {row.il} | {row.resmi} | {row.osm} |")
    if not named.empty:
        add("")
        add("Ad farkları (sayı aynı, yazım farklı):")
        add("")
        add("| İl | Resmî listede | OSM'de |")
        add("|---|---|---|")
        for row in named.itertuples():
            add(f"| {row.il} | {row.resmi_eslesmeyen} | {row.osm_eslesmeyen} |")
    add("")
    add("## İl bazında birimler ve kapsam")
    add("")
    add(
        "OSM: sınırı OSM'de olan; yaklaşık: Voronoi ile üretilen. Kapsam, ilçelerin kara alanına oranıdır."
    )
    add("")
    add(
        "| İl | İlçe | Mahalle (OSM + yaklaşık) | Köy (OSM + yaklaşık) | Özel | OSM kapsamı | Yaklaşıkla | Boşluk km² | Çakışma km² |"
    )
    add("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in provinces.itertuples():
        add(
            f"| {row.kod} {row.il} | {row.ilce} | {row.mahalle_osm} + {row.mahalle_yaklasik} | "
            f"{row.koy_osm} + {row.koy_yaklasik} | {row.ozel_birim} | {pct(row.osm_kapsam)} | "
            f"{pct(row.yaklasikla_kapsam)} | {dec(row.bosluk_km2)} | {dec(row.cakisma_km2)} |"
        )
    add("")
    add("## En sorunlu iller")
    add("")
    worst = provinces.sort_values("osm_kapsam").head(15)
    add("OSM sınır kapsamı en düşük 15 il (birimlerin neredeyse tamamı yaklaşık):")
    add("")
    add(", ".join(f"{row.il} ({pct(row.osm_kapsam)})" for row in worst.itertuples()) + ".")
    add("")
    full = provinces[provinces["osm_kapsam"] >= 0.99]
    add(f"Mahalle/köy sınırları tam (%99 ve üstü) olan iller: {', '.join(full['il'])}.")
    add("")
    districts = district_table(build)
    add(
        "En büyük boşluklar: yaklaşık sınırlardan sonra da kaplanmayan alanlar. Bunlar, içinde aday yer noktası bulunmayan alanlardır: göller, yerleşimsiz araziler ya da OSM'de noktası eksik birimler. İlçe bazında bütün değerler `sinir_kalitesi_ilce.csv` dosyasında."
    )
    add("")
    add("| İl | İlçe | Boşluk km² | İlçe alanı km² |")
    add("|---|---|---:|---:|")
    for row in districts.sort_values("bosluk_km2", ascending=False).head(10).itertuples():
        add(f"| {row.il} | {row.ilce} | {dec(row.bosluk_km2)} | {n(row.alan_km2)} |")
    add("")
    add("En büyük çakışmalar (aynı alanın birden fazla OSM birimine ait olması):")
    add("")
    add("| İl | İlçe | Çakışma km² |")
    add("|---|---|---:|")
    for row in districts.sort_values("cakisma_km2", ascending=False).head(8).itertuples():
        if row.cakisma_km2 >= 0.01:
            add(f"| {row.il} | {row.ilce} | {dec(row.cakisma_km2, 2)} |")
    add("")
    add("## Yaklaşık sınırlar")
    add("")
    add(
        f"Sınırı OSM'de olmayan mahalle ve köyler için, ilçenin OSM sınırlarıyla kaplanmamış kısmı yer noktaları "
        f"arasında Voronoi ile bölündü ({n(len(approx))} birim, `approx=true`). Kullanılan noktalar: "
        f"`place={', '.join(settings.approx_place_values)}`. Mezra/yayla, `is_in:village` ile köy parçası "
        f"olduğu belirtilen ve `turkey_class=belde` olan noktalar kullanılmadı."
    )
    add("")
    add(
        f"Mahalle noktaları (`neighbourhood`, `suburb`, `quarter`) yalnızca bir kasaba noktasına "
        f"{settings.urban_radius_km.town:g} km, bir şehir noktasına {settings.urban_radius_km.city:g} km "
        f"mesafede ya da bir belediye sınırının içindeyse kullanıldı. Kırsaldaki bu tür noktalar çoğunlukla "
        f"köy mahallesidir (idari birim değildir); bu kuralla {n(stats['approx_dropped_village_quarters'])} "
        f"nokta elendi. Yarıçapın sonuca etkisi docs/decisions.md'de (K-042)."
    )
    add("")
    add("## Ayıklanan nesneler")
    add("")
    add("| Neden | Adet |")
    add("|---|---:|")
    for reason, value in build.excluded["reason"].value_counts().items():
        add(f"| {EXCLUDED_LABELS.get(reason, reason)} | {value} |")
    add("")
    add("## Tutarsızlıklar")
    add("")
    if build.issues.empty:
        add("Yok.")
    else:
        add("| Tür | OSM | Ad | Ayrıntı |")
        add("|---|---|---|---|")
        for row in build.issues.itertuples():
            ident = row.id
            link = f"https://www.openstreetmap.org/{_osm_path(ident)}" if ident else ""
            add(
                f"| {ISSUE_LABELS.get(row.kind, row.kind)} | [{ident}]({link}) | {row.name or ''} | {row.detail} |"
            )
    add("")
    add("## Bilinen eksikler")
    add("")
    add(
        f"- Köylerin çok azının sınırı OSM'de var ({n(count(real, 'koy'))} köy); köy sınırlarının büyük kısmı yaklaşıktır."
    )
    add(
        '- Yaklaşık sınırlar gerçek idari sınırları değil, yer noktalarına yakınlığı gösterir; alanları ve dolayısıyla yoğunluk değerleri belirsizdir. Arayüzde kesikli çizgiyle ve "yaklaşık sınır" notuyla gösterilir.'
    )
    add(
        "- Mahalle sayısı resmî sayının altındadır: OSM'de hiç noktası olmayan mahalleler ve kentsel yarıçap dışında kalan mahalle noktaları eksik kalır. Kentsel yarıçap içindeki köy mahalleleri ise fazladan mahalle olarak görünebilir."
    )
    add(
        "- Büyükşehirlerde 2014'ten beri köy yoktur; OSM'de hâlâ köy olarak etiketlenmiş birimler mahalle sayıldı."
    )
    add(
        "- Birim adlarının resmî adlarla eşleştirilmesi ve nüfus karşılaştırması TÜİK ADNKS dosyası geldiğinde (Adım 4) yapılacak; bu karşılaştırma yaklaşık birimlerdeki fazla/eksik birimleri de ortaya çıkaracak."
    )
    add("")
    return "\n".join(lines)


def _osm_path(ident: str) -> str:
    kind = {"r": "relation", "w": "way", "n": "node"}[ident[0]]
    return f"{kind}/{ident[1:]}"
