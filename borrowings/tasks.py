import time
from datetime import date, timedelta

import stripe
from celery import shared_task

from borrowings.messenger import send_notification
from borrowings.models import Payment, Borrowing
from library_service_api.settings import STRIPE_PUBLIC_KEY


@shared_task
def check_overdue_borrowings() -> None:
    """
    Sends a message about overdue borrowings to admin
    """
    overdue_borrowings = Borrowing.objects.filter(
        actual_return_date__isnull=True,
        expected_return_date__lte=date.today() + timedelta(days=1),
    )
    if overdue_borrowings:
        for borrowing in overdue_borrowings:
            message = (
                f"User {borrowing.user.email} haven't returned the "
                f"{borrowing.book.title} book yet."
                f"Expected return date for this borrowing is "
                f"{borrowing.expected_return_date}."
            )
            send_notification(message)
    else:
        message = "There are no overdue borrowings."
        send_notification(message)


@shared_task
def check_expired_payment_sessions() -> None:
    """
    For pending payments checks if the session is expired
    and marks payment as expired
    """
    if STRIPE_PUBLIC_KEY:
        now = time.time()
        pending_payments = Payment.objects.filter(status="PENDING")
        for payment in pending_payments:
            expires_at = stripe.checkout.Session.retrieve(payment.session_id)[
                "expires_at"
            ]
            if now > expires_at:
                payment.status = "EXPIRED"
                payment.save()
