from django.urls import path, include
from rest_framework import routers

from borrowings.views import (
    BorrowingViewSet,
    PaymentViewSet,
)

router = routers.DefaultRouter()
router.register("borrowings", BorrowingViewSet)
router.register("payments", PaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "borrowings"
