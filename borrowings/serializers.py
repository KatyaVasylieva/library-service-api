from decimal import Decimal

from django.db import transaction
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

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date", "expected_return_date", "book")

    def create(self, validated_data):
        with transaction.atomic():
            borrowing = Borrowing.objects.create(**validated_data)
            session = create_stripe_session(
                borrowing,
                self.context["request"].build_absolute_uri(),
                borrowing.borrow_date,
                borrowing.expected_return_date,
                is_fine=False
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
