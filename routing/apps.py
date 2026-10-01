import logging
import os
import sys
import threading

from django.apps import AppConfig

log = logging.getLogger(__name__)


class RoutingConfig(AppConfig):
    name = "routing"

    def ready(self):
        if _is_serving_process():
            threading.Thread(target=_refresh, name="fuel-station-refresh", daemon=True).start()


def _is_serving_process():
    # only refresh when actually serving, not for test/shell/other commands
    prog = os.path.basename(sys.argv[0]).removesuffix(".exe")
    if prog not in ("manage.py", "django-admin", "__main__.py"):
        return True  # gunicorn / uwsgi / etc
    if len(sys.argv) < 2 or sys.argv[1] != "runserver":
        return False
    # runserver's autoreloader runs twice, the child (RUN_MAIN) is the one serving
    return os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv


def _refresh():
    from .services.station_loader import refresh_fuel_stations

    try:
        refresh_fuel_stations()
    except Exception:
        log.exception("Fuel station refresh failed")
