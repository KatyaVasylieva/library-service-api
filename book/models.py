from django.db import models


class Book(models.Model):
    class Cover(models.TextChoices):
        HARD = "HARD", "Hard"
        SOFT = "SOFT", "Soft"

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=63)
    cover = models.CharField(max_length=4, choices=Cover.choices)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=3, decimal_places=2)