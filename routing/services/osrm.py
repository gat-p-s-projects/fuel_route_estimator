import requests
from django.conf import settings

from .domain import Route
from .errors import ExternalServiceError, RouteNotPossible

METERS_PER_MILE = 1609.344


def fetch_route(start, finish):
    points = f"{start.longitude},{start.latitude};{finish.longitude},{finish.latitude}"
    try:
        resp = requests.get(
            f"{settings.OSRM_BASE_URL}/route/v1/driving/{points}",
            # polyline is ~6x smaller than geojson
            params={"overview": "full", "geometries": "polyline"},
            timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS,
        )
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        raise ExternalServiceError(f"Routing service failed: {e}") from e

    if data.get("code") == "NoRoute":
        raise RouteNotPossible("No drivable route exists between these locations.")
    if data.get("code") != "Ok":
        raise ExternalServiceError(f"Routing service error: {data.get('message', data.get('code'))}")

    r = data["routes"][0]
    return Route(decode_polyline(r["geometry"]), r["distance"] / METERS_PER_MILE, r["duration"] / 3600)


def decode_polyline(s, precision=5):
    # google encoded polyline -> [(lat, lon), ...]
    coords = []
    i = lat = lon = 0
    while i < len(s):
        vals = []
        for _ in range(2):
            shift = result = 0
            while True:
                b = ord(s[i]) - 63
                i += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            vals.append(~(result >> 1) if result & 1 else result >> 1)
        lat += vals[0]
        lon += vals[1]
        coords.append((lat / 10 ** precision, lon / 10 ** precision))
    return coords
