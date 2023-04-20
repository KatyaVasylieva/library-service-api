from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from books.models import Book

BOOK_URL = reverse("books:book-list")


class UnauthenticatedBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_not_required(self):
        response = self.client.get(BOOK_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AuthenticatedBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "authenticated@library.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_create_book_forbidden(self):
        payload = {
            "title": "Harry Potter 2",
            "author": "J.K. Rowling",
            "cover": "HARD",
            "inventory": 5,
            "daily_fee": 0.5,
        }

        response = self.client.post(BOOK_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class AdminBookApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@library.com", "password"
        )
        self.client.force_authenticate(self.user)

    def test_create_book_allowed(self):
        payload = {
            "title": "Harry Potter 2",
            "author": "J.K. Rowling",
            "cover": "HARD",
            "inventory": 5,
            "daily_fee": 0.5,
        }

        response = self.client.post(BOOK_URL, payload)
        book = Book.objects.get(id=response.data["id"])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key in payload:
            self.assertEqual(payload[key], getattr(book, key))
