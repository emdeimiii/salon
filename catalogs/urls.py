from django.urls import path
from . import views

app_name = 'catalogs' 

urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services_list, name='services_list'),
    path("masters/", views.masters_list, name="masters_list"),
    path('appointment/create/', views.create_appointment, name='create_appointment'),
    path('appointment/success/', views.appointment_success, name='appointment_success'),
    path('profile/', views.profile, name='profile'),
    path('appointment/<int:pk>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('api/masters-by-service/', views.masters_by_service, name='masters_by_service'),

    path('master/dashboard/', views.master_dashboard, name='master_dashboard'),
    path('master/appointment/<int:pk>/status/', views.master_update_status, name='master_update_status'),
    path('salon/admin/', views.salon_admin_dashboard, name='salon_admin_dashboard'),
    
]
