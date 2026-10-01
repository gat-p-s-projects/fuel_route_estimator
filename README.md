# Fuel Route Estimator

A Django REST API that plans a driving route between two US locations. It picks the cheapest fuel stops along the way (500 mile range, 10 mpg) and returns the total fuel cost and a map.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows, use source .venv/bin/activate for linux 
pip install -r requirements.txt
python manage.py runserver
```

There is no database. On every start the server loads `fuel-prices-for-be-assessment.csv` into memory in a background thread, which takes about 0.2 s. To pick up new prices or stations, replace the file and restart.

- **First run:** downloads the US Census Gazetteer (city coordinates) to `routing/data/us_places.csv`. Cities not in the Gazetteer are looked up on Nominatim, about one per second. The results go into `routing/data/station_coordinates.csv`. Both files are already included, so this step is normally skipped.
- **Later runs:** only cities that have never been seen before hit the network.
- Each server process holds its own copy of the data, about 6,600 stations and 47k places.

## API

`POST /api/trip/` with a JSON body:

```json
{
  "start": "New York, NY",
  "finish": "Los Angeles, CA",
  "start_fuel_percent": 20
}
```

| Field | Required | Notes |
|---|---|---|
| `start`, `finish` | yes | `"City, ST"`, `"City, State"`, a street address, or `"lat,lon"` |
| `start_fuel_percent` | no | 0–100, default 100 |

Opening `http://localhost:8000/api/trip/` in a browser shows DRF's browsable page. It has a form and a raw-JSON editor for sending requests. From Python:

```python
import requests
requests.post("http://localhost:8000/api/trip/", json={"start": "Chicago, IL", "finish": "Dallas, TX"}).json()
```

Response (shortened):

```json
{
  "start": {"label": "New York, NY", "latitude": 40.66, "longitude": -73.94},
  "finish": {"label": "Los Angeles, CA", "latitude": 34.02, "longitude": -118.41},
  "distance_miles": 2810.4,
  "duration_hours": 50.3,
  "start_fuel_percent": 20.0,
  "start_fuel_gallons": 10.0,
  "total_gallons_purchased": 271.04,
  "total_fuel_cost": 821.54,
  "fuel_stops": [
    {"name": "ACI TRUCK STOP", "city": "Columbia", "state": "NJ", "price_per_gallon": 3.079,
     "route_mile": 72.0, "distance_from_route_miles": 0.4, "gallons": 29.6, "cost": 91.14, "...": "..."}
  ],
  "map_url": "http://localhost:8000/map/?start=New+York%2C+NY&finish=Los+Angeles%2C+CA&start_fuel_percent=20.0",
  "route": {"type": "LineString", "coordinates": [[-73.94, 40.66], "..."]}
}
```

Error responses:

| Status | Cause |
|---|---|
| 400 | Invalid body or unknown location |
| 422 | No route, or a gap between stations longer than the vehicle's range |
| 502 | The routing or geocoding service failed |
| 503 | Station data is still loading (the first fraction of a second after start) |

## Map

`map_url` opens a Leaflet/OpenStreetMap page showing the route, numbered fuel stops, and a cost summary. `/map/` with no parameters shows a form for planning a trip in the browser.

## External API calls per request

| Case | Calls |
|---|---|
| Start and finish given as `"City, ST"` or `"lat,lon"` | 1 (OSRM route) |
| A street address not in the local places table | +1 Nominatim lookup per address (at most 3 in total) |
| Repeat request (cached for an hour) | 0 |

## How it works

1. Resolve start and finish, from local data where possible.
2. Get the route geometry from the public OSRM server in one call.
3. Resample the route to one point per mile.
4. Keep the stations within `ROUTE_CORRIDOR_MILES` (10) of the route. This is a vectorized numpy nearest-point search.
5. Pick stops with the greedy minimum-cost refuelling algorithm:
   - If a cheaper station is within range, buy only enough fuel to reach it.
   - Otherwise fill up, or buy just enough to finish, and drive to the cheapest station in range.

Vehicle and corridor settings live in `fuelroute/settings.py`: `VEHICLE_RANGE_MILES`, `VEHICLE_MPG`, `ROUTE_CORRIDOR_MILES`.

## Limitations

- The CSV has no coordinates, so each station is placed at its city's centre. Positions are accurate to a few miles, which is enough to choose stops along a highway.
- The map line is the direct start-to-finish route, so it doesn't turn off to each fuel stop. Stop markers can sit a few miles off the line.
- The optimizer minimizes cost only. It can suggest a small top-up at a slightly cheaper station shortly before a bigger stop.
- Only US stations are used. Canadian rows in the CSV are ignored.

## Tests

```bash
python manage.py test routing
```
