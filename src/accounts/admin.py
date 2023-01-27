from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

from .models import Company, WorkLocation, CustomUser


class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description',)


admin.site.register(Company, CompanyAdmin)


class WorkLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'remote', 'longitude', 'latitude')
    search_fields = ('name', 'longitude', 'latitude')


admin.site.register(WorkLocation, WorkLocationAdmin)


class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = CustomUser
    list_display = ['username', 'first_name', 'last_name', 'timezone', 'default_company']
    add_fieldsets = UserAdmin.add_fieldsets \
        + ((None, {'fields': ('email', 'first_name', 'last_name', 'laboral_hours', 'timezone', 'companies', 'default_company', 'worklocations')}),)

    fieldsets = UserAdmin.fieldsets \
        + ((None, {'fields': ('timezone', 'laboral_hours', 'companies', 'default_company', 'worklocations')}),)


admin.site.register(CustomUser, CustomUserAdmin)