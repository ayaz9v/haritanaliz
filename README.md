# haritanaliz

[![CI](https://github.com/ayaz9v/haritanaliz/actions/workflows/ci.yml/badge.svg)](https://github.com/ayaz9v/haritanaliz/actions/workflows/ci.yml)

Türkiye geneli için harita tabanlı bölgesel işletme analizi. Site, bir bölgedeki işletme arzını nüfus, nüfus yoğunluğu, sosyoekonomik düzey, gündüz talebi ve tedarik/ulaşım koşullarıyla karşılaştırır; hangi işletme türünün fazla, hangisinin eksik olduğunu gösterir. Ekonometri okul projesi olarak başladı, kamuya açık bir site olarak tasarlanıyor.

> **Durum: Adım 0 (kurulum ve iskelet).** Harita arayüzü, filtreler ve pipeline iskeleti hazır. Gerçek veri ve analiz henüz yok; arayüz örnek veriyle çalışıyor ve bunu "örnek" etiketiyle belirtiyor. Ayrıntılar: [docs/progress.md](docs/progress.md).

## Klasörler

| Klasör | İçerik |
|---|---|
| [`apps/web/`](apps/web) | statik site: Vite, React, TypeScript, Tailwind, shadcn/ui, MapLibre, pmtiles |
| [`pipeline/`](pipeline) | Python veri ve analiz paketi (`haritanaliz` komutu) |
| [`config/`](config) | `settings.yaml` (eşikler, ağırlıklar, yollar), `categories.yaml` (23 işletme kategorisi) |
| [`docs/`](docs) | mimari, karar kaydı, yöntem, veri kaynakları, ilerleme |
| `data/` | yerel veri önbelleği; git'e eklenmez |

## Gereksinimler

- [Node.js](https://nodejs.org) 24 LTS (npm ile birlikte gelir)
- [uv](https://docs.astral.sh/uv/) (Python 3.12'yi kendisi indirir; sistem geneline Python kurmak gerekmez)
- Git
- Uçtan uca testler için kurulu Microsoft Edge veya Playwright'ın Chromium'u

Aşağıdaki komutlar PowerShell'de çalışır.

```powershell
git clone https://github.com/ayaz9v/haritanaliz.git
cd haritanaliz
```

## Web uygulaması

```powershell
cd apps/web
npm ci
npm run dev
```

Site <http://localhost:5173> adresinde açılır.

| Komut | Ne yapar |
|---|---|
| `npm run dev` | geliştirme sunucusu |
| `npm run build` | tip kontrolü ve üretim derlemesi (`dist/`) |
| `npm run preview` | derlenmiş siteyi yerelde sunar |
| `npm run lint` | ESLint |
| `npm run format` / `npm run format:check` | Prettier ile biçimlendirme / kontrol |
| `npm test` | Vitest birim testleri |
| `npm run e2e` | Playwright uçtan uca testleri (masaüstü ve mobil) |
| `npm run screenshots` | masaüstü ve mobil ekran görüntülerini `screenshots/` klasörüne kaydeder |

Uçtan uca testler için tarayıcı:

```powershell
# Kurulu Microsoft Edge ile (ek indirme yok)
$env:PW_CHANNEL = "msedge"
npm run e2e

# ya da Playwright'ın Chromium'u ile
npx playwright install chromium
npm run e2e
```

**Veri adresi:** Varsayılan olarak `apps/web/public/data-sample/` altındaki örnek veri kullanılır. Başka bir adres için `apps/web/.env.example` dosyasını `.env.local` adıyla kopyalayın ve `VITE_DATA_BASE_URL` değerini girin.

## Pipeline

```powershell
cd pipeline
uv sync
uv run haritanaliz --help
uv run haritanaliz validate-config
```

| Komut | Ne yapar |
|---|---|
| `uv run haritanaliz validate-config` | `config/settings.yaml` ve `config/categories.yaml` dosyalarını doğrular |
| `uv run haritanaliz export-web-config --out <dosya>` | web için `config.json` üretir |
| `uv run haritanaliz boundaries` … `publish` | veri komutları; henüz uygulanmadı |
| `uv run pytest` | testler |
| `uv run ruff check .` / `uv run ruff format .` | lint / biçimlendirme |

`config/` altındaki bir dosya değişirse web'in örnek `config.json` dosyası yeniden üretilmelidir. Aksi hâlde pytest uyumsuzluğu yakalar ve testler başarısız olur:

```powershell
cd pipeline
uv run haritanaliz export-web-config --out ../apps/web/public/data-sample/v/2026-10-20/config.json
```

TÜİK ADNKS nüfus dosyaları MEDAS'tan elle indirilip `data/raw/tuik/` altına konur (bkz. [docs/data_sources.md](docs/data_sources.md)).

## Belgeler

- [Mimari](docs/architecture.md): bileşenler, veri akışı, veri sözleşmesi
- [Karar kaydı](docs/decisions.md): mimari kararlar, tarih ve gerekçeleriyle
- [Yöntem](docs/methodology.md): göstergeler, sayım modelleri, skorlar (taslak)
- [Veri kaynakları](docs/data_sources.md): erişim, lisanslar, atıflar, veri kalitesi günlüğü
- [İlerleme](docs/progress.md): adım adım yapılanlar

## Veri kaynakları ve atıf

Altlık harita: [OpenFreeMap](https://openfreemap.org) © [OpenMapTiles](https://www.openmaptiles.org/), © [OpenStreetMap katkıcıları](https://www.openstreetmap.org/copyright). Analiz verisi: © OpenStreetMap katkıcıları (ODbL), [Overture Maps Foundation](https://overturemaps.org), TÜİK, SEGE. Lisans ayrıntıları [docs/data_sources.md](docs/data_sources.md)'de.

## Lisans

Kodun lisansı henüz belirlenmedi. Verilerin lisansları kaynaklarına aittir.
