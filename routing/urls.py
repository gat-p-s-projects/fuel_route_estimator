from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="trip-map")),
    path("api/trip/", views.TripPlanView.as_view(), name="trip-plan"),
    path("map/", views.trip_map, name="trip-map"),
]
