from django.contrib import admin

from .models import DayType


@admin.register(DayType)
class DayTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "requires_signing"]
    list_filter = ["requires_signing"]
