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
