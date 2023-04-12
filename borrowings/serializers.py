from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from books.serializers import BookSerializer
from borrowings.models import Borrowing, Payment
from borrowings.stripe import create_stripe_session


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
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

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
            session = create_stripe_session(
                borrowing,
                self.context["request"].build_absolute_uri(),
                borrowing.borrow_date,
                borrowing.expected_return_date,
                is_fine=False,
            )
            Payment.objects.create(
                status="PENDING",
                type="PAYMENT",
                borrowing=borrowing,
                session_url=session["url"],
                session_id=session["id"],
                to_pay=Decimal(session["amount_total"] / 100),
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
