from dataclasses import dataclass, field


@dataclass
class Location:
    label: str
    latitude: float
    longitude: float


@dataclass
class Route:
    coordinates: list  # [(lat, lon), ...]
    distance_miles: float
    duration_hours: float


@dataclass
class Station:
    id: int
    name: str
    address: str
    city: str
    state: str
    price: float
    latitude: float
    longitude: float


@dataclass
class StationOnRoute:
    station: Station
    route_mile: float
    distance_from_route_miles: float

    @property
    def price(self):
        return self.station.price


@dataclass
class FuelStop:
    stop: StationOnRoute
    gallons: float

    @property
    def cost(self):
        return self.gallons * self.stop.price


@dataclass
class TripPlan:
    start: Location
    finish: Location
    distance_miles: float
    duration_hours: float
    start_fuel_percent: float
    start_fuel_gallons: float
    fuel_stops: list
    route_coordinates: list = field(repr=False)

    @property
    def total_gallons_purchased(self):
        return sum(s.gallons for s in self.fuel_stops)

    @property
    def total_fuel_cost(self):
        return sum(s.cost for s in self.fuel_stops)
