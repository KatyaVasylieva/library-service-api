from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import generics

from users.serializers import UserSerializer


@extend_schema_view(
    post=extend_schema(description="Endpoint for creating a new user."),
)
class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer


@extend_schema_view(
    get=extend_schema(
        description="Endpoint for getting a detailed info about the current user."
    ),
    put=extend_schema(description="Endpoint for updating the current user."),
    patch=extend_schema(
        description="Endpoint for updating the current user partially."
    ),
)
class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
