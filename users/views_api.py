from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import CustomUserCreationSerializer, CustomUserShowSerializer


@api_view(["GET"])
def me_view(request: Request) -> Response:
    user = request.user
    serializer = CustomUserShowSerializer(user)
    return Response(serializer.data)


class CreateUserView(APIView):
    permission_classes = (IsAdminUser,)

    def post(self, request: Request) -> Response:
        serializer = CustomUserCreationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.validated_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
