from unittest import mock

from django.test import SimpleTestCase

from routing.services import store
from routing.services.domain import Location
from routing.services.errors import LocationNotFound
from routing.services.geocoding import resolve_location


class ResolveLocationTests(SimpleTestCase):
    def setUp(self):
        store.set_places(
            {("AL", "MC CALLA"): (33.3, -87.0), ("MO", "SAINT LOUIS"): (38.6, -90.2)},
            {("AL", "MCCALLA"): (33.3, -87.0), ("MO", "SAINTLOUIS"): (38.6, -90.2)},
        )
        self.addCleanup(store.set_places, {}, {})

    @mock.patch("routing.services.geocoding.nominatim.search_us_location")
    def test_coordinates_are_parsed_without_network(self, search):
        location = resolve_location("40.71, -74.0")
        self.assertEqual((location.latitude, location.longitude), (40.71, -74.0))
        search.assert_not_called()

    def test_coordinates_outside_the_usa_are_rejected(self):
        with self.assertRaises(LocationNotFound):
            resolve_location("51.5, -0.12")

    @mock.patch("routing.services.geocoding.nominatim.search_us_location")
    def test_city_and_state_resolve_from_local_places(self, search):
        self.assertEqual(resolve_location("St. Louis, Missouri").latitude, 38.6)
        self.assertEqual(resolve_location("McCalla, AL").latitude, 33.3)
        search.assert_not_called()

    @mock.patch("routing.services.geocoding.nominatim.search_us_location")
    def test_unknown_places_fall_back_to_nominatim(self, search):
        search.return_value = Location("1600 Pennsylvania Ave, Washington, DC", 38.9, -77.0)
        self.assertEqual(resolve_location("1600 Pennsylvania Ave, Washington, DC").latitude, 38.9)
        search.assert_called_once()

    @mock.patch("routing.services.geocoding.nominatim.search_us_location", return_value=None)
    def test_unresolvable_location_raises(self, search):
        with self.assertRaises(LocationNotFound):
            resolve_location("Nowhere, ZZ")
