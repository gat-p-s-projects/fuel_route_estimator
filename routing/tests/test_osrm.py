from unittest import mock

from django.test import SimpleTestCase

from routing.services.domain import Location
from routing.services.errors import ExternalServiceError, RouteNotPossible
from routing.services.osrm import decode_polyline, fetch_route

GOOGLE_EXAMPLE = "_p~iF~ps|U_ulLnnqC_mqNvxq`@"
START = Location("A", 38.5, -120.2)
FINISH = Location("B", 43.252, -126.453)


def osrm_response(payload):
    return mock.Mock(json=mock.Mock(return_value=payload))


class OsrmTests(SimpleTestCase):
    def test_decodes_google_reference_polyline(self):
        self.assertEqual(decode_polyline(GOOGLE_EXAMPLE), [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)])

    @mock.patch("routing.services.osrm.requests.get")
    def test_fetch_route_converts_units(self, get):
        get.return_value = osrm_response({
            "code": "Ok",
            "routes": [{"geometry": GOOGLE_EXAMPLE, "distance": 160934.4, "duration": 7200}],
        })
        route = fetch_route(START, FINISH)
        self.assertAlmostEqual(route.distance_miles, 100)
        self.assertEqual(route.duration_hours, 2)
        self.assertEqual(route.coordinates[0], (38.5, -120.2))
        get.assert_called_once()

    @mock.patch("routing.services.osrm.requests.get", return_value=osrm_response({"code": "NoRoute"}))
    def test_no_route_is_a_client_error(self, get):
        with self.assertRaises(RouteNotPossible):
            fetch_route(START, FINISH)

    @mock.patch("routing.services.osrm.requests.get", return_value=osrm_response({"code": "InvalidQuery", "message": "bad"}))
    def test_other_osrm_failures_are_gateway_errors(self, get):
        with self.assertRaises(ExternalServiceError):
            fetch_route(START, FINISH)
