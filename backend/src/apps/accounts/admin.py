from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["username", "email", "first_name", "last_name", "locations_display", "is_staff"]
    list_filter = ["is_staff", "is_superuser", "is_active", "locations"]
    search_fields = ["username", "first_name", "last_name", "email"]
    filter_horizontal = ["locations", "groups", "user_permissions"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Work Locations", {"fields": ["locations"]}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Work Locations", {"fields": ["locations"]}),
    )

    @admin.display(description="Locations")
    def locations_display(self, obj):
        locations = obj.locations.all()[:3]
        names = [loc.name for loc in locations]
        if obj.locations.count() > 3:
            names.append("...")
        return ", ".join(names) if names else "-"
