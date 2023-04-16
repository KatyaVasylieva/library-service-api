from typing import Any

import stripe
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from borrowings.models import Borrowing, Payment
from borrowings.scrapper import send_notification
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingCreateSerializer,
    BorrowingReturnSerializer,
    PaymentSerializer,
    PaymentRenewSerializer,
)


class BorrowingViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Borrowing.objects.select_related(
        "book", "user"
    ).prefetch_related(
        "payments"
    )
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "create":
            return BorrowingCreateSerializer

        if self.action == "return_book":
            return BorrowingReturnSerializer

        return BorrowingSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get("user_id")
        is_active = self.request.query_params.get("is_active")
        queryset = self.queryset.all()

        if self.request.user.is_superuser:
            if user_id:
                queryset = queryset.filter(user__id=user_id)

        if not self.request.user.is_superuser:
            queryset = queryset.filter(user=self.request.user)

        if is_active:
            queryset = queryset.filter(
                actual_return_date__isnull=eval(is_active)
            )

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="user_id",
                description="For admins - filter by user_id (ex. '?user_id=1)",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="is_active",
                description="Filter by active borrowings "
                            "(ex. ?is_active=True)",
                required=False,
                type=str,
            ),
        ],
    )
    def list(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        return super().list(self, request, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @action(
        methods=["POST"],
        detail=True,
        url_path="return",
    )
    def return_book(self, request, pk=None):
        """Endpoint for returning book and closing the specific borrowing"""
        borrowing = self.get_object()
        was_not_returned = borrowing.actual_return_date
        if was_not_returned is not None:
            return Response("This borrowing was already returned.", status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(borrowing, data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        methods=["GET"],
        detail=True,
        url_path="success",
    )
    def borrowing_is_successfully_paid(self, request, pk=None):
        """Success endpoint after paying for the borrowing"""
        borrowing = self.get_object()
        session_id = request.query_params.get("session_id")
        payment = Payment.objects.get(session_id=session_id)
        session = stripe.checkout.Session.retrieve(session_id)
        if session["payment_status"] == "paid":
            payment.status = "PAID"
            payment.save()
            send_notification(f"{payment} was paid.")
            serializer = self.get_serializer(borrowing)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(
            {"Fail": "Payment wasn't successful."},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        methods=["GET"],
        detail=True,
        url_path="cancel",
    )
    def borrowing_payment_is_cancelled(self, request, pk=None):
        """Cancel endpoint for borrowing payment"""
        borrowing = self.get_object()
        session_id = request.query_params.get("session_id")
        session = stripe.checkout.Session.retrieve(session_id)
        return Response(
            {
                "Cancel": f"The payment for the {borrowing} is cancelled. "
                          f"Make sure to pay during 24 hours. Payment url: "
                          f"{session.url}. Thanks!"
            },
            status=status.HTTP_200_OK,
        )


class PaymentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Payment.objects.select_related(
        "borrowing__book", "borrowing__user"
    ).prefetch_related("borrowing__payments")
    serializer_class = PaymentSerializer
    permission_classes = (IsAuthenticated,)

    def get_serializer_class(self):
        if self.action == "renew":
            return PaymentRenewSerializer

        return PaymentSerializer

    def get_queryset(self):
        queryset = self.queryset.all()

        if not self.request.user.is_superuser:
            queryset = queryset.filter(borrowing__user=self.request.user)

        return queryset

    @action(
        methods=["POST"],
        detail=True,
        url_path="renew",
    )
    def renew(self, request, pk=None):
        payment = self.get_object()
        old_session_id = payment.session_id
        serializer = self.get_serializer(payment, data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()
        payment.refresh_from_db()
        if payment.session_id == old_session_id:
            return Response(
                {
                    "The payment you want to update is not expired. "
                    "You can still make the payment following the session url."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "Payment session is successfully updated!"
            },
            status=status.HTTP_200_OK,
        )
