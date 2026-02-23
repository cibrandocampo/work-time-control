from django.db import models


class DayType(models.Model):
    """Types of days: Working, Vacation, Sick, Holiday, Leave, Rest."""

    name = models.CharField(max_length=50, unique=True)
    requires_signing = models.BooleanField(
        default=True,
        help_text="Whether this day type requires time signing",
    )

    class Meta:
        db_table = "day_types"
        verbose_name = "Day Type"
        verbose_name_plural = "Day Types"

    def __str__(self):
        return self.name
