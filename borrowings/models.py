from django.db import models
from django.db.models import DO_NOTHING, Q, F

from books.models import Book
from users.models import User


class Borrowing(models.Model):
    borrow_date = models.DateField()
    expected_return_date = models.DateField()
    actual_return_date = models.DateField()
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
