from urllib.parse import urlencode

from django.shortcuts import render
from django.urls import reverse
from rest_framework.exceptions import APIException
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from .serializers import TripPlanSerializer, TripRequestSerializer
from .services.trip_planner import plan_trip

EXAMPLE_REQUEST = {"start": "New York, NY", "finish": "Los Angeles, CA", "start_fuel_percent": 50}


class TripPlanView(GenericAPIView):
    serializer_class = TripRequestSerializer

    def get(self, request):
        return Response({"detail": "POST a JSON body to plan a trip.", "example": EXAMPLE_REQUEST})

    def post(self, request):
        s = self.get_serializer(data=request.data)
        s.is_valid(raise_exception=True)
        plan = plan_trip(**s.validated_data)
        map_url = request.build_absolute_uri(reverse("trip-map") + "?" + urlencode(s.validated_data))
        return Response(TripPlanSerializer(plan, context={"map_url": map_url}).data)


def trip_map(request):
    ctx = {"values": {"start_fuel_percent": 100, **request.GET.dict()}}
    if request.GET:
        s = TripRequestSerializer(data=request.GET)
        if not s.is_valid():
            ctx["error"] = "; ".join(f"{k}: {' '.join(v)}" for k, v in s.errors.items())
        else:
            try:
                ctx["plan"] = TripPlanSerializer(plan_trip(**s.validated_data)).data
            except APIException as e:
                ctx["error"] = str(e.detail)
    return render(request, "routing/map.html", ctx)
