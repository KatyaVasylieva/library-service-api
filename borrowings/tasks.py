from borrowings.models import Borrowing

from celery import shared_task

from borrowings.scrapper import send_notification_about_overdue


@shared_task
def check_overdue_borrowings() -> None:
    send_notification_about_overdue()
