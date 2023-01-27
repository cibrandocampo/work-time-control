from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import CustomUser, Company


class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = CustomUser
    list_display = ['username', 'first_name', 'last_name', 'timezone', 'default_company']
    add_fieldsets = UserAdmin.add_fieldsets \
        + ((None, {'fields': ('email', 'first_name', 'last_name', 'laboral_hours', 'timezone', 'companies', 'default_company')}),)

    fieldsets = UserAdmin.fieldsets \
        + ((None, {'fields': ('timezone', 'laboral_hours', 'companies', 'default_company')}),)


admin.site.register(CustomUser, CustomUserAdmin)


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description',)


admin.site.register(Company, CompanyAdmin)
