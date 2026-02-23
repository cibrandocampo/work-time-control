from django.conf import settings
from django.db import models


class WorkDay(models.Model):
    """
    Daily record for a user at a specific location.
    Created automatically when a Signing is created, or manually for
    vacations, holidays, sick days, etc.
    """

    date = models.DateField()
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workdays",
    )
    location = models.ForeignKey(
        "companies.Location",
        on_delete=models.CASCADE,
        related_name="workdays",
    )
    day_type = models.ForeignKey(
        "core.DayType",
        on_delete=models.PROTECT,
        related_name="workdays",
    )
    expected_hours = models.FloatField(
        null=True,
        blank=True,
        help_text="Override default hours for this specific day",
    )
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "workdays"
        verbose_name = "Work Day"
        verbose_name_plural = "Work Days"
        unique_together = ["date", "employee", "location"]

    def __str__(self):
        return f"{self.employee} - {self.date} @ {self.location.name}"

    def get_expected_hours(self):
        """
        Return expected hours for this day.
        Priority: override > location default (if day requires signing) > 0
        """
        if self.expected_hours is not None:
            return self.expected_hours
        if self.day_type.requires_signing:
            return self.location.default_daily_hours
        return 0.0


class Signing(models.Model):
    """Time signing record (check-in/check-out)."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signings",
    )
    workday = models.ForeignKey(
        WorkDay,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signings",
    )

    # Time tracking
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    # Location where signing happened
    location = models.ForeignKey(
        "companies.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signings",
    )

    # Coordinates at signing time
    latitude_start = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude_start = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    latitude_end = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude_end = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Additional info
    description = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "signings"
        verbose_name = "Signing"
        verbose_name_plural = "Signings"
        ordering = ["start_time"]

    def __str__(self):
        return f"{self.employee} - {self.start_time.date()}"

    @property
    def duration(self):
        """Return duration in hours."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return delta.total_seconds() / 3600

    @property
    def duration_minutes(self):
        """Return duration in minutes."""
        if self.end_time is None:
            return None
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)
