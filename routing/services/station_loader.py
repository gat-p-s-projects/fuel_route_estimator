import csv
import logging
import math
from pathlib import Path

from django.conf import settings

from . import gazetteer, nominatim, store
from .domain import Station
from .errors import ExternalServiceError
from .place_names import US_STATES, normalize_place_name

log = logging.getLogger(__name__)


def refresh_fuel_stations():
    places = gazetteer.load_places()
    by_name, by_compact = {}, {}
    for p in places:
        pos = (float(p["latitude"]), float(p["longitude"]))
        by_name.setdefault((p["state"], p["name"]), pos)
        by_compact.setdefault((p["state"], p["compact_name"]), pos)
    store.set_places(by_name, by_compact)

    rows = read_fuel_prices(Path(settings.FUEL_PRICES_CSV))
    # (state, CITY KEY) -> city as written in the csv, used for the nominatim query
    cities = {(r["state"], r["city_key"]): r["city"] for r in rows}
    cache = read_geocode_cache()

    coords = {}
    for key in cities:
        hit = store.find_place(*key) or cache.get(key)
        if hit:
            coords[key] = hit

    todo = [k for k in cities if k not in coords and k not in cache]
    if todo:
        # publish what we have first so the api works while nominatim is slowly going
        store.set_stations(build_stations(rows, coords))
        log.info("Geocoding %d new cities online (about one per second)", len(todo))
        for state, city in todo:
            try:
                loc = nominatim.search_us_location(f"{cities[(state, city)]}, {state}")
            except ExternalServiceError as e:
                log.warning("Stopping online geocoding, will retry on next start: %s", e)
                break
            append_geocode_cache(state, city, loc)
            if loc:
                coords[(state, city)] = (loc.latitude, loc.longitude)

    stations = build_stations(rows, coords)
    store.set_stations(stations)
    log.info("Fuel station refresh finished: %d stations loaded, %d skipped (no coordinates), %d places",
             len(stations), len(rows) - len(stations), len(places))
    return len(stations), len(rows) - len(stations), len(places)


def read_fuel_prices(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            state = r["State"].strip().upper()
            if state not in US_STATES:
                continue
            rows.append({
                "opis_id": int(r["OPIS Truckstop ID"]),
                "name": r["Truckstop Name"].strip(),
                "address": r["Address"].strip(),
                "city": r["City"].strip(),
                "state": state,
                "price": float(r["Retail Price"]),
            })

    # same station shows up more than once, keep the cheapest price
    best = {}
    for r in sorted(rows, key=lambda r: r["price"]):
        best.setdefault((r["opis_id"], r["address"]), r)
    for r in best.values():
        r["city_key"] = normalize_place_name(r["city"])
    return list(best.values())


def build_stations(rows, coords):
    stations = []
    for r in rows:
        pos = coords.get((r["state"], r["city_key"]))
        if pos:
            stations.append(Station(len(stations), r["name"], r["address"], r["city"], r["state"], r["price"], *pos))
    return stations


def _cache_file():
    return Path(settings.ROUTING_DATA_DIR) / "station_coordinates.csv"


def read_geocode_cache():
    # cities nominatim already answered; None means it found nothing so we don't ask again
    path = _cache_file()
    if not path.exists():
        return {}
    out = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lat, lon = float(row["latitude"] or "nan"), float(row["longitude"] or "nan")
            out[(row["state"], row["city_key"])] = None if math.isnan(lat) or math.isnan(lon) else (lat, lon)
    return out


def append_geocode_cache(state, city_key, loc):
    path = _cache_file()
    new_file = not path.exists()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["state", "city_key", "latitude", "longitude"])
        w.writerow([state, city_key, loc.latitude if loc else "", loc.longitude if loc else ""])
