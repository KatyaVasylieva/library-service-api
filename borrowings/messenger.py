from datetime import date

import requests

from books.models import Book
from library_service_api.settings import TELEGRAM_TOKEN, CHAT_ID
from users.models import User


def send_notification(message: str) -> None:
    """
    Sends a message to admin
    """
    if CHAT_ID:
        url = (
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
            f"sendMessage?chat_id={CHAT_ID}&text={message}"
        )
        requests.get(url)


def send_borrowing_create_message(
        user: User, book: Book, expected_return_date: date
) -> None:
    """Sends a message while creating a borrowing with detailed info"""
    message = (
        f"User {user.email} have just borrowed a {book.title} book. "
        f"It is expected to be returned 'till "
        f"{expected_return_date.strftime('%Y-%m-%d')}."
    )
    send_notification(message)
