from django.contrib import admin
from django.urls import path, include

admin.site.site_header = "Work Time Control (WTC)"
admin.site.site_title = "Work Time Control"
admin.site.index_title = "WTC"

from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', include('workday.urls')),
    path('workday/', include('workday.urls')),
    path('user/', include('accounts.urls')),
    path('admin/', admin.site.urls),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
