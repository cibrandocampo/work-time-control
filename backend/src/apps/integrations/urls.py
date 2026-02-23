from django.urls import path

from .views import SyncView

urlpatterns = [
    path("integrations/sync/", SyncView.as_view(), name="integration-sync"),
]
