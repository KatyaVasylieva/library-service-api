from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework import viewsets

from books.models import Book
from books.permissions import IsAdminOrReadOnly
from books.serializers import BookSerializer


@extend_schema_view(
    list=extend_schema(description="Endpoint for getting all the books in the library"),
    retrieve=extend_schema(description="Endpoint for getting a specific book"),
    create=extend_schema(description="Endpoint for creating a new book"),
    update=extend_schema(description="Endpoint for updating a book"),
    partial_update=extend_schema(description="Endpoint for updating a book partially"),
    destroy=extend_schema(description="Endpoint for deleting a book"),
)
class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = (IsAdminOrReadOnly,)
