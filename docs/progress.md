# İlerleme günlüğü

Her adımın sonunda güncellenir: ne yapıldı, nasıl doğrulandı, ne açık kaldı, sonraki adım için ne gerekiyor.

---

## Adım 0: Kurulum ve iskelet (2026-10-20)

**Durum:** Tamamlandı. GitHub'a push ve CI kontrolü, GitHub CLI girişi yapıldıktan sonra kaydedilecek.

### Ortam

| Araç | Sürüm | Not |
|---|---|---|
| Çalışma klasörü | `C:\Projeler\haritanaliz` | OneDrive dışında olduğu doğrulandı |
| Node.js / npm | 24.20.0 (LTS) / 11.19.0 | kuruluydu |
| Git | 2.55.0 | kuruluydu; bu depoda yazar `ayaz9v <150811499+ayaz9v@users.noreply.github.com>` |
| uv / Python | 0.13.1 / 3.12.15 | Python'u uv yönetiyor; sistem geneline Python kurulmadı |
| GitHub CLI | 2.102.0 | onayla winget ile kuruldu |

### Yapılanlar

**Depo**
- `git init` (dal: `main`). `.gitignore`: `data/`, `.env*`, derleme ve önbellek klasörleri. `.gitattributes`: LF satır sonu, Windows betikleri CRLF, ikili dosyalar. `.editorconfig`.

**Web (`apps/web`)**
- Vite 8.3 + React 19.3 + TypeScript 6.0 (strict, `noUncheckedIndexedAccess`), Tailwind CSS 4.3, shadcn/ui (Radix, "nova"), MapLibre GL JS 6.15, pmtiles 4.5, Zustand 5, TanStack Query 5, Recharts 3 (kuruldu, henüz kullanılmıyor), ESLint 10 (tip bilgili kurallar) + Prettier, Vitest 5, Playwright 1.64.
- Harita: açılışta Türkiye'nin tamamı (`fitBounds`), serbest yakınlaştırma/kaydırma, `pmtiles://` protokolü kayıtlı, OpenFreeMap "positron" altlığı, Türkçe yer adı etiketleri, Türkçe kontrol metinleri, "Türkiye'nin tamamı" düğmesi, ölçek çubuğu. Harita konumu URL hash'inde (`#map=z/enlem/boylam`). WebGL2 yoksa Türkçe hata mesajı.
- Üst bar ("haritanaliz"), Türkçe karakterlere duyarsız bölge arama kutusu (örnek veride 81 il), veri tarihi rozeti (`manifest.json`'dan okunur, örnek veride "örnek" etiketli), her zaman görünen atıf alanı, yakınlık bandı göstergesi.
- Filtre paneli iskeleti: mod (bölge analizi / fırsat arama), seçili bölge, gösterilecek ölçü (sayı, 10.000 kişiye düşen, doygunluk, fırsat), gruplu 23 işletme türü (fırsat modunda tek seçim), analiz paneli yer tutucusu. Masaüstünde açılır-kapanır yan panel; mobilde modal olmayan bottom sheet.
- Zustand filtre store'u ve URL eşitlemesi (`?cat=…&metric=…&region=…&mode=…`). Geçersiz parametreler yok sayılır ve temizlenir; geri/ileri gezinme desteklenir.
- Örnek veri sürümü: `public/data-sample/` (`manifest.json`, `v/2026-10-20/config.json`, `v/2026-10-20/regions.json`).

**Pipeline (`pipeline`)**
- uv paketi `haritanaliz` (Python 3.12). Bağımlılıklar: pydantic, PyYAML, Typer, DuckDB 1.5, geopandas 1.2, shapely 2.2, statsmodels 0.15, libpysal 4.15, esda 2.10, spreg 1.9; geliştirme için pytest 9, Ruff 0.17. Sürümler `uv.lock` ile sabit.
- CLI: `validate-config`, `export-web-config` çalışıyor. `boundaries`, `pois`, `population`, `analyze`, `tiles`, `publish` yer tutucu; çalıştırılınca "not implemented yet" yazar ve 1 koduyla çıkar (K-031).
- pydantic modelleri: `settings.yaml` (bbox, yollar, kaynaklar, eşleştirme, H3, analiz eşikleri ve ağırlıkları, yakınlaştırma bantları, yayın ayarları) ve `categories.yaml` (gruplar, marka kümeleri, kategoriler). Bilinmeyen anahtarlar hata verir.
- `manifest.json` sözleşmesi (`manifest.py`), web için `config.json` üretimi (`webconfig.py`).

**Config**
- `config/settings.yaml`: eşikler, skor ağırlıkları, yakınlaştırma bantları, R2 ve arşiv için yer tutucular.
- `config/categories.yaml`: 6 grupta 23 kategori. OSM etiketleri dolu. Overture eşlemeleri aday değerler ve `verified: false` (Adım 2'de doğrulanacak). Zincir market ayrımı için `discount_chains` marka kümesi (BİM, A101, ŞOK).

**CI ve belgeler**
- `.github/workflows/ci.yml`: her push ve PR'da web (ESLint, Prettier, Vitest, build) ve pipeline (ruff check, ruff format --check, pytest).
- `CLAUDE.md` (proje tanımı, aynen), `README.md`, `docs/architecture.md` (Mermaid diyagramları), `docs/decisions.md` (K-001…K-035), `docs/methodology.md` (taslak), `docs/data_sources.md`.

### Doğrulama (yerel, 2026-10-20)

| Kontrol | Sonuç |
|---|---|
| Pipeline: `ruff check`, `ruff format --check` | temiz |
| Pipeline: `pytest` | 50 test geçti (config kuralları, CLI, veri sözleşmesi, bağımlılıkların yüklenmesi) |
| Web: `tsc -b`, `eslint`, `prettier --check` | temiz |
| Web: `vitest run` | 35 test geçti (Türkçe arama, manifest, config, URL eşitleme, store, kategori filtresi, Türkçe etiketler) |
| Web: `npm run build` | başarılı; uygulama kodu 13 kB, React 68 kB, MapLibre 294 kB (gzip) |
| Uçtan uca: Playwright, headless Edge | 8 test geçti: masaüstü 1440×900 ve mobil Pixel 7 (harita açılışı, veri tarihi, atıf, URL'de filtre, bölge arama, sayfa hatası yok) |
| Ekran görüntüleri | masaüstü ve mobil; açılış, arama ve filtre durumları gözle kontrol edildi |
| GitHub CI | push sonrasında |

### Açık konular ve bilinen sınırlamalar

- Overture kategori eşlemeleri ve zincir market marka listesi veriyle doğrulanmadı (Adım 2).
- Bölge araması örnek veride yalnızca 81 il içeriyor; seçilen bölgeye harita henüz yakınlaşmıyor (sınır verisi gelince eklenecek).
- Bottom sheet dokunarak açılıp kapanıyor; sürükleme hareketi yok.
- Fırsat modunda tek tür seçimi onay kutularıyla yapılıyor; ileride radyo düğmesine çevrilebilir.
- Uçtan uca testler CI'da çalışmıyor (K-034).
- ODbL "aynı lisansla paylaş" yükümlülüğünün yayınlanan veriye etkisi değerlendirilecek (bkz. `docs/data_sources.md`).
- Kod lisansı seçilmedi.
- typescript-eslint TypeScript 7'yi desteklediğinde TS 7'ye geçilecek (K-023).

### Sonraki adım için gerekenler

- TÜİK ADNKS mahalle/köy nüfus dosyalarının MEDAS'tan indirilip `data/raw/tuik/` altına konması.
- Geofabrik Türkiye OSM extract'ının indirilmesi (boyutu indirmeden önce kontrol edilecek).
