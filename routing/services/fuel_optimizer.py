from .domain import FuelStop
from .errors import RouteNotPossible


def plan_fuel_stops(stations, trip_miles, range_miles, mpg, start_gallons):
    # greedy: buy just enough to reach a cheaper station, otherwise fill up
    stations = sorted(stations, key=lambda s: s.route_mile)
    tank = range_miles / mpg
    start_range = start_gallons * mpg

    if trip_miles <= start_range:
        return []

    reachable = [i for i, s in enumerate(stations) if s.route_mile <= start_range]
    if not reachable:
        first = f"mile {stations[0].route_mile:.0f}" if stations else "none along the route"
        raise RouteNotPossible(
            f"Starting fuel covers {start_range:.0f} miles but the first fuel station is at {first}. "
            "Increase start_fuel_percent."
        )
    # nothing before the cheapest reachable station is cheaper, so go straight there
    i = min(reachable, key=lambda j: (stations[j].price, -stations[j].route_mile))
    fuel = start_gallons - stations[i].route_mile / mpg

    stops = []
    while True:
        here = stations[i]
        ahead = [j for j in range(i + 1, len(stations)) if stations[j].route_mile - here.route_mile <= range_miles]
        cheaper = next((j for j in ahead if stations[j].price < here.price), None)

        if cheaper is not None:
            nxt, need = cheaper, (stations[cheaper].route_mile - here.route_mile) / mpg
        elif trip_miles - here.route_mile <= range_miles:
            nxt, need = None, (trip_miles - here.route_mile) / mpg
        elif ahead:
            nxt, need = min(ahead, key=lambda j: (stations[j].price, -stations[j].route_mile)), tank
        else:
            gap_end = stations[i + 1].route_mile if i + 1 < len(stations) else trip_miles
            raise RouteNotPossible(
                f"No fuel station between mile {here.route_mile:.0f} and mile {gap_end:.0f}; "
                f"the {gap_end - here.route_mile:.0f} mile gap exceeds the {range_miles:.0f} mile range."
            )

        buy = need - fuel
        if buy > 1e-9:
            stops.append(FuelStop(here, buy))
            fuel += buy

        if nxt is None:
            return stops
        fuel -= (stations[nxt].route_mile - here.route_mile) / mpg
        i = nxt
