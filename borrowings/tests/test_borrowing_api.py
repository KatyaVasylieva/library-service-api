import os
from datetime import datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book
from borrowings.models import Borrowing, Payment
from borrowings.serializers import BorrowingSerializer
from borrowings.stripe import FINE_MULTIPLIER
from borrowings.tasks import check_overdue_borrowings
from library_service_api.settings import STRIPE_PUBLIC_KEY

BORROWING_URL = reverse("borrowings:borrowing-list")


def detail_url(borrowing_id):
    return reverse("borrowings:borrowing-detail", args=[borrowing_id])


def sample_book(**params):
    defaults = {
        "title": "Harry Potter 2",
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


def sample_setup(instance):
    instance.book = sample_book()
    instance.borrowing = sample_borrowing(book=instance.book, user=instance.user)

    instance.another_user = get_user_model().objects.create_user(
        "another_user@library.com", "password"
    )
    instance.borrowing_another_user = sample_borrowing(
        book=instance.book, user=instance.another_user
    )


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
        sample_setup(self)

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

    def test_create_borrowing_expected_return_date_before_borrow_should_fail(self):
        payload = {
            "borrow_date": "2023-01-04",
            "expected_return_date": "2023-01-01",
            "book": self.book.id,
        }

        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_borrowing_of_book_with_inventory_0(self):
        book = sample_book(title="Harry Potter 3", inventory=0)
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
        self.assertEqual(
            Book.objects.get(pk=self.book.id).inventory, start_inventory - 1
        )

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

    def test_borrowing_return_book(self):
        start_inventory = self.book.inventory
        active_borrowing = sample_borrowing(
            actual_return_date=None, user=self.user, book=self.book
        )
        response = self.client.post(
            os.path.join(detail_url(active_borrowing.id), "return/"),
            {"actual_return_date": "2023-04-07"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            start_inventory + 1, Book.objects.get(pk=active_borrowing.book.id).inventory
        )

        self.client.post(
            os.path.join(detail_url(active_borrowing.id), "return/"),
            {"actual_return_date": "2023-04-07"},
        )
        self.assertEqual(
            start_inventory + 1, Book.objects.get(pk=active_borrowing.book.id).inventory
        )

    def test_borrowing_return_actual_return_date_before_borrow_should_fail(self):
        active_borrowing = sample_borrowing(
            actual_return_date=None, user=self.user, book=self.book
        )

        response = self.client.post(
            os.path.join(detail_url(active_borrowing.id), "return/"),
            {"actual_return_date": "2022-12-12"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sending_notifications_when_borrowing_creation(self):
        payload = {
            "borrow_date": "2023-01-01",
            "expected_return_date": "2023-01-04",
            "book": self.book.id,
        }

        with patch(
                "borrowings.serializers.send_borrowing_create_message"
        ) as mock_send_message:
            self.client.post(BORROWING_URL, payload)
            mock_send_message.assert_called_once_with(
                self.user, self.book, datetime.strptime("2023-01-04", "%Y-%m-%d").date()
            )

    def test_task_borrowings_overdue(self):
        with patch("requests.get") as mock_send_notification:
            check_overdue_borrowings()
            mock_send_notification.assert_called()

    def test_crate_payment_and_stripe_session_when_creating_a_borrowing(self):
        payload = {
            "borrow_date": "2023-01-01",
            "expected_return_date": "2023-01-04",
            "book": self.book.id,
        }

        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        payment = Payment.objects.last()
        self.assertEqual(payment.borrowing, Borrowing.objects.last())

        self.assertEqual(payment.status, "PENDING")
        self.assertEqual(payment.type, "PAYMENT")

        if STRIPE_PUBLIC_KEY:
            self.assertIsNotNone(payment.session_id)
            self.assertIsNotNone(payment.session_url)
        else:
            self.assertIsNone(payment.session_id)
            self.assertIsNone(payment.session_url)

    def test_create_fine_payment_if_borrowing_was_returned_after_expected_date(self):
        payload = {
            "borrow_date": "2023-01-01",
            "expected_return_date": "2023-01-04",
            "book": self.book.id,
        }
        response = self.client.post(BORROWING_URL, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        borrowing = Borrowing.objects.last()
        self.assertEqual(len(borrowing.payments.all()), 1)
        self.assertEqual(borrowing.payments.all()[0].type, "PAYMENT")

        response = self.client.post(
            os.path.join(detail_url(borrowing.id), "return/"),
            {"actual_return_date": "2023-04-07"},
        )
        borrowing.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(borrowing.payments.all()), 2)
        fine = borrowing.payments.all()[1]
        self.assertEqual(fine.type, "FINE")
        self.assertEqual(
            fine.to_pay,
            (borrowing.actual_return_date - borrowing.expected_return_date).days
            * FINE_MULTIPLIER
            * borrowing.book.daily_fee,
        )

        payments_len = borrowing.payments.count()
        response = self.client.post(
            os.path.join(detail_url(borrowing.id), "return/"),
            {"actual_return_date": "2023-04-07"},
        )
        borrowing.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(borrowing.payments.all()), payments_len)


class AdminBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "authenticated@library.com", "password"
        )
        self.client.force_authenticate(self.user)
        sample_setup(self)

    def test_filtering_by_user_id(self):
        another_borrowings = Borrowing.objects.filter(user__id=self.another_user.id)
        serializer_another = BorrowingSerializer(another_borrowings, many=True)

        response = self.client.get(BORROWING_URL, {"user_id": self.another_user.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(serializer_another.data, response.data)
