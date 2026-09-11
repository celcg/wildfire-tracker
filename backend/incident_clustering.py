"""Explainable spatiotemporal clustering for satellite fire detections."""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from math import asin, cos, pi, radians, sin, sqrt

import pandas as pd

import config
from schemas import FireDetection, FireIncident, GeoPoint, IncidentCollection


EARTH_RADIUS_KM = 6371.0088
CONFIDENCE_RANK = {"unknown": 0, "low": 1, "nominal": 2, "high": 3}
CONFIDENCE_ALIASES = {
    "l": "low",
    "low": "low",
    "n": "nominal",
    "nominal": "nominal",
    "h": "high",
    "high": "high",
}


class UnionFind:
    """Join neighboring detections into connected components efficiently."""

    def __init__(self, size: int) -> None:
        self._parent = list(range(size))
        self._rank = [0] * size

    def find(self, item: int) -> int:
        while self._parent[item] != item:
            self._parent[item] = self._parent[self._parent[item]]
            item = self._parent[item]
        return item

    def union(self, first: int, second: int) -> None:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root == second_root:
            return

        if self._rank[first_root] < self._rank[second_root]:
            first_root, second_root = second_root, first_root

        self._parent[second_root] = first_root
        if self._rank[first_root] == self._rank[second_root]:
            self._rank[first_root] += 1


def haversine_km(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    """Return great-circle distance, which is sufficient at Iberian scale."""
    first_latitude_rad = radians(first_latitude)
    second_latitude_rad = radians(second_latitude)
    latitude_delta = radians(second_latitude - first_latitude)
    longitude_delta = radians(second_longitude - first_longitude)

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude_rad)
        * cos(second_latitude_rad)
        * sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def _parse_acquisition_time(value: object) -> str:
    if pd.isna(value):
        return ""

    try:
        return str(int(float(value))).zfill(4)
    except (TypeError, ValueError):
        return str(value).zfill(4)


def _normalize_fires(fires: pd.DataFrame) -> pd.DataFrame:
    """Coerce untrusted CSV values once before running distance calculations."""
    normalized = fires.copy()
    normalized["latitude"] = pd.to_numeric(
        normalized["latitude"], errors="coerce"
    )
    normalized["longitude"] = pd.to_numeric(
        normalized["longitude"], errors="coerce"
    )
    normalized["frp"] = pd.to_numeric(normalized["frp"], errors="coerce").fillna(0)
    normalized["acq_time_text"] = normalized["acq_time"].map(
        _parse_acquisition_time
    )
    normalized["observed_at"] = pd.to_datetime(
        normalized["acq_date"].astype(str)
        + " "
        + normalized["acq_time_text"],
        format="%Y-%m-%d %H%M",
        utc=True,
        errors="coerce",
    )
    normalized["confidence_normalized"] = (
        normalized["confidence"]
        .astype(str)
        .str.lower()
        .map(CONFIDENCE_ALIASES)
        .fillna("unknown")
    )
    return (
        normalized.dropna(subset=["latitude", "longitude", "observed_at"])
        .sort_values("observed_at")
        .reset_index(drop=True)
    )


def _build_components(fires: pd.DataFrame) -> list[list[int]]:
    """Connect points using time-sorted pair checks and spatial distance."""
    union_find = UnionFind(len(fires))
    time_limit_seconds = config.CLUSTER_TIME_WINDOW_HOURS * 3600
    latitudes = fires["latitude"].to_numpy()
    longitudes = fires["longitude"].to_numpy()
    # Timestamp.timestamp() is independent of Pandas' internal us/ns resolution.
    observed_seconds = fires["observed_at"].map(pd.Timestamp.timestamp).to_numpy()

    for first_index in range(len(fires)):
        for second_index in range(first_index + 1, len(fires)):
            time_delta = (
                observed_seconds[second_index] - observed_seconds[first_index]
            )

            # Rows are time-sorted, so every later pair will also exceed the limit.
            if time_delta > time_limit_seconds:
                break

            distance = haversine_km(
                latitudes[first_index],
                longitudes[first_index],
                latitudes[second_index],
                longitudes[second_index],
            )
            if distance <= config.CLUSTER_RADIUS_KM:
                union_find.union(first_index, second_index)

    components: dict[int, list[int]] = defaultdict(list)
    for index in range(len(fires)):
        components[union_find.find(index)].append(index)
    return list(components.values())


def _dominant_confidence(cluster: pd.DataFrame) -> str:
    counts = Counter(cluster["confidence_normalized"])
    return max(
        counts,
        key=lambda label: (counts[label], CONFIDENCE_RANK[label]),
        default="unknown",
    )


def _trend(cluster: pd.DataFrame) -> str:
    """Compare chronological halves and ignore changes smaller than 20 percent."""
    if len(cluster) < 3 or cluster["observed_at"].nunique() < 2:
        return "stable"

    midpoint = len(cluster) // 2
    earlier_mean = cluster.iloc[:midpoint]["frp"].mean()
    later_mean = cluster.iloc[midpoint:]["frp"].mean()

    if earlier_mean <= 0:
        return "increasing" if later_mean > 0 else "stable"
    if later_mean > earlier_mean * 1.2:
        return "increasing"
    if later_mean < earlier_mean * 0.8:
        return "decreasing"
    return "stable"


def _severity(total_frp: float) -> str:
    if total_frp < 10:
        return "low"
    if total_frp < 50:
        return "moderate"
    if total_frp < 150:
        return "high"
    return "extreme"


def _incident_id(cluster: pd.DataFrame) -> str:
    """Hash stable source fields so the same component keeps the same identity."""
    fingerprints = sorted(
        (
            f"{row.latitude:.5f},{row.longitude:.5f},"
            f"{row.observed_at.isoformat()},{row.satellite}"
        )
        for row in cluster.itertuples()
    )
    digest = sha256("|".join(fingerprints).encode("utf-8")).hexdigest()[:10]
    return f"incident-{digest}"


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return the smallest convex ring containing the supplied lon/lat points."""
    unique_points = sorted(set(points))
    if len(unique_points) <= 1:
        return unique_points

    def cross(
        origin: tuple[float, float],
        first: tuple[float, float],
        second: tuple[float, float],
    ) -> float:
        return (first[0] - origin[0]) * (second[1] - origin[1]) - (
            first[1] - origin[1]
        ) * (second[0] - origin[0])

    lower: list[tuple[float, float]] = []
    for point in unique_points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)

    upper: list[tuple[float, float]] = []
    for point in reversed(unique_points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)

    return lower[:-1] + upper[:-1]


def _observation_envelope(cluster: pd.DataFrame) -> list[GeoPoint]:
    """Buffer detections before taking their hull so every group has an area.

    The buffer is deliberately modest and is only visual context. It must not
    be interpreted as a remotely sensed or modelled burned-area perimeter.
    """
    buffered_points: list[tuple[float, float]] = []
    radius_km = config.CLUSTER_ENVELOPE_BUFFER_KM

    for row in cluster.itertuples():
        latitude_scale = radius_km / 111.32
        longitude_scale = radius_km / (
            111.32 * max(cos(radians(row.latitude)), 0.01)
        )
        for step in range(12):
            angle = 2 * pi * step / 12
            buffered_points.append(
                (
                    row.longitude + longitude_scale * cos(angle),
                    row.latitude + latitude_scale * sin(angle),
                )
            )

    return [
        GeoPoint(latitude=round(latitude, 5), longitude=round(longitude, 5))
        for longitude, latitude in _convex_hull(buffered_points)
    ]


def _build_detection(row: object) -> FireDetection:
    """Expose the exact observations used by a cluster beside its envelope."""
    return FireDetection(
        latitude=float(row.latitude),
        longitude=float(row.longitude),
        confidence=str(row.confidence),
        acq_date=str(row.acq_date),
        acq_time=str(row.acq_time_text),
        satellite=str(row.satellite),
        frp=float(row.frp),
    )


def _build_incident(cluster: pd.DataFrame) -> FireIncident:
    first_seen = cluster["observed_at"].min().to_pydatetime()
    last_seen = cluster["observed_at"].max().to_pydatetime()
    total_frp = float(cluster["frp"].sum())

    return FireIncident(
        id=_incident_id(cluster),
        center=GeoPoint(
            latitude=round(float(cluster["latitude"].mean()), 5),
            longitude=round(float(cluster["longitude"].mean()), 5),
        ),
        boundary=_observation_envelope(cluster),
        detections=[_build_detection(row) for row in cluster.itertuples()],
        detection_count=len(cluster),
        total_frp_mw=round(total_frp, 2),
        maximum_frp_mw=round(float(cluster["frp"].max()), 2),
        first_detected_at=first_seen,
        last_detected_at=last_seen,
        duration_hours=round((last_seen - first_seen).total_seconds() / 3600, 2),
        confidence=_dominant_confidence(cluster),
        trend=_trend(cluster),
        severity=_severity(total_frp),
    )


def cluster_fires(fires: pd.DataFrame, days: int) -> IncidentCollection:
    """Return sorted possible fire areas, including isolated single detections."""
    normalized = _normalize_fires(fires)
    incidents = [
        _build_incident(normalized.iloc[indexes])
        for indexes in _build_components(normalized)
    ]
    incidents.sort(key=lambda incident: incident.total_frp_mw, reverse=True)

    return IncidentCollection(
        days=days,
        incident_count=len(incidents),
        generated_at=datetime.now(timezone.utc),
        incidents=incidents,
    )
