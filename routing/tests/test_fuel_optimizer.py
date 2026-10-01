from django.test import SimpleTestCase

from routing.services.errors import RouteNotPossible
from routing.services.fuel_optimizer import plan_fuel_stops

from .factories import station_at

RANGE, MPG = 500, 10


def summarize(stops):
    return [(stop.stop.route_mile, round(stop.gallons, 6)) for stop in stops]


class PlanFuelStopsTests(SimpleTestCase):
    def test_no_stops_when_starting_fuel_covers_the_trip(self):
        stops = plan_fuel_stops([station_at(100, 3.0)], trip_miles=400, range_miles=RANGE, mpg=MPG, start_gallons=50)
        self.assertEqual(stops, [])

    def test_buys_only_enough_to_reach_a_cheaper_station_ahead(self):
        stations = [station_at(10, 4.00), station_at(300, 3.00)]
        stops = plan_fuel_stops(stations, trip_miles=700, range_miles=RANGE, mpg=MPG, start_gallons=1)
        self.assertEqual(summarize(stops), [(10, 29.0), (300, 40.0)])

    def test_fills_up_when_everything_in_range_is_more_expensive(self):
        stations = [station_at(0, 3.00), station_at(400, 3.50), station_at(700, 3.80)]
        stops = plan_fuel_stops(stations, trip_miles=1000, range_miles=RANGE, mpg=MPG, start_gallons=0)
        self.assertEqual(summarize(stops), [(0, 50.0), (400, 40.0), (700, 10.0)])

    def test_buys_just_enough_to_finish(self):
        stations = [station_at(0, 3.00)]
        stops = plan_fuel_stops(stations, trip_miles=300, range_miles=RANGE, mpg=MPG, start_gallons=0)
        self.assertEqual(summarize(stops), [(0, 30.0)])
        self.assertAlmostEqual(stops[0].cost, 90.0)

    def test_skips_expensive_stations_reachable_on_starting_fuel(self):
        stations = [station_at(50, 4.00), station_at(200, 3.00), station_at(450, 3.90)]
        stops = plan_fuel_stops(stations, trip_miles=600, range_miles=RANGE, mpg=MPG, start_gallons=50)
        self.assertEqual(summarize(stops), [(200, 10.0)])

    def test_more_starting_fuel_costs_less(self):
        stations = [station_at(0, 3.00), station_at(450, 3.20)]
        empty = plan_fuel_stops(stations, trip_miles=900, range_miles=RANGE, mpg=MPG, start_gallons=0)
        full = plan_fuel_stops(stations, trip_miles=900, range_miles=RANGE, mpg=MPG, start_gallons=50)
        self.assertLess(sum(s.cost for s in full), sum(s.cost for s in empty))

    def test_gap_longer_than_range_is_rejected(self):
        stations = [station_at(100, 3.00), station_at(700, 3.00)]
        with self.assertRaisesMessage(RouteNotPossible, "between mile 100 and mile 700"):
            plan_fuel_stops(stations, trip_miles=900, range_miles=RANGE, mpg=MPG, start_gallons=50)

    def test_starting_fuel_that_cannot_reach_any_station_is_rejected(self):
        with self.assertRaisesMessage(RouteNotPossible, "Increase start_fuel_percent"):
            plan_fuel_stops([station_at(80, 3.00)], trip_miles=900, range_miles=RANGE, mpg=MPG, start_gallons=5)

    def test_never_runs_out_of_fuel_between_stops(self):
        stations = [station_at(mile, 3 + (mile % 7) / 10) for mile in range(0, 2500, 90)]
        start_gallons = 20
        stops = plan_fuel_stops(stations, trip_miles=2500, range_miles=RANGE, mpg=MPG, start_gallons=start_gallons)

        fuel, position = start_gallons, 0.0
        for stop in stops:
            fuel -= (stop.stop.route_mile - position) / MPG
            self.assertGreaterEqual(fuel, -1e-9)
            fuel += stop.gallons
            self.assertLessEqual(fuel, RANGE / MPG + 1e-9)
            position = stop.stop.route_mile
        self.assertGreaterEqual(fuel - (2500 - position) / MPG, -1e-9)
