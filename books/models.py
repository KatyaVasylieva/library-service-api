from django.core.validators import MinValueValidator
from django.db import models


class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = "HARD", "Hard"
        SOFT = "SOFT", "Soft"

    title = models.CharField(max_length=255, unique=True)
    author = models.CharField(max_length=63)
    cover = models.CharField(max_length=4, choices=Cover.choices)
    inventory = models.IntegerField(validators=[MinValueValidator(0)])
    daily_fee = models.DecimalField(max_digits=3, decimal_places=2)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title
