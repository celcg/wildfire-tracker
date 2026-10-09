"""Validated experiment settings loaded from the versioned TOML file."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Periods:
    train_start: date
    train_end: date
    validation_start: date
    validation_end: date
    test_start: date
    test_end: date

    def __post_init__(self) -> None:
        ranges = (
            (self.train_start, self.train_end),
            (self.validation_start, self.validation_end),
            (self.test_start, self.test_end),
        )
        if any(start > end for start, end in ranges):
            raise ValueError("Each experiment period must start before it ends")
        if self.validation_start != self.train_end + timedelta(days=1):
            raise ValueError("Validation must start the day after training")
        if self.test_start != self.validation_end + timedelta(days=1):
            raise ValueError("Test must start the day after validation")

    @property
    def start(self) -> date:
        return self.train_start

    @property
    def end(self) -> date:
        return self.test_end

    def split_for(self, value: date) -> str:
        if self.train_start <= value <= self.train_end:
            return "train"
        if self.validation_start <= value <= self.validation_end:
            return "validation"
        if self.test_start <= value <= self.test_end:
            return "test"
        raise ValueError("Date is outside the configured experiment periods")


@dataclass(frozen=True)
class ExperimentSettings:
    schema_version: int
    timezone: str
    h3_resolution: int
    periods: Periods
    firms_source_product: str
    firms_api_source: str
    firms_api_max_days: int
    firms_satellite_code: str
    accepted_confidence: frozenset[str]
    weather_model: str


def _date(value: object, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date") from exc


def load_settings(path: str | Path) -> ExperimentSettings:
    with Path(path).open("rb") as config_file:
        values = tomllib.load(config_file)

    timezone = str(values["timezone"])
    weather_timezone = str(values["weather"]["timezone"])
    if timezone != "UTC" or weather_timezone != "UTC":
        raise ValueError("The experiment and weather timezone must be UTC")

    resolution = int(values["h3"]["resolution"])
    if not 0 <= resolution <= 15:
        raise ValueError("H3 resolution must be between 0 and 15")

    period_values = values["periods"]
    periods = Periods(
        train_start=_date(period_values["train_start"], "train_start"),
        train_end=_date(period_values["train_end"], "train_end"),
        validation_start=_date(
            period_values["validation_start"], "validation_start"
        ),
        validation_end=_date(period_values["validation_end"], "validation_end"),
        test_start=_date(period_values["test_start"], "test_start"),
        test_end=_date(period_values["test_end"], "test_end"),
    )
    accepted = frozenset(
        str(value).strip().lower()
        for value in values["firms"]["accepted_confidence"]
    )
    if not accepted or not accepted <= {"nominal", "high"}:
        raise ValueError("Accepted confidence must contain nominal and/or high")
    api_source = str(values["firms"]["api_source"])
    if api_source != "VIIRS_SNPP_SP":
        raise ValueError("FIRMS API source must be VIIRS_SNPP_SP")
    api_max_days = int(values["firms"]["api_max_days"])
    if not 1 <= api_max_days <= 5:
        raise ValueError("FIRMS API slice length must be between 1 and 5 days")

    return ExperimentSettings(
        schema_version=int(values["schema_version"]),
        timezone=timezone,
        h3_resolution=resolution,
        periods=periods,
        firms_source_product=str(values["firms"]["source_product"]),
        firms_api_source=api_source,
        firms_api_max_days=api_max_days,
        firms_satellite_code=str(values["firms"]["satellite_code"]),
        accepted_confidence=accepted,
        weather_model=str(values["weather"]["model"]),
    )
