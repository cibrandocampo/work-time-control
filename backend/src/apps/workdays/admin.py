from django import forms
from django.contrib import admin
from django.urls import path
from django.http import JsonResponse

from apps.core.models import DayType

from .models import Signing, WorkDay


class WorkDayForm(forms.ModelForm):
    class Meta:
        model = WorkDay
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default day_type to "Working"
        if not self.instance.pk:
            try:
                working = DayType.objects.get(name="Working")
                self.fields["day_type"].initial = working
            except DayType.DoesNotExist:
                pass


@admin.register(WorkDay)
class WorkDayAdmin(admin.ModelAdmin):
    form = WorkDayForm
    list_display = ["date", "employee", "location", "day_type", "expected_hours_display", "note"]
    list_filter = ["day_type", "date", "location__company", "employee"]
    search_fields = ["employee__username", "location__name", "note"]
    date_hierarchy = "date"
    autocomplete_fields = ["employee", "location"]

    class Media:
        js = ("workdays/admin/workday_form.js",)

    @admin.display(description="Expected Hours")
    def expected_hours_display(self, obj):
        return obj.get_expected_hours()

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "get-location-hours/<int:location_id>/",
                self.admin_site.admin_view(self.get_location_hours),
                name="workday-get-location-hours",
            ),
        ]
        return custom_urls + urls

    def get_location_hours(self, request, location_id):
        """API endpoint to get default hours for a location."""
        from apps.companies.models import Location

        try:
            location = Location.objects.get(pk=location_id)
            return JsonResponse({"hours": location.default_daily_hours})
        except Location.DoesNotExist:
            return JsonResponse({"hours": 8.0})


@admin.register(Signing)
class SigningAdmin(admin.ModelAdmin):
    list_display = [
        "employee",
        "date",
        "start_time_display",
        "end_time_display",
        "duration_display",
        "location",
    ]
    list_filter = ["location", "employee"]
    search_fields = ["employee__username", "description"]
    date_hierarchy = "start_time"
    autocomplete_fields = ["employee", "workday", "location"]

    fieldsets = [
        (None, {"fields": ["employee", "workday", "location"]}),
        ("Time", {"fields": ["start_time", "end_time"]}),
        (
            "Coordinates",
            {
                "fields": [
                    ("latitude_start", "longitude_start"),
                    ("latitude_end", "longitude_end"),
                ],
                "classes": ["collapse"],
            },
        ),
        ("Details", {"fields": ["description"]}),
    ]

    @admin.display(description="Date")
    def date(self, obj):
        return obj.start_time.date()

    @admin.display(description="Start")
    def start_time_display(self, obj):
        return obj.start_time.strftime("%H:%M")

    @admin.display(description="End")
    def end_time_display(self, obj):
        return obj.end_time.strftime("%H:%M") if obj.end_time else "-"

    @admin.display(description="Duration")
    def duration_display(self, obj):
        if obj.duration_minutes is None:
            return "Active"
        hours, mins = divmod(obj.duration_minutes, 60)
        return f"{hours}h {mins}m"
