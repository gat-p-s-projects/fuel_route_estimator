from routing.services.domain import Station, StationOnRoute


def station_at(route_mile: float, price: float, name: str | None = None) -> StationOnRoute:
    station = Station(
        id=int(route_mile * 10),
        name=name or f"Station @ {route_mile}",
        address="I-40",
        city="Somewhere",
        state="TX",
        price=price,
        latitude=35.0,
        longitude=-100.0,
    )
    return StationOnRoute(station=station, route_mile=route_mile, distance_from_route_miles=0.5)
