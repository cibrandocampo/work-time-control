from django import forms
from django.contrib import admin

from .models import BankHoliday, Company, Location


WEEKDAY_CHOICES = [
    (0, "Monday"),
    (1, "Tuesday"),
    (2, "Wednesday"),
    (3, "Thursday"),
    (4, "Friday"),
    (5, "Saturday"),
    (6, "Sunday"),
]


class RestDaysWidget(forms.CheckboxSelectMultiple):
    """Checkbox widget for selecting rest days."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, choices=WEEKDAY_CHOICES, **kwargs)


class LocationForm(forms.ModelForm):
    default_rest_days = forms.MultipleChoiceField(
        choices=WEEKDAY_CHOICES,
        widget=RestDaysWidget,
        required=False,
        help_text="Select the days that are rest days for this location",
    )

    class Meta:
        model = Location
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.default_rest_days:
            self.initial["default_rest_days"] = [
                str(d) for d in self.instance.default_rest_days
            ]

    def clean_default_rest_days(self):
        """Convert string values back to integers."""
        days = self.cleaned_data.get("default_rest_days", [])
        return [int(d) for d in days]


class LocationInline(admin.TabularInline):
    model = Location
    extra = 1
    fields = ["name", "default_daily_hours", "city", "country"]


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["name", "location_count"]
    search_fields = ["name"]
    inlines = [LocationInline]

    @admin.display(description="Locations")
    def location_count(self, obj):
        return obj.locations.count()


class BankHolidayInline(admin.TabularInline):
    model = BankHoliday
    extra = 1


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    form = LocationForm
    list_display = ["name", "company", "default_daily_hours", "rest_days_display", "city", "country"]
    list_filter = ["company", "country"]
    search_fields = ["name", "city", "address", "company__name"]
    inlines = [BankHolidayInline]

    fieldsets = [
        (None, {"fields": ["company", "name", ("latitude", "longitude")]}),
        ("Work Schedule", {"fields": ["default_daily_hours", "default_rest_days"]}),
        ("Address (optional)", {"fields": ["address", "city", "country"], "classes": ["collapse"]}),
    ]

    @admin.display(description="Rest Days")
    def rest_days_display(self, obj):
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        if not obj.default_rest_days:
            return "None"
        return ", ".join(day_names[d] for d in sorted(obj.default_rest_days))


@admin.register(BankHoliday)
class BankHolidayAdmin(admin.ModelAdmin):
    list_display = ["name", "date", "location"]
    list_filter = ["location", "date"]
    search_fields = ["name"]
    date_hierarchy = "date"
