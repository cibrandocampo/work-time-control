from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DayTypeViewSet

router = DefaultRouter()
router.register("day-types", DayTypeViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
