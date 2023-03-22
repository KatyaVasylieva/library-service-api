from django.db import models


class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = "HARD", "Hard"
        SOFT = "SOFT", "Soft"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=63)
    cover = models.CharField(
        max_length=2,
        choices=Cover.choices,
    )
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(decimal_places=2)
