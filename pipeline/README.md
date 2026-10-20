# haritanaliz pipeline

haritanaliz'in Python veri ve analiz paketi. Kurulum ve projenin geneli için kök dizindeki [README.md](../README.md)'ye, mimari için [docs/architecture.md](../docs/architecture.md)'ye bakın.

```powershell
uv sync
uv run haritanaliz --help
uv run haritanaliz validate-config
uv run pytest
```

| Modül | Görev |
|---|---|
| `cli.py` | `haritanaliz` komutu (Typer) |
| `config.py` | `config/*.yaml` için pydantic modelleri ve doğrulama |
| `manifest.py` | `manifest.json` veri sözleşmesi |
| `webconfig.py` | web için `config.json` üretimi |
| `paths.py` | depo kökünü ve config klasörünü bulma (`HARITANALIZ_ROOT` ile değiştirilebilir) |
