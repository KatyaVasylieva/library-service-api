from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from books.models import Book
from books.serializers import BookSerializer
from borrowings.models import Borrowing, Payment
from borrowings.scrapper import send_notification
from borrowings.stripe import create_stripe_session, FINE_MULTIPLIER
from library_service_api.settings import STRIPE_PUBLIC_KEY
from users.models import User


def send_borrowing_create_message(
        user: User, book: Book, expected_return_date: date
) -> None:
    """Sends a message while creating a borrowing with detailed info"""
    message = (
        f"User {user.email} have just borrowed a {book.title} book. "
        f"It is expected to be returned 'till {expected_return_date.strftime('%Y-%m-%d')}."
    )
    send_notification(message)


class BorrowingSerializer(serializers.ModelSerializer):
    borrow_date = serializers.DateField(required=True)
    expected_return_date = serializers.DateField(required=True)
    book = BookSerializer()
    user = serializers.CharField()
    payments = serializers.StringRelatedField(many=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "actual_return_date",
            "book",
            "user",
            "payments",
        )
        read_only_fields = ("payments",)


class BorrowingCreateSerializer(serializers.ModelSerializer):
    borrow_date = serializers.DateField(required=True)
    expected_return_date = serializers.DateField(required=True)
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date", "expected_return_date", "book", "user")

    def validate(self, data):
        """
        Validates that borrow date is before expected return date.
        Also validates that user does not have any unpaid borrowings and fines.
        """

        if data["borrow_date"] > data["expected_return_date"]:
            raise serializers.ValidationError(
                "Borrow date cannot be after return date."
            )
        user_payments_unpaid = Payment.objects.filter(
            Q(borrowing__user=data["user"]) & ~Q(status="PAID")
        )
        if user_payments_unpaid:
            raise serializers.ValidationError(
                "Make sure you paid your previous borrowings "
                "and fines before creating new borrowing."
            )

        return data

    def create(self, validated_data):
        with transaction.atomic():
            borrowing = Borrowing.objects.create(**validated_data)
            book = borrowing.book
            book.inventory -= 1
            book.save()

            if STRIPE_PUBLIC_KEY:
                session = create_stripe_session(
                    borrowing,
                    self.context["request"].build_absolute_uri(),
                    borrowing.borrow_date,
                    borrowing.expected_return_date,
                    is_fine=False,
                )
            else:
                session = {
                    "url": None,
                    "id": None,
                    "amount_total": (
                                            borrowing.expected_return_date - borrowing.borrow_date
                                    ).days
                                    * borrowing.book.daily_fee
                                    * 100,
                }
            Payment.objects.create(
                status="PENDING",
                type="PAYMENT",
                borrowing=borrowing,
                session_url=session["url"],
                session_id=session["id"],
                to_pay=Decimal(session["amount_total"] / 100),
            )

            send_borrowing_create_message(
                borrowing.user,
                book,
                borrowing.expected_return_date
            )

            return borrowing


class BorrowingReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = ("id", "actual_return_date")

    def validate_actual_return_date(self, value):
        """
        Validates that borrow date is before actual return date.
        """

        if value < self.instance.borrow_date:
            raise serializers.ValidationError(
                "Borrow date cannot be after return date."
            )
        return value

    def update(self, instance, validated_data):

        was_not_returned = instance.actual_return_date
        if not was_not_returned:
            instance.book.inventory += 1
            instance.book.save()
        instance.actual_return_date = validated_data["actual_return_date"]
        instance.save()

        if (
                instance.actual_return_date - instance.expected_return_date > timedelta(0)
        ):
            if STRIPE_PUBLIC_KEY:
                session = create_stripe_session(
                    instance,
                    self.context["request"].build_absolute_uri(),
                    instance.expected_return_date,
                    instance.actual_return_date,
                    is_fine=True,
                )
            else:
                session = {
                    "url": None,
                    "id": None,
                    "amount_total": (
                                            instance.actual_return_date
                                            - instance.expected_return_date
                                    ).days
                                    * instance.book.daily_fee
                                    * FINE_MULTIPLIER
                                    * 100,
                }
            Payment.objects.create(
                status="PENDING",
                type="FINE",
                borrowing=instance,
                session_url=session["url"],
                session_id=session["id"],
                to_pay=Decimal(session["amount_total"] / 100),
            )

        return instance


class PaymentSerializer(serializers.ModelSerializer):
    borrowing = BorrowingSerializer()

    class Meta:
        model = Payment
        fields = (
            "id",
            "status",
            "type",
            "borrowing",
            "session_url",
            "session_id",
            "to_pay",
        )
        read_only_fields = ("session_url", "session_id")


class PaymentRenewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ("id",)
        read_only_fields = ("id",)

    def update(self, instance, validated_data):
        borrowing = instance.borrowing

        if instance.status == "EXPIRED":
            if instance.type == "PAYMENT":
                session = create_stripe_session(
                    borrowing,
                    self.context["request"].build_absolute_uri().rsplit("/", 2)[0],
                    borrowing.borrow_date,
                    borrowing.expected_return_date,
                    is_fine=False,
                )
            else:
                session = create_stripe_session(
                    borrowing,
                    self.context["request"].build_absolute_uri().rsplit("/", 2)[0],
                    borrowing.expected_return_date,
                    borrowing.actual_return_date,
                    is_fine=True,
                )

            instance.session_id = session["id"]
            instance.session_url = session["url"]
            instance.status = "PENDING"
            instance.save()

        return instance
