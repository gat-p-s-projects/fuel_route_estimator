import re

from . import nominatim, store
from .domain import Location
from .errors import LocationNotFound
from .place_names import normalize_place_name, to_state_code

LATLON_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$")


def resolve_location(text):
    # try "lat,lon", then our local places table, then nominatim as a last resort
    loc = parse_coordinates(text) or find_local_place(text) or nominatim.search_us_location(text)
    if loc is None:
        raise LocationNotFound(f"Could not find a US location matching '{text}'.")
    return loc


def parse_coordinates(text):
    m = LATLON_RE.match(text)
    if not m:
        return None
    lat, lon = float(m.group(1)), float(m.group(2))
    # rough box around the 50 states
    if not (18 <= lat <= 72 and -180 <= lon <= -65):
        raise LocationNotFound(f"Coordinates {lat}, {lon} are outside the USA.")
    return Location(f"{lat}, {lon}", lat, lon)


def find_local_place(text):
    city, _, state = text.rpartition(",")
    state = to_state_code(state)
    if not city.strip() or not state:
        return None

    pos = store.find_place(state, normalize_place_name(city))
    return Location(text.strip(), *pos) if pos else None
