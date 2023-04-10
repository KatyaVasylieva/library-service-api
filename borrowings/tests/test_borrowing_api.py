from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer

BORROWING_URL = reverse("borrowings:borrowing-list")


def detail_url(borrowing_id):
    return reverse("borrowings:borrowing-detail", args=[borrowing_id])


def sample_book(**params):
    defaults = {
        "title": "Harry Potter",
        "author": "J.K. Rowling",
        "cover": "HARD",
        "inventory": 5,
        "daily_fee": 0.5,
    }
    defaults.update(params)

    return Book.objects.create(**defaults)


def sample_borrowing(**params):
    defaults = {
        "borrow_date": "2023-01-01",
        "expected_return_date": "2023-01-04",
        "actual_return_date": "2023-01-04",
        "book": None,
        "user": None,
    }
    defaults.update(params)

    return Borrowing.objects.create(**defaults)


class UnauthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(BORROWING_URL)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "authenticated@library.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.book = sample_book()
        self.borrowing = sample_borrowing(book=self.book, user=self.user)

        self.another_user = get_user_model().objects.create_user(
            "another_user@library.com", "password"
        )
        self.borrowing_another_user = sample_borrowing(
            book=self.book, user=self.another_user
        )

    def test_list_borrowings_display_this_user_borrowings(self):
        response = self.client.get(BORROWING_URL)
        borrowings = Borrowing.objects.filter(user=self.user)
        serializer = BorrowingSerializer(borrowings, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_retrieve_borrowings_allowed(self):
        response = self.client.get(detail_url(self.user.borrowings.first().id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_another_user_borrowings_not_allowed(self):
        response = self.client.get(detail_url(self.another_user.borrowings.first().id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_borrowing_expected_return_date_before_borrow(self):
        payload = {
            "borrow_date": "2023-01-04",
            "expected_return_date": "2023-01-01",
            "actual_return_date": "2023-01-04",
            "book": self.book,
        }

        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_borrowing_actual_return_date_before_borrow(self):
        payload = {
            "borrow_date": "2023-01-04",
            "expected_return_date": "2023-01-05",
            "actual_return_date": "2023-01-01",
            "book": self.book,
        }

        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_borrowing_of_book_with_inventory_0(self):
        book = sample_book(title="Harry Potter 2", inventory=0)
        payload = {
            "borrow_date": "2023-01-01",
            "expected_return_date": "2023-01-04",
            "actual_return_date": "2023-01-04",
            "book": book,
        }
        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_success_borrowing_and_decrease_inventory_by_1(self):
        start_inventory = self.book.inventory
        payload = {
            "borrow_date": "2023-01-01",
            "expected_return_date": "2023-01-04",
            "book": self.book.id,
        }
        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Book.objects.get(pk=1).inventory, start_inventory - 1)

    def test_filtering_by_is_active(self):
        active_borrowing = sample_borrowing(
            actual_return_date=None, user=self.user, book=self.book
        )

        serializer_active = BorrowingSerializer(active_borrowing)
        serializer_closed_user = BorrowingSerializer(self.borrowing)
        serializer_closed_another = BorrowingSerializer(self.borrowing_another_user)

        response = self.client.get(BORROWING_URL, {"is_active": "True"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(serializer_active.data, response.data)
        self.assertNotIn(serializer_closed_user.data, response.data)
        self.assertNotIn(serializer_closed_another.data, response.data)


class AdminBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "authenticated@library.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.book = sample_book()
        self.borrowing = sample_borrowing(book=self.book, user=self.user)

        self.another_user = get_user_model().objects.create_user(
            "another_user@library.com", "password"
        )
        self.borrowing_another_user = sample_borrowing(
            book=self.book, user=self.another_user
        )

    def test_filtering_by_user_id(self):
        another_borrowings = Borrowing.objects.filter(user__id=self.another_user.id)
        serializer_another = BorrowingSerializer(another_borrowings, many=True)

        response = self.client.get(BORROWING_URL, {"user_id": self.another_user.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer_another.data, response.data)
