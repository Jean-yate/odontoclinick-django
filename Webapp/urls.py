from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('panel-secretaria/', views.panel_secretaria, name='panel_secretaria'),
    path('pacientes/', views.lista_pacientes, name='lista_pacientes'),
    path('pacientes/editar/<int:id_usuario>/', views.editar_paciente, name='editar_paciente'),
    path('pacientes/detalle/<int:id_usuario>/', views.detalle_paciente, name='detalle_paciente'),
]