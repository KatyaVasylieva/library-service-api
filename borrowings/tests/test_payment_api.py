import os
from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from borrowings.models import Borrowing, Payment
from borrowings.serializers import PaymentSerializer
from borrowings.tests.test_borrowing_api import (
    sample_book,
    detail_url,
    sample_borrowing,
)
from library_service_api.settings import STRIPE_PUBLIC_KEY

PAYMENT_URL = reverse("borrowings:payment-list")
BORROWING_URL = reverse("borrowings:borrowing-list")


class UnauthenticatedBorrowingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        response = self.client.get(PAYMENT_URL)
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

    def test_list_payments_display_this_user_payments(self):
        response = self.client.get(PAYMENT_URL)
        payments = Payment.objects.filter(borrowing__user=self.user)
        serializer = PaymentSerializer(payments, many=True)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    @patch("stripe.checkout.Session.retrieve")
    def test_change_payment_status_when_session_is_paid_successfully(
        self, session_mock
    ):
        if STRIPE_PUBLIC_KEY:
            payload = {
                "borrow_date": "2023-01-01",
                "expected_return_date": "2023-01-04",
                "book": self.book.id,
            }

            response_post_borrowing = self.client.post(BORROWING_URL, payload)
            self.assertEqual(
                response_post_borrowing.status_code, status.HTTP_201_CREATED
            )
            borrowing = Borrowing.objects.last()
            payment = Payment.objects.last()

            self.assertEqual(payment.status, "PENDING")
            session_mock.return_value = {"payment_status": "paid"}

            res = self.client.get(
                os.path.join(
                    detail_url(borrowing.id),
                    f"success/?session_id={payment.session_id}",
                )
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            payment.refresh_from_db()
            self.assertEqual(payment.status, "PAID")

    def test_renew_payment_if_stripe_connected(self):
        if STRIPE_PUBLIC_KEY:
            payload = {
                "borrow_date": "2023-01-01",
                "expected_return_date": "2023-01-04",
                "book": self.book.id,
            }

            self.client.post(BORROWING_URL, payload)
            borrowing = Borrowing.objects.last()
            payment = borrowing.payments.first()

            self.assertEqual(payment.status, "PENDING")
            payment.status = "EXPIRED"
            payment.save()
            expired_session_id = payment.session_id
            self.client.post(
                os.path.join(
                    reverse("borrowings:payment-detail", args=[payment.id]), "renew/"
                ),
                {},
            )
            payment.refresh_from_db()
            new_session = stripe.checkout.Session.retrieve(payment.session_id)

            self.assertNotEqual(expired_session_id, new_session)
            self.assertEqual(new_session["status"], "open")
            self.assertEqual(payment.status, "PENDING")


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
