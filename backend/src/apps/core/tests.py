"""Tests for core models."""
import pytest
from django.db import IntegrityError

from apps.core.models import DayType


@pytest.mark.django_db
class TestDayType:
    """Tests for the DayType model."""

    def test_create_day_type(self):
        """Can create a day type with required fields."""
        day_type = DayType.objects.create(
            name="Working",
            requires_signing=True
        )
        assert day_type.name == "Working"
        assert day_type.requires_signing is True

    def test_default_requires_signing_is_true(self):
        """requires_signing defaults to True."""
        day_type = DayType.objects.create(name="Test")
        assert day_type.requires_signing is True

    def test_name_is_unique(self, working_day_type):
        """Day type names must be unique."""
        with pytest.raises(IntegrityError):
            DayType.objects.create(name="Working")

    def test_str_representation(self):
        """String representation is the name."""
        day_type = DayType.objects.create(name="Holiday")
        assert str(day_type) == "Holiday"

    def test_vacation_day_type(self, vacation_day_type):
        """Vacation day type does not require signing."""
        assert vacation_day_type.name == "Vacation"
        assert vacation_day_type.requires_signing is False
