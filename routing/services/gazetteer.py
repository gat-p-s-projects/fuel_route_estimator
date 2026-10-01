import csv
import io
import logging
import zipfile
from pathlib import Path

import requests
from django.conf import settings

from .place_names import US_STATES, compact_place_name, normalize_place_name

log = logging.getLogger(__name__)

URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2024_Gazetteer/2024_Gaz_{}_national.zip"
FIELDS = ["state", "name", "compact_name", "latitude", "longitude"]


def load_places():
    path = Path(settings.ROUTING_DATA_DIR) / "us_places.csv"
    if not path.exists():
        _download_places(path)
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _download_places(path):
    log.info("Downloading US Census Gazetteer place files")
    rows, seen = [], set()
    # places before county subdivisions so a city wins over a township with the same name
    for kind in ["place", "cousubs"]:
        for r in _download(kind):
            key = (r["state"], r["name"])
            if r["state"] in US_STATES and key not in seen:
                seen.add(key)
                rows.append(r)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def _download(kind):
    resp = requests.get(URL.format(kind), timeout=120)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        text = z.read(z.namelist()[0]).decode("latin-1")

    for raw in csv.DictReader(io.StringIO(text), delimiter="\t"):
        r = {k.strip(): (v or "").strip() for k, v in raw.items()}
        name = normalize_place_name(_strip_place_type(r["NAME"]))
        yield {
            "state": r["USPS"],
            "name": name,
            "compact_name": compact_place_name(name),
            "latitude": r["INTPTLAT"],
            "longitude": r["INTPTLONG"],
        }


def _strip_place_type(name):
    # 'Big Cabin town' -> 'Big Cabin'
    words = name.split()
    while len(words) > 1 and (words[-1][0].islower() or words[-1][0] == "(" or words[-1] in ("CDP", "CCD")):
        words.pop()
    return " ".join(words)
