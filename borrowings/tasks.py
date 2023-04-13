from celery import shared_task

from borrowings.scrapper import (
    send_notification_about_overdue,
    scrape_expired_payments
)
from library_service_api.settings import STRIPE_PUBLIC_KEY


@shared_task
def check_overdue_borrowings() -> None:
    send_notification_about_overdue()


@shared_task
def check_expired_payment_sessions() -> None:
    if STRIPE_PUBLIC_KEY:
        scrape_expired_payments()
