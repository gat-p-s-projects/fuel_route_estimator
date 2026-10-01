import numpy as np

EARTH_RADIUS = 3958.8  # miles
MILES_PER_DEG = 69.0


def haversine_miles(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS * np.arcsin(np.sqrt(a))


def build_route_profile(coords, total_miles, step=1.0):
    """Returns (lats, lons, miles) sampled roughly every `step` miles along the route."""
    # osrm gives ~35k points for a cross country trip, one per mile is plenty
    pts = np.asarray(coords, dtype=float)
    seg = haversine_miles(pts[:-1, 0], pts[:-1, 1], pts[1:, 0], pts[1:, 1])
    cum = np.concatenate(([0.0], np.cumsum(seg)))
    if cum[-1] > 0:
        cum *= total_miles / cum[-1]

    idx = np.searchsorted(cum, np.arange(0.0, cum[-1], step))
    idx = np.unique(np.append(idx, len(pts) - 1))
    return pts[idx, 0], pts[idx, 1], cum[idx]


def find_stations_near_route(lats, lons, miles, st_lat, st_lon, corridor):
    """Returns (station indices, route mile, miles off route) for stations within `corridor` miles."""
    buf = corridor / MILES_PER_DEG
    lon_buf = buf / np.cos(np.radians(np.abs(lats).max() + buf))
    cand = np.flatnonzero(
        (st_lat >= lats.min() - buf) & (st_lat <= lats.max() + buf)
        & (st_lon >= lons.min() - lon_buf) & (st_lon <= lons.max() + lon_buf)
    )

    nearest = np.empty(len(cand), dtype=int)
    dist = np.empty(len(cand))
    for k in range(0, len(cand), 512):
        c = cand[k:k + 512]
        # flat-earth approximation, good enough at this scale and much cheaper than haversine
        dy = (st_lat[c, None] - lats[None, :]) * MILES_PER_DEG
        dx = (st_lon[c, None] - lons[None, :]) * MILES_PER_DEG * np.cos(np.radians(st_lat[c]))[:, None]
        d = np.hypot(dx, dy)
        j = d.argmin(axis=1)
        nearest[k:k + len(c)] = j
        dist[k:k + len(c)] = d[np.arange(len(c)), j]

    ok = dist <= corridor
    return cand[ok], miles[nearest[ok]], dist[ok]
