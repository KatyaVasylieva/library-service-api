from celery import shared_task

from borrowings.scrapper import (
    send_notification_about_overdue,
    mark_expired_payments_as_expired
)


@shared_task
def check_overdue_borrowings() -> None:
    send_notification_about_overdue()


@shared_task
def check_expired_payment_sessions() -> None:
    mark_expired_payments_as_expired()
