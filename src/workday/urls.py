from django.urls import path

from . import views

urlpatterns = [
    path('', views.signing, name='signing'),
    path('signing/', views.signing, name='signing'),
    path('worklocation/', views.get_worklocation, name='get_worklocation'),
    path('summary/', views.summary, name='summary'),
    path('export/', views.export_signings, name='export_signings'),
]
