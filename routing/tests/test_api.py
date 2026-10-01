from unittest import mock

from django.core.cache import cache
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from routing.services import store
from routing.services.domain import Route, Station

# A straight 700 mile road heading east from (35, -100); one degree of longitude is ~56.7 miles here.
ROUTE = Route(
    coordinates=[(35.0, -100.0 + step * 0.01) for step in range(1236)],
    distance_miles=700,
    duration_hours=10,
)


def station(name, miles_east, price):
    return Station(miles_east, name, "I-40", "Town", "TX", price, 35.0, -100.0 + miles_east / 56.7)


@mock.patch("routing.services.trip_planner.fetch_route", return_value=ROUTE)
class TripPlanApiTests(SimpleTestCase):
    def setUp(self):
        store.set_stations([station("Expensive", 20, 4.00), station("Cheap", 300, 3.00)])
        self.addCleanup(store.set_stations, [])
        cache.clear()
        self.client = APIClient()

    def post(self, body):
        return self.client.post("/api/trip/", body, format="json")

    def test_plans_a_trip_from_a_json_body(self, fetch_route):
        response = self.post({"start": "35.0,-100.0", "finish": "35.0,-87.66", "start_fuel_percent": 5})

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([stop["name"] for stop in response.data["fuel_stops"]], ["Expensive", "Cheap"])
        # 2.5 gal start, 0.5 left at mile 20: buy 27.5 gal to reach mile 300, then 40 gal to finish.
        self.assertAlmostEqual(response.data["total_fuel_cost"], 27.5 * 4.00 + 40 * 3.00, delta=1)
        self.assertEqual(response.data["route"]["type"], "LineString")
        self.assertIn("/map/?start=", response.data["map_url"])

    def test_repeat_requests_are_served_from_cache(self, fetch_route):
        body = {"start": "35.0,-100.0", "finish": "35.0,-87.66"}
        self.post(body)
        self.post(body)
        fetch_route.assert_called_once()

    def test_start_fuel_percent_defaults_to_full(self, fetch_route):
        response = self.post({"start": "35.0,-100.0", "finish": "35.0,-87.66"})
        self.assertEqual(response.data["start_fuel_percent"], 100)
        self.assertEqual(response.data["start_fuel_gallons"], 50)

    def test_invalid_body_returns_400(self, fetch_route):
        response = self.post({"start": "35.0,-100.0", "start_fuel_percent": 150})
        self.assertEqual(response.status_code, 400)
        self.assertIn("finish", response.data)
        self.assertIn("start_fuel_percent", response.data)

    def test_unreachable_first_station_returns_422(self, fetch_route):
        response = self.post({"start": "35.0,-100.0", "finish": "35.0,-87.66", "start_fuel_percent": 0})
        self.assertEqual(response.status_code, 422)

    def test_map_page_renders_the_plan(self, fetch_route):
        response = self.client.get("/map/", {"start": "35.0,-100.0", "finish": "35.0,-87.66"})
        self.assertContains(response, "Cheap")
        self.assertContains(response, 'id="trip-plan"')


class EmptyStationDataTests(SimpleTestCase):
    def test_returns_503_while_stations_are_loading(self):
        store.set_stations([])
        response = APIClient().post("/api/trip/", {"start": "35,-100", "finish": "35,-90"}, format="json")
        self.assertEqual(response.status_code, 503)
