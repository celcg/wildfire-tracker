# Galicia VIIRS data pipeline

This package builds the local, reproducible dataset described in
[`DATA_ENGINEERING_SUBPLAN.md`](../DATA_ENGINEERING_SUBPLAN.md).

The first implemented slice validates the experiment configuration and creates
the complete cell/day label panel from normalized detections. It performs no
network or cloud operation.

Run its tests from the repository root with the existing backend environment:

```powershell
$env:PYTHONPATH = "ml/src"
backend/.venv/Scripts/python.exe -m unittest discover -s ml/tests -v
```
