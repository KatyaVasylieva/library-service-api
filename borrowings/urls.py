from rest_framework import routers

from borrowings.views import (
    BorrowingViewSet,
    PaymentViewSet,
)

router = routers.DefaultRouter()
router.register("borrowings", BorrowingViewSet)
router.register("payments", PaymentViewSet)

urlpatterns = router.urls

app_name = "borrowings"
