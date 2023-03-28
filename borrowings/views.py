import os

import requests
from django.db import transaction
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]


def get_telegram_chat_id() -> int:
    """Returns user's chat id to send notifications to"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    response = requests.get(url).json()
    chat_id = response["result"][0]["message"]["chat"]["id"]
    return chat_id


def send_borrowing_create_message(
        chat_id: int, book: Book, expected_return_date: str
):
    """Sends a message while creating a borrowing with detailed info"""
    message = (
        f"Greetings! You've just borrowed the book {book.title}. "
        f"Make sure to return it 'till {expected_return_date}. "
        f"Have a good read!"
    )
    url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
        f"sendMessage?chat_id={chat_id}&text={message}"
    )
    requests.get(url)


class BorrowingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrowing.objects.all()
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer

        if self.action == "return_book":
            return BorrowingReturnSerializer

        return BorrowingSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        is_active = self.request.query_params.get("is_active")
        queryset = self.queryset.all()

        if self.request.user.is_superuser:
            if user_id:
                queryset = queryset.filter(user__id=user_id)

        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)

        if is_active:
            queryset = queryset.filter(
                actual_return_date__isnull=eval(is_active)
            )

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            self.perform_create(serializer)
            book_ind = self.request.data["book"]
            book = Book.objects.get(pk=book_ind)
            book.inventory -= 1
            book.save()
            headers = self.get_success_headers(serializer.data)

            chat_id = get_telegram_chat_id()
            send_borrowing_create_message(
                chat_id, book, self.request.data["expected_return_date"]
            )

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(
        methods=["POST"],
        detail=True,
        url_path="return",
    )
    def return_book(self, request, pk=None):
        """Endpoint for returning book and closing specific borrowing"""
        borrowing = self.get_object()
        was_not_returned = borrowing.actual_return_date
        serializer = self.get_serializer(borrowing, data=request.data)

        if serializer.is_valid():
            serializer.save()
            if not was_not_returned:
                borrowing.book.inventory += 1
                borrowing.book.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
