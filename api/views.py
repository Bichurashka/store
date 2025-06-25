from django.db import connections
from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

# Create your views here.


@api_view(["GET"])
def health_check(request: Request) -> Response:
    conn = connections["default"]
    try:
        conn.cursor()
    except OperationalError:
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(status=status.HTTP_200_OK)
