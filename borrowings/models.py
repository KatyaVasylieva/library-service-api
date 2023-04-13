from django.db import models
from django.db.models import DO_NOTHING, Q, F
from django.utils.translation import gettext_lazy as _

from books.models import Book
from users.models import User


class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(blank=True, null=True)
    book = models.ForeignKey(
        Book, on_delete=DO_NOTHING, related_name="borrowings"
    )
    user = models.ForeignKey(
        User, on_delete=DO_NOTHING, related_name="borrowings"
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                name="borrow_date_before_return_date",
                check=(
                    Q(borrow_date__lte=F("expected_return_date"))
                    & Q(borrow_date__lte=F("actual_return_date"))
                ),
            )
        ]

    def __str__(self):
        return (
            f"Borrowing of {self.book.title} by {self.user.email} "
            f"for {self.borrow_date} - {self.expected_return_date}"
        )


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PAID = "PAID", _("Paid")
        EXPIRED = "EXPIRED", _("Expired")

    class Type(models.TextChoices):
        PAYMENT = "PAYMENT", _("Payment")
        FINE = "FINE", _("Fine")

    status = models.CharField(max_length=7, choices=Status.choices)
    type = models.CharField(max_length=7, choices=Type.choices)
    borrowing = models.ForeignKey(
        Borrowing, on_delete=models.DO_NOTHING, related_name="payments"
    )
    session_url = models.CharField(max_length=500, null=True, blank=True)
    session_id = models.CharField(max_length=500, null=True, blank=True)
    to_pay = models.DecimalField(decimal_places=2, max_digits=4)

    def __str__(self):
        return (
            f"{self.status}: {self.get_type_display()} of {self.to_pay} "
            f"dollars for the {self.borrowing}"
        )
