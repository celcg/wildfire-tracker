"""Typed public contracts for derived incident data."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    latitude: float
    longitude: float


class FireIncident(BaseModel):
    id: str
    center: GeoPoint
    detection_count: int = Field(ge=1)
    total_frp_mw: float = Field(ge=0)
    maximum_frp_mw: float = Field(ge=0)
    first_detected_at: datetime
    last_detected_at: datetime
    duration_hours: float = Field(ge=0)
    confidence: Literal["low", "nominal", "high", "unknown"]
    trend: Literal["increasing", "stable", "decreasing"]
    severity: Literal["low", "moderate", "high", "extreme"]


class IncidentCollection(BaseModel):
    days: int = Field(ge=1, le=10)
    incident_count: int = Field(ge=0)
    generated_at: datetime
    incidents: list[FireIncident]
