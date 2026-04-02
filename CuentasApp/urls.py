from django.urls import path
from django.contrib.auth import views as auth_views
from . import views # Vistas de Cuentas
from CitaApp import views as cita_views # Vistas de Citas
from Webapp import views as web_views # Vistas de Webapp

# CuentasApp/urls.py
urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('registro-base/', views.registro_view, name='registro_base'), # Cambio de nombre
    
    # ESTA ES LA LÍNEA CLAVE: Asegúrate de que el name sea 'registro'
    path('registro-paciente/', web_views.registro_integral_paciente, name='registro'),
    
    path('agenda-citas/', cita_views.lista_citas, name='lista_citas'),
]