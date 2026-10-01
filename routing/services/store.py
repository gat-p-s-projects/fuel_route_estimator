import numpy as np

from .place_names import compact_place_name

# everything lives in memory, loaded from the csv files at startup (see station_loader)
_snapshot = {"version": 0, "stations": [], "lat": np.empty(0), "lon": np.empty(0)}
_places_by_name = {}
_places_by_compact = {}


def current_snapshot():
    return _snapshot


def set_stations(stations):
    global _snapshot
    # swap the whole dict so requests never see a half-updated snapshot
    _snapshot = {
        "version": _snapshot["version"] + 1,
        "stations": stations,
        "lat": np.array([s.latitude for s in stations], dtype=float),
        "lon": np.array([s.longitude for s in stations], dtype=float),
    }


def set_places(by_name, by_compact):
    global _places_by_name, _places_by_compact
    _places_by_name, _places_by_compact = by_name, by_compact


def find_place(state, name):
    """(lat, lon) for a normalized city name, or None."""
    return _places_by_name.get((state, name)) or _places_by_compact.get((state, compact_place_name(name)))
