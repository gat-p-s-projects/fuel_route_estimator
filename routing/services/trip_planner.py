import hashlib

from django.conf import settings
from django.core.cache import cache

from .domain import StationOnRoute, TripPlan
from .errors import StationDataUnavailable
from .fuel_optimizer import plan_fuel_stops
from .geocoding import resolve_location
from .geometry import build_route_profile, find_stations_near_route
from .osrm import fetch_route
from .store import current_snapshot


def plan_trip(start, finish, start_fuel_percent):
    snap = current_snapshot()
    if not snap["stations"]:
        raise StationDataUnavailable()

    raw = f"{start.strip().lower()}|{finish.strip().lower()}|{start_fuel_percent:.2f}|{snap['version']}"
    key = "trip:" + hashlib.sha256(raw.encode()).hexdigest()
    return cache.get_or_set(key, lambda: _build_plan(start, finish, start_fuel_percent, snap), settings.TRIP_CACHE_SECONDS)


def _build_plan(start_text, finish_text, start_fuel_percent, snap):
    start = resolve_location(start_text)
    finish = resolve_location(finish_text)
    route = fetch_route(start, finish)
    lats, lons, miles = build_route_profile(route.coordinates, route.distance_miles)

    idx, route_miles, off_route = find_stations_near_route(
        lats, lons, miles, snap["lat"], snap["lon"], settings.ROUTE_CORRIDOR_MILES
    )
    on_route = [StationOnRoute(snap["stations"][i], float(m), float(d)) for i, m, d in zip(idx, route_miles, off_route)]

    range_miles, mpg = settings.VEHICLE_RANGE_MILES, settings.VEHICLE_MPG
    start_gallons = range_miles / mpg * start_fuel_percent / 100
    stops = plan_fuel_stops(on_route, route.distance_miles, range_miles, mpg, start_gallons)

    return TripPlan(
        start=start,
        finish=finish,
        distance_miles=route.distance_miles,
        duration_hours=route.duration_hours,
        start_fuel_percent=start_fuel_percent,
        start_fuel_gallons=start_gallons,
        fuel_stops=stops,
        route_coordinates=list(zip(lats.tolist(), lons.tolist())),
    )
