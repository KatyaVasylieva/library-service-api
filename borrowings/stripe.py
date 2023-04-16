from datetime import date

import stripe
from django.conf import settings

from borrowings.models import Borrowing

FINE_MULTIPLIER = 2
stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_session(
        borrowing: Borrowing,
        abs_url: str,
        start_date: date,
        end_date: date,
        is_fine: bool,
) -> stripe.checkout.Session:
    to_pay = (end_date - start_date).days * borrowing.book.daily_fee
    product = ""
    if is_fine:
        to_pay *= FINE_MULTIPLIER
        product = "Fine for "

    abs_url = abs_url.rsplit("/", 2)[0] + "/borrowings/" + str(borrowing.id)
    checkout_session = stripe.checkout.Session.create(
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": int(to_pay * 100),
                    "product_data": {
                        "name": product + str(borrowing),
                    },
                },
                "quantity": 1,
            },
        ],
        mode="payment",
        success_url=abs_url
                    + "/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=abs_url
                   + "/cancel?session_id={CHECKOUT_SESSION_ID}",
    )

    return checkout_session
