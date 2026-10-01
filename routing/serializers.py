from rest_framework import serializers


class RoundedFloatField(serializers.FloatField):
    def __init__(self, decimals: int = 2, **kwargs):
        self.decimals = decimals
        kwargs.setdefault("read_only", True)
        super().__init__(**kwargs)

    def to_representation(self, value):
        return round(float(value), self.decimals)


class TripRequestSerializer(serializers.Serializer):
    start = serializers.CharField(max_length=200, help_text='"City, ST", a street address, or "lat,lon".')
    finish = serializers.CharField(max_length=200, help_text='"City, ST", a street address, or "lat,lon".')
    start_fuel_percent = serializers.FloatField(min_value=0, max_value=100, default=100)


class LocationSerializer(serializers.Serializer):
    label = serializers.CharField()
    latitude = RoundedFloatField(decimals=5)
    longitude = RoundedFloatField(decimals=5)


class FuelStopSerializer(serializers.Serializer):
    name = serializers.CharField(source="stop.station.name")
    address = serializers.CharField(source="stop.station.address")
    city = serializers.CharField(source="stop.station.city")
    state = serializers.CharField(source="stop.station.state")
    latitude = RoundedFloatField(source="stop.station.latitude", decimals=5)
    longitude = RoundedFloatField(source="stop.station.longitude", decimals=5)
    price_per_gallon = RoundedFloatField(source="stop.station.price", decimals=3)
    route_mile = RoundedFloatField(source="stop.route_mile", decimals=1)
    distance_from_route_miles = RoundedFloatField(source="stop.distance_from_route_miles", decimals=1)
    gallons = RoundedFloatField(decimals=2)
    cost = RoundedFloatField(decimals=2)


class TripPlanSerializer(serializers.Serializer):
    start = LocationSerializer()
    finish = LocationSerializer()
    distance_miles = RoundedFloatField(decimals=1)
    duration_hours = RoundedFloatField(decimals=1)
    start_fuel_percent = RoundedFloatField(decimals=1)
    start_fuel_gallons = RoundedFloatField(decimals=2)
    total_gallons_purchased = RoundedFloatField(decimals=2)
    total_fuel_cost = RoundedFloatField(decimals=2)
    fuel_stops = FuelStopSerializer(many=True)
    map_url = serializers.SerializerMethodField()
    route = serializers.SerializerMethodField()

    def get_map_url(self, plan):
        return self.context.get("map_url")

    def get_route(self, plan):
        return {
            "type": "LineString",
            "coordinates": [[round(lon, 5), round(lat, 5)] for lat, lon in plan.route_coordinates],
        }
