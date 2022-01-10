from django.contrib import admin
from .models import Signing


class SigningAdmin(admin.ModelAdmin):
    list_display = ('employee', 'start_date', 'end_date')
    search_fields = ('employee', 'start_date', 'end_date')


admin.site.register(Signing, SigningAdmin)
