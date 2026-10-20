# Karar kaydı

Mimari ve teknik kararlar burada tarih ve gerekçeyle tutulur. Bir karar değişirse eski kayıt silinmez; "Durum" alanı güncellenir ve yeni kayıt eskisine bağlanır. CLAUDE.md ile çelişen bir karar gerekiyorsa önce proje sahibine sorulur.

Kayıt biçimi: **Karar** (ne), **Gerekçe** (neden), **Sonuçlar** (neyi etkiler, neyi kabul ediyoruz).

- K-001 – K-021: proje tanımında (CLAUDE.md) verilen kararlar.
- K-022 ve sonrası: uygulama sırasında verilen kararlar.

---

## Proje tanımından gelen kararlar

### K-001 · Sunucusuz, statik mimari (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Site statiktir ve Cloudflare'de barındırılır. Kullanıcı isteğinde sunucu tarafında hesaplama yapılmaz.
- **Gerekçe:** Bir okul projesinden doğan, kamuya açık bir sitede işletme maliyeti ve bakım yükü düşük olmalı. Statik dosyalar CDN'den hızlı sunulur, ölçeklenir ve saldırı yüzeyi küçüktür. Analizler aylık veriyle önceden hesaplanabildiği için anlık sunucu hesabına ihtiyaç yok.
- **Sonuçlar:** Etkileşimli her şey tarayıcıda olur. Kullanıcıya özel hesap gerektiren özellikler (K-009) ve serbest alan analizi (K-008) bu mimarinin dışında kalır.

### K-002 · Harita verisi PMTiles olarak R2'de (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Vektör tile'lar tek dosyalık PMTiles arşivleri olarak Cloudflare R2'de tutulur. MapLibre, `pmtiles://` protokolüyle dosyanın yalnızca gereken bayt aralıklarını (HTTP Range) okur.
- **Gerekçe:** Tile sunucusu gerektirmez. Tek dosya yüklemek ve sürümlemek kolaydır. R2'de dışa veri aktarım ücreti yoktur.
- **Sonuçlar:** R2 kovası Range isteklerine ve CORS'a göre ayarlanmalı (Cloudflare kurulum adımı).

### K-003 · Analiz sonuçları önceden hesaplanır (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Bölge bazındaki sonuçlar küçük JSON dosyaları olarak R2'de yayınlanır.
- **Gerekçe:** K-001 ile uyumlu. Tarayıcı yalnızca seçilen bölgenin dosyasını indirir.
- **Sonuçlar:** Önceden tanımlı olmayan alanlar (ör. kullanıcının çizdiği alan) bu yolla analiz edilemez; bkz. K-008.

### K-004 · Python pipeline, GitHub Actions'ta aylık (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Veri pipeline'ı Python ile yazılır, GitHub Actions'ta ayda bir çalışır ve çıktıları R2'ye yükler.
- **Gerekçe:** Overture aylık sürüm yayımlar. Actions, public depolarda ücretsizdir ve tekrarlanabilir bir Linux ortamı sağlar.
- **Sonuçlar:** Pipeline'ın standart bir Actions makinesinin disk, bellek ve süre sınırlarına sığması gerekir. Bu sınırlar ilk veri adımlarında ölçülecek.

### K-005 · Sürümlü yayın ve atomik geçiş (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Her veri yenilemesi `/v/YYYY-MM-DD/` altında yayımlanır. `manifest.json` en güncel sürümü gösterir ve en son yazılır. Önceki sürüme dönmek için manifest yeniden yazılır.
- **Gerekçe:** Yarım kalmış bir yükleme siteyi bozmaz. Sürüm klasörlerindeki dosyalar değişmediği için uzun süre önbelleğe alınabilir.
- **Sonuçlar:** Manifest kısa süreli, sürüm dosyaları uzun süreli (immutable) önbellekle sunulur. Manifest biçimi için bkz. K-030.

### K-006 · R2'de son iki sürüm, eskiler Google Drive'da (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı); arşivleme Adım 8'de kurulacak
- **Karar:** R2'de canlı olarak yalnızca son iki sürüm tutulur. Daha eskiler Google Drive'a arşivlenir.
- **Gerekçe:** Depolama maliyetini sınırlar. Bir önceki sürüm canlıda kaldığı için geri dönüş anında yapılabilir.
- **Sonuçlar:** `config/settings.yaml` içindeki `publish.keep_live_versions` en az 2 olmalı; doğrulama bunu zorunlu kılar.

### K-007 · Canlıda kendi alan adı, r2.dev yalnızca geliştirme (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Canlı yayında R2'ye kendi alan adımız üzerinden erişilir. `r2.dev` adresi yalnızca geliştirme içindir.
- **Gerekçe:** `r2.dev` hız sınırlıdır ve Cloudflare önbelleği ile özel kurallar orada kullanılamaz.
- **Sonuçlar:** Web uygulaması veri adresini `VITE_DATA_BASE_URL` ortam değişkeninden alır.

### K-008 · Serbest alan analizi v2'de (2026-10-20)
- **Durum:** Ertelendi (proje tanımı)
- **Karar:** Kullanıcının çizdiği alan veya yarıçap için analiz v2 kapsamındadır. DuckDB-WASM veya bir Cloudflare Worker ile değerlendirilecek.
- **Gerekçe:** Önce önceden hesaplanmış idari birimler ve H3 hücreleriyle çalışan bir ürün çıkarmak.

### K-009 · Sunucu tarafı gerekirse Workers + D1 (2026-10-20)
- **Durum:** Ertelendi (proje tanımı)
- **Karar:** Kullanıcı hesabı veya kayıtlı raporlar gerekirse Cloudflare Workers + D1 değerlendirilir; şimdi kurulmaz.

### K-010 · Web teknoloji yığını (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Vite + React + TypeScript (strict), Tailwind CSS, shadcn/ui, MapLibre GL JS, pmtiles, Zustand (filtre durumu), TanStack Query, Recharts. ESLint + Prettier. Birim testleri Vitest, uçtan uca testler Playwright.
- **Gerekçe:** Yaygın, iyi belgelenmiş, açık kaynak araçlar. MapLibre açık kaynaklıdır ve PMTiles'ı protokol eklentisiyle doğrudan okur.

### K-011 · Harita altlığı OpenFreeMap (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Altlık harita OpenFreeMap'ten gelir. İleride Türkiye'ye özel bir Protomaps altlığı R2'de barındırılabilir.
- **Gerekçe:** API anahtarı ve kullanım ücreti yoktur; OpenStreetMap tabanlıdır.
- **Sonuçlar:** Harici bir hizmete bağımlıyız. Hizmet erişilemezse altlık görünmez ama veri katmanları çalışır. Kendi altlığımızı barındırma seçeneği açık.

### K-012 · Pipeline teknoloji yığını (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Python 3.12, uv, DuckDB (spatial, httpfs, h3), geopandas, shapely, pydantic (config doğrulama), statsmodels, PySAL (libpysal, esda, spreg). Ruff ve pytest.
- **Gerekçe:** DuckDB, Overture GeoParquet dosyalarını uzaktan ve yalnızca gereken satırlarla okur. statsmodels ve PySAL, sayım modelleri ve mekânsal ekonometri için standart araçlardır.

### K-013 · Tile üretimi tippecanoe + pmtiles CLI (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Tile'lar tippecanoe ve pmtiles CLI ile, GitHub Actions'ta (Linux) üretilir. Windows'ta yerel üretim gerekirse WSL kullanılır.
- **Gerekçe:** tippecanoe'nun Windows için resmî derlemesi yoktur.

### K-014 · Monorepo, public GitHub, GitHub Actions (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Tek depo (`apps/web`, `pipeline`, `config`, `docs`), GitHub'da public. Test, veri yenileme ve yayın GitHub Actions ile yapılır.
- **Gerekçe:** Web ve pipeline aynı veri sözleşmesini paylaşır; tek depoda birlikte değişir ve birlikte test edilir.
- **Sonuçlar:** Gizli bilgiler asla depoya girmez; CI'da GitHub Secrets kullanılır.

### K-015 · İşletme verisi: Overture birincil, OSM ikincil (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Birincil kaynak Overture Maps Places (aylık). Türkiye alt kümesi DuckDB ile doğrudan GeoParquet'ten okunur; dünyanın tamamı indirilmez. Kategoriler `basic_category` ve `taxonomy` alanlarından alınır (eski `categories` alanı kullanımdan kaldırıldı). `confidence`, `operating_status`, `sources` ve `brand` saklanır. İkincil kaynak OpenStreetMap'tir (Geofabrik Türkiye .osm.pbf). İki kaynak mesafe, Türkçe normalize edilmiş ad benzerliği ve kategori uyumuyla eşleştirilir; her işletme için hangi kaynaklarda bulunduğu ve bir güven skoru tutulur.
- **Gerekçe:** İki bağımsız kaynağın birleşimi kapsamı artırır; iki kaynakta birden bulunmak güvenilirlik göstergesidir.

### K-016 · Nüfus TÜİK ADNKS, sosyoekonomik düzey SEGE (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Mahalle/köy nüfusları TÜİK ADNKS'den alınır (yıllık; MEDAS'tan elle indirilip `data/raw/tuik/` altına konur). Sosyoekonomik düzey için il/ilçe SEGE kullanılır.
- **Gerekçe:** Mahalle/köy düzeyinde resmî ve kamuya açık tek nüfus kaynağı ADNKS'dir.
- **Sonuçlar:** Nüfus dosyalarının otomatik indirilmesi yoktur; yıllık güncellemede elle indirme gerekir.

### K-017 · Kullanılmayan kaynaklar (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Google Maps/Places, ilan sitelerinden veri kazıma ve kişisel veriler kullanılmaz.
- **Gerekçe:** Google'ın koşulları yalnızca `place_id` saklamaya izin veriyor ve verinin Google dışı bir haritada gösterilmesini yasaklıyor. Kazıma site koşullarına aykırıdır. Kişisel veri işlemek KVKK yükümlülükleri doğurur ve analiz için gerekli değildir.

### K-018 · Lisans, atıf ve yayınlanan alanlar (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** OSM verisi ODbL, Overture verisi kayıt bazında lisanslıdır (Foursquare kaynaklı kayıtlar Apache 2.0). Atıflar sitede her zaman görünür ve `docs/data_sources.md`'de listelenir. İşletmelerden yalnızca analize gereken alanlar (ad, kategori, marka, konum) yayınlanır.
- **Sonuçlar:** OSM'den türetilen ve yayınlanan veritabanları ODbL'nin "aynı lisansla paylaş" koşuluna tabidir; ayrıntılar `docs/data_sources.md`'de.

### K-019 · Coğrafi birimler ve H3 (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** Birimler il (81), ilçe, mahalle ve köydür; OSM `admin_level` karşılıkları veriyle doğrulanır. Sınırı OSM'de olmayan mahalle/köyler için ilçe sınırı içinde Voronoi ile yaklaşık sınır üretilir ve arayüzde "yaklaşık sınır" olarak işaretlenir. OSB ve serbest bölge gibi özel bölgeler işaretlenir ve ikamet nüfusuna dayalı modelden ayrı tutulur; içlerindeki işletmeler korunur. H3 altıgen ızgarası, yoğunluk katmanları ve idari sınırlardan bağımsız (MAUP'a dayanıklı) analiz için kullanılır.

### K-020 · Kategoriler config dosyasında (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı)
- **Karar:** İşletme kategorileri `config/categories.yaml` dosyasındadır; her kategori için OSM etiketleri ve Overture kategorileri yan yana tutulur. Başlangıçta 23 kategori var. Zincir marketler (BİM, A101, ŞOK vb.) marka bilgisiyle ayrılır, bakkal kategorisi zincirleri dışarıda bırakır.

### K-021 · Analiz yöntemi (2026-10-20)
- **Durum:** Kabul edildi (proje tanımı); ayrıntılar `docs/methodology.md`'de
- **Karar:** Göstergeler (10.000 kişiye düşen, km² başına, LQ); mahalle/köy düzeyinde Poisson ve negatif binom beklenen sayı modeli (aşırı yayılım testiyle seçim); Pearson artığından doygunluk sınıfları; Moran's I ve gerekirse mekânsal gecikme/hata modelleri; 0-100 tedarik ve erişilebilirlik skoru; ağırlıklı fırsat skoru; her sonuçla veri güven düzeyi. Eşikler ve ağırlıklar `config/settings.yaml`'dadır.

---

## Adım 0'da verilen uygulama kararları

### K-022 · Çalışma ortamı: Node 24 LTS + npm, uv ile Python 3.12 (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** Web için Node.js 24 LTS ve npm kullanılır (`apps/web/.nvmrc`, `engines.node >= 24`). Python sürümü uv ile yönetilir: `requires-python = ">=3.12,<3.13"` ve `pipeline/.python-version`.
- **Gerekçe:** npm Node ile birlikte gelir, ek araç gerektirmez. uv, sistem geneline Python kurmadan proje içinde Python 3.12 sağlar.

### K-023 · TypeScript 6.0 hattında kalınması (2026-10-20)
- **Durum:** Kabul edildi; yeniden değerlendirilecek
- **Karar:** TypeScript `~6.0` kullanılır, 7.0'a geçilmez.
- **Gerekçe:** TypeScript 7 (Go ile yazılmış yeni derleyici) yayımlandı, ancak typescript-eslint şu an yalnızca `<6.1` sürümlerini destekliyor. Tip bilgili ESLint kuralları için 6.0 gerekli.
- **Sonuçlar:** typescript-eslint TS 7 desteğini duyurduğunda yükseltilecek.

### K-024 · Linter olarak ESLint (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** create-vite 9 varsayılan olarak Oxlint öneriyor; proje tanımına uygun olarak ESLint seçildi. Tip bilgili kurallar (`recommendedTypeChecked`), React Hooks ve React Refresh kuralları açık; biçim kuralları Prettier'a bırakıldı (`eslint-config-prettier`).

### K-025 · shadcn/ui ayarları (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** shadcn/ui Radix tabanıyla ve "nova" ön ayarıyla (kompakt yerleşim) kuruldu. Yazı tipi Geist, npm paketinden gelir (harici yazı tipi isteği yok).
- **Gerekçe:** Harita arayüzünde panel alanı dar olduğu için kompakt bileşenler uygun. Geist'in latin-ext alt kümesi Türkçe karakterleri (ğ, ş, ı, İ) kapsıyor.

### K-026 · MapLibre 6 kurulumu (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** MapLibre GL JS 6 kullanılır: yalnızca ESM, WebGL2 zorunlu. Vite ile `setWorkerUrl()` çağrısı ve `?worker&url` içe aktarımı gerekir (`apps/web/src/map/maplibre.ts`). pmtiles protokolü uygulama açılırken bir kez kaydedilir. WebGL2 desteklenmiyorsa kullanıcıya Türkçe bir hata mesajı gösterilir.
- **Sonuçlar:** WebGL2 desteklemeyen çok eski tarayıcılarda harita açılmaz; bu kabul edildi.

### K-027 · Altlık stili ve Türkçe etiketler (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** OpenFreeMap "positron" stili kullanılır. Yer adı etiketleri `name:tr` → `name:latin` → `name` sırasıyla Türkçeleştirilir (`apps/web/src/map/labels.ts`).
- **Gerekçe:** Açık renkli, düşük kontrastlı bir altlık skor haritalarını okunur kılar. Varsayılan stil İngilizce adları ve yerel alfabeyi gösteriyor ("Turkey", "Syria سوريا"); Türkçe arayüzle uyumsuz.

### K-028 · Durumun URL'de tutulması (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** Filtreler sorgu dizesinde tutulur: `cat` (virgülle ayrılmış kategori kimlikleri), `metric`, `region`, `mode`. Varsayılan değerler yazılmaz; geçersiz değerler yok sayılır ve URL'den temizlenir. Değişiklikler `history.replaceState` ile yazılır. Harita konumu MapLibre'nin yönettiği hash'te durur (`#map=zoom/enlem/boylam`).
- **Gerekçe:** Her görünüm link olarak paylaşılabilir. replaceState, her tıklamanın geri tuşu geçmişini doldurmasını engeller.

### K-029 · Veri sözleşmesi: manifest.json, config.json, regions.json (2026-10-20)
- **Durum:** Kabul edildi (şema sürümü 1)
- **Karar:** `manifest.json` canlı sürümleri ve `latest`'i listeler. Her sürüm klasöründe web için şu dosyalar bulunur: `config.json` (kategoriler, gruplar, yakınlaştırma bantları; pipeline'ın `export-web-config` komutu YAML'dan üretir) ve `regions.json` (aranabilir bölge listesi). Aynı kurallar iki tarafta doğrulanır: pipeline'da pydantic (`manifest.py`), web'de TypeScript (`src/data/*.ts`). pytest, web'deki örnek verinin bu sözleşmeye ve config dosyalarına uyduğunu kontrol eder. Kimlikler İngilizce (`pharmacy`), görünen adlar Türkçedir ("Eczane").
- **Gerekçe:** Web asla YAML okumaz. Kategoriler ve bantlar, birlikte üretildikleri veriyle aynı sürüm klasöründe durduğu için birbirleriyle hep uyumludur.
- **Sonuçlar:** Şemayı değiştiren her değişiklik `schema_version`'ı artırmalı ve iki tarafı birlikte güncellemelidir.

### K-030 · Yakınlaştırma bantları (2026-10-20)
- **Durum:** Kabul edildi (başlangıç değerleri)
- **Karar:** Bantlar `config/settings.yaml` içindeki `map.zoom_bands` alanındadır: 0-9 "Türkiye / il ölçeği", 9-14 "İlçe ölçeği", 14 ve üstü "Sokak ölçeği". Web arayüzü ve tile üretimi aynı değerleri kullanır.
- **Gerekçe:** Proje tanımı nokta katmanının yaklaşık 14'te başladığını belirtiyor. Bir ilçe tipik olarak 9-11 yakınlıkta ekrana sığıyor.

### K-031 · Pipeline CLI: Typer; henüz yazılmamış komutlar hata koduyla döner (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** CLI Typer ile yazıldı (`haritanaliz <komut>`). `boundaries`, `pois`, `population`, `analyze`, `tiles`, `publish` henüz uygulanmadı; çalıştırılınca "not implemented yet" yazar ve 1 koduyla çıkar. Çalışan yardımcı komutlar: `validate-config`, `export-web-config`.
- **Gerekçe:** Boş bir komutun "başarılı" görünmesi, ileride bir iş akışında hiçbir şey yapılmadığı hâlde başarı raporlanmasına yol açabilir.

### K-032 · Pipeline bağımlılıkları şimdiden kuruldu (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** K-012'deki bütün kütüphaneler (DuckDB, geopandas, shapely, statsmodels, libpysal, esda, spreg) Adım 0'da `pyproject.toml`'a eklendi ve `uv.lock` ile sabitlendi. Bir içe aktarma testi, kütüphanelerin hem Windows'ta hem CI'da (Linux) yüklendiğini doğrular.
- **Gerekçe:** Platform veya sürüm uyumsuzlukları veri işine başlamadan önce ortaya çıksın.

### K-033 · Mobilde modal olmayan bottom sheet (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** Mobilde (768 px altı) filtreler, haritanın altında 56 px'lik özet satırıyla duran ve dokununca ekranın %75'ine açılan özel bir panelde yer alır. Panel modal değildir; harita açıkken kullanılabilir kalır. Masaüstünde filtreler, açılıp kapanan bir yan paneldedir.
- **Gerekçe:** Harita uygulamalarında alışılmış davranış budur. shadcn'in Drawer bileşeni (vaul) modal bir diyalog olarak tasarlanmış.
- **Sonuçlar:** Sürükleyerek açma-kapama sonraki bir adımda eklenecek.

### K-034 · Uçtan uca testler ve CI kapsamı (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** Playwright testleri masaüstü (1440×900) ve mobil (Pixel 7) profilleriyle çalışır. Yerelde, tarayıcı indirmeden kurulu Microsoft Edge kullanılabilir (`PW_CHANNEL=msedge`). CI şimdilik web için lint, biçim, birim testi ve build; pipeline için ruff ve pytest çalıştırır. Uçtan uca testler CI'a sonra eklenecek.
- **Gerekçe:** Adım 0'da istenen CI kapsamı bu. Uçtan uca testler dış hizmete (OpenFreeMap) bağlı ve CI'da tarayıcı kurulumu gerektiriyor.

### K-035 · Satır sonları LF (2026-10-20)
- **Durum:** Kabul edildi
- **Karar:** `.gitattributes` ile depoda ve çalışma kopyasında LF kullanılır (`* text=auto eol=lf`); yalnızca `.ps1`, `.bat` ve `.cmd` dosyaları CRLF'tir. `.editorconfig` aynı kuralı editörlere bildirir.
- **Gerekçe:** Git for Windows varsayılan olarak `core.autocrlf=true` kullanır. Linux CI, Prettier ve Ruff ise LF bekler; tek kural, her commit'te satır sonu farkı oluşmasını engeller.
