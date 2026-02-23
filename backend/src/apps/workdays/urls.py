from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DaySummaryView,
    ExportSigningsView,
    ImportSigningsView,
    PeriodSummaryView,
    RangeSummaryView,
    SigningViewSet,
    WorkDayViewSet,
)

router = DefaultRouter()
router.register("workdays", WorkDayViewSet, basename="workday")
router.register("signings", SigningViewSet, basename="signing")

urlpatterns = [
    # Import/Export routes BEFORE router to avoid conflicts
    path("signings/import/", ImportSigningsView.as_view(), name="signing-import"),
    path("signings/export/", ExportSigningsView.as_view(), name="signing-export"),
    # Router routes
    path("", include(router.urls)),
    # Summary routes
    path("summary/day/", DaySummaryView.as_view(), name="day-summary-today"),
    path("summary/day/<str:day>/", DaySummaryView.as_view(), name="day-summary"),
    path("summary/period/", PeriodSummaryView.as_view(), name="period-summary"),
    path("summary/range/", RangeSummaryView.as_view(), name="range-summary"),
]
