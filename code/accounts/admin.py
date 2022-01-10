from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = CustomUser
    list_display = ['username', 'first_name', 'last_name', 'timezone']
    add_fieldsets = UserAdmin.add_fieldsets \
        + ((None, {'fields': ('email', 'first_name', 'last_name', 'laboral_hours', 'timezone')}),)
    fieldsets = UserAdmin.fieldsets + ((None, {'fields': ('laboral_hours', 'timezone',)}),)

admin.site.register(CustomUser, CustomUserAdmin)

