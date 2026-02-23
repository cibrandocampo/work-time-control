from django.db import models


class Company(models.Model):
    """Company/Organization."""

    name = models.CharField(max_length=200)
    external_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Company ID in external time manager system",
    )

    class Meta:
        db_table = "companies"
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name


class Location(models.Model):
    """Company location (office, branch, site)."""

    # Weekday constants (Python's weekday(): 0=Monday, 6=Sunday)
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

    WEEKDAY_CHOICES = [
        (MONDAY, "Monday"),
        (TUESDAY, "Tuesday"),
        (WEDNESDAY, "Wednesday"),
        (THURSDAY, "Thursday"),
        (FRIDAY, "Friday"),
        (SATURDAY, "Saturday"),
        (SUNDAY, "Sunday"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    name = models.CharField(max_length=100)

    # Work schedule defaults
    default_daily_hours = models.FloatField(
        default=8.0,
        help_text="Default expected working hours per day",
    )
    default_rest_days = models.JSONField(
        default=list,
        help_text="Days of the week that are rest days (0=Monday, 6=Sunday)",
    )

    # Address
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # Coordinates for geolocation (required)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)

    class Meta:
        db_table = "locations"
        verbose_name = "Location"
        verbose_name_plural = "Locations"

    def __str__(self):
        return f"{self.name} ({self.company.name})"

    def save(self, *args, **kwargs):
        if not self.default_rest_days:
            self.default_rest_days = [self.SATURDAY, self.SUNDAY]
        super().save(*args, **kwargs)


class BankHoliday(models.Model):
    """Bank holidays for a specific location."""

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="bank_holidays",
    )
    date = models.DateField()
    name = models.CharField(max_length=100)

    class Meta:
        db_table = "bank_holidays"
        verbose_name = "Bank Holiday"
        verbose_name_plural = "Bank Holidays"
        unique_together = ["location", "date"]

    def __str__(self):
        return f"{self.name} ({self.date})"
