# Galicia VIIRS data pipeline

This package builds the local, reproducible dataset described in
[`DATA_ENGINEERING_SUBPLAN.md`](../DATA_ENGINEERING_SUBPLAN.md).

Implemented local stages validate the experiment configuration, normalize FIRMS
archive rows, build the H3 grid from a supplied Galicia boundary, and create the
complete cell/day label panel. They perform no cloud operation.

Create the isolated environment and run tests from the repository root:

```powershell
python -m venv ml/.venv
ml/.venv/Scripts/python.exe -m pip install -r ml/requirements.txt
$env:PYTHONPATH = "ml/src"
ml/.venv/Scripts/python.exe -m unittest discover -s ml/tests -v
```

The Galicia boundary is the pinned Eurostat/GISCO NUTS 2024 ES11 dataset
declared in `config/sources.toml`. This portfolio use is non-commercial and
must retain the attribution: © EuroGeographics for the administrative
boundaries. Review the source terms before any commercial publication.

FIRMS retrieval uses the standard-processing `VIIRS_SNPP_SP` Area API in
validated slices of at most five days. Set `FIRMS_MAP_KEY` only in the local
environment; source metadata uses a redacted `[MAP_KEY]` URL.

Historical weather uses Open-Meteo `era5_seamless` in GMT: ERA5-Land
temperature and humidity combined with ERA5 forcing for wind and precipitation.
Weather data is CC BY 4.0 and requires attribution to Open-Meteo and
Copernicus/ECMWF; the exact source metadata is in `config/sources.toml`.

The dataset builder preserves the full cell/day panel, marks missing weather,
adds D-1 and D-7…D-1 features, assigns temporal splits, and writes validated
Zstandard Parquet files atomically.
