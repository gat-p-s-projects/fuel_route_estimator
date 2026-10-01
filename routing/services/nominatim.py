import threading
import time

import requests
from django.conf import settings

from .domain import Location
from .errors import ExternalServiceError

_lock = threading.Lock()
_last_call = 0.0


def search_us_location(query):
    global _last_call
    with _lock:
        wait = 1.0 - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = requests.get(
                f"{settings.NOMINATIM_BASE_URL}/search",
                params={"q": query, "countrycodes": "us", "format": "json", "limit": 1},
                headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
                timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise ExternalServiceError(f"Geocoding service failed: {e}") from e
        finally:
            _last_call = time.monotonic()

    results = resp.json()
    if not results:
        return None
    return Location(query, float(results[0]["lat"]), float(results[0]["lon"]))
