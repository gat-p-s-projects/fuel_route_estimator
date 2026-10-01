import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase

from routing.apps import _is_serving_process
from routing.services.gazetteer import _strip_place_type
from routing.services.station_loader import read_fuel_prices

CSV = """OPIS Truckstop ID,Truckstop Name,Address,City,State,Rack ID,Retail Price
20,PILOT TRAVEL CENTER #1243,"I-8, EXIT 119",Gila Bend,AZ,930,3.899
20,PILOT #1243,"I-8, EXIT 119",Gila Bend,AZ,930,3.799
35,ACI TRUCK STOP,US-46,Columbia,NJ,90,3.079
99,CANADIAN STOP,HWY 1,Edmonton,AB,1,1.5
"""


class ReadFuelPricesTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "prices.csv"
        self.path.write_text(CSV)

    def test_duplicates_keep_the_lowest_price_and_non_us_rows_are_dropped(self):
        rows = {r["state"]: r for r in read_fuel_prices(self.path)}
        self.assertEqual(sorted(rows), ["AZ", "NJ"])
        self.assertEqual(rows["AZ"]["price"], 3.799)
        self.assertEqual(rows["AZ"]["city_key"], "GILA BEND")


class GazetteerNameTests(SimpleTestCase):
    def test_strips_census_place_type(self):
        self.assertEqual(_strip_place_type("Big Cabin town"), "Big Cabin")
        self.assertEqual(_strip_place_type("Abanda CDP"), "Abanda")
        self.assertEqual(_strip_place_type("Boise City city"), "Boise City")


class StartupRefreshGuardTests(SimpleTestCase):
    def check(self, argv, run_main=None):
        environment = {"RUN_MAIN": run_main} if run_main else {}
        with mock.patch.object(sys, "argv", argv), mock.patch.dict(os.environ, environment, clear=False):
            if not run_main:
                os.environ.pop("RUN_MAIN", None)
            return _is_serving_process()

    def test_refreshes_only_in_serving_processes(self):
        self.assertTrue(self.check(["manage.py", "runserver"], run_main="true"))
        self.assertFalse(self.check(["manage.py", "runserver"]))
        self.assertTrue(self.check(["manage.py", "runserver", "--noreload"]))
        self.assertFalse(self.check(["manage.py", "shell"]))
        self.assertFalse(self.check(["manage.py", "test"]))
        self.assertTrue(self.check(["gunicorn", "fuelroute.wsgi"]))
