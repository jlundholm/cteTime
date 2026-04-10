from django.urls import path
from . import views

urlpatterns = [
    path('', views.clock_view, name='clock'),
    path('success/<str:code>/', views.clock_success, name='clock_success'),
    path('lookup/', views.clock_lookup, name='clock_lookup'),
]
