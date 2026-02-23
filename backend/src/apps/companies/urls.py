from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BankHolidayViewSet, CompanyViewSet, LocationViewSet

router = DefaultRouter()
router.register("companies", CompanyViewSet)
router.register("locations", LocationViewSet)
router.register("bank-holidays", BankHolidayViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
