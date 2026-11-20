const CONFIDENCE_RANK = { l: 0, low: 0, n: 1, nominal: 1, h: 2, high: 2 };
const SEVERITY_RANK = { low: 0, moderate: 1, high: 2, extreme: 3 };
const PLACE_BOUNDS = {
  galicia: { south: 41.8, north: 43.8, west: -9.4, east: -6.7 },
};

function normalized(value) {
  return String(value ?? "").trim().toLowerCase();
}

export function isSupportedSearchPlace(place) {
  return !place || Boolean(PLACE_BOUNDS[normalized(place)]);
}

function coordinatesFor(item, layer) {
  return layer === "clusters"
    ? [Number(item.center?.latitude), Number(item.center?.longitude)]
    : [Number(item.latitude), Number(item.longitude)];
}

function matchesPlace(item, layer, place) {
  if (!place) return true;
  const bounds = PLACE_BOUNDS[normalized(place)];
  if (!bounds) return false;
  const [latitude, longitude] = coordinatesFor(item, layer);
  return (
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    latitude >= bounds.south &&
    latitude <= bounds.north &&
    longitude >= bounds.west &&
    longitude <= bounds.east
  );
}

function confidenceFor(item) {
  return CONFIDENCE_RANK[normalized(item.confidence)] ?? -1;
}

function valueForSort(item, layer, sort) {
  if (sort === "highest_frp") {
    return Number(layer === "clusters" ? item.maximum_frp_mw : item.frp) || 0;
  }
  if (sort === "highest_confidence") return confidenceFor(item);
  if (sort === "persistent") return Number(item.duration_hours) || 0;
  const observed =
    layer === "clusters"
      ? item.last_detected_at
      : (() => {
          const time = String(item.acq_time ?? "0").padStart(4, "0");
          return `${item.acq_date ?? ""}T${time.slice(0, 2)}:${time.slice(2)}:00Z`;
        })();
  return Date.parse(observed) || 0;
}

function matches(item, layer, filters) {
  if (!matchesPlace(item, layer, filters.place)) return false;
  if (
    filters.minimum_confidence &&
    confidenceFor(item) < CONFIDENCE_RANK[filters.minimum_confidence]
  ) {
    return false;
  }
  const frp = Number(layer === "clusters" ? item.maximum_frp_mw : item.frp);
  if (
    filters.minimum_frp_mw != null &&
    (!Number.isFinite(frp) || frp < filters.minimum_frp_mw)
  ) {
    return false;
  }
  if (
    layer === "clusters" &&
    filters.minimum_severity &&
    (SEVERITY_RANK[item.severity] ?? -1) <
      SEVERITY_RANK[filters.minimum_severity]
  ) {
    return false;
  }
  if (
    layer === "clusters" &&
    filters.minimum_persistence_hours != null &&
    (!Number.isFinite(Number(item.duration_hours)) ||
      Number(item.duration_hours) < filters.minimum_persistence_hours)
  ) {
    return false;
  }
  return true;
}

export function applyFireSearchFilters(items, layer, filters) {
  if (!filters) return items;
  return items
    .filter((item) => matches(item, layer, filters))
    .toSorted(
      (left, right) =>
        valueForSort(right, layer, filters.sort) -
        valueForSort(left, layer, filters.sort),
    )
    .slice(0, filters.limit);
}

export function describeFireSearchFilters(filters) {
  if (!filters) return [];
  const descriptions = [
    filters.days === 1 ? "Last 24 hours" : `Last ${filters.days} days`,
    filters.layer === "clusters" ? "Possible clusters" : "Detections",
  ];
  if (filters.place) descriptions.push(filters.place);
  if (filters.minimum_severity) descriptions.push(`${filters.minimum_severity}+ severity`);
  if (filters.minimum_confidence) descriptions.push(`${filters.minimum_confidence}+ confidence`);
  if (filters.minimum_frp_mw != null) descriptions.push(`${filters.minimum_frp_mw}+ MW`);
  if (filters.minimum_persistence_hours != null) {
    descriptions.push(`${filters.minimum_persistence_hours}+ hours observed`);
  }
  return descriptions;
}
