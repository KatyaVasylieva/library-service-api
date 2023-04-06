import stripe
from django.conf import settings

from borrowings.models import Borrowing


stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_session_for_borrowing(
    borrowing: Borrowing,
    abs_url: str,
) -> stripe.checkout.Session:
    borrowing_price = (
        borrowing.expected_return_date - borrowing.borrow_date
    ).days * borrowing.book.daily_fee

    checkout_session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(borrowing_price * 100),
                    "product_data": {
                        "name": borrowing,
                    },
                },
                "quantity": 1,
            },
        ],
        mode="payment",
        success_url=abs_url
        + str(borrowing.id)
        + "/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=abs_url
        + str(borrowing.id)
        + "/cancel?session_id={CHECKOUT_SESSION_ID}",
    )

    return checkout_session