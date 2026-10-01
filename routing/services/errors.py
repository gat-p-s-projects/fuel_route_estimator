from rest_framework import status
from rest_framework.exceptions import APIException


class LocationNotFound(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "location_not_found"


class RouteNotPossible(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_code = "route_not_possible"


class ExternalServiceError(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_code = "external_service_error"


class StationDataUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Fuel station data is still loading, please retry shortly."
    default_code = "station_data_unavailable"
