# haritanaliz

## Amaç
Türkiye geneli için harita tabanlı bölgesel işletme analizi sitesi. Ekonometri okul projesi olarak başladı, kamuya açık bir site olarak tasarlanıyor. Kullanıcı haritada gezinir veya il / ilçe / mahalle / köy seçer, işletme türlerini filtreler. Site, bölgedeki işletme arzını nüfus, nüfus yoğunluğu, sosyoekonomik düzey, gündüz talebi ve tedarik/ulaşım koşullarıyla karşılaştırır; hangi işletme türünün fazla, hangisinin eksik olduğunu gösterir.

## Kullanıcı deneyimi
- Açılışta Türkiye haritası; serbest yakınlaştırma ve kaydırma.
- Yakınlaştırmaya göre katmanlar:
  - Türkiye / il ölçeği: il ve ilçe bazında skor haritası (choropleth)
  - İlçe ölçeği: mahalle/köy skor haritası ve H3 altıgen yoğunluk katmanı
  - Sokak ölçeği (yaklaşık zoom 14 ve üstü): filtrelenen işletme türlerinin tek tek noktaları
- Filtreler: işletme türü (çoklu seçim), gösterilecek ölçü (sayı, 10.000 kişiye düşen, doygunluk, fırsat), bölge seçimi (il → ilçe → mahalle/köy, aramalı).
- Bölge seçilince analiz paneli: kategori bazında doygunluk tablosu, grafikler, kısa Türkçe yorum, veri güven düzeyi, veri tarihi.
- Mod 2: işletme türü seçilir, seçili alandaki en fırsatlı mahalleler sıralanır.
- Mobil öncelikli tasarım: mobilde filtreler alttan açılan panel (bottom sheet).
- Seçimler URL'de tutulur, linkle paylaşılabilir.
- Arayüz Türkçe; veri atıfları her zaman görünür.

## Mimari (sunucusuz)
- Site statiktir ve Cloudflare'de barındırılır; kullanıcı isteğinde sunucu tarafı hesaplama yoktur.
- Harita verisi PMTiles (vektör tile) olarak Cloudflare R2'de tutulur; MapLibre, pmtiles protokolüyle dosyanın yalnızca gereken parçalarını okur.
- Analiz sonuçları önceden hesaplanır ve bölge bazında küçük JSON dosyaları olarak R2'de tutulur.
- Veri pipeline'ı Python ile yazılır, GitHub Actions'ta aylık çalışır, çıktıları R2'ye yükler.
- Sürümleme: her veri yenilemesi /v/YYYY-MM-DD/ altında yayınlanır; manifest.json en güncel sürümü gösterir. Geçiş atomiktir, gerekirse önceki sürüme dönülebilir.
- R2'de canlı yalnızca son iki sürüm tutulur; eski sürümler Google Drive'a arşivlenir (Adım 8'de kurulacak).
- Canlı yayında R2'ye kendi alan adı üzerinden erişilir; r2.dev adresi yalnızca geliştirme içindir.
- Kullanıcının çizdiği alan veya yarıçap için serbest analiz v2 kapsamındadır (DuckDB-WASM veya Cloudflare Worker ile değerlendirilecek).
- İleride sunucu tarafı gerekirse (kullanıcı hesabı, kayıtlı raporlar) Cloudflare Workers + D1 değerlendirilir; şimdi kurulmaz.

## Teknoloji
- Web: Vite + React + TypeScript (strict), Tailwind CSS, shadcn/ui, MapLibre GL JS, pmtiles, Zustand (filtre durumu), TanStack Query, Recharts. ESLint + Prettier. Vitest; uçtan uca testler için Playwright.
- Harita altlığı: OpenFreeMap. İleride Türkiye'ye özel bir Protomaps altlığını R2'de kendimiz barındırabiliriz.
- Pipeline: Python 3.12, uv, DuckDB (spatial, httpfs, h3), geopandas, shapely, pydantic (config doğrulama), statsmodels, PySAL (libpysal, esda, spreg). Ruff, pytest.
- Tile üretimi: tippecanoe ve pmtiles CLI. GitHub Actions'ta (Linux) çalışır; Windows'ta yerel çalıştırmak gerekirse WSL kullanılır.
- CI/CD: GitHub Actions (test, veri yenileme, yayın). Depo tek bir monorepo, GitHub'da public.

## Veri kaynakları
- İşletmeler (birincil): Overture Maps Places, aylık sürüm. Türkiye alt kümesi DuckDB ile doğrudan GeoParquet'ten okunur, tüm dünya indirilmez. Kategoriler için basic_category ve taxonomy alanları kullanılır (eski categories alanı kullanımdan kaldırıldı). confidence, operating_status, sources ve brand saklanır.
- İşletmeler (ikincil), idari sınırlar, yollar, tedarik ve talep noktaları: OpenStreetMap, Geofabrik Türkiye .osm.pbf dosyası.
- İki kaynak mesafe, Türkçe normalize edilmiş ad benzerliği ve kategori uyumuyla eşleştirilir; her işletmenin hangi kaynaklarda bulunduğu ve bir güven skoru tutulur.
- Nüfus: TÜİK ADNKS mahalle/köy nüfusları (yıllık; MEDAS'tan elle indirilip data/raw/tuik/ altına konur).
- Sosyoekonomik: SEGE (il/ilçe).
- Kullanılmayanlar: Google Maps/Places (koşullar yalnızca place_id saklamaya izin veriyor ve Google dışı haritada gösterimi yasaklıyor), ilan sitelerinden veri kazıma, kişisel veriler.
- Lisans ve atıf: OSM (ODbL), Overture (kayıt bazında lisans; Foursquare kaynaklı kayıtlar Apache 2.0). Atıflar sitede ve docs/data_sources.md'de.
- İşletmelerden yalnızca analize gereken alanlar (ad, kategori, marka, konum) yayınlanır.

## Coğrafi birimler
- İl (81), ilçe, mahalle ve köy. Türkiye'deki admin_level karşılıkları veriyle doğrulanır.
- Sınırı OSM'de bulunmayan mahalle/köyler için ilçe sınırı içinde Voronoi ile yaklaşık sınır üretilir ve arayüzde "yaklaşık sınır" olarak işaretlenir.
- OSB, serbest bölge gibi özel bölgeler işaretlenir ve ikamet nüfusuna dayalı modelden ayrı tutulur; içlerindeki işletmeler korunur.
- H3 altıgen ızgarası, yoğunluk katmanları ve idari sınırlardan bağımsız (MAUP'a dayanıklı) analiz için kullanılır.

## İşletme kategorileri
config/categories.yaml dosyasında, her kategori için OSM etiketleri ve Overture kategorileri yan yana tutulur. Başlangıç (23 kategori): restoran, kafe, fast food, pastane, fırın, süpermarket, zincir market (BİM, A101, ŞOK vb.; marka bilgisiyle ayrılır), bakkal (zincirler hariç), kasap, manav, eczane, kuaför/berber, oto yedek parça, oto tamir, akaryakıt istasyonu, giyim, elektronik, cep telefonu, beyaz eşya, kırtasiye, spor salonu, veteriner, diş kliniği.

## Analiz yöntemi (özet; ayrıntılar docs/methodology.md'de)
1. Göstergeler: 10.000 kişiye düşen işletme, km² başına işletme, lokasyon katsayısı (LQ).
2. Beklenen sayı modeli: mahalle/köy düzeyinde Poisson ve negatif binom regresyonu (aşırı yayılım testiyle seçim). Açıklayıcılar: log nüfus, yoğunluk, sosyoekonomik düzey, gündüz talebi göstergeleri (ofis, okul, hastane, AVM, istasyon, ticari ve sanayi alanları), ana yola ve merkeze uzaklık, kentsel/kırsal ayrımı, il sabit etkileri.
3. Doygunluk skoru: Pearson artığından fazla / dengeli / eksik sınıfları (eşikler config'te).
4. Mekânsal analiz: Moran's I; gerekirse spatial lag ve spatial error modelleri.
5. Tedarik ve erişilebilirlik skoru (0-100).
6. Fırsat skoru: eksiklik, erişilebilirlik ve talebin ağırlıklı birleşimi (ağırlıklar config'te).
7. Her sonuçla birlikte veri güven düzeyi gösterilir.

## Klasör yapısı
- CLAUDE.md, README.md
- apps/web/ — site
- pipeline/ — Python veri ve analiz paketi
- config/ — categories.yaml, settings.yaml
- docs/ — architecture.md, decisions.md (karar kaydı), methodology.md, data_sources.md, progress.md
- .github/workflows/ — CI, veri yenileme, yayın
- data/ — yerel önbellek, git'e eklenmez

## Çalışma kuralları
- Her adımın sonunda: testleri çalıştır, docs/progress.md'yi güncelle, anlamlı bir commit at ve GitHub'a push et.
- Mimari kararlar docs/decisions.md'ye tarih ve gerekçeyle yazılır. Bu dosyayla çelişen bir karar gerekiyorsa önce bana sor.
- Veri kalitesi sorunları gizlenmez; data_sources.md'de ve arayüzde güven düzeyiyle gösterilir.
- Gizli bilgiler (.env, API anahtarları) git'e girmez; CI'da GitHub Secrets kullanılır.
- Sistem geneline kurulumdan, 2 GB'ı aşan indirmelerden ve ücretli servis işlemlerinden önce bana sor.
- Kod ve kod yorumları İngilizce; arayüz ve belgeler Türkçe.
- Kullanıcı Windows kullanıyor; yerel komutlar PowerShell uyumlu olmalı.
