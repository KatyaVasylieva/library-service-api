import os
from datetime import date, timedelta

import requests
from django.db.models import QuerySet

from borrowings.models import Borrowing


def scrape_overdue_borrowings() -> QuerySet:
    """
    Returns borrowings where expected return date is tomorrow or less
    """
    borrowings_overdue = Borrowing.objects.filter(
        actual_return_date__isnull=True,
        expected_return_date__lte=date.today() + timedelta(days=1),
    )
    return borrowings_overdue


def send_notification(message: str) -> None:
    """
    Sends a message to admin
    """
    url = (
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/"
        f"sendMessage?chat_id={os.environ['CHAT_ID']}&text={message}"
    )
    requests.get(url)


def send_notification_about_overdue() -> None:
    """
    Forms a message about overdue borrowings to send to admin
    """
    overdue_borrowings = scrape_overdue_borrowings()
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
