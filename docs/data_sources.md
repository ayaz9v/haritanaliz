# Veri kaynakları

Bu belge, kullanılan her veri kaynağının içeriğini, erişim yolunu, güncellenme sıklığını, lisansını ve atıf metnini tutar. **Veri kalitesi sorunları gizlenmez:** bilinen her sorun aşağıdaki kalite günlüğüne yazılır ve arayüzde güven düzeyiyle gösterilir.

> Durum (Adım 0): Henüz hiçbir kaynaktan veri çekilmedi. "Doğrulanacak" diye işaretli maddeler, ilgili adımda gerçek veriyle kontrol edilecek.

## Özet

| Kaynak | Kullanım | Güncelleme | Lisans | Durum |
|---|---|---|---|---|
| Overture Maps Places | işletmeler (birincil) | aylık | kayıt bazında (bkz. aşağı) | Adım 2 |
| OpenStreetMap (Geofabrik) | işletmeler (ikincil), idari sınırlar, yollar, talep ve tedarik noktaları | günlük extract; aylık kullanım | ODbL 1.0 | henüz çekilmedi |
| TÜİK ADNKS | mahalle/köy nüfusları | yıllık | TÜİK kullanım koşulları | dosyalar bekleniyor |
| SEGE | il/ilçe sosyoekonomik gelişmişlik | birkaç yılda bir | kamu yayını | henüz çekilmedi |
| OpenFreeMap | altlık harita (yalnızca görüntü) | sürekli | OpenFreeMap koşulları; veri ODbL | kullanılıyor |

## Overture Maps Places (işletmeler, birincil)

- **Erişim:** `s3://overturemaps-us-west-2/release/<sürüm>/theme=places/type=place/*` GeoParquet dosyaları. DuckDB (`httpfs` + `spatial`) ile uzaktan okunur. Türkiye `region.bbox` ile önceden süzülür, sonra ülke sınırıyla kırpılır; dünyanın tamamı indirilmez.
- **Sürüm:** `sources.overture.release` (boş bırakılırsa en güncel sürüm kullanılır). Kullanılan sürüm, `manifest.json`'daki `sources` listesine yazılır.
- **Kullanılan alanlar:** `id`, `names.primary`, `basic_category`, `taxonomy` (`primary`, `hierarchy`), `confidence`, `operating_status`, `sources`, `brand`, geometri. Kullanımdan kaldırılan `categories` alanı **kullanılmaz**.
- **Kategori eşlemesi:** `config/categories.yaml` → `overture.basic_category` ve `overture.taxonomy`. Şu an **doğrulanmamış adaylar** (`verified: false`); Adım 2'de Türkiye alt kümesindeki gerçek değerlerle karşılaştırılacak.
- **Lisans:** kayıt bazındadır ve kaydın `sources` alanındaki veri setine bağlıdır. Proje tanımına göre Foursquare kaynaklı kayıtlar Apache 2.0 lisanslıdır; diğer veri setlerinin lisansları ve gerektirdikleri atıflar Adım 2'de kayıt düzeyinde doğrulanacak.
- **Atıf:** "Overture Maps Foundation" (sitede her zaman görünür) ve gerekiyorsa kaynak veri setleri.

## OpenStreetMap (Geofabrik Türkiye extract)

- **Erişim:** `https://download.geofabrik.de/europe/turkey-latest.osm.pbf` (`sources.osm.pbf_url`). Dosya boyutu indirmeden önce kontrol edilir; 2 GB'ı aşarsa proje sahibine sorulur.
- **Kullanım:**
  - idari sınırlar (`boundary=administrative`): il, ilçe, mahalle/köy. Türkiye'deki `admin_level` karşılıkları (il, ilçe, mahalle/köy) sınırların işlendiği adımda veriyle doğrulanacak.
  - işletmeler (ikincil kaynak): `config/categories.yaml` → `osm` etiketleri.
  - yol ağı (ana yola uzaklık), gündüz talebi noktaları (ofis, okul, hastane, AVM, istasyon, ticari/sanayi alanları), tedarik noktaları.
- **Lisans:** Open Database License (ODbL) 1.0. Yükümlülükler ve çıktılarımıza etkisi aşağıda, "OpenStreetMap ve ODbL" bölümünde.
- **Atıf:** "© OpenStreetMap katkıcıları", bağlantı: <https://www.openstreetmap.org/copyright> (sitede her zaman görünür).

## OpenStreetMap ve ODbL

Kodun lisansı ile verinin lisansı birbirinden ayrıdır (K-036, K-037). ODbL, OSM'den türetilen **veriyi** bağlar; kodu bağlamaz.

### ODbL'nin üç kavramı

- **Türetilmiş veritabanı:** OSM verisinden çıkarılmış, dönüştürülmüş veya başka veriyle karıştırılmış veri. Örnekler: süzülmüş sınırlar, sadeleştirilmiş poligonlar, OSM noktalarından üretilen Voronoi alanları, OSM ile eşleştirilmiş işletmeler, bunlardan hesaplanan bölge değerleri. Kamuya kullanılırsa **ODbL ile** sunulmalı ve makinece okunur biçimde erişilebilir olmalıdır (ODbL 4.4 ve 4.6).
- **Üretilmiş eser (produced work):** Veriden üretilen ama veri olarak kullanılmak üzere tasarlanmamış çıktı; tipik örneği ekranda çizilen harita görüntüsü. Yalnızca **atıf** gerektirir (ODbL 4.3). Vektör tile'lar ise içindeki nesneler geri çıkarılabildiği için görüntü değil veritabanı sayılır.
- **Toplu veritabanı (collective database):** OSM verisi ile bağımsız bir veri kümesi, birbirine karışmadan yan yana duruyorsa (ör. ayrı katmanlar), bağımsız veri ODbL'ye girmez. Aynı türden veriyi birleştirmek veya eşleştirmek ise karışım sayılır ve bütünü türetilmiş veritabanı yapar.

### Yayınlayacağımız çıktılar

| Çıktı | OSM'den türetilmiş mi? | Kapsam | Yapılacak |
|---|---|---|---|
| Ekranda çizilen harita | evet | üretilmiş eser | görünür atıf (var) |
| Sınır tile'ları (`boundaries.pmtiles`: il, ilçe, mahalle/köy, yaklaşık sınırlar) | evet: OSM sınırları ve yer noktaları | türetilmiş veritabanı → **ODbL** | ODbL ile yayınla; dosya metadata'sında atıf ve lisans |
| Bölge listeleri / gazetteer (`regions/*.json`) | evet: adlar, hiyerarşi, bbox, alanlar | türetilmiş veritabanı → **ODbL** | ODbL; dosyada `license` ve `attribution` alanları |
| İşletme tile'ları (Adım 2) | evet: OSM işletmeleri Overture ile eşleştirilir | eşleştirme karışım üretir → bütünü **ODbL** | ODbL; Overture kayıtlarının kendi atıf ve bildirim koşulları da korunur (lisansları izin verici: Apache 2.0 vb.; Adım 2'de kayıt bazında doğrulanacak) |
| Analiz JSON'ları (sayılar, oranlar, skorlar) | evet: OSM'den türetilen işletme sayıları ve sınırlarla hesaplanır | en güvenli yorumla türetilmiş veritabanı → **ODbL** | ODbL. TÜİK ve SEGE değerleri de içerdikleri için bu kaynakların koşullarıyla uyum ilk kamuya açık yayından önce kontrol edilecek (**açık konu**) |
| Altlık harita (OpenFreeMap) | evet (onların ürünü) | OpenFreeMap/OpenMapTiles koşulları | altlık atfı (var) |
| Kod (`apps/`, `pipeline/`) | hayır | ODbL dışı | tüm hakları saklı (K-036) |

### Yükümlülükler ve uygulama

1. **Atıf:** Sitede "© OpenStreetMap katkıcıları" ve telif sayfası bağlantısı her zaman görünür (var). İndirilebilen her dosyada da atıf bulunur: PMTiles metadata'sında `attribution`, JSON dosyalarında `attribution` ve `license` alanları.
2. **Lisans bildirimi:** Veri çıktılarının ODbL 1.0 altında olduğu `manifest.json`'da ve sitede belirtilir. Lisans metnine bağlantı verilir: <https://opendatacommons.org/licenses/odbl/1-0/>.
3. **Aynı lisansla paylaşım:** Türetilmiş veritabanlarına ODbL'yi daraltan ek kullanım koşulu konmaz.
4. **Teknik kısıt yok:** Dosyalar düz HTTP ile indirilebilir kalır. Şifreleme, DRM veya erişimi kısıtlayan bir önlem uygulanmaz (ODbL 4.7).
5. **Erişim:** Kamuya kullandığımız veriler sürüm klasöründe zaten herkese açıktır. Tile'lar sadeleştirildiği için yayın adımında her sürüme tam çözünürlüklü sınır dosyası da eklenir (ör. GeoParquet veya GeoPackage). Sitede bir "veri indir ve lisans" bağlantısı olur.
6. **Yerel çalışma dosyaları** (`data/`) yayımlanmadığı sürece bu yükümlülükler doğmaz. Depodaki küçük örnek veri (`apps/web/public/data-sample/`) OSM'den türetilmişse ODbL kapsamındadır ve öyle işaretlenir.

## TÜİK ADNKS (nüfus)

- **İçerik:** Adrese Dayalı Nüfus Kayıt Sistemi sonuçları; mahalle ve köy nüfusları.
- **Erişim:** MEDAS (<https://biruni.tuik.gov.tr/medas/>) üzerinden **elle** indirilir ve `data/raw/tuik/` altına konur (`paths.tuik_dir`). Otomatik indirme yoktur. Sonuçlar yılda bir yayımlanır.
- **Eşleştirme riski:** Nüfus tablolarındaki mahalle/köy adları ile OSM'deki sınır adları birebir uyuşmayabilir (yazım farkları, birleşen veya bölünen mahalleler). Eşleşmeyenler kalite günlüğüne yazılacak.
- **Lisans/atıf:** TÜİK verileri kaynak gösterilerek kullanılır. Atıf: "Kaynak: TÜİK, ADNKS (yıl)". Kullanım koşulları, nüfus verisinin işlendiği adımda ayrıca kontrol edilecek.

## SEGE (sosyoekonomik düzey)

- **İçerik:** Sanayi ve Teknoloji Bakanlığı'nın il ve ilçe sosyo-ekonomik gelişmişlik sıralaması araştırmaları (endeks değeri ve kademe).
- **Erişim:** Bakanlığın yayımladığı raporlar ve tablolar. Kullanılacak yıllar (`sources.sege.year`) ve makinece okunur tablo bulunup bulunmadığı, SEGE'nin işlendiği adımda netleşecek.
- **Not:** SEGE il ve ilçe düzeyindedir; mahalle/köylere üst birimden atanır. Aynı ilçedeki bütün mahalleler aynı değeri alır.

## OpenFreeMap (altlık harita)

- **Erişim:** `https://tiles.openfreemap.org/styles/positron`; API anahtarı gerekmez.
- **Kullanım:** yalnızca görsel altlık. Analize veri sağlamaz. Etiketler Türkçe adlarla gösterilir (K-027).
- **Atıf:** "OpenFreeMap © OpenMapTiles Data from OpenStreetMap" (sitede "Altlık" başlığı altında her zaman görünür).

## Kullanılmayan kaynaklar

| Kaynak | Gerekçe |
|---|---|
| Google Maps / Places API | Koşullar yalnızca `place_id` saklamaya izin veriyor ve içeriğin Google dışı bir haritada gösterilmesini yasaklıyor. |
| İlan sitelerinden veri kazıma | Site kullanım koşullarına aykırı; güvenilirliği ve sürekliliği belirsiz. |
| Kişisel veriler | Analiz için gerekli değil; KVKK yükümlülükleri doğurur. |

## Yayınlanan alanlar

- **İşletmeler:** yalnızca ad, kategori, marka ve konum. Ham kaynak kimlikleri, adres ayrıntıları ve iletişim bilgileri yayınlanmaz.
- **Bölge sonuçları:** sayılar, oranlar, model beklentisi, doygunluk sınıfı, skorlar, güven düzeyi, veri tarihi.

## Sitedeki atıf metni

Atıf alanı (`apps/web/src/data/attributions.ts`) her ekran boyutunda görünür:

> Altlık: OpenFreeMap · © OpenMapTiles | Veri: © OpenStreetMap katkıcıları · Overture Maps Foundation · TÜİK · SEGE

Bu dosyadaki kaynak listesi değişirse atıf alanı da güncellenmelidir.

## Örnek veri (geliştirme)

`apps/web/public/data-sample/` bir veri sürümünün yapısını taklit eder ve web uygulaması gerçek veri yokken onu okur:

- `manifest.json`: `"sample": true`. Arayüzdeki veri tarihi rozetinde "örnek" etiketi görünür.
- `v/2026-10-20/config.json`: pipeline'ın `export-web-config` komutuyla config dosyalarından üretilir. pytest, config dosyalarıyla uyumunu kontrol eder.
- `v/2026-10-20/regions.json`: 81 il ve plaka kodları; elle yazıldı. Gerçek sürümde `boundaries` komutu üretecek. Analiz verisi içermez.

## Veri kalitesi günlüğü

Bilinen sorunlar bulundukça buraya eklenir (tarih, kaynak, sorun, etki, alınan önlem).

| Tarih | Kaynak | Sorun | Etki | Önlem |
|---|---|---|---|---|
| 2026-10-20 | Overture | Kategori eşlemeleri henüz veriyle doğrulanmadı | Yanlış veya eksik kategori ataması | Adım 2'de doğrulama; o zamana kadar `verified: false` |
| 2026-10-20 | OSM + Overture | Zincir market marka listesi başlangıç düzeyinde (BİM, A101, ŞOK) | Diğer zincirler "süpermarket" veya "bakkal" sayılabilir | Adım 2'de marka sıklıklarıyla genişletme |
