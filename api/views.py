from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connections
from django.db.utils import OperationalError


# Create your views here.

@api_view(['GET'])
def health_check(request):
    conn = connections['default']
    try:
        c = conn.cursor()
    except OperationalError:
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(status=status.HTTP_200_OK)
