from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model for WTC."""

    locations = models.ManyToManyField(
        "companies.Location",
        blank=True,
        related_name="users",
    )
    external_user_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="User ID in external time manager system",
    )

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"
