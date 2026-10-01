import numpy as np
from django.test import SimpleTestCase

from routing.services.geometry import build_route_profile, find_stations_near_route, haversine_miles


def straight_route_along_equator(miles: float) -> list[tuple[float, float]]:
    return [(0.0, lon) for lon in np.linspace(0.0, miles / 69.17, 500)]


class GeometryTests(SimpleTestCase):
    def test_haversine_one_degree_of_latitude(self):
        self.assertAlmostEqual(float(haversine_miles(0, 0, 1, 0)), 69.1, delta=0.1)

    def test_route_profile_is_scaled_to_the_routed_distance(self):
        _, _, miles = build_route_profile(straight_route_along_equator(100), total_miles=110)
        self.assertAlmostEqual(miles[-1], 110)
        self.assertLessEqual(np.diff(miles).max(), 1.5)

    def test_only_stations_inside_the_corridor_are_matched(self):
        lats, lons, miles = build_route_profile(straight_route_along_equator(100), total_miles=100)
        station_latitudes = np.array([0.05, 0.5, 0.0])  # ~3.5 mi off, ~35 mi off, beyond the end
        station_longitudes = np.array([50 / 69.17, 50 / 69.17, 130 / 69.17])

        idx, route_miles, off_route = find_stations_near_route(lats, lons, miles, station_latitudes, station_longitudes, 10)

        self.assertEqual(idx.tolist(), [0])
        self.assertAlmostEqual(route_miles[0], 50, delta=1)
        self.assertAlmostEqual(off_route[0], 3.45, delta=0.1)
