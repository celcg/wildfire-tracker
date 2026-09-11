"""Typed public contracts for derived incident data."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GeoPoint(BaseModel):
    latitude: float
    longitude: float


class FireDetection(BaseModel):
    latitude: float
    longitude: float
    confidence: str
    acq_date: str
    acq_time: str
    satellite: str
    frp: float = Field(ge=0)


class FireIncident(BaseModel):
    id: str
    center: GeoPoint
    boundary: list[GeoPoint] = Field(min_length=3)
    detections: list[FireDetection] = Field(min_length=1)
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
